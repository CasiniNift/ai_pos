# src/app_mobile.py - Mobile-optimized version for pilots

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

# Mobile-optimized CSS
mobile_css = """
/* Mobile-first responsive design */
@media (max-width: 768px) {
    .gradio-container {
        padding: 10px !important;
    }
    
    .block {
        margin: 5px 0 !important;
    }
    
    .upload-area {
        padding: 10px !important;
        margin: 5px 0 !important;
    }
    
    /* Stack columns on mobile */
    .row {
        flex-direction: column !important;
    }
    
    /* Better button sizing */
    .gr-button {
        min-height: 44px !important;
        font-size: 16px !important;
        padding: 12px !important;
    }
    
    /* Improve table display */
    table {
        font-size: 12px !important;
        overflow-x: auto !important;
        display: block !important;
        white-space: nowrap !important;
    }
    
    /* Better form inputs */
    input, select, textarea {
        font-size: 16px !important; /* Prevents zoom on iOS */
        min-height: 44px !important;
    }
    
    /* Compact headers */
    h1, h2, h3 {
        font-size: 1.2em !important;
        margin: 10px 0 !important;
    }
}

/* Status indicators */
.status-success { 
    background-color: #d4edda; 
    border: 1px solid #c3e6cb; 
    color: #155724; 
    padding: 10px; 
    border-radius: 5px; 
    margin: 10px 0;
}

.status-error { 
    background-color: #f8d7da; 
    border: 1px solid #f1aeb5; 
    color: #721c24; 
    padding: 10px; 
    border-radius: 5px; 
    margin: 10px 0;
}

.ai-insights {
    background-color: #e8f5e8;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
    border-left: 4px solid #28a745;
}

/* Loading indicator */
.loading {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
"""

def _df_html_mobile(df, title=None):
    """Mobile-optimized DataFrame display"""
    if df is None or getattr(df, "empty", True):
        return ""
    
    # Limit columns and rows for mobile
    if len(df.columns) > 4:
        # Show only most important columns
        key_cols = df.columns[:4].tolist()
        df_display = df[key_cols].head(5)
        more_info = f"<p><small>Showing {len(key_cols)} of {len(df.columns)} columns, {len(df_display)} of {len(df)} rows</small></p>"
    else:
        df_display = df.head(10)
        more_info = ""
    
    heading = f"<h4>{title}</h4>" if title else ""
    table_html = df_display.to_html(
        index=False, 
        border=0, 
        classes="table table-striped", 
        justify="left",
        table_id="mobile-table"
    )
    
    return f"""
    <div class="table-container">
        {heading}
        <div style="overflow-x: auto;">
            {table_html}
        </div>
        {more_info}
    </div>
    """

def _apply_uploaded_data_to_runtime(dfs: dict):
    """Apply uploaded data to analysis functions with mobile-friendly messages"""
    if not dfs:
        return "📱 Please upload your CSV files to get started."
    
    # Check required files
    required_files = {"tx": "Transactions", "rf": "Refunds", "po": "Payouts", "pm": "Products"}
    missing_files = [desc for key, desc in required_files.items() if key not in dfs]
    
    if missing_files:
        return f"📋 Still need: {', '.join(missing_files)}"
    
    try:
        # Validate schemas
        for key, df in dfs.items():
            validate_schema_or_raise(key, df, DEFAULT_SCHEMAS[key])
        
        # Save and set data
        persist_uploads_to_data_dir(dfs)
        set_data(
            transactions=dfs.get("tx"),
            refunds=dfs.get("rf"), 
            payouts=dfs.get("po"),
            products=dfs.get("pm")
        )
        
        # Mobile-friendly summary
        summary = "✅ Data loaded successfully!\n\n"
        for key, df in dfs.items():
            file_names = {"tx": "Transactions", "rf": "Refunds", "po": "Payouts", "pm": "Products"}
            summary += f"• {file_names[key]}: {len(df)} rows\n"
        
        summary += "\n🚀 Ready for analysis!"
        return summary
        
    except Exception as e:
        return f"❌ Error: {str(e)}\n\nPlease check your files."

