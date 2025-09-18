# minimal_app.py - Working version that bypasses Gradio API issues

import gradio as gr
import pandas as pd
import sys
import os

# Add src to path so we can import our modules
sys.path.append('src')

try:
    from analysis import cash_eaters, executive_snapshot, set_data
    from utils import load_csv_from_uploads, validate_schema_or_raise, DEFAULT_SCHEMAS
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

def process_files(tx_file, rf_file, po_file, pm_file):
    """Process uploaded CSV files"""
    if not any([tx_file, rf_file, po_file, pm_file]):
        return "Please upload at least one CSV file to begin."
    
    try:
        dfs = load_csv_from_uploads(tx_file, rf_file, po_file, pm_file)
        
        if not dfs:
            return "No valid CSV files found. Please check your files and try again."
        
        # Validate schemas
        for key, df in dfs.items():
            if key in DEFAULT_SCHEMAS:
                validate_schema_or_raise(key, df, DEFAULT_SCHEMAS[key])
        
        # Set data in analysis module
        set_data(
            transactions=dfs.get("tx"),
            refunds=dfs.get("rf"),
            payouts=dfs.get("po"),
            products=dfs.get("pm")
        )
        
        # Build success message
        file_names = {"tx": "Transactions", "rf": "Refunds", "po": "Payouts", "pm": "Products"}
        summary = "Data loaded successfully!\n\n"
        for key, df in dfs.items():
            summary += f"✅ {file_names.get(key, key)}: {len(df)} rows\n"
        
        return summary + "\nYou can now run analysis questions!"
        
    except Exception as e:
        return f"Error processing files: {str(e)}"

def run_analysis(question):
    """Run cash flow analysis"""
    try:
        if question == "What's eating my cash flow?":
            snap, ce, low, ai_insights = cash_eaters()
            
            # Format results as text
            result = snap + "\n\n"
            
            if ce is not None and not ce.empty:
                result += "💸 Cash Drains:\n"
                for _, row in ce.iterrows():
                    result += f"• {row['category']}: €{row['amount']:,.2f}\n"
                result += "\n"
            
            if low is not None and not low.empty:
                result += "📉 Lowest Margin Products:\n"
                for _, row in low.head(3).iterrows():
                    margin = row.get('margin_pct', 0) * 100
                    result += f"• {row['product_name']}: {margin:.1f}% margin\n"
                result += "\n"
            
            # Add AI insights if available (strip HTML tags for text display)
            if ai_insights and "AI Analysis" in str(ai_insights):
                import re
                clean_ai = re.sub('<[^<]+?>', '', str(ai_insights))
                clean_ai = clean_ai.replace('AI Analysis', '🤖 AI Analysis')
                result += clean_ai
            
            return result
            
        else:
            return executive_snapshot() + "\n\n(Other analysis questions coming soon!)"
            
    except Exception as e:
        return f"Analysis error: {str(e)}\n\nPlease ensure you've uploaded all required CSV files first."

# Create simple interface
with gr.Blocks(title="AI Cash Flow Assistant - Minimal") as app:
    
    gr.Markdown("# AI Cash Flow Assistant")
    gr.Markdown("Upload your POS CSV data to get cash flow insights")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Upload CSV Files")
            
            tx_file = gr.File(label="Transactions CSV", file_types=[".csv"])
            rf_file = gr.File(label="Refunds CSV", file_types=[".csv"]) 
            po_file = gr.File(label="Payouts CSV", file_types=[".csv"])
            pm_file = gr.File(label="Product Master CSV", file_types=[".csv"])
            
            upload_btn = gr.Button("Load Data", variant="primary")
            
            gr.Markdown("### Ask Questions")
            question = gr.Dropdown(
                ["What's eating my cash flow?", "Executive Summary"], 
                value="What's eating my cash flow?",
                label="Question"
            )
            analyze_btn = gr.Button("Run Analysis", variant="primary")
        
        with gr.Column():
            gr.Markdown("### Results")
            output = gr.Textbox(
                label="Analysis Results",
                lines=20,
                max_lines=30,
                show_copy_button=True
            )
    
    # Event handlers
    upload_btn.click(
        process_files,
        inputs=[tx_file, rf_file, po_file, pm_file],
        outputs=output
    )
    
    analyze_btn.click(
        run_analysis,
        inputs=question,
        outputs=output
    )

if __name__ == "__main__":
    print("Starting minimal cash flow app...")
    app.launch(
        server_port=7863,  # Different port to avoid conflicts
        share=False,       # Disable sharing to reduce API calls
        show_api=False,    # Disable API docs
        show_error=True,
        inbrowser=True
    )