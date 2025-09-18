#!/bin/bash
# deploy_pilot.sh - Quick deployment script for pilot clients

echo "🚀 Deploying AI Cash Flow Assistant for Pilot Clients"
echo "=================================================="

# Check if we're on a cloud instance
if [ -f /etc/cloud/cloud.cfg ]; then
    echo "✅ Cloud instance detected"
else
    echo "⚠️  Local deployment - consider using cloud for pilots"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install python-dotenv  # For environment variables

# Create .env file for configuration
cat > .env << EOF
# AI Cash Flow Assistant - Pilot Configuration
ANTHROPIC_API_KEY=your_claude_api_key_here
DEBUG=False
PORT=7860
MAX_CONCURRENT_SESSIONS=10
SESSION_CLEANUP_HOURS=24

# Pilot-specific settings
PILOT_MODE=True
PILOT_CLIENT_1=coffee_shop_alpha
PILOT_CLIENT_2=restaurant_beta
EOF

echo "📝 Created .env configuration file"
echo "❗ IMPORTANT: Edit .env and add your actual Claude API key"

# Create pilot-specific app
cat > src/app_pilot.py << 'PYTHON_EOF'
# src/app_pilot.py - Pilot deployment with session management
import gradio as gr
import os
from dotenv import load_dotenv
from session_analysis import SessionManager, SessionAnalyzer
from utils import load_csv_from_uploads
import threading
import time

# Load environment variables
load_dotenv()

# Pilot configuration
PILOT_MODE = os.getenv('PILOT_MODE', 'True').lower() == 'true'
MAX_SESSIONS = int(os.getenv('MAX_CONCURRENT_SESSIONS', '10'))
CLEANUP_HOURS = int(os.getenv('SESSION_CLEANUP_HOURS', '24'))

# Session cleanup thread
def session_cleanup_worker():
    """Background thread to clean up old sessions"""
    while True:
        try:
            cleaned = SessionManager.cleanup_old_sessions(CLEANUP_HOURS)
            if cleaned > 0:
                print(f"🧹 Cleaned up {cleaned} old sessions")
        except Exception as e:
            print(f"⚠️ Session cleanup error: {e}")
        time.sleep(3600)  # Run every hour

# Start cleanup thread
cleanup_thread = threading.Thread(target=session_cleanup_worker, daemon=True)
cleanup_thread.start()

# Mobile-optimized CSS
mobile_css = """
@media (max-width: 768px) {
    .gradio-container { padding: 10px !important; }
    .block { margin: 5px 0 !important; }
    .gr-button { min-height: 44px !important; font-size: 16px !important; }
    input, select { font-size: 16px !important; min-height: 44px !important; }
    table { font-size: 12px !important; overflow-x: auto !important; }
    h1, h2, h3 { font-size: 1.2em !important; margin: 10px 0 !important; }
}

.pilot-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 20px;
}

.status-success { 
    background-color: #d4edda; 
    border: 1px solid #c3e6cb; 
    color: #155724; 
    padding: 10px; 
    border-radius: 5px; 
}

.ai-insights {
    background-color: #e8f5e8;
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #28a745;
}
"""

def _df_html_mobile(df, title=None):
    """Mobile-optimized table display"""
    if df is None or getattr(df, "empty", True):
        return ""
    
    # Limit for mobile display
    if len(df) > 5:
        df_display = df.head(5)
        more_info = f"<small>Showing 5 of {len(df)} rows</small>"
    else:
        df_display = df
        more_info = ""
    
    heading = f"<h4>{title}</h4>" if title else ""
    table_html = df_display.to_html(index=False, classes="table", border=0)
    
    return f"<div>{heading}<div style='overflow-x:auto;'>{table_html}</div>{more_info}</div>"

