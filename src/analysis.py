# src/analysis.py - Enhanced with Claude AI integration
import pandas as pd
import numpy as np
from utils import load_transactions, load_refunds, load_payouts, load_product_master
from ai_assistant import CashFlowAIAssistant

# Load data once at module import
transactions = load_transactions()
refunds = load_refunds()
payouts = load_payouts()
products = load_product_master()

# Initialize Claude AI assistant
ai_assistant = CashFlowAIAssistant()

# Merge product info (COGS)
tx = transactions.merge(products[["product_id", "cogs"]], on="product_id", how="left")
tx["unit_margin"] = tx["unit_price"] - tx["cogs"]
tx["gross_profit"] = tx["quantity"] * tx["unit_margin"] - tx["discount"]
tx["day"] = pd.to_datetime(tx["date"]).dt.date

def executive_snapshot():
    """Return a simple HTML executive snapshot."""
    card_sales = float(tx.loc[tx["payment_type"] == "CARD", "line_total"].sum())
    cash_sales = float(tx.loc[tx["payment_type"] == "CASH", "line_total"].sum())

    html = f"""
    <h3>Executive Dashboard ({tx['day'].min()} → {tx['day'].max()})</h3>
    
    <h4>Key Metrics</h4>
    <ul>
      <li>Transactions: <b>{int(tx['transaction_id'].nunique())}</b></li>
      <li>Items sold: <b>{int(tx['quantity'].sum())}</b></li>
      <li>Gross sales: <b>€{float(tx['gross_sales'].sum()):,.2f}</b></li>
      <li>Discounts: <b>€{float(tx['discount'].sum()):,.2f}</b></li>
      <li>Tax collected: <b>€{float(tx['tax'].sum()):,.2f}</b></li>
      <li>Tips collected: <b>€{float(tx['tip_amount'].sum()):,.2f}</b></li>
      <li>Card sales: <b>€{card_sales:,.2f}</b></li>
      <li>Cash sales: <b>€{cash_sales:,.2f}</b></li>
      <li>Processor fees: <b>€{float(payouts['processor_fees'].sum()):,.2f}</b></li>
      <li>Refunds processed: <b>€{float(refunds['refund_amount'].sum()):,.2f}</b></li>
      <li>Net card payouts: <b>€{float(payouts['net_payout_amount'].sum()):,.2f}</b></li>
    </ul>
    """
    return html

def cash_eaters_with_ai():
    """Show where cash is leaking + AI analysis"""
    ce = pd.DataFrame([
        {"category": "Discounts", "amount": float(tx["discount"].sum())},
        {"category": "Refunds", "amount": float(refunds["refund_amount"].sum())},
        {"category": "Processor fees", "amount": float(payouts["processor_fees"].sum())},
    ]).sort_values("amount", ascending=False)

    sku = tx.groupby(["product_id", "product_name"], as_index=False) \
        .agg(revenue=("net_sales", "sum"), gp=("gross_profit", "sum"))
    sku["margin_pct"] = np.where(sku["revenue"] > 0, sku["gp"] / sku["revenue"], 0.0)
    low = sku.sort_values(["margin_pct", "revenue"]).head(5)

    # Prepare data for AI analysis
    business_context = ai_assistant._prepare_business_context(tx, refunds, payouts, products)
    cash_eaters_data = {
        'discounts': float(tx["discount"].sum()),
        'refunds': float(refunds["refund_amount"].sum()),
        'processor_fees': float(payouts["processor_fees"].sum()),
        'low_margin_products': low.to_string()
    }
    
    # Get AI analysis
    ai_analysis = ai_assistant.analyze_cash_eaters(business_context, cash_eaters_data)

    return executive_snapshot(), ce, low, ai_analysis

def reorder_plan_with_ai(budget=500.0):
    """Suggest what to reorder with AI analysis"""
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
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "unit_cogs": round(cogs, 2),
                "suggested_qty": buy_units,
                "budget_spend": round(buy_units * cogs, 2),
                "est_gp_uplift_week": round(buy_units * (row["gp"] / max(1, row["qty"])), 2)
            })
            remaining -= buy_units * cogs
        if remaining < sku_rank["cogs"].min():
            break

    plan_df = pd.DataFrame(plan)
    msg = f"Budget: €{budget:.0f} → Remaining: €{remaining:.2f}"
    
    # Prepare data for AI analysis
    business_context = ai_assistant._prepare_business_context(tx, refunds, payouts, products)
    reorder_data = {
        'purchase_plan': plan_df.to_string() if not plan_df.empty else 'No recommendations within budget',
        'remaining_budget': remaining
    }
    
    # Get AI analysis
    ai_analysis = ai_assistant.analyze_reorder_plan(business_context, reorder_data, budget)
    
    return executive_snapshot(), msg, plan_df, ai_analysis

def free_up_cash_with_ai():
    """Estimate extra cash with AI analysis"""
    days = (tx["day"].max() - tx["day"].min()).days + 1
    sku_daily = tx.groupby(["product_id", "product_name"], as_index=False).agg(qty=("quantity", "sum"))
    sku_daily["qty_per_day"] = sku_daily["qty"] / days
    slow = sku_daily.sort_values("qty_per_day").head(max(1, int(0.2 * len(sku_daily))))

    price_lookup = tx.groupby("product_id", as_index=False)["unit_price"].median().rename(columns={"unit_price": "price"})
    slow = slow.merge(price_lookup, on="product_id", how="left")
    slow["discount_rate"] = 0.20
    slow["assumed_lift"] = 1.5
    slow["extra_units"] = (slow["qty_per_day"] * 7 * (slow["assumed_lift"] - 1)).round(0)
    slow["discounted_price"] = (slow["price"] * (1 - slow["discount_rate"])).round(2)
    slow["extra_cash_inflow"] = (slow["extra_units"] * slow["discounted_price"]).round(2)

    total = float(slow["extra_cash_inflow"].sum())
    msg = f"Estimated extra cash this week from clearance: €{total:.2f}"
    
    # Prepare data for AI analysis
    business_context = ai_assistant._prepare_business_context(tx, refunds, payouts, products)
    clearance_data = {
        'total_extra_cash': total,
        'slow_movers': slow.to_string()
    }
    
    # Get AI analysis
    ai_analysis = ai_assistant.analyze_cash_liberation(business_context, clearance_data)
    
    return executive_snapshot(), msg, slow, ai_analysis

def sales_impact_analysis_with_ai(sales_drop_percent=10):
    """Analyze impact of sales drop with AI"""
    business_context = ai_assistant._prepare_business_context(tx, refunds, payouts, products)
    ai_analysis = ai_assistant.analyze_sales_impact(business_context, sales_drop_percent)
    
    return executive_snapshot(), ai_analysis

# Backward compatibility - keep original functions
def cash_eaters():
    snap, ce, low, _ = cash_eaters_with_ai()
    return snap, ce, low

def reorder_plan(budget=500.0):
    snap, msg, plan, _ = reorder_plan_with_ai(budget)
    return snap, msg, plan

def free_up_cash():
    snap, msg, slow, _ = free_up_cash_with_ai()
    return snap, msg, slow