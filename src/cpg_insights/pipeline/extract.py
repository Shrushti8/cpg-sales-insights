"""
Extract stage — reads raw source files and maps them to a unified schema.

Two sources, two completely different shapes:
  - transactions_pos.csv   (store register feed)
  - transactions_ecom.json (e-commerce feed)

After extraction both return a DataFrame with the same columns so the
rest of the pipeline is source-agnostic.
"""

from pathlib import Path

import pandas as pd

# Unified column names every downstream stage expects
UNIFIED_COLS = [
    "transaction_id",
    "txn_date",
    "store_id",
    "sku_id",
    "quantity",
    "unit_price",
    "total_amount",
    "source",
    "channel",
]

# POS column → unified column
_POS_RENAME = {
    "transaction_id": "transaction_id",
    "date": "txn_date",
    "store_id": "store_id",
    "sku": "sku_id",
    "qty": "quantity",
    "unit_price": "unit_price",
    "total": "total_amount",
}

# Ecom column → unified column
_ECOM_RENAME = {
    "order_id": "transaction_id",
    "order_date": "txn_date",
    "store_ref": "store_id",
    "product_code": "sku_id",
    "quantity": "quantity",
    "price_each": "unit_price",
    "amount": "total_amount",
    "channel": "channel",
}


def extract_pos(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df = df.rename(columns=_POS_RENAME)
    df["source"] = "pos"
    df["channel"] = "store"
    return df[UNIFIED_COLS]


def extract_ecom(path: Path) -> pd.DataFrame:
    df = pd.read_json(path, dtype=str)
    df = df.rename(columns=_ECOM_RENAME)
    df["source"] = "ecom"
    # channel already present in ecom; fill missing with 'unknown'
    df["channel"] = df["channel"].fillna("unknown")
    return df[UNIFIED_COLS]


def extract_all(raw_dir: Path) -> pd.DataFrame:
    pos = extract_pos(raw_dir / "transactions_pos.csv")
    ecom = extract_ecom(raw_dir / "transactions_ecom.json")
    combined = pd.concat([pos, ecom], ignore_index=True)
    return combined
