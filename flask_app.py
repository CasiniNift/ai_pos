# flask_app.py - Enhanced Flask version matching app.py structure and functionality
from flask import session
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
import pandas as pd
import sys
import os
from werkzeug.utils import secure_filename
import traceback
import uuid
from datetime import datetime

# Add src to path
sys.path.append('src')

try:
    from analysis import (
        cash_eaters, reorder_plan, free_up_cash, executive_snapshot, 
        set_data, reset_to_uploads, get_data_status, analyze_executive_summary
    )
    from utils import (
        load_csv_from_uploads, persist_uploads_to_data_dir,
        validate_schema_or_raise, DEFAULT_SCHEMAS
    )
    from ai_assistant import CashFlowAIAssistant
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = 'ai-pos-cash-flow-secret-key-change-in-production'  # Change in production
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max file size

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add language handling function to flask_app.py
def get_current_language():
    """Get current language from session or default to English"""
    return session.get('language', 'English')

def set_language(language):
    """Set language in session"""
    session['language'] = language

# Add language route to flask_app.py
@app.route('/set_language/<language>')
def set_language_route(language):
    """Set the interface language"""
    valid_languages = ['English', 'Italiano']
    if language in valid_languages:
        session['language'] = language
        flash(f'Language changed to {language}', 'success')
    else:
        flash('Invalid language selected', 'error')
    
    # Redirect back to the page they came from
    return redirect(request.referrer or url_for('index'))

# Initialize AI assistant
ai_assistant = CashFlowAIAssistant()

def format_df_as_html(df, title=None):
    """Format DataFrame as HTML table with responsive design"""
    if df is None or df.empty:
        return ""
    
    heading = f"<h4 class='mb-3'>{title}</h4>" if title else ""
    table_html = df.to_html(
        index=False, 
        classes="table table-striped table-responsive table-hover",
        table_id=f"table-{title.lower().replace(' ', '-')}" if title else "data-table"
    )
    
    return f"""
    <div class="table-container mb-4">
        {heading}
        <div class="table-responsive">
            {table_html}
        </div>
    </div>
    """

def clean_currency_display(value):
    """Clean and format currency values for display"""
    if pd.isna(value):
        return "€0.00"
    try:
        return f"€{float(value):,.2f}"
    except (ValueError, TypeError):
        return "€0.00"

