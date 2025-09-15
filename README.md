# AI POS – Cash Flow Assistant

An intelligent Point-of-Sale cash flow analysis tool that helps businesses understand their financial patterns, optimize inventory, and make data-driven decisions.

## 🚀 Features

- **Cash Flow Analysis**: Identify what's eating into your cash flow with detailed breakdowns of discounts, refunds, and fees
- **Smart Reordering**: Get AI-powered purchase recommendations based on your budget and sales patterns
- **Cash Liberation**: Discover how much cash you can free up by clearing slow-moving inventory
- **Runway Forecasting**: Analyze the impact of sales changes on your cash runway
- **Easy Data Upload**: Simple CSV upload interface with automatic data validation
- **Real-time Analysis**: Hot-reload functionality for immediate insights when new data is uploaded

## 🛠️ Tech Stack

- **Backend**: Python, Pandas for data analysis
- **Frontend**: Gradio for the web interface
- **Data Processing**: CSV-based data ingestion with schema validation

## 📋 Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/CasiniNift/ai_pos.git
   cd ai_pos
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

1. **Start the application**
   ```bash
   python3 src/app.py
   ```

2. **Open your browser**
   The app will automatically open at `http://localhost:7860` (or the next available port)

3. **Upload your data**
   - Use the CSV upload interface on the left panel
   - Or connect via POS API (coming soon)

4. **Ask questions**
   - Select from pre-built questions in the dropdown
   - Get instant AI-powered insights
   - View results in clean, formatted tables

## 📊 Required Data Format

The application expects four CSV files with specific schemas:

### Transactions CSV
Required columns: `date`, `transaction_id`, `product_id`, `product_name`, `category`, `quantity`, `unit_price`, `gross_sales`, `discount`, `net_sales`, `tax`, `line_total`, `payment_type`, `tip_amount`

### Refunds CSV
Required columns: `original_transaction_id`, `refund_date`, `refund_amount`

### Payouts CSV
Required columns: `covering_sales_date`, `gross_card_volume`, `processor_fees`, `net_payout_amount`, `payout_date`

### Product Master CSV
Required columns: `product_id`, `product_name`, `category`, `cogs`

## 🎯 Available Questions

1. **"What's eating my cash flow?"**
   - Analyzes discounts, refunds, and fees
   - Identifies lowest-margin SKUs

2. **"What should I reorder with budget?"**
   - Provides purchase recommendations based on available budget
   - Prioritizes high-velocity, profitable items

3. **"How much cash can I free up?"**
   - Identifies slow-moving inventory
   - Estimates clearance potential

4. **"If sales drop 10% next month, impact on runway?"**
   - Forecasts cash flow impact of sales changes
   - Helps with scenario planning

## 📁 Project Structure

```
ai_pos/
├── src/
│   ├── app.py          # Main Gradio application
│   ├── analysis.py     # Core analysis functions
│   └── utils.py        # Data loading and validation utilities
├── data/               # Sample data files
├── requirements.txt    # Python dependencies
├── generate_sample_data.py  # Sample data generator
└── README.md
```

## 🔄 Development Workflow

1. **Data Validation**: All uploaded CSV files are validated against required schemas
2. **Hot Reload**: Analysis functions automatically reload when new data is uploaded
3. **Error Handling**: Comprehensive error handling for missing or malformed data
4. **Modular Design**: Separate modules for UI, analysis, and utilities

## 📈 Sample Data

The project includes sample data generators and example CSV files in the `/data` directory. Use these to test the application before uploading your own POS data.

## 🛡️ Data Privacy

- All data processing happens locally
- No data is sent to external servers
- CSV files are processed in-memory and optionally saved to local `/data` directory

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♂️ Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check the documentation in the CSV format guide within the app

## 🚧 Roadmap

- [ ] POS system API integrations
- [ ] Advanced forecasting models
- [ ] Export capabilities for reports
- [ ] Multi-location support
- [ ] Real-time dashboard features

---

**Built with ❤️ for small business owners who want to understand their cash flow better.**