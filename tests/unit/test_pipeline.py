"""Unit tests for each pipeline stage in isolation."""

import json

import pandas as pd
import pytest

from cpg_insights.pipeline.dedupe import dedupe
from cpg_insights.pipeline.extract import UNIFIED_COLS, extract_ecom, extract_pos
from cpg_insights.pipeline.transform import transform
from cpg_insights.pipeline.validate import validate

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def pos_file(tmp_path):
    df = pd.DataFrame([
        {"transaction_id": "T001", "date": "2024-01-15", "store_id": "N001",
         "sku": "BEV001", "qty": 2, "unit_price": 1.50, "total": 3.00},
        {"transaction_id": "T002", "date": "2024-02-10", "store_id": "S001",
         "sku": "SNK001", "qty": 1, "unit_price": 2.99, "total": 2.99},
    ])
    path = tmp_path / "transactions_pos.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture()
def ecom_file(tmp_path):
    rows = [
        {"order_id": "E001", "order_date": "15/03/2024", "store_ref": "W001",
         "product_code": "BEV002", "quantity": 3, "price_each": "$3.20", "amount": 9.60,
         "channel": "web"},
        {"order_id": "E002", "order_date": "2024-04-20", "store_ref": "N002",
         "product_code": "DAI001", "quantity": 2, "price_each": "1.89", "amount": 3.78,
         "channel": "app"},
    ]
    path = tmp_path / "transactions_ecom.json"
    path.write_text(json.dumps(rows))
    return path


@pytest.fixture()
def clean_df():
    return pd.DataFrame([
        {"transaction_id": "T001", "txn_date": "2024-01-15", "store_id": "N001",
         "sku_id": "BEV001", "quantity": "2", "unit_price": "1.50",
         "total_amount": "3.00", "source": "pos", "channel": "store"},
        {"transaction_id": "T002", "txn_date": "2024-02-10", "store_id": "S001",
         "sku_id": "SNK001", "quantity": "1", "unit_price": "2.99",
         "total_amount": "2.99", "source": "pos", "channel": "store"},
    ])


# ── Extract tests ─────────────────────────────────────────────────────────────

def test_extract_pos_returns_unified_columns(pos_file):
    df = extract_pos(pos_file)
    assert list(df.columns) == UNIFIED_COLS


def test_extract_pos_sets_source_as_pos(pos_file):
    df = extract_pos(pos_file)
    assert (df["source"] == "pos").all()


def test_extract_ecom_returns_unified_columns(ecom_file):
    df = extract_ecom(ecom_file)
    assert list(df.columns) == UNIFIED_COLS


def test_extract_ecom_sets_source_as_ecom(ecom_file):
    df = extract_ecom(ecom_file)
    assert (df["source"] == "ecom").all()


def test_extract_ecom_maps_order_id_to_transaction_id(ecom_file):
    df = extract_ecom(ecom_file)
    assert "E001" in df["transaction_id"].values


def test_extract_ecom_maps_product_code_to_sku_id(ecom_file):
    df = extract_ecom(ecom_file)
    assert "BEV002" in df["sku_id"].values


# ── Validate tests ────────────────────────────────────────────────────────────

def test_validate_passes_clean_rows(clean_df):
    valid_skus = {"BEV001", "SNK001"}
    clean, rejected, report = validate(clean_df, valid_skus)
    assert len(clean) == 2
    assert len(rejected) == 0


def test_validate_rejects_null_sku(clean_df):
    clean_df.loc[0, "sku_id"] = None
    clean, rejected, report = validate(clean_df, {"SNK001"})
    assert len(rejected) == 1
    assert "null_sku" in report.rejection_rules


def test_validate_rejects_null_store(clean_df):
    clean_df.loc[0, "store_id"] = None
    clean, rejected, report = validate(clean_df, {"BEV001", "SNK001"})
    assert "null_store" in report.rejection_rules


def test_validate_rejects_negative_quantity(clean_df):
    clean_df.loc[0, "quantity"] = "-3"
    clean, rejected, report = validate(clean_df, {"BEV001", "SNK001"})
    assert "negative_quantity" in report.rejection_rules


def test_validate_rejects_zero_quantity(clean_df):
    clean_df.loc[0, "quantity"] = "0"
    clean, rejected, report = validate(clean_df, {"BEV001", "SNK001"})
    assert "zero_quantity" in report.rejection_rules


def test_validate_rejects_unknown_sku(clean_df):
    clean_df.loc[0, "sku_id"] = "UNKNOWN_999"
    clean, rejected, report = validate(clean_df, {"SNK001"})
    assert "unknown_sku" in report.rejection_rules


def test_validate_report_counts_match(clean_df):
    valid_skus = {"BEV001", "SNK001"}
    clean, rejected, report = validate(clean_df, valid_skus)
    assert report.rows_extracted == 2
    assert report.rows_valid + report.rows_rejected == report.rows_extracted


