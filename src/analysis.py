# src/analysis.py - Business logic with multilingual support
import pandas as pd
import numpy as np
from utils import load_transactions, load_refunds, load_payouts, load_product_master
import os
import sys

# Get language from command line argument or environment
CURRENT_LANGUAGE = 'en'
if len(sys.argv) > 1:
    lang_arg = sys.argv[1].lower()
    if lang_arg in ['en', 'it', 'es']:
        CURRENT_LANGUAGE = lang_arg

# Translation dictionaries
TRANSLATIONS = {
    'en': {
        'snapshot_title': 'Snapshot',
        'transactions': 'Transactions',
        'items_sold': 'Items sold',
        'gross_sales': 'Gross sales',
        'discounts': 'Discounts',
        'tax_collected': 'Tax collected',
        'tips_collected': 'Tips collected',
        'card_sales': 'Card sales',
        'cash_sales': 'Cash sales',
        'processor_fees': 'Processor fees',
        'refunds_processed': 'Refunds processed',
        'net_card_payouts': 'Net card payouts',
        'ai_analysis': 'AI Analysis',
    },
    'it': {
        'snapshot_title': 'Panoramica',
        'transactions': 'Transazioni',
        'items_sold': 'Articoli venduti',
        'gross_sales': 'Vendite lorde',
        'discounts': 'Sconti',
        'tax_collected': 'Tasse raccolte',
        'tips_collected': 'Mance raccolte',
        'card_sales': 'Vendite con carta',
        'cash_sales': 'Vendite in contanti',
        'processor_fees': 'Commissioni elaborazione',
        'refunds_processed': 'Rimborsi elaborati',
        'net_card_payouts': 'Incassi netti carta',
        'ai_analysis': 'Analisi IA',
    },
    'es': {
        'snapshot_title': 'Resumen',
        'transactions': 'Transacciones',
        'items_sold': 'Artículos vendidos',
        'gross_sales': 'Ventas brutas',
        'discounts': 'Descuentos',
        'tax_collected': 'Impuestos recaudados',
        'tips_collected': 'Propinas recaudadas',
        'card_sales': 'Ventas con tarjeta',
        'cash_sales': 'Ventas en efectivo',
        'processor_fees': 'Comisiones procesamiento',
        'refunds_processed': 'Reembolsos procesados',
        'net_card_payouts': 'Pagos netos tarjeta',
        'ai_analysis': 'Análisis IA',
    }
}

def get_text(key):
    """Get translated text for current language"""
    return TRANSLATIONS.get(CURRENT_LANGUAGE, TRANSLATIONS['en']).get(key, key)

# Global variables to hold current data
_current_transactions = None
_current_refunds = None
_current_payouts = None
_current_products = None

def get_current_data():
    """Get current data, loading defaults if none set"""
    global _current_transactions, _current_refunds, _current_payouts, _current_products
    
    if _current_transactions is None:
        _current_transactions = load_transactions()
        _current_refunds = load_refunds()
        _current_payouts = load_payouts()
        _current_products = load_product_master()
    
    return _current_transactions, _current_refunds, _current_payouts, _current_products

def set_data(transactions=None, refunds=None, payouts=None, products=None):
    """Set new data from uploads"""
    global _current_transactions, _current_refunds, _current_payouts, _current_products
    
    if transactions is not None:
        _current_transactions = transactions
    if refunds is not None:
        _current_refunds = refunds
    if payouts is not None:
        _current_payouts = payouts
    if products is not None:
        _current_products = products
    
    print(f"✅ Data updated: {len(_current_transactions)} transactions, {len(_current_refunds)} refunds")

def reset_to_defaults():
    """Reset to default data files"""
    global _current_transactions, _current_refunds, _current_payouts, _current_products
    
    _current_transactions = load_transactions()
    _current_refunds = load_refunds()
    _current_payouts = load_payouts()
    _current_products = load_product_master()
    
    print("✅ Reset to default data")

def get_processed_data():
    """Get processed transaction data with margins calculated"""
    transactions, refunds, payouts, products = get_current_data()
    
    # Merge product info (COGS)
    tx = transactions.merge(products[["product_id", "cogs"]], on="product_id", how="left")
    tx["unit_margin"] = tx["unit_price"] - tx["cogs"]
    tx["gross_profit"] = tx["quantity"] * tx["unit_margin"] - tx["discount"]
    tx["day"] = pd.to_datetime(tx["date"]).dt.date
    
    return tx, refunds, payouts

