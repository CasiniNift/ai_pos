# src/analysis.py - Business logic with Claude AI integration
import pandas as pd
import numpy as np
from utils import load_transactions, load_refunds, load_payouts, load_product_master
from ai_assistant import CashFlowAIAssistant
import os
import sys

# Get language from command line argument or environment
CURRENT_LANGUAGE = 'en'
if len(sys.argv) > 1:
    lang_arg = sys.argv[1].lower()
    if lang_arg in ['en', 'it', 'es']:
        CURRENT_LANGUAGE = lang_arg

# Initialize AI Assistant
ai_assistant = CashFlowAIAssistant()

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

def get_language_from_ui_language(ui_language):
    """Convert UI language selection to AI language code"""
    mapping = {
        "English": "english",
        "Italiano": "italian", 
        "Español": "spanish"
    }
    return mapping.get(ui_language, "english")

def generate_ai_insights_html(ai_text, title="AI Analysis"):
    """Wrap AI text in consistent HTML formatting with proper paragraph breaks"""
    if not ai_text or "Error" in ai_text:
        return f"""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4>🤖 {title}</h4>
        <p>{ai_text or 'AI analysis not available. Please check your API key configuration.'}</p>
        </div>
        """
    
    # Format the AI text with proper paragraph breaks and structure
    formatted_text = format_ai_response(ai_text)
    
    return f"""
    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
    <h4>🤖 {title}</h4>
    <div style="line-height: 1.6; color: #2d5016;">
    {formatted_text}
    </div>
    </div>
    """

def format_ai_response(text):
    """Format AI response text with proper HTML structure - convert markdown to HTML"""
    if not text:
        return "<p>No analysis available.</p>"
    
    # First, convert all **text** markdown to HTML bold tags
    import re
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Split into paragraphs and format
    paragraphs = text.split('\n\n')
    formatted_paragraphs = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # Check if it's a numbered list item
        if para.startswith(('1. ', '2. ', '3. ', '4. ', '5. ')):
            # Extract number and content
            parts = para.split('. ', 1)
            if len(parts) == 2:
                number = parts[0]
                content = parts[1]
                
                # Check if there's a header (look for <strong> tags or colon)
                if '<strong>' in content and '</strong>' in content:
                    # Format: 1. <strong>Header</strong> content
                    formatted_paragraphs.append(f'<p><strong>{number}.</strong> {content}</p>')
                elif ': ' in content:
                    # Format: 1. Header: content
                    header_part = content.split(': ')[0].strip()
                    remaining_content = content.split(': ', 1)[1].strip()
                    formatted_paragraphs.append(f'<p><strong>{number}. {header_part}:</strong></p>')
                    if remaining_content:
                        formatted_paragraphs.append(f'<p style="margin-left: 20px;">{remaining_content}</p>')
                else:
                    # No clear header, just format as regular numbered item
                    formatted_paragraphs.append(f'<p><strong>{number}.</strong> {content}</p>')
            else:
                formatted_paragraphs.append(f'<p>{para}</p>')
        
        # Check if it's a bullet point or sub-item (a., b., c.)
        elif para.startswith(('- ', 'a. ', 'b. ', 'c. ', 'd. ', 'e. ')):
            # Handle sub-items with proper formatting
            if para.startswith(('a. ', 'b. ', 'c. ', 'd. ', 'e. ')):
                parts = para.split('. ', 1)
                if len(parts) == 2:
                    letter = parts[0]
                    content = parts[1]
                    # Check if there's a header with colon
                    if ': ' in content:
                        header_part = content.split(': ')[0].strip()
                        remaining_content = content.split(': ', 1)[1].strip()
                        formatted_paragraphs.append(f'<p style="margin-left: 20px;"><strong>{letter}. {header_part}:</strong> {remaining_content}</p>')
                    else:
                        formatted_paragraphs.append(f'<p style="margin-left: 20px;"><strong>{letter}.</strong> {content}</p>')
                else:
                    formatted_paragraphs.append(f'<p style="margin-left: 20px;">{para}</p>')
            else:
                # Regular bullet point
                formatted_paragraphs.append(f'<p style="margin-left: 20px;">• {para[2:]}</p>')
        
        # Check if it contains a colon (likely a section header)
        elif ':' in para and len(para.split(':')[0]) < 100 and not '<strong>' in para:
            parts = para.split(':', 1)
            if len(parts) == 2:
                header = parts[0].strip()
                content = parts[1].strip()
                formatted_paragraphs.append(f'<p><strong>{header}:</strong> {content}</p>')
            else:
                formatted_paragraphs.append(f'<p>{para}</p>')
        
        # Regular paragraph
        else:
            formatted_paragraphs.append(f'<p>{para}</p>')
    
    # If no proper formatting was applied, split by sentences for readability
    if len(formatted_paragraphs) <= 1 and text:
        sentences = text.split('. ')
        formatted_sentences = []
        current_para = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Add period back if it's not the last sentence
            if i < len(sentences) - 1 and not sentence.endswith('.'):
                sentence += '.'
            
            current_para.append(sentence)
            
            # Break into new paragraph every 2-3 sentences or when we detect a topic change
            if (len(current_para) >= 2 and any(keyword in sentence.lower() for keyword in 
                ['raccomand', 'suggest', 'consider', 'important', 'consiglio', 'inoltre', 'è importante'])) or len(current_para) >= 3:
                formatted_sentences.append(f'<p>{" ".join(current_para)}</p>')
                current_para = []
        
        # Add any remaining sentences
        if current_para:
            formatted_sentences.append(f'<p>{" ".join(current_para)}</p>')
        
        return '\n'.join(formatted_sentences)
    
    return '\n'.join(formatted_paragraphs)