def test_validate_rejected_df_has_rejection_reason(clean_df):
    clean_df.loc[0, "sku_id"] = None
    _, rejected, _ = validate(clean_df, {"SNK001"})
    assert "rejection_reason" in rejected.columns
    assert rejected.iloc[0]["rejection_reason"] == "null_sku"


def test_validate_rejects_invalid_price(clean_df):
    clean_df.loc[0, "unit_price"] = "N/A"
    _, _, report = validate(clean_df, {"BEV001", "SNK001"})
    assert "invalid_price" in report.rejection_rules


def test_validate_rejects_zero_price(clean_df):
    clean_df.loc[0, "unit_price"] = "0.0"
    _, _, report = validate(clean_df, {"BEV001", "SNK001"})
    assert "zero_price" in report.rejection_rules


def test_validate_rejects_invalid_date(clean_df):
    clean_df.loc[0, "txn_date"] = "not-a-date"
    _, _, report = validate(clean_df, {"BEV001", "SNK001"})
    assert "invalid_date" in report.rejection_rules


def test_validate_rejects_date_before_2020(clean_df):
    clean_df.loc[0, "txn_date"] = "2019-12-31"
    _, _, report = validate(clean_df, {"BEV001", "SNK001"})
    assert "date_out_of_range" in report.rejection_rules


def test_validate_first_rule_wins(clean_df):
    """A row with both null_sku AND invalid_price is tagged with null_sku (comes first)."""
    clean_df.loc[0, "sku_id"] = None
    clean_df.loc[0, "unit_price"] = "N/A"
    _, rejected, report = validate(clean_df, {"SNK001"})
    assert rejected.iloc[0]["rejection_reason"] == "null_sku"
    assert "invalid_price" not in report.rejection_rules


# ── Transform tests ───────────────────────────────────────────────────────────

def test_transform_parses_iso_date(clean_df):
    clean_df = transform(clean_df)
    from datetime import date
    assert clean_df.iloc[0]["txn_date"] == date(2024, 1, 15)


def test_transform_parses_dmy_date():
    df = pd.DataFrame([{
        "transaction_id": "T1", "txn_date": "15/03/2024", "store_id": "S1",
        "sku_id": "X", "quantity": "1", "unit_price": "1.0",
        "total_amount": "1.0", "source": "ecom", "channel": "web",
    }])
    result = transform(df)
    from datetime import date
    assert result.iloc[0]["txn_date"] == date(2024, 3, 15)


def test_transform_strips_dollar_sign():
    df = pd.DataFrame([{
        "transaction_id": "T1", "txn_date": "2024-01-01", "store_id": "S1",
        "sku_id": "X", "quantity": "2", "unit_price": "$3.99",
        "total_amount": "7.98", "source": "ecom", "channel": "web",
    }])
    result = transform(df)
    assert result.iloc[0]["unit_price"] == pytest.approx(3.99)


def test_transform_casts_quantity_to_integer(clean_df):
    result = transform(clean_df)
    assert result["quantity"].dtype.name in ("Int64", "int64")


# ── Dedupe tests ──────────────────────────────────────────────────────────────

def test_dedupe_removes_exact_duplicates():
    df = pd.DataFrame([
        {"transaction_id": "T001", "txn_date": None, "store_id": None,
         "sku_id": None, "quantity": None, "unit_price": None,
         "total_amount": None, "source": "pos", "channel": "store"},
        {"transaction_id": "T001", "txn_date": None, "store_id": None,
         "sku_id": None, "quantity": None, "unit_price": None,
         "total_amount": None, "source": "pos", "channel": "store"},
        {"transaction_id": "T002", "txn_date": None, "store_id": None,
         "sku_id": None, "quantity": None, "unit_price": None,
         "total_amount": None, "source": "pos", "channel": "store"},
    ])
    result, n_removed = dedupe(df)
    assert len(result) == 2
    assert n_removed == 1


def test_dedupe_keeps_first_occurrence():
    df = pd.DataFrame([
        {"transaction_id": "T001", "txn_date": "2024-01-01", "store_id": "A",
         "sku_id": None, "quantity": None, "unit_price": None,
         "total_amount": None, "source": "pos", "channel": "store"},
        {"transaction_id": "T001", "txn_date": "2024-01-02", "store_id": "B",
         "sku_id": None, "quantity": None, "unit_price": None,
         "total_amount": None, "source": "pos", "channel": "store"},
    ])
    result, _ = dedupe(df)
    assert result.iloc[0]["store_id"] == "A"


def test_dedupe_no_duplicates_unchanged():
    df = pd.DataFrame([
        {"transaction_id": "T001", "txn_date": None, "store_id": None,
         "sku_id": None, "quantity": None, "unit_price": None,
         "total_amount": None, "source": "pos", "channel": "store"},
        {"transaction_id": "T002", "txn_date": None, "store_id": None,
         "sku_id": None, "quantity": None, "unit_price": None,
         "total_amount": None, "source": "pos", "channel": "store"},
    ])
    result, n_removed = dedupe(df)
    assert len(result) == 2
    assert n_removed == 0
