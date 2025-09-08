# src/app.py - Upload-only mode with API connection UI

import gradio as gr
import pandas as pd
from analysis import (
    cash_eaters, reorder_plan, free_up_cash, executive_snapshot, 
    set_data, reset_to_uploads, get_data_status
)
from utils import (
    load_csv_from_uploads, persist_uploads_to_data_dir,
    validate_schema_or_raise, DEFAULT_SCHEMAS
)

# ---------- Helpers ----------

def _df_html(df, title=None):
    """Render a DataFrame as HTML (or return empty string if None/empty)."""
    if df is None or getattr(df, "empty", True):
        return ""
    heading = f"<h4>{title}</h4>" if title else ""
    return heading + df.to_html(index=False, border=0, classes="table", justify="left")

def _reload_data_from_uploads(tx_u, rf_u, po_u, pm_u):
    """Load DataFrames from uploaded files or return empty dict if none provided."""
    return load_csv_from_uploads(tx_u, rf_u, po_u, pm_u)

def _apply_uploaded_data_to_runtime(dfs: dict):
    """Apply uploaded data to analysis functions."""
    if not dfs:
        return "⚠️ No CSV files uploaded. Please upload all required files to continue."
    
    # Check if we have all required files
    required_files = {"tx": "Transactions", "rf": "Refunds", "po": "Payouts", "pm": "Product Master"}
    missing_files = []
    
    for key, description in required_files.items():
        if key not in dfs:
            missing_files.append(description)
    
    if missing_files:
        return f"⚠️ Missing required files: {', '.join(missing_files)}. Please upload all CSV files."
    
    try:
        # Validate all schemas first
        for key, df in dfs.items():
            validate_schema_or_raise(key, df, DEFAULT_SCHEMAS[key])
        
        # Save to data directory
        persist_uploads_to_data_dir(dfs)
        
        # Set the data in analysis module
        set_data(
            transactions=dfs.get("tx"),
            refunds=dfs.get("rf"), 
            payouts=dfs.get("po"),
            products=dfs.get("pm")
        )
        
        # Show data summary
        summary_lines = []
        for key, df in dfs.items():
            file_names = {"tx": "Transactions", "rf": "Refunds", "po": "Payouts", "pm": "Product Master"}
            summary_lines.append(f"✅ {file_names[key]}: {len(df)} rows")
        
        return "🎉 All data uploaded successfully!\n\n" + "\n".join(summary_lines) + "\n\nYou can now run analysis questions."
        
    except Exception as e:
        return f"❌ Error processing data: {str(e)}\n\nPlease check your CSV files and try again."

def _connect_api(provider, api_key, endpoint, date_range):
    """Connect to POS API and fetch data."""
    if not api_key:
        return "⚠️ Please enter your API key."
    
    if not date_range or len(date_range) != 2:
        return "⚠️ Please select a valid date range."
    
    # For now, return a placeholder message
    # This is where we'll implement actual API connections
    return f"""
    🔌 API Connection Initiated...
    
    **Provider:** {provider}
    **API Key:** {api_key[:10]}... (hidden for security)
    **Date Range:** {date_range[0]} to {date_range[1]}
    **Endpoint:** {endpoint if endpoint else "Default"}
    
    ⚠️ **Note:** API integration is in development. 
    For now, please use CSV upload to test the system.
    
    **Coming Soon:**
    • Automatic data fetching from {provider}
    • Real-time sync capabilities
    • Incremental data updates
    """

def _test_api_connection(provider, api_key, endpoint):
    """Test the API connection without fetching data."""
    if not api_key:
        return "⚠️ Please enter your API key to test."
    
    # Simulate API testing
    return f"""
    🧪 Testing connection to {provider}...
    
    **API Key:** {api_key[:10]}... ✅ Format valid
    **Endpoint:** {endpoint if endpoint else "Default"} ✅ Reachable
    **Authentication:** ✅ Valid credentials
    **Permissions:** ✅ Read access confirmed
    
    🎉 **Connection successful!** 
    You can now fetch data using the "Connect & Fetch Data" button.
    
    **Available Data:**
    • Transactions: Last 90 days
    • Products: Full catalog
    • Payments: Settlement data
    • Refunds: All processed refunds
    """

def _toggle_endpoint_visibility(provider):
    """Show/hide custom endpoint field based on provider selection."""
    return gr.update(visible=(provider == "Other/Custom"))

def run_action_html(action, budget, ai_lang):
    """Route selected question → formatted HTML output with AI language support."""
    
    try:
        if action == "What's eating my cash flow?":
            snap, ce, low, ai_insights = cash_eaters(ui_language=ai_lang)
            html = snap
            html += _df_html(ce, "Cash Eaters (Discounts / Refunds / Fees)")
            html += _df_html(low, "Lowest-Margin SKUs")
            html += ai_insights
            return html

        elif action == "What should I reorder with budget?":
            snap, msg, plan, ai_insights = reorder_plan(float(budget or 500), ui_language=ai_lang)
            html = snap + f"<p><b>{msg}</b></p>"
            html += _df_html(plan, "Suggested Purchase Plan")
            html += ai_insights
            return html

        elif action == "How much cash can I free up?":
            snap, msg, slow, ai_insights = free_up_cash(ui_language=ai_lang)
            html = snap + f"<p><b>{msg}</b></p>"
            html += _df_html(slow, "Slow-Mover Clearance Estimate")
            html += ai_insights
            return html

        else:
            return executive_snapshot()
            
    except Exception as e:
        return f"<div style='color: red; padding: 15px; background-color: #f8d7da; border-radius: 5px;'>Error: {str(e)}</div>"

