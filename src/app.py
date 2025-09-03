import gradio as gr
import pandas as pd
from analysis import (
    cash_eaters_with_ai, reorder_plan_with_ai, free_up_cash_with_ai, 
    sales_impact_analysis_with_ai, executive_snapshot
)
from utils import (
    load_csv_from_uploads, persist_uploads_to_data_dir,
    validate_schema_or_raise, DEFAULT_SCHEMAS
)
from config import get_claude_key, validate_claude_key
import os

def _df_html(df, title=None):
    if df is None or getattr(df, "empty", True):
        return ""
    heading = f"<h4>{title}</h4>" if title else ""
    return heading + df.to_html(index=False, border=0, classes="table", justify="left")

def _ai_response_html(ai_response):
    if not ai_response or ai_response.startswith("AI Analysis Error"):
        return f'<div style="background-color: #ffebee; padding: 10px; border-radius: 5px; color: #c62828;"><strong>⚠️ {ai_response}</strong></div>'
    
    return f'''
    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #4caf50;">
        <h4 style="color: #2e7d32; margin-top: 0;">🤖 AI Analysis</h4>
        <div style="color: #1b5e20; line-height: 1.6;">{ai_response.replace(chr(10), "<br>")}</div>
    </div>
    '''

def _reload_data_from_uploads(tx_u, rf_u, po_u, pm_u):
    return load_csv_from_uploads(tx_u, rf_u, po_u, pm_u)

def _apply_uploaded_data_to_runtime(dfs: dict):
    if not dfs:
        return "No files uploaded. Using existing /data files."
    for key, df in dfs.items():
        validate_schema_or_raise(key, df, DEFAULT_SCHEMAS[key])
    persist_uploads_to_data_dir(dfs)
    import importlib, analysis
    importlib.reload(analysis)
    return "✅ Data applied. Analysis reloaded."

def run_action_with_ai(action, budget, pos_api_key):
    # Use Claude API key instead of OpenAI
    from config import get_claude_key, validate_claude_key
    
    claude_key = get_claude_key()
    
    if claude_key and validate_claude_key(claude_key):
        os.environ["ANTHROPIC_API_KEY"] = claude_key
        try:
            from analysis import ai_assistant
            ai_assistant.set_api_key(claude_key)
        except:
            pass

    if action == "What's eating my cash flow?":
        try:
            snap, ce, low, ai_analysis = cash_eaters_with_ai()
            html = snap
            html += _df_html(ce, "💸 Cash Eaters (Discounts / Refunds / Fees)")
            html += _df_html(low, "📉 Lowest-Margin SKUs")
            html += _ai_response_html(ai_analysis)  # AI Analysis at the bottom
            return html
        except Exception as e:
            from analysis import cash_eaters
            snap, ce, low = cash_eaters()
            html = snap
            html += _df_html(ce, "💸 Cash Eaters (Discounts / Refunds / Fees)")
            html += _df_html(low, "📉 Lowest-Margin SKUs")
            html += f'<div style="background-color: #fff3cd; padding: 10px; border-radius: 5px;"><strong>ℹ️ AI analysis unavailable: {str(e)}</strong></div>'
            return html

    if action == "What should I reorder with budget?":
        try:
            snap, msg, plan, ai_analysis = reorder_plan_with_ai(float(budget or 0))
            html = snap + f"<p><b>{msg}</b></p>"
            html += _df_html(plan, "🛒 Suggested Purchase Plan")
            html += _ai_response_html(ai_analysis)  # AI Analysis at the bottom
            return html
        except Exception as e:
            from analysis import reorder_plan
            snap, msg, plan = reorder_plan(float(budget or 0))
            html = snap + f"<p><b>{msg}</b></p>"
            html += _df_html(plan, "🛒 Suggested Purchase Plan")
            html += f'<div style="background-color: #fff3cd; padding: 10px; border-radius: 5px;"><strong>ℹ️ AI unavailable: {str(e)}</strong></div>'
            return html

    if action == "How much cash can I free up?":
        try:
            snap, msg, slow, ai_analysis = free_up_cash_with_ai()
            html = snap + f"<p><b>{msg}</b></p>"
            html += _df_html(slow, "🏷️ Slow-Mover Clearance Estimate")
            html += _ai_response_html(ai_analysis)  # AI Analysis at the bottom
            return html
        except Exception as e:
            from analysis import free_up_cash
            snap, msg, slow = free_up_cash()
            html = snap + f"<p><b>{msg}</b></p>"
            html += _df_html(slow, "🏷️ Slow-Mover Clearance Estimate")
            html += f'<div style="background-color: #fff3cd; padding: 10px; border-radius: 5px;"><strong>ℹ️ AI unavailable: {str(e)}</strong></div>'
            return html

    if action == "If sales drop 10% next month, impact on runway?":
        try:
            snap, ai_analysis = sales_impact_analysis_with_ai(10)
            html = snap
            html += _ai_response_html(ai_analysis)  # AI Analysis at the bottom (only content here)
            return html
        except Exception as e:
            snap = executive_snapshot()
            html = snap
            html += f'<div style="background-color: #fff3cd; padding: 10px; border-radius: 5px;"><strong>ℹ️ AI unavailable: {str(e)}</strong></div>'
            html += "<p><i>📊 Forecast model placeholder: would run a 4–12 week cash model with -10% sales.</i></p>"
            return html

    return executive_snapshot()

