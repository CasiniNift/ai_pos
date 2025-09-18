# src/app_mobile_minimal.py - Start with working app.py and add minimal mobile fixes

# Copy the EXACT working app.py imports and functions
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

# ---------- Helpers (EXACT copy from working app.py) ----------

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

# ---------- UI Layout (Same as working app.py with ONLY mobile CSS added) ----------

with gr.Blocks(title="AI POS – Cash Flow Assistant (Mobile)", css="""
    /* ONLY add mobile text wrapping - keep everything else the same */
    @media (max-width: 768px) {
        .gradio-container {
            padding: 10px !important;
        }
        
        .gr-button {
            min-height: 44px !important;
            font-size: 16px !important;
        }
        
        input, select, textarea {
            font-size: 16px !important;
            min-height: 44px !important;
        }
    }
    
    /* Essential text wrapping fixes */
    .gr-html {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        max-width: 100% !important;
        overflow-x: hidden !important;
    }
    
    /* Keep original app.py styles */
    .ai-toggle { 
        background-color: #e8f5e8; 
        padding: 10px; 
        border-radius: 5px; 
    }
    
    .upload-area { 
        background-color: #f8f9fa; 
        padding: 15px; 
        border-radius: 8px; 
        border: 2px dashed #dee2e6; 
    }
    
    .status-box { 
        background-color: #e3f2fd; 
        padding: 10px; 
        border-radius: 5px; 
        margin: 10px 0; 
    }
""") as app:
    
    gr.Markdown("# AI POS – Cash Flow Assistant (Mobile)")
    gr.Markdown("**Upload your POS CSV data or connect via API to get AI-powered cash flow insights.**")

    with gr.Row():
        # LEFT: Data inputs (EXACT same as app.py)
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("### 🔌 Data Connection")
                gr.Markdown("Choose how to connect your POS data:")
                
                # Simplified for mobile - just CSV upload tab
                with gr.Tabs():
                    with gr.TabItem("📁 CSV Upload", id="csv_tab"):
                        gr.Markdown("**Upload CSV files manually**")
                        gr.Markdown("Upload all 4 CSV files to enable analysis:")
                        
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
                
                # Common controls
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear All Data", variant="secondary")
                    refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
                
                # Status display
                with gr.Group():
                    apply_msg = gr.HTML()
                    data_status = gr.HTML(show_current_data_status())

        # RIGHT: Questions + Results (EXACT same as app.py)
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

    # ========== EVENT HANDLERS (EXACT copy from app.py) ==========
    
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

# ---------- Launch with public URL ----------
if __name__ == "__main__":
    app.launch(
        share=True,  # Creates public URL
        inbrowser=True,
        server_port=7862  # Different port
    )