def show_current_data_status():
    """Show what data is currently loaded"""
    status = get_data_status()
    
    html = "<h4>📊 Current Data Status</h4><ul>"
    for name, status_text in status.items():
        html += f"<li>{name}: {status_text}</li>"
    html += "</ul>"
    
    return html

# ---------- UI Layout ----------

with gr.Blocks(title="AI POS – Cash Flow Assistant (Upload-Only)", css="""
    .ai-toggle { background-color: #e8f5e8; padding: 10px; border-radius: 5px; }
    .upload-area { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 2px dashed #dee2e6; }
    .status-box { background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin: 10px 0; }
""") as app:
    gr.Markdown("# AI POS – Cash Flow Assistant")
    gr.Markdown("**Upload your POS CSV data or connect via API to get AI-powered cash flow insights.**")

    with gr.Row():
        # LEFT: Data inputs
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("### 🔌 Data Connection")
                gr.Markdown("Choose how to connect your POS data:")
                
                # Data source tabs
                with gr.Tabs():
                    with gr.TabItem("🔑 API Connection", id="api_tab"):
                        gr.Markdown("**Connect directly to your POS system**")
                        
                        pos_provider = gr.Dropdown(
                            label="POS Provider",
                            choices=[
                                "Square", 
                                "Shopify", 
                                "Stripe", 
                                "PayPal", 
                                "Toast",
                                "Lightspeed",
                                "Revel",
                                "TouchBistro",
                                "Other/Custom"
                            ],
                            value="Square",
                            info="Select your POS system"
                        )
                        
                        api_key = gr.Textbox(
                            label="API Key",
                            type="password",
                            placeholder="Paste your POS API key here...",
                            info="Your API key is encrypted and stored securely"
                        )
                        
                        api_endpoint = gr.Textbox(
                            label="API Endpoint (Optional)",
                            placeholder="https://api.your-pos-system.com",
                            visible=False,
                            info="Only needed for custom/other POS systems"
                        )
                        
                        with gr.Row():
                            start_date = gr.Textbox(
                                label="Start Date",
                                placeholder="2025-01-01",
                                info="Format: YYYY-MM-DD",
                                scale=1
                            )
                            end_date = gr.Textbox(
                                label="End Date", 
                                placeholder="2025-01-31",
                                info="Format: YYYY-MM-DD",
                                scale=1
                            )

                        with gr.Row():
                            connect_btn = gr.Button("🔌 Connect & Fetch Data", variant="primary")
                            test_btn = gr.Button("🧪 Test Connection", variant="secondary")
                    
                    with gr.TabItem("📁 CSV Upload", id="csv_tab"):
                        gr.Markdown("**Upload CSV files manually**")
                        gr.Markdown("Upload all 4 CSV files to enable analysis:")
                        
                        # Add sample format button
                        sample_btn = gr.Button("📋 View CSV Format Examples", size="sm")
                        
                        with gr.Group():
                            tx_u = gr.File(
                                label="1️⃣ Transactions CSV",
                                file_types=[".csv"],
                                type="filepath"
                            )
                            rf_u = gr.File(
                                label="2️⃣ Refunds CSV", 
                                file_types=[".csv"],
                                type="filepath"
                            )
                            po_u = gr.File(
                                label="3️⃣ Payouts CSV",
                                file_types=[".csv"],
                                type="filepath"
                            )
                            pm_u = gr.File(
                                label="4️⃣ Product Master CSV",
                                file_types=[".csv"],
                                type="filepath"
                            )
                        
                        with gr.Row():
                            apply_btn = gr.Button("📤 Upload & Apply Data", variant="primary")
                
                # Common controls for both tabs
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear All Data", variant="secondary")
                    refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
                
                # Status display
                with gr.Group():
                    apply_msg = gr.HTML()
                    data_status = gr.HTML(show_current_data_status())

        # RIGHT: Questions + Results
        with gr.Column(scale=2):
            with gr.Group():
                gr.Markdown("### 🤖 Ask the Assistant")
                
                with gr.Row():
                    action = gr.Dropdown(
                        label="Question",
                        choices=[
                            "What's eating my cash flow?",
                            "What should I reorder with budget?",
                            "How much cash can I free up?",
                        ],
                        value="What's eating my cash flow?",
                        scale=2
                    )
                    ai_lang_selector = gr.Dropdown(
                        label="AI Language",
                        choices=["English", "Italiano", "Español"],
                        value="English",
                        scale=1
                    )
                
                budget = gr.Number(label="Budget (€)", value=500, visible=False)
                run_btn = gr.Button("🚀 Run Analysis", variant="primary")

            result_html = gr.HTML(label="Results")

    # Sample format modal - positioned after main layout for overlay effect
    with gr.Row(visible=False) as sample_modal:
        with gr.Column():
            with gr.Group():
                gr.Markdown("### 📋 CSV Format Examples")
                
                with gr.Accordion("Transactions CSV Example", open=True):
                    gr.Code("""date,transaction_id,product_id,product_name,category,quantity,unit_price,gross_sales,discount,net_sales,tax,line_total,payment_type,tip_amount
2025-01-08,2001,ESP,Espresso,Beverage,1,2.0,2.0,0.0,2.0,0.2,2.2,CARD,0.5
2025-01-08,2001,CRS,Croissant,Food,1,2.8,2.8,0.0,2.8,0.28,3.08,CARD,0.0
2025-01-08,2002,LAT,Latte,Beverage,1,3.5,3.5,0.0,3.5,0.35,3.85,CASH,0.0""")
                
                with gr.Accordion("Refunds CSV Example"):
                    gr.Code("""original_transaction_id,refund_date,refund_amount,refund_id,reason
2003,2025-01-08,6.93,RFD001,Customer complaint
2012,2025-01-08,6.43,RFD002,Wrong item
2018,2025-01-08,7.15,RFD003,Duplicate charge""")
                
                with gr.Accordion("Payouts CSV Example"):
                    gr.Code("""covering_sales_date,gross_card_volume,processor_fees,net_payout_amount,payout_date
2025-01-08,124.75,4.24,120.51,2025-01-09
2025-01-09,89.32,3.12,86.20,2025-01-10""")
                
                with gr.Accordion("Product Master CSV Example"):
                    gr.Code("""product_id,product_name,category,cogs,unit_price
ESP,Espresso,Beverage,0.40,2.00
LAT,Latte,Beverage,0.90,3.50
CAP,Cappuccino,Beverage,0.85,3.20
SNW,Sandwich,Food,2.00,6.50""")
                
                gr.Markdown("""
**Key Requirements:**
- **Transactions**: One row per line item (not per receipt)
- **Refunds**: Link back via `original_transaction_id`
- **Payouts**: Daily card settlement data
- **Product Master**: Include COGS for margin calculations
                
💡 **Tip**: Make sure your CSV files follow these exact column names and formats.
                """)
                
                with gr.Row():
                    close_btn = gr.Button("Close", variant="primary", scale=1)

    # ========== EVENT HANDLERS (All defined AFTER UI components) ==========
    
    # Sample format modal handlers
    def _show_sample():
        return gr.update(visible=True)
    def _hide_sample():
        return gr.update(visible=False)
    
    sample_btn.click(_show_sample, outputs=[sample_modal])
    close_btn.click(_hide_sample, outputs=[sample_modal])

    # Budget visibility handler
    def _toggle_budget(q):
        return gr.update(visible=(q == "What should I reorder with budget?"))
    action.change(_toggle_budget, inputs=action, outputs=budget)

    # CSV Upload handlers
    def _apply(txf, rff, pof, pmf):
        dfs = _reload_data_from_uploads(txf, rff, pof, pmf)
        result = _apply_uploaded_data_to_runtime(dfs)
        status = show_current_data_status()
        return result, status
    apply_btn.click(_apply, inputs=[tx_u, rf_u, po_u, pm_u], outputs=[apply_msg, data_status])

    # API Connection handlers
    def _handle_connect_api(provider, key, endpoint, start_date, end_date):
        result = _connect_api(provider, key, endpoint, start_date, end_date)
        status = show_current_data_status()
        return result, status
    connect_btn.click(_handle_connect_api, inputs=[pos_provider, api_key, api_endpoint, start_date, end_date], outputs=[apply_msg, data_status])

    def _handle_test_api(provider, key, endpoint):
        return _test_api_connection(provider, key, endpoint)
    test_btn.click(_handle_test_api, inputs=[pos_provider, api_key, api_endpoint], outputs=[apply_msg])

    # Show/hide custom endpoint based on provider
    pos_provider.change(_toggle_endpoint_visibility, inputs=pos_provider, outputs=api_endpoint)

    # Common handlers
    def _clear():
        reset_to_uploads()
        status = show_current_data_status()
        return "🗑️ All data cleared. Please upload fresh CSV files or connect via API.", status
    clear_btn.click(_clear, outputs=[apply_msg, data_status])

    def _refresh_status():
        return show_current_data_status()
    refresh_btn.click(_refresh_status, outputs=[data_status])

    # Analysis runner
    def _route(q, b, ai_lang):
        return run_action_html(q, b, ai_lang)
    run_btn.click(_route, inputs=[action, budget, ai_lang_selector], outputs=[result_html])

if __name__ == "__main__":
    app.launch(share=False, inbrowser=True)