def cash_eaters(ui_language="English"):
    """Show where cash is leaking + lowest margin SKUs with AI analysis."""
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

    # Get AI insights using Claude
    if ai_assistant.is_available():
        try:
            # Prepare business context
            transactions, refunds_df, payouts_df, products = get_current_data()
            business_context = ai_assistant._prepare_business_context(tx, refunds_df, payouts_df, products)
            
            # Prepare cash eaters data
            cash_eaters_data = {
                'discounts': float(tx["discount"].sum()),
                'refunds': float(refunds["refund_amount"].sum()),
                'processor_fees': float(payouts["processor_fees"].sum()),
                'low_margin_products': low.to_string()
            }
            
            # Get AI analysis
            language = get_language_from_ui_language(ui_language)
            ai_text = ai_assistant.analyze_cash_eaters(business_context, cash_eaters_data, language)
            ai_insights = generate_ai_insights_html(ai_text, get_text('ai_analysis'))
            
        except Exception as e:
            ai_insights = generate_ai_insights_html(f"Error generating AI insights: {str(e)}")
    else:
        ai_insights = generate_ai_insights_html("AI analysis requires Claude API key. Set ANTHROPIC_API_KEY environment variable.")
    
    return executive_snapshot(), ce, low, ai_insights

def reorder_plan(budget=500.0, ui_language="English"):
    """Suggest what to reorder with a given budget with AI analysis."""
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
    
    # Get AI insights using Claude
    if ai_assistant.is_available():
        try:
            # Prepare business context
            transactions, refunds_df, payouts_df, products = get_current_data()
            business_context = ai_assistant._prepare_business_context(tx, refunds_df, payouts_df, products)
            
            # Prepare reorder data
            reorder_data = {
                'remaining_budget': remaining,
                'purchase_plan': plan_df.to_string() if not plan_df.empty else "No items fit within budget"
            }
            
            # Get AI analysis
            language = get_language_from_ui_language(ui_language)
            ai_text = ai_assistant.analyze_reorder_plan(business_context, reorder_data, budget, language)
            ai_insights = generate_ai_insights_html(ai_text, get_text('ai_analysis'))
            
        except Exception as e:
            ai_insights = generate_ai_insights_html(f"Error generating AI insights: {str(e)}")
    else:
        ai_insights = generate_ai_insights_html("AI analysis requires Claude API key. Set ANTHROPIC_API_KEY environment variable.")
    
    return executive_snapshot(), msg, plan_df, ai_insights

def free_up_cash(ui_language="English"):
    """Estimate extra cash if we discount slow movers with AI analysis."""
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
    
    # Get AI insights using Claude
    if ai_assistant.is_available():
        try:
            # Prepare business context
            transactions, refunds_df, payouts_df, products = get_current_data()
            business_context = ai_assistant._prepare_business_context(tx, refunds_df, payouts_df, products)
            
            # Prepare clearance data
            clearance_data = {
                'total_extra_cash': total,
                'slow_movers': slow.to_string() if not slow.empty else "No slow-moving items identified"
            }
            
            # Get AI analysis
            language = get_language_from_ui_language(ui_language)
            ai_text = ai_assistant.analyze_cash_liberation(business_context, clearance_data, language)
            ai_insights = generate_ai_insights_html(ai_text, get_text('ai_analysis'))
            
        except Exception as e:
            ai_insights = generate_ai_insights_html(f"Error generating AI insights: {str(e)}")
    else:
        ai_insights = generate_ai_insights_html("AI analysis requires Claude API key. Set ANTHROPIC_API_KEY environment variable.")
    
    return executive_snapshot(), msg, slow, ai_insights

def sales_impact_scenario(ui_language="English"):
    """Analyze sales impact scenario - exactly like the other working functions."""
    tx, refunds, payouts = get_processed_data()
    
    # Calculate the actual impact
    current_revenue = float(tx['line_total'].sum())
    impact_amount = current_revenue * 0.1
    
    # Get AI insights using Claude (same pattern as other functions)
    if ai_assistant.is_available():
        try:
            # Prepare business context
            transactions, refunds_df, payouts_df, products = get_current_data()
            business_context = ai_assistant._prepare_business_context(tx, refunds_df, payouts_df, products)
            
            # Get AI analysis
            language = get_language_from_ui_language(ui_language)
            ai_text = ai_assistant.analyze_sales_impact(business_context, 10, language)
            ai_insights = generate_ai_insights_html(ai_text, get_text('ai_analysis'))
            
        except Exception as e:
            ai_insights = generate_ai_insights_html(f"Error generating AI insights: {str(e)}")
    else:
        ai_insights = generate_ai_insights_html("AI analysis requires Claude API key. Set ANTHROPIC_API_KEY environment variable.")
    
    return executive_snapshot(), ai_insights