# src/analysis.py - Business logic with upload-only data (no defaults)
import pandas as pd
import numpy as np
from utils import (
    load_transactions, load_refunds, load_payouts, load_product_master,
    clear_data_directory, check_data_status
)
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

# Global variables to hold current data - NO DEFAULT LOADING
_current_transactions = None
_current_refunds = None
_current_payouts = None
_current_products = None

def get_current_data():
    """Get current data - will raise error if no data uploaded"""
    global _current_transactions, _current_refunds, _current_payouts, _current_products
    
    # Don't auto-load defaults anymore - force uploads
    if _current_transactions is None:
        raise ValueError("No data loaded. Please upload CSV files first.")
    
    return _current_transactions, _current_refunds, _current_payouts, _current_products

def set_data(transactions=None, refunds=None, payouts=None, products=None):
    """Set new data from uploads"""
    global _current_transactions, _current_refunds, _current_payouts, _current_products
    
    if transactions is not None:
        _current_transactions = transactions
        print(f"✅ Transactions loaded: {len(_current_transactions)} rows")
    if refunds is not None:
        _current_refunds = refunds
        print(f"✅ Refunds loaded: {len(_current_refunds)} rows")
    if payouts is not None:
        _current_payouts = payouts
        print(f"✅ Payouts loaded: {len(_current_payouts)} rows")
    if products is not None:
        _current_products = products
        print(f"✅ Products loaded: {len(_current_products)} rows")

def reset_to_uploads():
    """Reset to force new uploads - clears all data"""
    global _current_transactions, _current_refunds, _current_payouts, _current_products
    
    _current_transactions = None
    _current_refunds = None
    _current_payouts = None
    _current_products = None
    
    # Clear the data directory
    clear_data_directory()
    
    print("🗑️  All data cleared. Please upload fresh CSV files.")

def get_data_status():
    """Get status of currently loaded data"""
    status = {}
    
    if _current_transactions is not None:
        status['Transactions'] = f"✅ {len(_current_transactions)} rows loaded"
    else:
        status['Transactions'] = "❌ Not loaded"
        
    if _current_refunds is not None:
        status['Refunds'] = f"✅ {len(_current_refunds)} rows loaded"
    else:
        status['Refunds'] = "❌ Not loaded"
        
    if _current_payouts is not None:
        status['Payouts'] = f"✅ {len(_current_payouts)} rows loaded"
    else:
        status['Payouts'] = "❌ Not loaded"
        
    if _current_products is not None:
        status['Products'] = f"✅ {len(_current_products)} rows loaded"
    else:
        status['Products'] = "❌ Not loaded"
    
    return status

def get_processed_data():
    """Get processed transaction data with margins calculated"""
    try:
        transactions, refunds, payouts, products = get_current_data()
    except ValueError as e:
        raise ValueError(f"Cannot process data: {str(e)}")
    
    # Merge product info (COGS)
    tx = transactions.merge(products[["product_id", "cogs"]], on="product_id", how="left")
    tx["unit_margin"] = tx["unit_price"] - tx["cogs"]
    tx["gross_profit"] = tx["quantity"] * tx["unit_margin"] - tx["discount"]
    tx["day"] = pd.to_datetime(tx["date"]).dt.date
    
    return tx, refunds, payouts

def executive_snapshot():
    """Return a multilingual HTML executive snapshot."""
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        return f"""
        <div style='color: red; padding: 15px; background-color: #f8d7da; border-radius: 5px;'>
        <h3>⚠️ No Data Available</h3>
        <p>{str(e)}</p>
        <p><strong>Please upload all required CSV files:</strong></p>
        <ul>
            <li>Transactions CSV</li>
            <li>Refunds CSV</li>
            <li>Payouts CSV</li>
            <li>Product Master CSV</li>
        </ul>
        </div>
        """
    
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
        
        # Regular paragraph
        else:
            formatted_paragraphs.append(f'<p>{para}</p>')
    
    return '\n'.join(formatted_paragraphs)

