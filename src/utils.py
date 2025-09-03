# src/utils.py - This is the file for loading data

import pandas as pd
from pathlib import Path
from typing import Optional, Dict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Minimal required columns for POC
DEFAULT_SCHEMAS = {
    "tx": ["date","transaction_id","product_id","product_name","category","quantity","unit_price",
           "gross_sales","discount","net_sales","tax","line_total","payment_type","tip_amount"],
    "rf": ["original_transaction_id","refund_date","refund_amount"],
    "po": ["covering_sales_date","gross_card_volume","processor_fees","net_payout_amount","payout_date"],
    "pm": ["product_id","product_name","category","cogs"]
}

def _read_csv(path_or_fp) -> pd.DataFrame:
    return pd.read_csv(path_or_fp)

def load_transactions():
    return _read_csv(DATA_DIR / "pos_transactions_week.csv")

def load_refunds():
    return _read_csv(DATA_DIR / "pos_refunds_week.csv")

def load_payouts():
    return _read_csv(DATA_DIR / "pos_payouts_week.csv")

def load_product_master():
    return _read_csv(DATA_DIR / "product_master.csv")

def load_csv_from_uploads(tx_u, rf_u, po_u, pm_u) -> Dict[str, pd.DataFrame]:
    dfs = {}
    if tx_u: dfs["tx"] = _read_csv(tx_u.name if hasattr(tx_u, "name") else tx_u)
    if rf_u: dfs["rf"] = _read_csv(rf_u.name if hasattr(rf_u, "name") else rf_u)
    if po_u: dfs["po"] = _read_csv(po_u.name if hasattr(po_u, "name") else po_u)
    if pm_u: dfs["pm"] = _read_csv(pmu.name if hasattr(pm_u, "name") else pm_u)
    return dfs

def validate_schema_or_raise(kind: str, df: pd.DataFrame, required_columns):
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(f"{kind}: missing required columns: {missing}")

def persist_uploads_to_data_dir(dfs: Dict[str, pd.DataFrame]):
    mapping = {
        "tx": DATA_DIR / "pos_transactions_week.csv",
        "rf": DATA_DIR / "pos_refunds_week.csv",
        "po": DATA_DIR / "pos_payouts_week.csv",
        "pm": DATA_DIR / "product_master.csv",
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for key, df in dfs.items():
        df.to_csv(mapping[key], index=False)
