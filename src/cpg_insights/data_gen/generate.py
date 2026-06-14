"""
Mock data generator for CPG sales insights.

Produces three datasets in data/raw/:
  - product_master.csv          (clean reference, slow-changing dimension)
  - store_regions.csv           (clean reference)
  - transactions_pos.csv        (store register feed — Source 1)
  - transactions_ecom.json      (e-commerce feed — Source 2, different schema)

Quality issues are deliberately injected so the pipeline has real work to do:
  - Nulls in key fields (~2-3%)
  - Mixed date formats across sources
  - Duplicate transaction IDs (simulating retry/at-least-once delivery)
  - Negative quantities (unfiltered returns)
  - Unknown SKUs not in the product master
  - Late-arriving records (timestamps out of chronological order)
  - Price as string with currency symbols in the ecom feed
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from cpg_insights.data_gen.products import PRODUCTS
from cpg_insights.data_gen.stores import STORES

SEED = 42
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)
N_TRANSACTIONS = 50_000
RAW_DIR = Path("data/raw")

# Category-level seasonal multipliers by month (1 = baseline)
SEASONAL = {
    "Beverages":     [0.8, 0.8, 0.9, 1.0, 1.1, 1.3, 1.4, 1.3, 1.0, 0.9, 1.0, 1.1],
    "Snacks":        [0.9, 0.9, 1.0, 1.0, 1.0, 1.0, 1.1, 1.1, 1.0, 1.1, 1.3, 1.5],
    "Personal Care": [1.0, 1.0, 1.1, 1.1, 1.2, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    "Household":     [1.1, 1.0, 1.2, 1.0, 1.0, 1.0, 0.9, 0.9, 1.0, 1.0, 1.1, 1.2],
    "Dairy":         [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.2],
}

# Region-level baseline revenue weight
REGION_WEIGHT = {
    "North": 1.3,
    "South": 1.2,
    "East": 0.9,
    "West": 1.4,
    "Central": 0.8,
}


def _random_date(rng: random.Random, start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, delta))


def _seasonal_weight(category: str, d: date) -> float:
    return SEASONAL[category][d.month - 1]


def _region_of(store_id: str, store_map: dict) -> str:
    return store_map[store_id]["region"]


def _build_transaction_pool(rng: random.Random) -> list[dict]:
    """Generate the clean core transaction pool before quality issues are injected."""
    sku_map = {p["sku_id"]: p for p in PRODUCTS}
    store_map = {s["store_id"]: s for s in STORES}
    store_ids = list(store_map.keys())
    sku_ids = list(sku_map.keys())

    total_days = (END_DATE - START_DATE).days
    records = []

    for i in range(N_TRANSACTIONS):
        txn_date = START_DATE + timedelta(days=rng.randint(0, total_days))
        store_id = rng.choices(
            store_ids,
            weights=[REGION_WEIGHT[store_map[s]["region"]] for s in store_ids],
        )[0]
        region = _region_of(store_id, store_map)

        # Weight SKU selection by seasonal demand for the category
        sku_weights = [
            _seasonal_weight(sku_map[s]["category"], txn_date) *
            REGION_WEIGHT[region]
            for s in sku_ids
        ]
        sku_id = rng.choices(sku_ids, weights=sku_weights)[0]
        product = sku_map[sku_id]

        qty = rng.randint(1, 6)
        unit_price = round(product["list_price"] * rng.uniform(0.9, 1.1), 2)
        total = round(qty * unit_price, 2)

        records.append({
            "txn_id": f"TXN{i:07d}",
            "txn_date": txn_date,
            "store_id": store_id,
            "sku_id": sku_id,
            "quantity": qty,
            "unit_price": unit_price,
            "total_amount": total,
            "category": product["category"],
        })

    return records


def _inject_quality_issues(
    records: list[dict], rng: random.Random
) -> tuple[list[dict], list[dict]]:
    """
    Split records into two source feeds and inject realistic quality issues.
    Returns (pos_records, ecom_records).
    """
    rng.shuffle(records)
    split = int(len(records) * 0.65)
    pos_raw = records[:split]
    ecom_raw = records[split:]

    # ── POS feed issues ───────────────────────────────────────────────────────
    pos_records = []
    for r in pos_raw:
        rec = {
            "transaction_id": r["txn_id"],
            "date": r["txn_date"].strftime("%Y-%m-%d"),  # ISO format
            "store_id": r["store_id"],
            "sku": r["sku_id"],
            "qty": r["quantity"],
            "unit_price": r["unit_price"],
            "total": r["total_amount"],
        }

        # Null store_id (~2%)
        if rng.random() < 0.02:
            rec["store_id"] = None

        # Null sku (~1.5%)
        if rng.random() < 0.015:
            rec["sku"] = None

        # Negative quantity — unfiltered return (~1%)
        if rng.random() < 0.01:
            rec["qty"] = -abs(rec["qty"])
            rec["total"] = round(rec["qty"] * rec["unit_price"], 2)

        # Unknown SKU not in product master (~0.5%)
        if rng.random() < 0.005:
            rec["sku"] = f"UNKNOWN_{rng.randint(100, 999)}"

        # Null / blank transaction_id (~0.3%) — broken upstream key
        if rng.random() < 0.003:
            rec["transaction_id"] = None

        # Unparseable date (~0.4%) — corrupted timestamp
        if rng.random() < 0.004:
            rec["date"] = rng.choice(["not-a-date", "00/00/0000", "2024-13-45"])

        pos_records.append(rec)

    # Duplicate ~2% of records (retry/at-least-once delivery)
    n_dupes = int(len(pos_records) * 0.02)
    dupes = rng.sample(pos_records, n_dupes)
    pos_records.extend(dupes)
    rng.shuffle(pos_records)

    # Late-arriving records: redate ~1% to simulate out-of-order delivery.
    # Skip records that already carry an injected null id or corrupted date.
    n_late = int(len(pos_records) * 0.01)
    for rec in rng.sample(pos_records, n_late):
        if rec["transaction_id"] is None:
            continue
        try:
            base = date.fromisoformat(rec["date"])
        except (ValueError, TypeError):
            continue  # corrupted date — leave it for the validate stage to catch
        d = base + timedelta(days=rng.randint(1, 10))
        if d > END_DATE:
            d = END_DATE  # clamp to keep within the dataset window
        rec["date"] = d.strftime("%Y-%m-%d")
        rec["transaction_id"] = rec["transaction_id"] + "_LATE"

    # ── Ecom feed issues — different schema + format ──────────────────────────
    ecom_records = []
    for r in ecom_raw:
        # Mixed date formats: DD/MM/YYYY
        fmt = rng.choice(["dmy_slash", "mdy_dash", "iso"])
        d = r["txn_date"]
        if fmt == "dmy_slash":
            date_str = d.strftime("%d/%m/%Y")
        elif fmt == "mdy_dash":
            date_str = d.strftime("%m-%d-%Y")
        else:
            date_str = d.strftime("%Y-%m-%d")

        # Price as currency string (~30% of rows)
        if rng.random() < 0.3:
            price_str = f"${r['unit_price']:.2f}"
        else:
            price_str = str(r["unit_price"])

        rec = {
            "order_id": r["txn_id"].replace("TXN", "ECM"),
            "order_date": date_str,
            "product_code": r["sku_id"],  # different column name
            "quantity": r["quantity"],
            "price_each": price_str,       # different column name, sometimes with $
            "amount": r["total_amount"],
            "channel": rng.choice(["web", "app", "marketplace"]),
            "store_ref": r["store_id"],    # different column name
        }

        # Null product_code (~2%)
        if rng.random() < 0.02:
            rec["product_code"] = None

        # Null store_ref (~3%) — ecom orders sometimes lack store mapping
        if rng.random() < 0.03:
            rec["store_ref"] = None

        # Zero-quantity ghost records (~0.5%) — cancelled orders not cleaned
        if rng.random() < 0.005:
            rec["quantity"] = 0
            rec["amount"] = 0.0

        # Invalid price string (~1%) — placeholder value never cleaned
        if rng.random() < 0.01:
            rec["price_each"] = rng.choice(["N/A", "TBD", ""])

        # Zero price (~0.5%) — pricing error / freebie not flagged
        if rng.random() < 0.005:
            rec["price_each"] = "0.00"

        # Out-of-range date (~0.3%) — year typo outside the 2020→today window
        if rng.random() < 0.003:
            rec["order_date"] = rng.choice(["1999-05-20", "2030-08-15"])

        ecom_records.append(rec)

    return pos_records, ecom_records


def generate(seed: int = SEED, out_dir: Path = RAW_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    print("Generating product master...")
    pd.DataFrame(PRODUCTS).to_csv(out_dir / "product_master.csv", index=False)

    print("Generating store regions...")
    pd.DataFrame(STORES).to_csv(out_dir / "store_regions.csv", index=False)

    print(f"Generating {N_TRANSACTIONS:,} transactions...")
    records = _build_transaction_pool(rng)
    pos_records, ecom_records = _inject_quality_issues(records, rng)

    print(f"  POS feed:  {len(pos_records):,} rows → transactions_pos.csv")
    pd.DataFrame(pos_records).to_csv(out_dir / "transactions_pos.csv", index=False)

    print(f"  Ecom feed: {len(ecom_records):,} rows → transactions_ecom.json")
    with open(out_dir / "transactions_ecom.json", "w") as f:
        json.dump(ecom_records, f, default=str, indent=2)

    print("Done. Raw data written to", out_dir)
    _print_quality_summary(pos_records, ecom_records)


def _print_quality_summary(pos: list[dict], ecom: list[dict]) -> None:
    print("\n── Quality issues injected ──────────────────────────────────────")
    null_store = sum(1 for r in pos if r.get("store_id") is None)
    null_sku = sum(1 for r in pos if r.get("sku") is None)
    null_txn = sum(1 for r in pos if r.get("transaction_id") is None)
    neg_qty = sum(1 for r in pos if isinstance(r.get("qty"), (int, float)) and r["qty"] < 0)
    unknown_sku = sum(
        1 for r in pos if isinstance(r.get("sku"), str) and r["sku"].startswith("UNKNOWN")
    )
    bad_dates = sum(
        1 for r in pos
        if str(r.get("date", "")) in ("not-a-date", "00/00/0000", "2024-13-45")
    )
    dupes = len(pos) - len(set(
        r["transaction_id"].replace("_LATE", "")
        for r in pos if r.get("transaction_id") is not None
    ))
    print(f"  POS  — null txn_id: {null_txn}, null store_id: {null_store}, null sku: {null_sku}, "
          f"negative qty: {neg_qty}, unknown sku: {unknown_sku}, "
          f"invalid dates: {bad_dates}, duplicates: ~{dupes}")
    null_prod = sum(1 for r in ecom if r.get("product_code") is None)
    zero_qty = sum(1 for r in ecom if r.get("quantity") == 0)
    mixed_dates = sum(1 for r in ecom if "/" in str(r.get("order_date", "")))
    currency_str = sum(1 for r in ecom if "$" in str(r.get("price_each", "")))
    invalid_price = sum(1 for r in ecom if str(r.get("price_each", "")) in ("N/A", "TBD", ""))
    zero_price = sum(1 for r in ecom if str(r.get("price_each", "")) == "0.00")
    oor_dates = sum(1 for r in ecom if str(r.get("order_date", "")) in ("1999-05-20", "2030-08-15"))
    print(f"  Ecom — null product_code: {null_prod}, zero qty: {zero_qty}, "
          f"mixed date formats: {mixed_dates}, price with $: {currency_str}, "
          f"invalid price: {invalid_price}, zero price: {zero_price}, "
          f"out-of-range dates: {oor_dates}")
    print("─────────────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    generate()