@app.route('/')
def index():
    """Main dashboard page matching app.py layout"""
    data_status = get_data_status()
    current_language = get_current_language()
    
    
    # Check if we have a session and data loaded
    has_data = all('✅' in status for status in data_status.values())
    
    # Get executive snapshot if data is loaded
    snapshot_html = ""
    if has_data:
        try:
            snapshot_html = executive_snapshot()
        except:
            snapshot_html = "<p class='text-muted'>Upload data to see executive snapshot</p>"
    else:
        snapshot_html = "<p class='text-muted'>Upload all 4 CSV files to see your business snapshot</p>"
    
    return render_template('dashboard.html', 
                         data_status=data_status,
                         has_data=has_data,
                         snapshot_html=snapshot_html,
                         ai_available=ai_assistant.is_available(),
                         current_language=current_language)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads - matching app.py functionality"""
    try:
        files = {}
        file_mapping = {
            'transactions': 'tx',
            'refunds': 'rf', 
            'payouts': 'po',
            'products': 'pm'
        }
        
        # Save uploaded files temporarily
        temp_files = {}
        for form_name, key in file_mapping.items():
            if form_name in request.files:
                file = request.files[form_name]
                if file and file.filename and file.filename.endswith('.csv'):
                    filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    temp_files[key] = filepath
        
        if not temp_files:
            flash('Please upload at least one CSV file', 'warning')
            return redirect(url_for('index'))
        
        # Load and validate CSV files
        dfs = load_csv_from_uploads(
            temp_files.get('tx'), 
            temp_files.get('rf'), 
            temp_files.get('po'), 
            temp_files.get('pm')
        )
        
        if not dfs:
            flash('No valid CSV files found. Please check your files and try again.', 'error')
            return redirect(url_for('index'))
        
        # Check for required files
        required_files = {"tx": "Transactions", "rf": "Refunds", "po": "Payouts", "pm": "Product Master"}
        missing_files = [desc for key, desc in required_files.items() if key not in dfs]
        
        if missing_files:
            flash(f'Missing required files: {", ".join(missing_files)}. Please upload all CSV files.', 'warning')
            return redirect(url_for('index'))
        
        # Validate schemas
        for key, df in dfs.items():
            if key in DEFAULT_SCHEMAS:
                try:
                    validate_schema_or_raise(key, df, DEFAULT_SCHEMAS[key])
                except Exception as e:
                    flash(f'Schema validation failed for {required_files.get(key, key)}: {str(e)}', 'error')
                    return redirect(url_for('index'))
        
        # Persist to data directory and set in analysis module
        persist_uploads_to_data_dir(dfs)
        set_data(
            transactions=dfs.get("tx"),
            refunds=dfs.get("rf"),
            payouts=dfs.get("po"),
            products=dfs.get("pm")
        )
        
        # Clean up temp files
        for filepath in temp_files.values():
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Build success message
        file_counts = [f"✅ {required_files[key]}: {len(df):,} rows" for key, df in dfs.items()]
        flash(f'Data uploaded successfully!\n\n{chr(10).join(file_counts)}\n\nYou can now run analysis questions!', 'success')
        
    except Exception as e:
        # Clean up temp files on error
        for filepath in temp_files.values():
            if os.path.exists(filepath):
                os.remove(filepath)
        flash(f'Error processing files: {str(e)}', 'error')
        print(f"Upload error: {traceback.format_exc()}")
    
    return redirect(url_for('index'))

def analyze(question):
    """Run analysis - matching all app.py questions"""
    try:
        budget = float(request.args.get('budget', 500))
        # Get language from session instead of request args
        language = get_current_language()
        
        # Rest of your analyze function stays the same...
        if question == "cash_flow":
            snap, ce, low, ai_insights = cash_eaters(ui_language=language)
            
            return render_template('analysis.html',
                                 question="What's eating my cash flow?",
                                 snapshot=snap,
                                 main_table=format_df_as_html(ce, "💸 Cash Drains"),
                                 secondary_table=format_df_as_html(low, "📉 Lowest Margin Products"),
                                 ai_insights=ai_insights,
                                 show_budget_form=False,
                                 current_language=current_language)
        
        elif question == "reorder":
            snap, msg, plan, ai_insights = reorder_plan(budget, ui_language=language)
            
            return render_template('analysis.html',
                                 question="What should I reorder with budget?",
                                 snapshot=snap,
                                 budget_message=msg,
                                 main_table=format_df_as_html(plan, "🛒 Suggested Purchase Plan"),
                                 secondary_table="",
                                 ai_insights=ai_insights,
                                 show_budget_form=True,
                                 current_budget=budget,
                                 current_language=current_language)
        
        elif question == "free_cash":
            snap, msg, slow, ai_insights = free_up_cash(ui_language=current_language)

            return render_template('analysis.html',
                                 question="How much cash can I free up?",
                                 snapshot=snap,
                                 budget_message=msg,
                                 main_table=format_df_as_html(slow, "🐌 Slow-Moving Inventory"),
                                 secondary_table="",
                                 ai_insights=ai_insights,
                                 show_budget_form=False,
                                 current_language=current_language)
        
        else:
            # Executive summary with AI analysis
            snap = executive_snapshot()
            
            # Get executive AI analysis
            try:
                ai_insights = analyze_executive_summary(language)
            except Exception as e:
                ai_insights = f"<div class='alert alert-warning'>Error generating executive analysis: {str(e)}</div>"
            
            return render_template('analysis.html',
                                 question="Executive Summary",
                                 snapshot=snap,
                                 main_table="",
                                 secondary_table="",
                                 ai_insights=ai_insights,
                                 show_budget_form=False,
                                 current_language=current_language)
            
    except Exception as e:
        error_msg = f"Analysis error: {str(e)}"
        print(f"Analysis error: {traceback.format_exc()}")
        
        return render_template('analysis.html',
                             question="Error",
                             snapshot=f"<div class='alert alert-danger'>{error_msg}</div>",
                             main_table="",
                             secondary_table="",
                             ai_insights="Please ensure you've uploaded all required CSV files first.",
                             show_budget_form=False,
                             current_language=get_current_language())

@app.route('/clear_data')
def clear_data():
    """Clear all data"""
    try:
        reset_to_uploads()
        flash('All data cleared. Please upload fresh CSV files.', 'info')
    except Exception as e:
        flash(f'Error clearing data: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/api/test_connection', methods=['POST'])
def test_api_connection():
    """Test API connection without fetching data"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        api_key = data.get('api_key')
        endpoint = data.get('endpoint')
        
        if not provider or not api_key:
            return jsonify({'error': 'Provider and API key are required'}), 400
        
        # Handle different POS providers
        if provider == "Square":
            try:
                from square_api import SquareAPIConnector
                connector = SquareAPIConnector(api_key, environment="sandbox")
                success, message = connector.test_connection()
                
                return jsonify({
                    'success': success,
                    'message': f"Square API Test: {message}",
                    'provider': provider
                })
                
            except ImportError:
                return jsonify({
                    'success': False,
                    'message': 'Square API connector not available. Please ensure square_api.py is installed.'
                })
        
        elif provider == "Stripe":
            try:
                from stripe_api import StripeAPIConnector
                connector = StripeAPIConnector(api_key)
                success, message = connector.test_connection()
                
                return jsonify({
                    'success': success,
                    'message': f"Stripe API Test: {message}",
                    'provider': provider
                })
                
            except ImportError:
                return jsonify({
                    'success': False,
                    'message': 'Stripe API connector not available. Please ensure stripe_api.py is installed.'
                })
        
        elif provider == "SumUp":
            try:
                from sumup_api import SumUpAPIConnector
                connector = SumUpAPIConnector(api_key, environment="sandbox")
                success, message = connector.test_connection()
                
                return jsonify({
                    'success': success,
                    'message': f"SumUp API Test: {message}",
                    'provider': provider
                })
                
            except ImportError:
                return jsonify({
                    'success': False,
                    'message': 'SumUp API connector not available. Please ensure sumup_api.py is installed.'
                })
        
        elif provider == "Shopify":
            try:
                from shopify_api import ShopifyAPIConnector
                # For Shopify, we'd need the shop name - using demo for testing
                shop_name = "demo-store"  # In production, this would be a separate field
                connector = ShopifyAPIConnector(shop_name, api_key)
                success, message = connector.test_connection()
                
                return jsonify({
                    'success': success,
                    'message': f"Shopify API Test: {message}",
                    'provider': provider
                })
                
            except ImportError:
                return jsonify({
                    'success': False,
                    'message': 'Shopify API connector not available. Please ensure shopify_api.py is installed.'
                })
        
        else:
            # For other providers, return a placeholder response
            return jsonify({
                'success': False,
                'message': f"{provider} integration is planned but not yet implemented. Currently available: Square, Stripe, SumUp, Shopify",
                'provider': provider
            })
    
    except Exception as e:
        return jsonify({'error': f'Connection test failed: {str(e)}'}), 500

