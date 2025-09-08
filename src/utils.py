# src/utils.py - Upload-only data loading (no default sample data)

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
    """Read CSV and clean up any unnamed columns"""
    df = pd.read_csv(path_or_fp)
    # Remove any 'Unnamed: X' columns that might come from Excel exports
    unnamed_cols = [col for col in df.columns if 'Unnamed:' in str(col)]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    return df

def load_transactions():
    """Load transactions from uploaded data only"""
    file_path = DATA_DIR / "pos_transactions_week.csv"
    if not file_path.exists():
        raise FileNotFoundError("No transaction data uploaded. Please upload a transactions CSV file.")
    return _read_csv(file_path)

def load_refunds():
    """Load refunds from uploaded data only"""
    file_path = DATA_DIR / "pos_refunds_week.csv"
    if not file_path.exists():
        raise FileNotFoundError("No refunds data uploaded. Please upload a refunds CSV file.")
    return _read_csv(file_path)

def load_payouts():
    """Load payouts from uploaded data only"""
    file_path = DATA_DIR / "pos_payouts_week.csv"
    if not file_path.exists():
        raise FileNotFoundError("No payouts data uploaded. Please upload a payouts CSV file.")
    return _read_csv(file_path)

def load_product_master():
    """Load product master from uploaded data only"""
    file_path = DATA_DIR / "product_master.csv"
    if not file_path.exists():
        raise FileNotFoundError("No product master data uploaded. Please upload a product master CSV file.")
    return _read_csv(file_path)

def load_csv_from_uploads(tx_u, rf_u, po_u, pm_u) -> Dict[str, pd.DataFrame]:
    """Load DataFrames from uploaded files"""
    dfs = {}
    if tx_u: 
        dfs["tx"] = _read_csv(tx_u.name if hasattr(tx_u, "name") else tx_u)
        print(f"✅ Loaded transactions: {len(dfs['tx'])} rows")
    if rf_u: 
        dfs["rf"] = _read_csv(rf_u.name if hasattr(rf_u, "name") else rf_u)
        print(f"✅ Loaded refunds: {len(dfs['rf'])} rows")
    if po_u: 
        dfs["po"] = _read_csv(po_u.name if hasattr(po_u, "name") else po_u)
        print(f"✅ Loaded payouts: {len(dfs['po'])} rows")
    if pm_u: 
        dfs["pm"] = _read_csv(pm_u.name if hasattr(pm_u, "name") else pm_u)
        print(f"✅ Loaded product master: {len(dfs['pm'])} rows")
    return dfs

def validate_schema_or_raise(kind: str, df: pd.DataFrame, required_columns):
    """Validate that uploaded CSV has required columns"""
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        available_cols = list(df.columns)
        raise ValueError(f"{kind} CSV validation failed.\nMissing required columns: {missing}\nAvailable columns: {available_cols}")

def persist_uploads_to_data_dir(dfs: Dict[str, pd.DataFrame]):
    """Save uploaded DataFrames to data directory"""
    mapping = {
        "tx": DATA_DIR / "pos_transactions_week.csv",
        "rf": DATA_DIR / "pos_refunds_week.csv",
        "po": DATA_DIR / "pos_payouts_week.csv",
        "pm": DATA_DIR / "product_master.csv",
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    for key, df in dfs.items():
        file_path = mapping[key]
        df.to_csv(file_path, index=False)
        print(f"💾 Saved {key} to {file_path}")

def clear_data_directory():
    """Clear all data files to force fresh uploads"""
    files_to_clear = [
        "pos_transactions_week.csv",
        "pos_refunds_week.csv", 
        "pos_payouts_week.csv",
        "product_master.csv"
    ]
    
    cleared_count = 0
    for filename in files_to_clear:
        file_path = DATA_DIR / filename
        if file_path.exists():
            file_path.unlink()
            cleared_count += 1
            print(f"🗑️  Cleared {filename}")
    
    if cleared_count > 0:
        print(f"✅ Cleared {cleared_count} data files. Upload fresh CSV files to continue.")
    else:
        print("ℹ️  No data files to clear.")

def check_data_status():
    """Check what data files are currently available"""
    files_to_check = {
        "pos_transactions_week.csv": "Transactions",
        "pos_refunds_week.csv": "Refunds", 
        "pos_payouts_week.csv": "Payouts",
        "product_master.csv": "Product Master"
    }
    
    status = {}
    for filename, description in files_to_check.items():
        file_path = DATA_DIR / filename
        if file_path.exists():
            try:
                df = _read_csv(file_path)
                status[description] = f"✅ {len(df)} rows"
            except Exception as e:
                status[description] = f"❌ Error: {str(e)}"
        else:
            status[description] = "❌ Not uploaded"
    
    return status