with gr.Blocks(title="AI POS – Cash Flow Assistant (POC)") as app:
    gr.Markdown("# AI POS – Cash Flow Assistant (POC)")
    gr.Markdown("Upload your POS data **or** paste an API key, choose a question, and get actionable insights.")

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("### Data Input")
                api_key = gr.Textbox(
                    label="POS API Key (optional)",
                    type="password",
                    placeholder="Paste your POS API key (not used in this POC)."
                )
                gr.Markdown("**OR upload CSV files:**")
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
            apply_msg = gr.Markdown()

            with gr.Accordion("CSV format guide (click to expand)", open=False):
                gr.Markdown("""
**Transactions CSV — required columns**

date,transaction_id,product_id,product_name,category,quantity,unit_price,
gross_sales,discount,net_sales,tax,line_total,payment_type,tip_amount

**Refunds CSV — required columns**

original_transaction_id,refund_date,refund_amount

**Payouts CSV — required columns**

covering_sales_date,gross_card_volume,processor_fees,net_payout_amount,payout_date

**Product Master CSV — required columns**

product_id,product_name,category,cogs

**Notes**
- *Transactions* should be **line-item** level (not one row per receipt).
- *Refunds* link back via `original_transaction_id`; `refund_date` is when cash leaves.
- *Payouts* represent processor settlements (e.g., D+1) for **card** volume.
- *Product Master* provides `cogs` to compute margins.
""")

        with gr.Column(scale=2):
            with gr.Group():
                gr.Markdown("### Ask the Assistant")
                action = gr.Dropdown(
                    label="Question",
                    choices=[
                        "What's eating my cash flow?",
                        "What should I reorder with budget?",
                        "How much cash can I free up?",
                        "If sales drop 10% next month, impact on runway?",
                    ],
                    value="What's eating my cash flow?"
                )
                budget = gr.Number(label="Budget (€)", value=500, visible=False)
                run_btn = gr.Button("Run")

            result_html = gr.HTML(label="Results")

    def _toggle_budget(q):
        return gr.update(visible=(q == "What should I reorder with budget?"))
    action.change(_toggle_budget, inputs=action, outputs=budget)

    def _apply(pos_api_key_val, txf, rff, pof, pmf):
        dfs = _reload_data_from_uploads(txf, rff, pof, pmf)
        return _apply_uploaded_data_to_runtime(dfs)
    apply_btn.click(_apply, inputs=[api_key, tx_u, rf_u, po_u, pm_u], outputs=[apply_msg])

    run_btn.click(run_action_with_ai, inputs=[action, budget, api_key], outputs=[result_html])

    def load_initial():
        return run_action_with_ai("What's eating my cash flow?", 500, "")
    app.load(load_initial, outputs=[result_html])

if __name__ == "__main__":
    print("🚀 Starting AI POS Cash Flow Assistant...")
    
    env_key = get_claude_key()
    if env_key and validate_claude_key(env_key):
        print("✅ AI analysis ready (Claude configured)")
    else:
        print("⚠️  AI analysis limited (Claude not configured)")
        print("💡 Basic analytics still available")
    
    app.launch(share=False, inbrowser=True)