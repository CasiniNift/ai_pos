# generate_sample_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

# ---- Products (with COGS) ----
products = [
    ("ESP", "Espresso", "Beverage", 0.40, 2.00),
    ("LAT", "Latte", "Beverage", 0.90, 3.50),
    ("CAP", "Cappuccino", "Beverage", 0.85, 3.20),
    ("TEA", "Tea", "Beverage", 0.35, 2.50),
    ("CRS", "Croissant", "Food", 0.70, 2.80),
    ("SNW", "Sandwich", "Food", 2.00, 6.50),
    ("SAL", "Salad", "Food", 2.30, 7.00),
]
product_master = pd.DataFrame(products, columns=["product_id","product_name","category","cogs","unit_price"])

# ---- Transactions ----
start_date = datetime(2025, 1, 1)
rows = []
txn_id = 1000
for d in range(7):  # 1 week
    date = start_date + timedelta(days=d)
    for _ in range(np.random.randint(30, 50)):  # transactions per day
        txn_id += 1
        num_items = np.random.randint(1, 4)
        for _ in range(num_items):
            pid, name, cat, cogs, price = products[np.random.randint(len(products))]
            qty = 1
            gross = qty * price
            discount = 0 if np.random.rand() > 0.1 else round(gross * 0.1, 2)
            net = gross - discount
            tax = round(net * 0.1, 2)
            line_total = net + tax
            pay_type = np.random.choice(["CARD","CASH"], p=[0.7,0.3])
            tip = 0 if np.random.rand() > 0.3 else round(np.random.uniform(0.2,1.0),2)
            rows.append([date.date(), txn_id, pid, name, cat, qty, price, gross, discount, net, tax, line_total, pay_type, tip])

transactions = pd.DataFrame(rows, columns=[
    "date","transaction_id","product_id","product_name","category","quantity","unit_price",
    "gross_sales","discount","net_sales","tax","line_total","payment_type","tip_amount"
])

# ---- Refunds ----
refunds = transactions.sample(frac=0.05).copy()
refunds = refunds[["transaction_id","date","line_total"]]
refunds["refund_id"] = ["RFD"+str(i) for i in range(len(refunds))]
refunds.rename(columns={"transaction_id":"original_transaction_id","date":"refund_date","line_total":"refund_amount"}, inplace=True)
refunds["reason"] = np.random.choice(["Customer complaint","Wrong item","Duplicate charge"], size=len(refunds))

# ---- Payouts ---- (daily card settlements minus 2.6% + €0.05 fee)
payouts = []
for d, g in transactions[transactions["payment_type"]=="CARD"].groupby("date"):
    gross_card = g["line_total"].sum() + g["tip_amount"].sum()
    fee = gross_card * 0.026 + 0.05*len(g)
    net = gross_card - fee
    payouts.append([d, gross_card, round(fee,2), round(net,2)])
payouts = pd.DataFrame(payouts, columns=["covering_sales_date","gross_card_volume","processor_fees","net_payout_amount"])
payouts["payout_date"] = pd.to_datetime(payouts["covering_sales_date"]) + timedelta(days=1)

# ---- Save CSVs ----
outdir = "data"
product_master.to_csv(f"{outdir}/product_master.csv", index=False)
transactions.to_csv(f"{outdir}/pos_transactions_week.csv", index=False)
refunds.to_csv(f"{outdir}/pos_refunds_week.csv", index=False)
payouts.to_csv(f"{outdir}/pos_payouts_week.csv", index=False)

print("✅ Sample data generated in /data/")
