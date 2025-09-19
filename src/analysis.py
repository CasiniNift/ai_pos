# src/analysis.py - Simplified version without translation dictionaries

import pandas as pd
import numpy as np
from utils import (
    load_transactions, load_refunds, load_payouts, load_product_master,
    clear_data_directory, check_data_status
)
from ai_assistant import CashFlowAIAssistant
import os
import sys

# Initialize AI Assistant
ai_assistant = CashFlowAIAssistant()

# Remove all the TRANSLATIONS dictionaries and get_text() complexity
# Keep everything in English - let Claude handle translations

# Global variables to hold current data
_current_transactions = None
_current_refunds = None
_current_payouts = None
_current_products = None

def get_current_data():
    """Get current data - will raise error if no data uploaded"""
    global _current_transactions, _current_refunds, _current_payouts, _current_products
    
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
    """Return HTML executive snapshot - always in English"""
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

    # Simple English snapshot - no translation complexity
    html = f"""
    <h3>📊 Business Snapshot ({tx['day'].min()} → {tx['day'].max()})</h3>
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

# Replace the get_claude_analysis function in your src/analysis.py with this corrected version:
# Replace your get_claude_analysis function in src/analysis.py with this improved version:

def get_claude_analysis(question_type, business_data, language="English"):
    """Get AI analysis in the specified language with proper formatting"""
    if not ai_assistant.is_available():
        return f"""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4>🤖 AI Analysis</h4>
        <p>AI analysis requires Claude API key. Set ANTHROPIC_API_KEY environment variable.</p>
        </div>
        """
    
    try:
        # Get current data properly
        transactions, refunds, payouts, products = get_current_data()
        
        # Build business context safely
        try:
            business_context = ai_assistant._prepare_business_context(transactions, refunds, payouts, products)
        except Exception as context_error:
            # If context building fails, create a simple summary
            total_transactions = len(transactions)
            total_revenue = float(transactions['line_total'].sum()) if 'line_total' in transactions.columns else 0
            total_refunds = float(refunds['refund_amount'].sum()) if not refunds.empty and 'refund_amount' in refunds.columns else 0
            
            business_context = f"""
            BUSINESS SUMMARY:
            - Total Transactions: {total_transactions}
            - Total Revenue: €{total_revenue:,.2f}
            - Total Refunds: €{total_refunds:,.2f}
            """
        
        # Create a focused prompt with EXPLICIT formatting instructions
        if question_type == "What's eating my cash flow?":
            prompt = f"""
            You are a business consultant. Analyze this cash flow data and respond in {language}.
            
            {business_context}
            
            IMPORTANT: Structure your response with clear numbered points like this:

            1. **Main Issue**: [Identify the biggest cash flow problem in 1-2 sentences]

            2. **Key Recommendations**: [Provide 2-3 specific actions in separate bullet points]

            3. **Quick Wins**: [List immediate actions they can take this week]

            Use short paragraphs and clear formatting. Keep each section concise and actionable.
            """
        elif "reorder" in question_type.lower():
            prompt = f"""
            You are an inventory expert. Respond in {language}.
            
            {business_context}
            
            IMPORTANT: Format your response like this:

            1. **Purchase Priority**: [Which products to reorder first and why]

            2. **Budget Optimization**: [How to get maximum value from available budget]

            3. **Inventory Strategy**: [Long-term recommendations]

            Keep each point brief and actionable.
            """
        elif "free up" in question_type.lower():
            prompt = f"""
            You are a cash flow expert. Respond in {language}.
            
            {business_context}
            
            IMPORTANT: Structure your response as:

            1. **Cash Liberation Opportunities**: [Biggest opportunities to free up cash]

            2. **Clearance Strategy**: [How to move slow inventory]

            3. **Implementation Plan**: [Steps to execute this week]

            Use numbered points with short, clear explanations.
            """
        else:
            prompt = f"""
            You are a business analyst. Provide an executive summary in {language}.
            
            {business_context}
            
            IMPORTANT: Format as:

            1. **Business Performance**: [Key financial insights]

            2. **Priority Issues**: [Main challenges to address]

            3. **Action Items**: [Specific next steps]

            Keep it concise with clear headings and short paragraphs.
            """
        
        # Get AI response
        ai_text = ai_assistant._make_claude_request(
            system_prompt=f"You are an expert business consultant. Always respond in {language} with numbered points and clear paragraph breaks. Use **bold** for headings.",
            user_prompt=prompt,
            max_tokens=600
        )
        
        # Format the response with proper HTML structure
        if ai_text and not ai_text.startswith("AI Analysis Error"):
            # Enhanced formatting function
            formatted_text = format_ai_text_with_structure(ai_text)
            
            return f"""
            <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin: 15px 0; line-height: 1.6;">
            <h4 style="color: #2d5016; margin-bottom: 15px;">🤖 AI Analysis</h4>
            <div style="color: #2d5016;">
            {formatted_text}
            </div>
            </div>
            """
        else:
            return f"""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4>🤖 AI Analysis</h4>
            <p>Error: {ai_text}</p>
            </div>
            """
        
    except Exception as e:
        return f"""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h4>🤖 AI Analysis</h4>
        <p>Error generating analysis: {str(e)}</p>
        </div>
        """

def format_ai_text_with_structure(text):
    """Format AI text with proper paragraphs and clean structure - bold headers only"""
    if not text:
        return "<p>No analysis available.</p>"
    
    # Split into paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    
    formatted_parts = []
    
    for paragraph in paragraphs:
        if not paragraph:
            continue
            
        # Handle numbered points (1., 2., 3., etc.)
        if paragraph.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
            # Extract number and content
            parts = paragraph.split('.', 1)
            if len(parts) == 2:
                number = parts[0].strip()
                content = parts[1].strip()
                
                # Look for pattern like "Header: content" or "**Header**: content"
                header_content = extract_header_and_content(content)
                
                if header_content:
                    header, body = header_content
                    formatted_parts.append(f'''
                        <div style="margin: 15px 0; padding: 12px; background-color: rgba(255,255,255,0.4); border-radius: 6px;">
                            <div style="margin-bottom: 8px;">
                                <strong style="color: #1a4c12;">{number}. {header}:</strong>
                            </div>
                            <div style="color: #2d5016; line-height: 1.5;">{body}</div>
                        </div>
                    ''')
                else:
                    # No clear header pattern, just format normally
                    # Remove any existing **bold** formatting from content
                    clean_content = content.replace('**', '').replace('**', '')
                    formatted_parts.append(f'''
                        <div style="margin: 15px 0; padding: 12px; background-color: rgba(255,255,255,0.4); border-radius: 6px;">
                            <div style="font-weight: bold; color: #1a4c12; margin-bottom: 8px;">{number}.</div>
                            <div style="color: #2d5016; line-height: 1.5;">{clean_content}</div>
                        </div>
                    ''')
            else:
                # If split didn't work as expected, treat as regular paragraph
                clean_paragraph = paragraph.replace('**', '').replace('**', '')
                formatted_parts.append(f'<p style="margin: 10px 0; line-height: 1.5;">{clean_paragraph}</p>')
        
        # Handle bullet points (-, •, *)
        elif paragraph.strip().startswith(('-', '•', '*')):
            content = paragraph.strip()[1:].strip()  # Remove bullet and trim
            
            # Extract header if present
            header_content = extract_header_and_content(content)
            if header_content:
                header, body = header_content
                formatted_parts.append(f'''
                    <li style="margin: 8px 0; line-height: 1.5;">
                        <strong>{header}:</strong> {body}
                    </li>
                ''')
            else:
                # Remove bold formatting and use as regular bullet
                clean_content = content.replace('**', '').replace('**', '')
                formatted_parts.append(f'<li style="margin: 5px 0; line-height: 1.5;">{clean_content}</li>')
        
        # Regular paragraphs
        else:
            # For regular paragraphs, look for header patterns too
            header_content = extract_header_and_content(paragraph)
            if header_content:
                header, body = header_content
                formatted_parts.append(f'''
                    <p style="margin: 12px 0; line-height: 1.5;">
                        <strong>{header}:</strong> {body}
                    </p>
                ''')
            else:
                # Remove all bold formatting for regular paragraphs
                clean_paragraph = paragraph.replace('**', '').replace('**', '')
                formatted_parts.append(f'<p style="margin: 12px 0; line-height: 1.5;">{clean_paragraph}</p>')
    
    return ''.join(formatted_parts)

def extract_header_and_content(text):
    """Extract header and content from text with patterns like 'Header: content' or '**Header**: content'"""
    
    # Pattern 1: **Header**: content
    if '**' in text and '**:' in text:
        try:
            # Find the first occurrence of **text**:
            start = text.find('**')
            if start != -1:
                # Find the matching closing **:
                end = text.find('**:', start)
                if end != -1:
                    header = text[start+2:end].strip()
                    content = text[end+3:].strip()
                    return header, content
        except:
            pass
    
    # Pattern 2: Text followed by colon (like "Problema Principale: content")
    if ':' in text:
        parts = text.split(':', 1)
        if len(parts) == 2:
            potential_header = parts[0].strip()
            content = parts[1].strip()
            
            # Only treat as header if it's reasonable length (not a sentence)
            # and doesn't contain periods (which would indicate it's part of content)
            if len(potential_header) < 80 and '.' not in potential_header:
                # Remove any **bold** markers from header
                clean_header = potential_header.replace('**', '').replace('**', '')
                return clean_header, content
    
    return None

def cash_eaters(ui_language="English"):
    """Show where cash is leaking + lowest margin SKUs with AI analysis"""
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        error_msg = f"<div style='color: red; padding: 15px;'>Error: {str(e)}</div>"
        return error_msg, None, None, error_msg
    
    # Business calculations - always in English
    ce = pd.DataFrame([
        {"category": "Discounts", "amount": float(tx["discount"].sum())},
        {"category": "Refunds", "amount": float(refunds["refund_amount"].sum())},
        {"category": "Processor fees", "amount": float(payouts["processor_fees"].sum())},
    ]).sort_values("amount", ascending=False)

    sku = tx.groupby(["product_id", "product_name"], as_index=False) \
        .agg(revenue=("net_sales", "sum"), gp=("gross_profit", "sum"))
    sku["margin_pct"] = np.where(sku["revenue"] > 0, sku["gp"] / sku["revenue"], 0.0)
    low = sku.sort_values(["margin_pct", "revenue"]).head(5)

    # Get AI insights - Claude handles the language
    ai_insights = get_claude_analysis("What's eating my cash flow?", {}, ui_language)
    
    return executive_snapshot(), ce, low, ai_insights

def reorder_plan(budget=500.0, ui_language="English"):
    """Suggest what to reorder with AI analysis"""
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        error_msg = f"<div style='color: red; padding: 15px;'>Error: {str(e)}</div>"
        return error_msg, f"Error: {str(e)}", None, error_msg
    
    # Business calculations - always in English
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
    
    # Get AI insights - Claude handles the language
    ai_insights = get_claude_analysis(f"What should I reorder with €{budget} budget?", {}, ui_language)
    
    return executive_snapshot(), msg, plan_df, ai_insights

def free_up_cash(ui_language="English"):
    """Estimate extra cash if we discount slow movers with AI analysis"""
    try:
        tx, refunds, payouts = get_processed_data()
    except ValueError as e:
        error_msg = f"<div style='color: red; padding: 15px;'>Error: {str(e)}</div>"
        return error_msg, f"Error: {str(e)}", None, error_msg
    
    # Business calculations - always in English
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
    
    # Get AI insights - Claude handles the language
    ai_insights = get_claude_analysis("How much cash can I free up?", {}, ui_language)
    
    return executive_snapshot(), msg, slow, ai_insights

def analyze_executive_summary(ui_language="English"):
    """Generate AI executive summary"""
    return get_claude_analysis("Executive Summary", {}, ui_language)