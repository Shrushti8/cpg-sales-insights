"""Unit tests for the mock data generator."""

import json

import pandas as pd
import pytest

from cpg_insights.data_gen.generate import generate
from cpg_insights.data_gen.products import PRODUCTS


@pytest.fixture(scope="module")
def generated_data(tmp_path_factory):
    out = tmp_path_factory.mktemp("raw")
    generate(seed=42, out_dir=out)
    return out


def test_product_master_columns(generated_data):
    df = pd.read_csv(generated_data / "product_master.csv")
    required = {"sku_id", "name", "category", "brand", "list_price", "launch_date"}
    assert required.issubset(df.columns)


def test_product_master_row_count(generated_data):
    df = pd.read_csv(generated_data / "product_master.csv")
    assert len(df) == len(PRODUCTS)


def test_store_regions_columns(generated_data):
    df = pd.read_csv(generated_data / "store_regions.csv")
    required = {"store_id", "region", "city", "segment"}
    assert required.issubset(df.columns)


def test_five_categories_present(generated_data):
    df = pd.read_csv(generated_data / "product_master.csv")
    expected = {"Beverages", "Snacks", "Personal Care", "Household", "Dairy"}
    assert set(df["category"].unique()) == expected


def test_five_regions_present(generated_data):
    df = pd.read_csv(generated_data / "store_regions.csv")
    assert set(df["region"].unique()) == {"North", "South", "East", "West", "Central"}


def test_pos_feed_has_expected_columns(generated_data):
    df = pd.read_csv(generated_data / "transactions_pos.csv")
    required = {"transaction_id", "date", "store_id", "sku", "qty", "unit_price", "total"}
    assert required.issubset(df.columns)


def test_pos_feed_row_count(generated_data):
    df = pd.read_csv(generated_data / "transactions_pos.csv")
    # ~65% of 50k + ~2% dupes ≈ 33k+
    assert 30_000 < len(df) < 40_000


def test_ecom_feed_different_schema(generated_data):
    rows = json.loads((generated_data / "transactions_ecom.json").read_text())
    assert len(rows) > 0
    first = rows[0]
    # ecom uses different column names than POS
    assert "order_id" in first
    assert "product_code" in first
    assert "price_each" in first
    assert "transaction_id" not in first  # POS column should NOT appear
    assert "sku" not in first


def test_pos_has_null_store_ids(generated_data):
    df = pd.read_csv(generated_data / "transactions_pos.csv")
    assert df["store_id"].isna().sum() > 0, "Expected some null store_ids (quality issue)"


def test_pos_has_null_skus(generated_data):
    df = pd.read_csv(generated_data / "transactions_pos.csv")
    assert df["sku"].isna().sum() > 0, "Expected some null skus (quality issue)"


def test_pos_has_negative_quantities(generated_data):
    df = pd.read_csv(generated_data / "transactions_pos.csv")
    assert (df["qty"] < 0).sum() > 0, "Expected negative quantities (unfiltered returns)"


def test_pos_has_unknown_skus(generated_data):
    df = pd.read_csv(generated_data / "transactions_pos.csv")
    unknowns = df["sku"].dropna().str.startswith("UNKNOWN").sum()
    assert unknowns > 0, "Expected some UNKNOWN_xxx SKUs"


def test_pos_has_duplicate_transaction_ids(generated_data):
    df = pd.read_csv(generated_data / "transactions_pos.csv")
    base_ids = df["transaction_id"].str.replace("_LATE", "", regex=False)
    assert base_ids.duplicated().sum() > 0, "Expected duplicate transaction IDs"


def test_ecom_has_mixed_date_formats(generated_data):
    rows = json.loads((generated_data / "transactions_ecom.json").read_text())
    dates = [r["order_date"] for r in rows]
    has_slash = any("/" in d for d in dates)
    has_dash = any("-" in d for d in dates)
    assert has_slash and has_dash, "Expected mixed date formats in ecom feed"


def test_ecom_has_currency_string_prices(generated_data):
    rows = json.loads((generated_data / "transactions_ecom.json").read_text())
    currency_rows = [r for r in rows if "$" in str(r.get("price_each", ""))]
    assert len(currency_rows) > 0, "Expected some prices with $ prefix in ecom feed"


def test_generator_is_deterministic(tmp_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    generate(seed=42, out_dir=out1)
    generate(seed=42, out_dir=out2)
    df1 = pd.read_csv(out1 / "transactions_pos.csv")
    df2 = pd.read_csv(out2 / "transactions_pos.csv")
    pd.testing.assert_frame_equal(df1, df2)
