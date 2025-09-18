# flask_app.py - Simple Flask version to bypass Gradio issues

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import pandas as pd
import sys
import os
from werkzeug.utils import secure_filename
import traceback

# Add src to path
sys.path.append('src')

try:
    from analysis import cash_eaters, executive_snapshot, set_data, get_data_status
    from utils import load_csv_from_uploads, validate_schema_or_raise, DEFAULT_SCHEMAS
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Main page"""
    data_status = get_data_status()
    return render_template('index.html', data_status=data_status)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads"""
    try:
        files = {}
        file_mapping = {
            'transactions': 'tx',
            'refunds': 'rf', 
            'payouts': 'po',
            'products': 'pm'
        }
        
        # Save uploaded files
        for form_name, key in file_mapping.items():
            if form_name in request.files:
                file = request.files[form_name]
                if file and file.filename and file.filename.endswith('.csv'):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    files[key] = filepath
        
        if not files:
            flash('No valid CSV files uploaded', 'error')
            return redirect(url_for('index'))
        
        # Process files
        dfs = {}
        for key, filepath in files.items():
            df = pd.read_csv(filepath)
            # Clean up any unnamed columns
            unnamed_cols = [col for col in df.columns if 'Unnamed:' in str(col)]
            if unnamed_cols:
                df = df.drop(columns=unnamed_cols)
            dfs[key] = df
        
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
        
        # Clean up temp files
        for filepath in files.values():
            if os.path.exists(filepath):
                os.remove(filepath)
        
        flash('Data uploaded successfully!', 'success')
        
    except Exception as e:
        flash(f'Error processing files: {str(e)}', 'error')
        # Clean up temp files on error
        for filepath in files.values():
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return redirect(url_for('index'))

@app.route('/analyze')
def analyze():
    """Run cash flow analysis"""
    try:
        question = request.args.get('question', 'What\'s eating my cash flow?')
        
        if question == "What's eating my cash flow?":
            snap, ce, low, ai_insights = cash_eaters()
            
            # Convert DataFrames to HTML tables
            ce_html = ce.to_html(classes='table table-striped', index=False) if ce is not None and not ce.empty else "No data"
            low_html = low.to_html(classes='table table-striped', index=False) if low is not None and not low.empty else "No data"
            
            return render_template('analysis.html', 
                                 question=question,
                                 snapshot=snap,
                                 cash_eaters_table=ce_html,
                                 low_margin_table=low_html,
                                 ai_insights=ai_insights)
        else:
            # For other questions, just show executive snapshot for now
            snap = executive_snapshot()
            return render_template('analysis.html', 
                                 question=question,
                                 snapshot=snap,
                                 cash_eaters_table="",
                                 low_margin_table="",
                                 ai_insights="Other analysis questions coming soon!")
            
    except Exception as e:
        error_msg = f"Analysis error: {str(e)}"
        return render_template('analysis.html', 
                             question="Error",
                             snapshot=error_msg,
                             cash_eaters_table="",
                             low_margin_table="",
                             ai_insights="")

@app.route('/status')
def status():
    """Get current data status"""
    data_status = get_data_status()
    return jsonify(data_status)

# HTML Templates
index_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI POS - Cash Flow Assistant</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .upload-area { 
            border: 2px dashed #dee2e6; 
            border-radius: 8px; 
            padding: 20px; 
            margin: 10px 0; 
            background-color: #f8f9fa;
        }
        .status-success { color: #28a745; }
        .status-error { color: #dc3545; }
    </style>
</head>
<body>
    <div class="container mt-4">
        <h1 class="mb-4">☕ AI POS - Cash Flow Assistant</h1>
        
        <!-- Flash messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'danger' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="row">
            <div class="col-md-6">
                <h3>📁 Upload CSV Files</h3>
                <div class="upload-area">
                    <form method="POST" action="/upload" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label for="transactions" class="form-label">📊 Transactions CSV</label>
                            <input type="file" class="form-control" name="transactions" accept=".csv">
                        </div>
                        <div class="mb-3">
                            <label for="refunds" class="form-label">↩️ Refunds CSV</label>
                            <input type="file" class="form-control" name="refunds" accept=".csv">
                        </div>
                        <div class="mb-3">
                            <label for="payouts" class="form-label">💳 Payouts CSV</label>
                            <input type="file" class="form-control" name="payouts" accept=".csv">
                        </div>
                        <div class="mb-3">
                            <label for="products" class="form-label">📦 Products CSV</label>
                            <input type="file" class="form-control" name="products" accept=".csv">
                        </div>
                        <button type="submit" class="btn btn-primary">📤 Upload & Process</button>
                    </form>
                </div>
            </div>
            
            <div class="col-md-6">
                <h3>📊 Current Data Status</h3>
                <ul class="list-group">
                    {% for name, status in data_status.items() %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            {{ name }}
                            <span class="{{ 'status-success' if '✅' in status else 'status-error' }}">
                                {{ status }}
                            </span>
                        </li>
                    {% endfor %}
                </ul>
                
                <h3 class="mt-4">🤖 Analysis</h3>
                <div class="d-grid gap-2">
                    <a href="/analyze?question=What's eating my cash flow?" class="btn btn-success">
                        🚀 What's eating my cash flow?
                    </a>
                    <a href="/analyze?question=Executive Summary" class="btn btn-outline-secondary">
                        📈 Executive Summary
                    </a>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

analysis_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Analysis Results - AI POS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .ai-insights { 
            background-color: #e8f5e8; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0; 
            border-left: 4px solid #28a745;
        }
    </style>
</head>
<body>
    <div class="container mt-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>📊 Analysis: {{ question }}</h1>
            <a href="/" class="btn btn-secondary">← Back</a>
        </div>
        
        <!-- Snapshot -->
        <div class="card mb-4">
            <div class="card-header"><h4>📈 Executive Snapshot</h4></div>
            <div class="card-body">
                {{ snapshot | safe }}
            </div>
        </div>
        
        <!-- Cash Eaters Table -->
        {% if cash_eaters_table %}
        <div class="card mb-4">
            <div class="card-header"><h4>💸 Cash Drains</h4></div>
            <div class="card-body">
                {{ cash_eaters_table | safe }}
            </div>
        </div>
        {% endif %}
        
        <!-- Low Margin Table -->
        {% if low_margin_table %}
        <div class="card mb-4">
            <div class="card-header"><h4>📉 Lowest Margin Products</h4></div>
            <div class="card-body">
                {{ low_margin_table | safe }}
            </div>
        </div>
        {% endif %}
        
        <!-- AI Insights -->
        {% if ai_insights %}
        <div class="ai-insights">
            {{ ai_insights | safe }}
        </div>
        {% endif %}
        
        <div class="mt-4">
            <a href="/" class="btn btn-primary">Run Another Analysis</a>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

# Create templates directory and save templates
templates_dir = 'templates'
os.makedirs(templates_dir, exist_ok=True)

with open(f'{templates_dir}/index.html', 'w') as f:
    f.write(index_template)

with open(f'{templates_dir}/analysis.html', 'w') as f:
    f.write(analysis_template)

if __name__ == '__main__':
    print("Starting Flask Cash Flow App...")
    print("Open your browser to: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)