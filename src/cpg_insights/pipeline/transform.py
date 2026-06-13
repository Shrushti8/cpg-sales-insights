"""
Transform stage — normalises data types and formats.

Handles the realistic mess from two different source feeds:
  - Mixed date formats (ISO, DD/MM/YYYY, MM-DD-YYYY)
  - Price strings with $ prefix  e.g. "$3.99"
  - Numeric columns stored as strings (everything was read as str in extract)
"""

from datetime import datetime

import pandas as pd

_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y"]


def _parse_date(val: str) -> datetime | None:
    if pd.isna(val):
        return None
    val = str(val).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _parse_price(val: str) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["txn_date"] = df["txn_date"].apply(_parse_date)
    df["unit_price"] = df["unit_price"].apply(_parse_price)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")

    # Recalculate total_amount from qty * unit_price where total looks wrong or missing
    mask = df["total_amount"].isna() & df["quantity"].notna() & df["unit_price"].notna()
    df.loc[mask, "total_amount"] = df.loc[mask, "quantity"] * df.loc[mask, "unit_price"]

    df["transaction_id"] = df["transaction_id"].str.strip()
    df["sku_id"] = df["sku_id"].str.strip()
    df["store_id"] = df["store_id"].str.strip()
    df["channel"] = df["channel"].str.strip().str.lower()

    return df
