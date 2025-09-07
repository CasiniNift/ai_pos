# src/app.py - Clean English UI with AI translation option

import gradio as gr
import pandas as pd
from analysis import cash_eaters, reorder_plan, free_up_cash, executive_snapshot, set_data, reset_to_defaults
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
    """Apply uploaded data to analysis functions or reset to defaults."""
    if not dfs:
        reset_to_defaults()
        return "🔄 Using default data from /data directory."
    
    try:
        for key, df in dfs.items():
            validate_schema_or_raise(key, df, DEFAULT_SCHEMAS[key])
        
        persist_uploads_to_data_dir(dfs)
        
        set_data(
            transactions=dfs.get("tx"),
            refunds=dfs.get("rf"), 
            payouts=dfs.get("po"),
            products=dfs.get("pm")
        )
        
        return "✅ Uploaded data applied successfully!"
        
    except Exception as e:
        reset_to_defaults()
        return f"❌ Error applying data: {str(e)}. Reset to defaults."

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

# ---------- UI Layout ----------

with gr.Blocks(title="AI POS – Cash Flow Assistant (POC)", css="""
    .ai-toggle { background-color: #e8f5e8; padding: 10px; border-radius: 5px; }
""") as app:
    gr.Markdown("# AI POS – Cash Flow Assistant (POC)")
    gr.Markdown("Upload your POS data or paste an API key, choose a question, and get actionable insights.")

    with gr.Row():
        # LEFT: Data inputs
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("### Data Input")
                api_key = gr.Textbox(
                    label="POS API Key (optional)",
                    type="password",
                    placeholder="Paste your POS API key (not used in this POC)."
                )
                gr.Markdown("**OR upload CSV files:**")
                gr.Markdown("*Leave files empty to use default sample data*")
                
                # Add sample format button
                sample_btn = gr.Button("📋 Sample CSV Format( Scroll Down to the Bottom of the Page )", size="sm")
                
                tx_u = gr.File(
                    label="Transactions CSV - All transaction line items (sales). One row per line item.",
                    file_types=[".csv"],
                    type="filepath"
                )
                rf_u = gr.File(
                    label="Refunds CSV - Only refunds. Each row represents a refund tied to an original transaction.",
                    file_types=[".csv"],
                    type="filepath"
                )
                po_u = gr.File(
                    label="Payouts CSV - Card settlement batches (processor payouts). Typically daily.",
                    file_types=[".csv"],
                    type="filepath"
                )
                pm_u = gr.File(
                    label="Product Master CSV - Catalog with COGS per product.",
                    file_types=[".csv"],
                    type="filepath"
                )
                apply_btn = gr.Button("Apply Data")
                reset_btn = gr.Button("Reset to Sample Data", variant="secondary")
            apply_msg = gr.Markdown()

        # RIGHT: Questions + Results
        with gr.Column(scale=2):
            with gr.Group():
                gr.Markdown("### Ask the Assistant")
                
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
                run_btn = gr.Button("Run", variant="primary")

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
                
💡 **Tip**: Download these examples as templates for your own data formatting.
                """)
                
                with gr.Row():
                    close_btn = gr.Button("Close", variant="primary", scale=1)

    # Sample format modal handlers
    def _show_sample():
        return gr.update(visible=True)
    def _hide_sample():
        return gr.update(visible=False)
    sample_btn.click(_show_sample, outputs=[sample_modal])
    close_btn.click(_hide_sample, outputs=[sample_modal])

    # Event handlers
    def _toggle_budget(q):
        return gr.update(visible=(q == "What should I reorder with budget?"))
    action.change(_toggle_budget, inputs=action, outputs=budget)

    def _apply(api_key_val, txf, rff, pof, pmf):
        dfs = _reload_data_from_uploads(txf, rff, pof, pmf)
        return _apply_uploaded_data_to_runtime(dfs)
    apply_btn.click(_apply, inputs=[api_key, tx_u, rf_u, po_u, pm_u], outputs=[apply_msg])

    def _reset():
        reset_to_defaults()
        return "🔄 Reset to default sample data."
    reset_btn.click(_reset, outputs=[apply_msg])

    def _route(q, b, ai_lang):
        return run_action_html(q, b, ai_lang)
    run_btn.click(_route, inputs=[action, budget, ai_lang_selector], outputs=[result_html])

if __name__ == "__main__":
    app.launch(share=False, inbrowser=True)