def run_action_html_mobile(action, budget, ai_lang):
    """Mobile-optimized analysis with simplified output"""
    try:
        if action == "What's eating my cash flow?":
            snap, ce, low, ai_insights = cash_eaters(ui_language=ai_lang)
            html = snap
            html += _df_html_mobile(ce, "💸 Cash Drains")
            html += _df_html_mobile(low, "📉 Low-Margin Items")
            html += ai_insights
            return html

        elif action == "What should I reorder with budget?":
            snap, msg, plan, ai_insights = reorder_plan(float(budget or 500), ui_language=ai_lang)
            html = snap + f"<div class='status-success'>{msg}</div>"
            html += _df_html_mobile(plan, "🛒 Purchase Plan")
            html += ai_insights
            return html

        elif action == "How much cash can I free up?":
            snap, msg, slow, ai_insights = free_up_cash(ui_language=ai_lang)
            html = snap + f"<div class='status-success'>{msg}</div>"
            html += _df_html_mobile(slow, "🐌 Slow Movers")
            html += ai_insights
            return html

        else:
            return executive_snapshot()
            
    except Exception as e:
        return f"<div class='status-error'>Error: {str(e)}</div>"

# Mobile-optimized layout
with gr.Blocks(
    title="AI Cash Flow Assistant", 
    css=mobile_css,
    theme=gr.themes.Soft()
) as app:
    
    # Header - more compact for mobile
    gr.Markdown("# ☕ AI Cash Flow Assistant")
    gr.Markdown("*Upload your POS data for instant insights*")
    
    # Status indicator
    with gr.Row():
        status_display = gr.HTML(value="📤 Upload CSV files to begin")
    
    # Simplified upload interface
    with gr.Group():
        gr.Markdown("### 📁 Upload Your Data")
        
        # Single column layout works better on mobile
        tx_upload = gr.File(
            label="📊 Transactions CSV", 
            file_types=[".csv"]
        )
        rf_upload = gr.File(
            label="↩️ Refunds CSV", 
            file_types=[".csv"]
        )
        po_upload = gr.File(
            label="💳 Payouts CSV", 
            file_types=[".csv"]
        )
        pm_upload = gr.File(
            label="📦 Products CSV", 
            file_types=[".csv"]
        )
        
        upload_btn = gr.Button(
            "📤 Load Data", 
            variant="primary",
            size="lg"
        )
    
    # Analysis interface
    with gr.Group():
        gr.Markdown("### 🤖 Ask Questions")
        
        question = gr.Dropdown(
            label="What would you like to know?",
            choices=[
                "What's eating my cash flow?",
                "What should I reorder with budget?", 
                "How much cash can I free up?"
            ],
            value="What's eating my cash flow?"
        )
        
        # Budget input - only show when relevant
        budget_input = gr.Number(
            label="Budget (€)", 
            value=500, 
            visible=False
        )
        
        # Language selector
        lang_selector = gr.Dropdown(
            label="Language",
            choices=["English", "Italiano", "Español"],
            value="English"
        )
        
        analyze_btn = gr.Button(
            "🚀 Analyze", 
            variant="primary",
            size="lg"
        )
    
    # Results area
    results = gr.HTML(label="Results")
    
    # Quick actions for mobile
    with gr.Row():
        clear_btn = gr.Button("🗑️ Clear", size="sm")
        refresh_btn = gr.Button("🔄 Refresh", size="sm")
    
    # Event handlers
    def toggle_budget(q):
        return gr.update(visible=(q == "What should I reorder with budget?"))
    
    def handle_upload(tx, rf, po, pm):
        dfs = load_csv_from_uploads(tx, rf, po, pm) if tx or rf or po or pm else {}
        result = _apply_uploaded_data_to_runtime(dfs)
        return result
    
    def handle_analysis(q, b, lang):
        return run_action_html_mobile(q, b, lang)
    
    def handle_clear():
        reset_to_uploads()
        return "🗑️ Data cleared. Upload fresh files."
    
    # Wire up events
    question.change(toggle_budget, inputs=question, outputs=budget_input)
    upload_btn.click(handle_upload, inputs=[tx_upload, rf_upload, po_upload, pm_upload], outputs=status_display)
    analyze_btn.click(handle_analysis, inputs=[question, budget_input, lang_selector], outputs=results)
    clear_btn.click(handle_clear, outputs=status_display)
    refresh_btn.click(lambda: get_data_status(), outputs=status_display)

if __name__ == "__main__":
    # Mobile-optimized launch settings
    app.launch(
        share=False, 
        inbrowser=True,
        server_port=7860,
        server_name="0.0.0.0",  # Allow external access
        show_api=False,  # Hide API docs for simpler interface
        favicon_path=None
    )