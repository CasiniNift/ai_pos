# src/app.py

import gradio as gr
import pandas as pd
from analysis import cash_eaters, reorder_plan, free_up_cash, executive_snapshot
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
    """Persist uploads to /data and hot-reload analysis by reimporting it."""
    if not dfs:
        return "No files uploaded. Using existing /data files."
    # Validate schemas (required columns)
    for key, df in dfs.items():
        validate_schema_or_raise(key, df, DEFAULT_SCHEMAS[key])
    # Persist to /data/
    persist_uploads_to_data_dir(dfs)
    # Hot-reload analysis so functions pick up new data immediately
    import importlib, analysis
    importlib.reload(analysis)
    return "✅ Data applied. Analysis reloaded."

def run_action_html(action, budget):
    """Route selected question → formatted HTML output."""
    if action == "Cash Eaters":
        snap, ce, low = cash_eaters()
        html = snap
        html += _df_html(ce, "Cash Eaters (Discounts / Refunds / Fees)")
        html += _df_html(low, "Lowest-Margin SKUs")
        return html

    if action == "What should I reorder with budget?":
        snap, msg, plan = reorder_plan(float(budget or 0))
        html = snap + f"<p><b>{msg}</b></p>"
        html += _df_html(plan, "Suggested Purchase Plan")
        return html

    if action == "How much cash can I free up?":
        snap, msg, slow = free_up_cash()
        html = snap + f"<p><b>{msg}</b></p>"
        html += _df_html(slow, "Slow-Mover Clearance Estimate")
        return html

    if action == "If sales drop 10% next month, impact on runway?":
        snap = executive_snapshot()
        html = snap + "<p><i>Forecast model placeholder: would run a 4–12 week cash model with -10% sales.</i></p>"
        return html

    return executive_snapshot()

# ---------- UI Layout ----------

with gr.Blocks(title="AI POS – Cash Flow Assistant (POC)") as app:
    gr.Markdown("# AI POS – Cash Flow Assistant (POC)")
    gr.Markdown("Upload your POS data **or** paste an API key, choose a question, and get actionable insights.")

    with gr.Row():
        # LEFT: Data inputs (with descriptions + format guide)
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

        # RIGHT: Questions + Results (single panel)
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

            # One tidy results panel
            result_html = gr.HTML(label="Results")

    # Toggle budget visibility based on question
    def _toggle_budget(q):
        return gr.update(visible=(q == "What should I reorder with budget?"))
    action.change(_toggle_budget, inputs=action, outputs=budget)

    # Apply data uploads (and hot-reload analysis)
    def _apply(api_key_val, txf, rff, pof, pmf):
        dfs = _reload_data_from_uploads(txf, rff, pof, pmf)
        return _apply_uploaded_data_to_runtime(dfs)
    apply_btn.click(_apply, inputs=[api_key, tx_u, rf_u, po_u, pm_u], outputs=[apply_msg])

    # Route selected action → HTML output
    def _route(q, b):
        mapping = {
            "What's eating my cash flow?": "Cash Eaters",
            "What should I reorder with budget?": "What should I reorder with budget?",
            "How much cash can I free up?": "How much cash can I free up?",
            "If sales drop 10% next month, impact on runway?": "If sales drop 10% next month, impact on runway?"
        }
        return run_action_html(mapping[q], b)
    run_btn.click(_route, inputs=[action, budget], outputs=[result_html])

if __name__ == "__main__":
    app.launch(share=False, inbrowser=True)