def executive_snapshot():
    """Return a multilingual HTML executive snapshot."""
    tx, refunds, payouts = get_processed_data()
    
    card_sales = float(tx.loc[tx["payment_type"] == "CARD", "line_total"].sum())
    cash_sales = float(tx.loc[tx["payment_type"] == "CASH", "line_total"].sum())

    html = f"""
    <h3>{get_text('snapshot_title')} ({tx['day'].min()} → {tx['day'].max()})</h3>
    <ul>
      <li>{get_text('transactions')}: <b>{int(tx['transaction_id'].nunique())}</b></li>
      <li>{get_text('items_sold')}: <b>{int(tx['quantity'].sum())}</b></li>
      <li>{get_text('gross_sales')}: <b>€{float(tx['gross_sales'].sum()):,.2f}</b></li>
      <li>{get_text('discounts')}: <b>€{float(tx['discount'].sum()):,.2f}</b></li>
      <li>{get_text('tax_collected')}: <b>€{float(tx['tax'].sum()):,.2f}</b></li>
      <li>{get_text('tips_collected')}: <b>€{float(tx['tip_amount'].sum()):,.2f}</b></li>
      <li>{get_text('card_sales')}: <b>€{card_sales:,.2f}</b></li>
      <li>{get_text('cash_sales')}: <b>€{cash_sales:,.2f}</b></li>
      <li>{get_text('processor_fees')}: <b>€{float(payouts['processor_fees'].sum()):,.2f}</b></li>
      <li>{get_text('refunds_processed')}: <b>€{float(refunds['refund_amount'].sum()):,.2f}</b></li>
      <li>{get_text('net_card_payouts')}: <b>€{float(payouts['net_payout_amount'].sum()):,.2f}</b></li>
    </ul>
    """
    return html

def generate_ai_insights(data_summary, question_type):
    """Generate multilingual AI insights"""
    
    if question_type == "cash_flow":
        if CURRENT_LANGUAGE == 'it':
            return f"""
            <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4>🤖 {get_text('ai_analysis')}</h4>
            <p><strong>Ecco la mia analisi delle sfide del flusso di cassa:</strong></p>
            
            <p><strong>1. Valutazione della situazione del flusso di cassa:</strong><br>
            I dati indicano che hai €{data_summary.get('total_outflows', 0):.2f} in deflussi di cassa totali da sconti, rimborsi e commissioni. Questo rappresenta circa il {data_summary.get('outflow_percentage', 0):.1f}% delle tue vendite lorde, il che suggerisce che ci sono opportunità per ottimizzare la tua ritenzione di cassa.</p>
            
            <p><strong>2. Principali preoccupazioni del flusso di cassa:</strong><br>
            Il tuo più grande drenaggio di cassa sembra essere {data_summary.get('biggest_drain', 'commissioni processore')}, seguito da {data_summary.get('second_drain', 'sconti')}. Raccomanderei di concentrarsi prima sulla riduzione di {data_summary.get('biggest_drain', 'commissioni processore')} poiché questo avrà l'impatto più immediato sulla tua cassa disponibile.</p>
            
            <p><strong>3. Raccomandazioni attuabili:</strong><br>
            Considera l'implementazione di politiche di sconto più rigorose e la revisione dei tuoi processi di rimborso. Inoltre, potresti voler negoziare tariffe di elaborazione migliori o incoraggiare più pagamenti in contanti per ridurre le commissioni del processore.</p>
            </div>
            """
        elif CURRENT_LANGUAGE == 'es':
            return f"""
            <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4>🤖 {get_text('ai_analysis')}</h4>
            <p><strong>Aquí está mi análisis de los desafíos del flujo de efectivo:</strong></p>
            
            <p><strong>1. Evaluación de la situación del flujo de efectivo:</strong><br>
            Los datos indican que tienes €{data_summary.get('total_outflows', 0):.2f} en salidas totales de efectivo por descuentos, reembolsos y comisiones. Esto representa aproximadamente {data_summary.get('outflow_percentage', 0):.1f}% de tus ventas brutas, lo que sugiere que hay oportunidades para optimizar tu retención de efectivo.</p>
            
            <p><strong>2. Principales preocupaciones del flujo de efectivo:</strong><br>
            Tu mayor drenaje de efectivo parece ser {data_summary.get('biggest_drain', 'comisiones procesamiento')}, seguido de {data_summary.get('second_drain', 'descuentos')}. Recomendaría enfocarse primero en reducir {data_summary.get('biggest_drain', 'comisiones procesamiento')} ya que esto tendrá el impacto más inmediato en tu efectivo disponible.</p>
            
            <p><strong>3. Recomendaciones accionables:</strong><br>
            Considera implementar políticas de descuento más estrictas y revisar tus procesos de reembolso. Además, podrías querer negociar mejores tarifas de procesamiento o fomentar más pagos en efectivo para reducir las comisiones del procesador.</p>
            </div>
            """
        else:  # English
            return f"""
            <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4>🤖 {get_text('ai_analysis')}</h4>
            <p><strong>Here's my analysis of the cash flow challenges:</strong></p>
            
            <p><strong>1. Assessment of the cash flow situation:</strong><br>
            The data indicates you have €{data_summary.get('total_outflows', 0):.2f} in total cash outflows from discounts, refunds, and processor fees. This represents approximately {data_summary.get('outflow_percentage', 0):.1f}% of your gross sales, which suggests there are opportunities to optimize your cash retention.</p>
            
            <p><strong>2. Primary cash flow concerns:</strong><br>
            Your biggest cash drain appears to be {data_summary.get('biggest_drain', 'processor fees')}, followed by {data_summary.get('second_drain', 'discounts')}. I'd recommend focusing on reducing {data_summary.get('biggest_drain', 'processor fees')} first as this will have the most immediate impact on your available cash.</p>
            
            <p><strong>3. Actionable recommendations:</strong><br>
            Consider implementing stricter discount policies and reviewing your refund processes. Additionally, you might want to negotiate better processing rates or encourage more cash payments to reduce processor fees.</p>
            </div>
            """
    
    # Similar patterns for other question types...
    return f"""
    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
    <h4>🤖 {get_text('ai_analysis')}</h4>
    <p><i>Advanced analysis in {CURRENT_LANGUAGE}</i></p>
    </div>
    """

