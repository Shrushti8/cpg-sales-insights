"""
Validate stage — applies rule-based checks and quarantines bad rows.

Each rule is a named function returning a boolean Series (True = invalid).
Bad rows are removed from the clean set, tagged with the reason that first
caught them, and returned as rejected_df for quarantine storage.
The quality report records counts per rule — surfaced in the API and UI.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

# Date formats accepted by the pipeline (same list as transform.py)
_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y"]

# Reasonable date range for CPG transactions
_MIN_DATE = date(2020, 1, 1)


def _try_parse_date(val: str) -> date | None:
    if pd.isna(val):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _try_parse_price(val: str) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


@dataclass
class QualityReport:
    source: str
    rows_extracted: int = 0
    rows_valid: int = 0
    rows_rejected: int = 0
    rejection_rules: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Source: {self.source}",
            f"  Extracted : {self.rows_extracted:,}",
            f"  Valid     : {self.rows_valid:,}",
            f"  Rejected  : {self.rows_rejected:,}",
        ]
        for rule, count in self.rejection_rules.items():
            lines.append(f"    [{rule}] {count:,} rows")
        return "\n".join(lines)


# ── Validation rules ──────────────────────────────────────────────────────────
# Convention: each returns a boolean Series; True = this row is INVALID.
# Rules are applied in order; a row is tagged with the FIRST rule that catches it.

def _rule_null_transaction_id(df: pd.DataFrame, **_) -> pd.Series:
    return df["transaction_id"].isna() | (df["transaction_id"].str.strip() == "")


def _rule_null_sku(df: pd.DataFrame, **_) -> pd.Series:
    return df["sku_id"].isna() | (df["sku_id"].str.strip() == "")


def _rule_null_store(df: pd.DataFrame, **_) -> pd.Series:
    return df["store_id"].isna() | (df["store_id"].str.strip() == "")


def _rule_negative_quantity(df: pd.DataFrame, **_) -> pd.Series:
    return pd.to_numeric(df["quantity"], errors="coerce") < 0


def _rule_zero_quantity(df: pd.DataFrame, **_) -> pd.Series:
    return pd.to_numeric(df["quantity"], errors="coerce") == 0


def _rule_unknown_sku(df: pd.DataFrame, valid_skus: set[str], **_) -> pd.Series:
    return df["sku_id"].notna() & ~df["sku_id"].isin(valid_skus)


def _rule_invalid_price(df: pd.DataFrame, **_) -> pd.Series:
    """Price column cannot be parsed to a number (e.g. 'N/A', 'TBD', empty)."""
    return df["unit_price"].apply(_try_parse_price).isna()


def _rule_zero_price(df: pd.DataFrame, **_) -> pd.Series:
    """Price is exactly zero — revenue would be £0, corrupting forecasts."""
    parsed = df["unit_price"].apply(_try_parse_price)
    qty = pd.to_numeric(df["quantity"], errors="coerce")
    return (parsed == 0.0) & (qty > 0)


def _rule_invalid_date(df: pd.DataFrame, **_) -> pd.Series:
    """Date cannot be parsed to any known format."""
    return df["txn_date"].apply(_try_parse_date).isna()


def _rule_date_out_of_range(df: pd.DataFrame, **_) -> pd.Series:
    """Date is parseable but outside the sensible 2020-01-01 → today+30 days window."""
    from datetime import timedelta
    max_date = date.today() + timedelta(days=30)

    def _out_of_range(val: str) -> bool:
        d = _try_parse_date(val)
        if d is None:
            return False  # already caught by invalid_date
        return d < _MIN_DATE or d > max_date

    return df["txn_date"].apply(_out_of_range)


# Ordered list — a row is tagged with the FIRST rule that catches it.
# Put structural nulls first (useless without an ID), then content rules.
RULES: list[tuple[str, callable]] = [
    ("null_transaction_id", _rule_null_transaction_id),
    ("null_sku",            _rule_null_sku),
    ("null_store",          _rule_null_store),
    ("invalid_date",        _rule_invalid_date),
    ("date_out_of_range",   _rule_date_out_of_range),
    ("invalid_price",       _rule_invalid_price),
    ("negative_quantity",   _rule_negative_quantity),
    ("zero_quantity",       _rule_zero_quantity),
    ("zero_price",          _rule_zero_price),
    ("unknown_sku",         _rule_unknown_sku),
]


def validate(
    df: pd.DataFrame,
    valid_skus: set[str],
    source_name: str = "combined",
) -> tuple[pd.DataFrame, pd.DataFrame, QualityReport]:
    """
    Returns (clean_df, rejected_df, report).

    rejected_df has an extra column `rejection_reason` naming the first rule
    that caught each row — stored in the quarantine table for manual review.
    """
    report = QualityReport(source=source_name, rows_extracted=len(df))

    # Track which rows are rejected and why (first rule wins)
    rejected_mask = pd.Series(False, index=df.index)
    rejection_reasons = pd.Series("", index=df.index, dtype=str)

    for rule_name, rule_fn in RULES:
        bad = rule_fn(df, valid_skus=valid_skus)
        newly_caught = bad & ~rejected_mask
        count = int(newly_caught.sum())
        if count:
            report.rejection_rules[rule_name] = count
            rejection_reasons[newly_caught] = rule_name
        rejected_mask = rejected_mask | bad

    clean_df = df[~rejected_mask].copy()
    rejected_df = df[rejected_mask].copy()
    rejected_df["rejection_reason"] = rejection_reasons[rejected_mask]

    report.rows_valid = len(clean_df)
    report.rows_rejected = len(rejected_df)

    return clean_df, rejected_df, report