# Create Gradio interface
with gr.Blocks(title="AI Cash Flow Assistant - Pilot", css=mobile_css) as app:
    
    # Pilot header
    gr.HTML("""
    <div class="pilot-header">
        <h1>☕ AI Cash Flow Assistant</h1>
        <p>Pilot Version - Coffee Shops & Restaurants</p>
        <small>Mobile-optimized | Session-based | Concurrent users supported</small>
    </div>
    """)
    
    # Hidden session ID state
    session_id = gr.State(value=SessionManager.create_session)
    
    # Status display
    status = gr.HTML("📱 Upload your CSV files to begin")
    
    # File uploads - optimized for mobile
    with gr.Group():
        gr.Markdown("### 📁 Upload Data")
        tx_file = gr.File(label="📊 Transactions", file_types=[".csv"])
        rf_file = gr.File(label="↩️ Refunds", file_types=[".csv"])
        po_file = gr.File(label="💳 Payouts", file_types=[".csv"])
        pm_file = gr.File(label="📦 Products", file_types=[".csv"])
        
        upload_btn = gr.Button("📤 Load Data", variant="primary", size="lg")
    
    # Analysis interface
    with gr.Group():
        gr.Markdown("### 🤖 Analysis")
        
        question = gr.Dropdown(
            choices=[
                "What's eating my cash flow?",
                "What should I reorder with budget?",
                "How much cash can I free up?"
            ],
            value="What's eating my cash flow?",
            label="Question"
        )
        
        budget = gr.Number(value=500, label="Budget (€)", visible=False)
        language = gr.Dropdown(
            choices=["English", "Italiano", "Español"],
            value="English",
            label="Language"
        )
        
        analyze_btn = gr.Button("🚀 Analyze", variant="primary", size="lg")
    
    # Results
    results = gr.HTML()
    
    # Quick actions
    with gr.Row():
        clear_btn = gr.Button("🗑️ Clear", size="sm")
        new_session_btn = gr.Button("🔄 New Session", size="sm")
    
    # Event handlers
    def handle_upload(sid, tx, rf, po, pm):
        try:
            if not any([tx, rf, po, pm]):
                return "📱 Please select CSV files to upload"
            
            analyzer = SessionAnalyzer(sid)
            dfs = load_csv_from_uploads(tx, rf, po, pm)
            
            if not dfs:
                return "⚠️ No valid CSV files found"
            
            # Set data in session
            analyzer.set_data(
                transactions=dfs.get("tx"),
                refunds=dfs.get("rf"),
                payouts=dfs.get("po"),
                products=dfs.get("pm")
            )
            
            summary = "✅ Data loaded!\n\n"
            file_map = {"tx": "Transactions", "rf": "Refunds", "po": "Payouts", "pm": "Products"}
            for key, df in dfs.items():
                summary += f"• {file_map[key]}: {len(df)} rows\n"
            
            return summary + "\n🚀 Ready for analysis!"
            
        except Exception as e:
            return f"❌ Upload error: {str(e)}"
    
    def handle_analysis(sid, q, b, lang):
        try:
            analyzer = SessionAnalyzer(sid)
            
            if q == "What's eating my cash flow?":
                snap, ce, low, ai = analyzer.cash_eaters(lang)
                html = snap + _df_html_mobile(ce, "💸 Cash Drains")
                html += _df_html_mobile(low, "📉 Low Margins") + ai
                return html
                
            elif q == "What should I reorder with budget?":
                snap, msg, plan, ai = analyzer.reorder_plan(b or 500, lang)
                html = snap + f"<div class='status-success'>{msg}</div>"
                html += _df_html_mobile(plan, "🛒 Purchase Plan") + ai
                return html
                
            else:  # Free up cash
                # Simplified for pilot
                return analyzer.executive_snapshot() + """
                <div class='ai-insights'>
                <h4>🤖 Cash Liberation Analysis</h4>
                <p>Feature coming soon in full version!</p>
                </div>
                """
                
        except Exception as e:
            return f"<div class='status-error'>Analysis error: {str(e)}</div>"
    
    def toggle_budget(q):
        return gr.update(visible=(q == "What should I reorder with budget?"))
    
    def create_new_session():
        new_sid = SessionManager.create_session()
        return new_sid, "🔄 New session created. Upload your data."
    
    def clear_session(sid):
        SessionManager.clear_session(sid)
        return "🗑️ Session cleared"
    
    # Wire up events
    question.change(toggle_budget, inputs=question, outputs=budget)
    upload_btn.click(handle_upload, inputs=[session_id, tx_file, rf_file, po_file, pm_file], outputs=status)
    analyze_btn.click(handle_analysis, inputs=[session_id, question, budget, language], outputs=results)
    new_session_btn.click(create_new_session, outputs=[session_id, status])
    clear_btn.click(clear_session, inputs=session_id, outputs=status)

if __name__ == "__main__":
    # Pilot deployment settings
    app.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=int(os.getenv('PORT', 7860)),
        share=False,  # Don't use Gradio share for pilots
        auth=None,  # Add auth later if needed
        show_api=False,
        favicon_path=None,
        inbrowser=False  # Don't auto-open browser on server
    )
PYTHON_EOF

echo "✅ Created pilot app with session management"

# Create systemd service for production deployment
cat > ai-cashflow-pilot.service << EOF
[Unit]
Description=AI Cash Flow Assistant - Pilot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ai_pos
Environment=PATH=/home/ubuntu/ai_pos/venv/bin
ExecStart=/home/ubuntu/ai_pos/venv/bin/python src/app_pilot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📋 Created systemd service file"

# Create nginx configuration
cat > nginx-pilot.conf << EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with actual domain
    
    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support for Gradio
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Mobile optimization
        proxy_buffering off;
        proxy_cache off;
    }
}
EOF

echo "🌐 Created nginx configuration"

# Create quick start script
cat > start_pilot.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting AI Cash Flow Assistant - Pilot Mode"

# Check if .env exists and has API key
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please create it first."
    exit 1
fi

if ! grep -q "sk-ant-" .env; then
    echo "⚠️  WARNING: No Claude API key found in .env"
    echo "Please add your ANTHROPIC_API_KEY to .env file"
fi

# Start the application
echo "📱 Starting mobile-optimized pilot app..."
echo "🌐 Will be available at: http://localhost:7860"
echo "📱 Mobile users can access via: http://YOUR_SERVER_IP:7860"
echo ""
echo "Press Ctrl+C to stop"

python src/app_pilot.py
EOF

chmod +x start_pilot.sh

echo ""
echo "🎉 Pilot deployment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your Claude API key"
echo "2. Run: ./start_pilot.sh"
echo "3. Test on mobile: http://YOUR_SERVER_IP:7860"
echo ""
echo "For production deployment:"
echo "1. Copy ai-cashflow-pilot.service to /etc/systemd/system/"
echo "2. Setup nginx with the provided config"
echo "3. Get SSL certificate (Let's Encrypt recommended)"
echo ""
echo "📱 Mobile-optimized ✅"
echo "👥 Concurrent users ✅"  
echo "🧹 Auto session cleanup ✅"
echo "☁️  Cloud deployment ready ✅"