def cash_eaters():
    """Show where cash is leaking + lowest margin SKUs."""
    tx, refunds, payouts = get_processed_data()
    
    ce = pd.DataFrame([
        {"category": get_text('discounts'), "amount": float(tx["discount"].sum())},
        {"category": "Refunds", "amount": float(refunds["refund_amount"].sum())},
        {"category": get_text('processor_fees'), "amount": float(payouts["processor_fees"].sum())},
    ]).sort_values("amount", ascending=False)

    sku = tx.groupby(["product_id", "product_name"], as_index=False) \
        .agg(revenue=("net_sales", "sum"), gp=("gross_profit", "sum"))
    sku["margin_pct"] = np.where(sku["revenue"] > 0, sku["gp"] / sku["revenue"], 0.0)
    low = sku.sort_values(["margin_pct", "revenue"]).head(5)

    # Prepare data for AI insights
    total_outflows = ce["amount"].sum()
    gross_sales = float(tx["gross_sales"].sum())
    outflow_percentage = (total_outflows / gross_sales * 100) if gross_sales > 0 else 0
    biggest_drain = ce.iloc[0]["category"].lower() if len(ce) > 0 else "fees"
    second_drain = ce.iloc[1]["category"].lower() if len(ce) > 1 else "discounts"
    
    data_summary = {
        "total_outflows": total_outflows,
        "outflow_percentage": outflow_percentage,
        "biggest_drain": biggest_drain,
        "second_drain": second_drain
    }
    
    ai_insights = generate_ai_insights(data_summary, "cash_flow")
    
    return executive_snapshot(), ce, low, ai_insights

def reorder_plan(budget=500.0):
    """Suggest what to reorder with a given budget (greedy allocation)."""
    tx, refunds, payouts = get_processed_data()
    
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
    total_gp_uplift = 0
    
    for _, row in sku_rank.iterrows():
        cogs = float(row["cogs"])
        if cogs <= 0:
            continue
        target_units = max(1, int(np.ceil(row["qty_per_day"] * 5)))
        max_units_by_budget = int(remaining // cogs)
        buy_units = max(0, min(target_units, max_units_by_budget))
        if buy_units > 0:
            gp_uplift = round(buy_units * (row["gp"] / max(1, row["qty"])), 2)
            plan.append({
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "unit_cogs": round(cogs, 2),
                "suggested_qty": buy_units,
                "budget_spend": round(buy_units * cogs, 2),
                "est_gp_uplift_week": gp_uplift
            })
            total_gp_uplift += gp_uplift
            remaining -= buy_units * cogs
        if remaining < sku_rank["cogs"].min():
            break

    plan_df = pd.DataFrame(plan)
    msg = f"Budget: €{budget:.0f} → Remaining: €{remaining:.2f}"
    
    # Prepare data for AI insights
    data_summary = {
        "total_gp_uplift": total_gp_uplift
    }
    
    ai_insights = generate_ai_insights(data_summary, "reorder")
    
    return executive_snapshot(), msg, plan_df, ai_insights

def free_up_cash():
    """Estimate extra cash if we discount slow movers."""
    tx, refunds, payouts = get_processed_data()
    
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
    
    # Prepare data for AI insights
    if len(slow) > 0:
        top_slow_item = slow.iloc[0]
        data_summary = {
            "total_cash_potential": total,
            "discount_rate": 20,
            "slow_item_name": top_slow_item["product_name"],
            "slow_item_qty": int(top_slow_item["qty"]),
            "assumed_lift": 1.5,
            "discounted_price": top_slow_item["discounted_price"],
            "extra_units": int(top_slow_item["extra_units"]),
            "extra_cash": top_slow_item["extra_cash_inflow"]
        }
    else:
        data_summary = {"total_cash_potential": total}
    
    ai_insights = generate_ai_insights(data_summary, "free_cash")
    
    return executive_snapshot(), msg, slow, ai_insights