@app.route('/api/connect', methods=['POST'])
def connect_api():
    """Connect to API and fetch data"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        api_key = data.get('api_key')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        endpoint = data.get('endpoint')
        
        if not all([provider, api_key, start_date, end_date]):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Handle different POS providers
        if provider == "Square":
            try:
                from square_api import SquareAPIConnector
                
                connector = SquareAPIConnector(api_key, environment="sandbox")
                success, test_message = connector.test_connection()
                if not success:
                    return jsonify({'error': f'Connection failed: {test_message}'}), 400
                
                # Generate mock data for demonstration
                mock_data = connector.generate_mock_data(start_date, end_date)
                
                # Set data in analysis module
                set_data(
                    transactions=mock_data["transactions"],
                    refunds=mock_data["refunds"],
                    payouts=mock_data["payouts"],
                    products=mock_data["products"]
                )
                
                return jsonify({
                    'success': True,
                    'message': f"""🎉 Square connection successful!
                    
Provider: {provider}
Environment: Sandbox
Date Range: {start_date} to {end_date}
Connection: {test_message}

Data Retrieved:
✅ Transactions: {len(mock_data["transactions"]):,} rows
✅ Products: {len(mock_data["products"])} items  
✅ Refunds: {len(mock_data["refunds"])} refunds
✅ Payouts: {len(mock_data["payouts"])} settlements