def cash_eaters(ui_language="English"):
    """Show where cash is leaking + lowest margin SKUs with AI analysis."""
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        error_msg = f"<div style='color: red; padding: 15px;'>Error: {str(e)}</div>"
        return error_msg, None, None, error_msg
    
    ce = pd.DataFrame([
        {"category": get_text('discounts'), "amount": float(tx["discount"].sum())},
        {"category": "Refunds", "amount": float(refunds["refund_amount"].sum())},
        {"category": get_text('processor_fees'), "amount": float(payouts["processor_fees"].sum())},
    ]).sort_values("amount", ascending=False)

    sku = tx.groupby(["product_id", "product_name"], as_index=False) \
        .agg(revenue=("net_sales", "sum"), gp=("gross_profit", "sum"))
    sku["margin_pct"] = np.where(sku["revenue"] > 0, sku["gp"] / sku["revenue"], 0.0)
    low = sku.sort_values(["margin_pct", "revenue"]).head(5)

    # Get AI insights using Claude with improved formatting
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
            
            # Get AI analysis with specific formatting request
            language = get_language_from_ui_language(ui_language)
            
            # Enhanced prompt for better formatting
            enhanced_prompt = f"""
            Analyze the cash flow issues and provide a structured response with clear sections:

            BUSINESS CONTEXT:
            {business_context}

            CASH FLOW DATA:
            - Discounts: €{cash_eaters_data['discounts']:,.2f}
            - Refunds: €{cash_eaters_data['refunds']:,.2f}
            - Processor Fees: €{cash_eaters_data['processor_fees']:,.2f}

            LOW MARGIN PRODUCTS:
            {cash_eaters_data['low_margin_products']}

            Please provide analysis in this exact format with numbered sections:

            1. **Biggest cash drain assessment** (2-3 sentences identifying the main issue)

            2. **Specific actionable recommendations** (3-4 concrete steps to address the issues)

            3. **Quick wins for this week** (immediate actions that can be implemented right away)

            Use clear paragraph breaks and avoid long dense paragraphs. Each section should be easy to scan and understand.
            """
            
            # Make the AI request with the enhanced prompt
            ai_text = ai_assistant._make_claude_request(
                system_prompt=f"You are an expert retail financial advisor who gives clear, actionable advice. {ai_assistant._get_language_instruction(language)}",
                user_prompt=enhanced_prompt,
                max_tokens=600
            )
            
            ai_insights = generate_ai_insights_html(ai_text, get_text('ai_analysis'))
            
        except Exception as e:
            ai_insights = generate_ai_insights_html(f"Error generating AI insights: {str(e)}")
    else:
        ai_insights = generate_ai_insights_html("AI analysis requires Claude API key. Set ANTHROPIC_API_KEY environment variable.")

    return executive_snapshot(), ce, low, ai_insights


def reorder_plan(budget=500.0, ui_language="English"):
    """Suggest what to reorder with a given budget with AI analysis."""
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        error_msg = f"<div style='color: red; padding: 15px;'>Error: {str(e)}</div>"
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
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        error_msg = f"<div style='color: red; padding: 15px;'>Error: {str(e)}</div>"
        return error_msg, f"Error: {str(e)}", None, error_msg
    
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

# Remove the old reset_to_defaults function and replace with upload-only version
def reset_to_defaults():
    """Legacy function - now redirects to upload-only mode"""
    return reset_to_uploads()

def analyze_executive_summary(ui_language="English"):
    """Generate AI analysis specifically for executive summary"""
    try:
        tx, refunds, payouts = get_processed_data()
        
        if ai_assistant.is_available():
            # Prepare comprehensive business context
            transactions, refunds_df, payouts_df, products = get_current_data()
            business_context = ai_assistant._prepare_business_context(tx, refunds_df, payouts_df, products)
            
            # Calculate key metrics for executive analysis
            total_revenue = float(tx['line_total'].sum())
            total_transactions = int(tx['transaction_id'].nunique())
            avg_ticket = total_revenue / total_transactions if total_transactions > 0 else 0
            total_refunds = float(refunds['refund_amount'].sum())
            total_fees = float(payouts['processor_fees'].sum())
            refund_rate = (total_refunds / total_revenue * 100) if total_revenue > 0 else 0
            
            language = get_language_from_ui_language(ui_language)
            
            executive_prompt = f"""
            Provide an executive-level business analysis based on this data:

            {business_context}

            KEY METRICS:
            - Total Revenue: €{total_revenue:,.2f}
            - Average Ticket: €{avg_ticket:.2f}
            - Total Transactions: {total_transactions:,}
            - Refund Rate: {refund_rate:.1f}%
            - Processing Costs: €{total_fees:,.2f}

            Please provide analysis in this format:

            1. **Business Health Overview** (2-3 sentences on overall performance)

            2. **Key Opportunities** (Top 2-3 areas for improvement with specific impact)

            3. **Priority Actions** (3 specific steps to take this week)

            4. **Financial Outlook** (Assessment of cash flow health and trajectory)

            Focus on actionable insights that an executive can act on immediately.
            """
            
            ai_text = ai_assistant._make_claude_request(
                system_prompt=f"You are a senior business consultant providing executive-level insights. {ai_assistant._get_language_instruction(language)}",
                user_prompt=executive_prompt,
                max_tokens=600
            )
            
            return generate_ai_insights_html(ai_text, "Executive AI Analysis")
        
        else:
            return generate_ai_insights_html("AI executive analysis requires Claude API key. Set ANTHROPIC_API_KEY environment variable.")
    
    except Exception as e:
        return generate_ai_insights_html(f"Error generating executive analysis: {str(e)}")

# Add the executive summary analysis to the existing functions
def executive_snapshot():
    """Return a multilingual HTML executive snapshot with optional AI analysis."""
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        return f"""
        <div style='color: red; padding: 15px; background-color: #f8d7da; border-radius: 5px;'>
        <h3>⚠️ No Data Available</h3>
        <p>{str(e)}</p>
        <p><strong>Please upload all required CSV files:</strong></p>
        <ul>
            <li>Transactions CSV</li>
            <li>Refunds CSV</li>
            <li>Payouts CSV</li>
            <li>Product Master CSV</li>
        </ul>
        </div>
        """
    
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

