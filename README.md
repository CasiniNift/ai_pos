AI POS – Cash Flow Assistant (POC)

AI-powered assistant that provides real-time cash flow insights for small retailers and cafés, built as a proof-of-concept on synthetic POS data.

The project shows how an AI layer on top of POS transactions can help business owners and executives quickly answer:

What’s eating my cash flow?

What should I reorder with my limited budget?

How much cash can I free up fast?

🚀 Features

Executive snapshot dashboard (transactions, sales, fees, refunds, payouts).

Cash eater analysis → discounts, refunds, processor fees, low-margin SKUs.

Smart reorder plan → suggests purchases with a given budget (default €500).

Free-up cash insights → clearance strategy for slow movers.

Minimal Gradio UI for easy demo.

📂 Project Structure
ai_pos/
│
├── data/                  # Synthetic POS data (sample week)
│   ├── pos_transactions_week.csv
│   ├── pos_refunds_week.csv
│   ├── pos_payouts_week.csv
│   └── product_master.csv
│
├── src/                   # Source code
│   ├── __init__.py
│   ├── app.py             # Gradio UI entrypoint
│   ├── analysis.py        # Business logic
│   └── utils.py           # Data loading helpers
│
├── notebooks/             # Optional: experiments
│   └── poc_experiments.ipynb
│
├── requirements.txt       # Dependencies
├── README.md              # This file
└── .gitignore             # Ignore venv, cache, temp files

🛠️ Setup

Clone the repo:

git clone https://github.com/your-username/ai_pos.git
cd ai_pos


Create a virtual environment:

python -m venv venv
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate       # Windows


Install dependencies:

pip install -r requirements.txt

▶️ Run the Demo

From the project root:

python src/app.py


This will start a Gradio app in your browser with three actions:

Cash Eaters

Reorder Plan (with budget input)

Free-Up Cash

📊 Data

The /data/ folder contains synthetic POS datasets simulating a Milan café for one week:

Transactions

Refunds

Payouts (settlements)

Product master with COGS

🌱 Next Steps

Replace synthetic CSVs with live POS APIs (SumUp, Square, etc.).

Add forecasting (cash balance, supplier payments, payroll).

Connect to a lightweight AI layer for natural language queries.