You can now run analysis questions!""",
                    'provider': provider,
                    'data_count': {
                        'transactions': len(mock_data["transactions"]),
                        'refunds': len(mock_data["refunds"]),
                        'payouts': len(mock_data["payouts"]),
                        'products': len(mock_data["products"])
                    }
                })
                
            except ImportError:
                return jsonify({'error': 'Square API connector not available'}), 500
        
        elif provider == "Stripe":
            try:
                from stripe_api import StripeAPIConnector
                
                connector = StripeAPIConnector(api_key)
                success, test_message = connector.test_connection()
                if not success:
                    return jsonify({'error': f'Connection failed: {test_message}'}), 400
                
                # Generate mock data for demonstration
                mock_data = connector.generate_mock_data(start_date, end_date)
                
                # Set data in analysis module
                set_data(
                    transactions=mock_data["transactions"],
                    refunds=mock_data["refunds"],
                    payouts=mock_data["payouts"],
                    products=mock_data["products"]
                )
                
                return jsonify({
                    'success': True,
                    'message': f"""🎉 Stripe connection successful!
                    
Provider: {provider}
Environment: {connector.environment.title()}
Date Range: {start_date} to {end_date}
Connection: {test_message}

Data Retrieved:
✅ Transactions: {len(mock_data["transactions"]):,} rows
✅ Products: {len(mock_data["products"])} items  
✅ Refunds: {len(mock_data["refunds"])} refunds
✅ Payouts: {len(mock_data["payouts"])} settlements

Business Type: Digital services & subscriptions
You can now run analysis questions!""",
                    'provider': provider
                })
                
            except ImportError:
                return jsonify({'error': 'Stripe API connector not available'}), 500
        
        else:
            return jsonify({
                'error': f'{provider} integration is not yet implemented. Currently available: Square, Stripe'
            }), 400
    
    except Exception as e:
        return jsonify({'error': f'Connection failed: {str(e)}'}), 500

@app.route('/api/status')
def api_status():
    """API endpoint for data status - for AJAX updates"""
    return jsonify(get_data_status())

@app.route('/sample_formats')
def sample_formats():
    """Show CSV format examples"""
    return render_template('sample_formats.html')

# Error handlers
@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 32MB.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 Starting AI Cash Flow Assistant (Flask)")
    print("=" * 50)
    print("📊 Professional cash flow analysis for coffee shops & restaurants")
    print("🤖 AI-powered insights with Claude integration")
    print("📱 Mobile-friendly interface")
    print("🌐 Open your browser to: http://127.0.0.1:5000")
    print("=" * 50)
    
    # Check for AI availability
    if ai_assistant.is_available():
        print("✅ Claude AI integration: ACTIVE")
    else:
        print("⚠️  Claude AI integration: INACTIVE (set ANTHROPIC_API_KEY)")
    
    print("\nStarting Flask server...")
    app.run(debug=True, host='127.0.0.1', port=5000)