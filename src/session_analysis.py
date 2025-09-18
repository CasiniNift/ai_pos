# src/session_analysis.py - Session-based analysis for concurrent users

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import uuid
import threading
from datetime import datetime

# Thread-safe session storage
_session_lock = threading.Lock()
_session_data: Dict[str, Dict] = {}

class SessionManager:
    """Manages per-session data for concurrent users"""
    
    @staticmethod
    def create_session() -> str:
        """Create a new session ID"""
        session_id = str(uuid.uuid4())
        with _session_lock:
            _session_data[session_id] = {
                'transactions': None,
                'refunds': None,
                'payouts': None,
                'products': None,
                'created_at': datetime.now(),
                'last_accessed': datetime.now()
            }
        return session_id
    
    @staticmethod
    def get_session_data(session_id: str) -> Optional[Dict]:
        """Get data for a specific session"""
        with _session_lock:
            if session_id in _session_data:
                _session_data[session_id]['last_accessed'] = datetime.now()
                return _session_data[session_id].copy()
        return None
    
    @staticmethod
    def set_session_data(session_id: str, data_type: str, data: pd.DataFrame):
        """Set data for a specific session"""
        with _session_lock:
            if session_id in _session_data:
                _session_data[session_id][data_type] = data
                _session_data[session_id]['last_accessed'] = datetime.now()
    
    @staticmethod
    def clear_session(session_id: str):
        """Clear a specific session"""
        with _session_lock:
            if session_id in _session_data:
                del _session_data[session_id]
    
    @staticmethod
    def cleanup_old_sessions(max_age_hours: int = 24):
        """Clean up sessions older than max_age_hours"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        with _session_lock:
            to_delete = [
                sid for sid, data in _session_data.items()
                if data['last_accessed'].timestamp() < cutoff
            ]
            for sid in to_delete:
                del _session_data[sid]
        return len(to_delete)

class SessionAnalyzer:
    """Session-based analysis functions"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_manager = SessionManager()
    
    def _get_current_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Get current session data or raise error"""
        session_data = self.session_manager.get_session_data(self.session_id)
        if not session_data:
            raise ValueError("Session not found. Please refresh and upload data again.")
        
        tx = session_data.get('transactions')
        rf = session_data.get('refunds') 
        po = session_data.get('payouts')
        pm = session_data.get('products')
        
        if any(data is None for data in [tx, rf, po, pm]):
            missing = [name for name, data in [
                ('transactions', tx), ('refunds', rf), 
                ('payouts', po), ('products', pm)
            ] if data is None]
            raise ValueError(f"Missing data: {', '.join(missing)}. Please upload all CSV files.")
        
        return tx, rf, po, pm
    
    def set_data(self, transactions=None, refunds=None, payouts=None, products=None):
        """Set data for this session"""
        if transactions is not None:
            self.session_manager.set_session_data(self.session_id, 'transactions', transactions)
        if refunds is not None:
            self.session_manager.set_session_data(self.session_id, 'refunds', refunds)
        if payouts is not None:
            self.session_manager.set_session_data(self.session_id, 'payouts', payouts)
        if products is not None:
            self.session_manager.set_session_data(self.session_id, 'products', products)
    
    def get_processed_data(self):
        """Get processed transaction data with margins"""
        transactions, refunds, payouts, products = self._get_current_data()
        
        # Merge product info (COGS)
        tx = transactions.merge(products[["product_id", "cogs"]], on="product_id", how="left")
        tx["unit_margin"] = tx["unit_price"] - tx["cogs"]
        tx["gross_profit"] = tx["quantity"] * tx["unit_margin"] - tx["discount"]
        tx["day"] = pd.to_datetime(tx["date"]).dt.date
        
        return tx, refunds, payouts
    
    def executive_snapshot(self):
        """Return executive snapshot for this session"""
        try:
            tx, refunds, payouts = self.get_processed_data()
        except ValueError as e:
            return f"""
            <div class='status-error'>
            <h3>⚠️ No Data Available</h3>
            <p>{str(e)}</p>
            </div>
            """
        
        card_sales = float(tx.loc[tx["payment_type"] == "CARD", "line_total"].sum())
        cash_sales = float(tx.loc[tx["payment_type"] == "CASH", "line_total"].sum())

        return f"""
        <h3>📊 Snapshot ({tx['day'].min()} → {tx['day'].max()})</h3>
        <ul>
          <li>Transactions: <b>{int(tx['transaction_id'].nunique())}</b></li>
          <li>Items sold: <b>{int(tx['quantity'].sum())}</b></li>
          <li>Gross sales: <b>€{float(tx['gross_sales'].sum()):,.2f}</b></li>
          <li>Discounts: <b>€{float(tx['discount'].sum()):,.2f}</b></li>
          <li>Card sales: <b>€{card_sales:,.2f}</b></li>
          <li>Cash sales: <b>€{cash_sales:,.2f}</b></li>
          <li>Processor fees: <b>€{float(payouts['processor_fees'].sum()):,.2f}</b></li>
          <li>Refunds: <b>€{float(refunds['refund_amount'].sum()):,.2f}</b></li>
        </ul>
        """
    
    def cash_eaters(self, ui_language="English"):
        """Session-based cash eaters analysis"""
        try:
            tx, refunds, payouts = self.get_processed_data()
        except ValueError as e:
            error_msg = f"<div class='status-error'>Error: {str(e)}</div>"
            return error_msg, None, None, error_msg
        
        ce = pd.DataFrame([
            {"category": "Discounts", "amount": float(tx["discount"].sum())},
            {"category": "Refunds", "amount": float(refunds["refund_amount"].sum())},
            {"category": "Processor fees", "amount": float(payouts["processor_fees"].sum())},
        ]).sort_values("amount", ascending=False)

        sku = tx.groupby(["product_id", "product_name"], as_index=False) \
            .agg(revenue=("net_sales", "sum"), gp=("gross_profit", "sum"))
        sku["margin_pct"] = np.where(sku["revenue"] > 0, sku["gp"] / sku["revenue"], 0.0)
        low = sku.sort_values(["margin_pct", "revenue"]).head(5)

        # Simplified AI insights for pilots
        ai_insights = f"""
        <div class='ai-insights'>
        <h4>🤖 AI Analysis</h4>
        <p><strong>Biggest cash drain:</strong> {ce.iloc[0]['category']} (€{ce.iloc[0]['amount']:.2f})</p>
        <p><strong>Quick win:</strong> Review {low.iloc[0]['product_name']} pricing - only {low.iloc[0]['margin_pct']:.1%} margin</p>
        <p><strong>Action:</strong> Focus on reducing {ce.iloc[0]['category'].lower()} to improve cash flow</p>
        </div>
        """
        
        return self.executive_snapshot(), ce, low, ai_insights
    
    def reorder_plan(self, budget=500.0, ui_language="English"):
        """Session-based reorder planning"""
        try:
            tx, refunds, payouts = self.get_processed_data()
        except ValueError as e:
            error_msg = f"<div class='status-error'>Error: {str(e)}</div>"
            return error_msg, f"Error: {str(e)}", None, error_msg
        
        days = (tx["day"].max() - tx["day"].min()).days + 1
        sku_daily = tx.groupby(["product_id", "product_name", "cogs"], as_index=False).agg(
            qty=("quantity", "sum"),
            gp=("gross_profit", "sum")
        )
        sku_daily["qty_per_day"] = sku_daily["qty"] / days
        sku_daily["gp_per_day"] = sku_daily["gp"] / days
        sku_rank = sku_daily.sort_values(["gp_per_day", "qty_per_day"], ascending=False)

        remaining = float(budget)
        plan = []
        
        for _, row in sku_rank.iterrows():
            cogs = float(row["cogs"])
            if cogs <= 0:
                continue
            target_units = max(1, int(np.ceil(row["qty_per_day"] * 5)))
            max_units_by_budget = int(remaining // cogs)
            buy_units = max(0, min(target_units, max_units_by_budget))
            if buy_units > 0:
                plan.append({
                    "product_name": row["product_name"],
                    "suggested_qty": buy_units,
                    "budget_spend": round(buy_units * cogs, 2),
                    "est_weekly_profit": round(buy_units * (row["gp"] / max(1, row["qty"])), 2)
                })
                remaining -= buy_units * cogs
            if remaining < sku_rank["cogs"].min():
                break

        plan_df = pd.DataFrame(plan)
        msg = f"Budget: €{budget:.0f} → Remaining: €{remaining:.2f}"
        
        ai_insights = f"""
        <div class='ai-insights'>
        <h4>🤖 Purchase Recommendations</h4>
        <p><strong>Top priority:</strong> {plan[0]['product_name'] if plan else 'None'}</p>
        <p><strong>Budget utilization:</strong> {((budget - remaining) / budget * 100):.1f}%</p>
        <p><strong>Expected weekly profit boost:</strong> €{sum(p['est_weekly_profit'] for p in plan):.2f}</p>
        </div>
        """
        
        return self.executive_snapshot(), msg, plan_df, ai_insights

# Usage example for Gradio app
def create_session_based_app():
    """Create session-based Gradio app"""
    
    def create_new_session():
        return SessionManager.create_session()
    
    def analyze_with_session(session_id, question, budget, language, tx_file, rf_file, po_file, pm_file):
        """Run analysis with session isolation"""
        
        # Create analyzer for this session
        analyzer = SessionAnalyzer(session_id)
        
        # Load data if files provided
        if any([tx_file, rf_file, po_file, pm_file]):
            # Load CSVs and set data
            dfs = load_csv_from_uploads(tx_file, rf_file, po_file, pm_file)
            if dfs:
                analyzer.set_data(
                    transactions=dfs.get("tx"),
                    refunds=dfs.get("rf"),
                    payouts=dfs.get("po"),
                    products=dfs.get("pm")
                )
        
        # Run analysis
        if question == "What's eating my cash flow?":
            return analyzer.cash_eaters(language)
        elif question == "What should I reorder with budget?":
            return analyzer.reorder_plan(budget, language)
        else:
            return analyzer.executive_snapshot(), None, None, ""
    
    return create_new_session, analyze_with_session