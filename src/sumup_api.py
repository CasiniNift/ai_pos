# src/sumup_api.py - SumUp API integration

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

class SumUpAPIConnector:
    """SumUp API integration for fetching transaction data"""
    
    def __init__(self, access_token: str, environment: str = "sandbox"):
        """
        Initialize SumUp API connector
        
        Args:
            access_token: SumUp access token
            environment: "sandbox" or "production"
        """
        self.access_token = access_token
        self.environment = environment
        
        # Set base URL based on environment
        if environment == "sandbox":
            self.base_url = "https://api.sumup.com"  # SumUp uses same URL for both
        else:
            self.base_url = "https://api.sumup.com"
        
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the API connection by fetching merchant profile
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = requests.get(
                f"{self.base_url}/v0.1/me",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                profile_data = response.json()
                merchant_name = profile_data.get("merchant_profile", {}).get("merchant_name", "Unknown Merchant")
                country = profile_data.get("merchant_profile", {}).get("country", "Unknown")
                return True, f"✅ Connesso a '{merchant_name}' ({country}) con successo!"
            else:
                error_data = response.json()
                error_msg = error_data.get("message", "Errore sconosciuto")
                return False, f"❌ Connessione fallita: {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "❌ Timeout della connessione. Controlla la tua connessione internet."
        except requests.exceptions.RequestException as e:
            return False, f"❌ Errore di rete: {str(e)}"
        except Exception as e:
            return False, f"❌ Errore imprevisto: {str(e)}"
    
    def fetch_transactions(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch transactions from SumUp API
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with transactions in our standard format
        """
        try:
            # Convert dates to SumUp format (ISO 8601)
            start_datetime = f"{start_date}T00:00:00.000Z"
            end_datetime = f"{end_date}T23:59:59.999Z"
            
            # Fetch transactions
            params = {
                "from_date": start_datetime,
                "to_date": end_datetime,
                "limit": 100,
                "order": "ascending"
            }
            
            response = requests.get(
                f"{self.base_url}/v0.1/me/transactions",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching transactions: {response.status_code} - {response.text}")
                return pd.DataFrame()
            
            transactions = response.json()
            print(f"Found {len(transactions)} transactions from SumUp API")
            
            # Convert to our standard format
            return self._convert_transactions_to_standard(transactions)
            
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return pd.DataFrame()
    
    def _convert_transactions_to_standard(self, transactions: List[Dict]) -> pd.DataFrame:
        """Convert SumUp transactions to our transaction format"""
        converted_transactions = []
        
        for txn in transactions:
            txn_id = txn.get("id", "")
            timestamp = txn.get("timestamp", "")
            
            # Parse date
            try:
                date_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_str = date_obj.date().isoformat()
            except:
                date_str = "2025-01-01"  # Fallback
            
            # Extract transaction details
            amount = float(txn.get("amount", 0))
            currency = txn.get("currency", "EUR")
            
            # Product info (SumUp doesn't have detailed product breakdown)
            product_name = txn.get("product_summary", "Vendita POS")
            
            # Calculate components
            gross_sales = amount
            discount = 0.0  # SumUp doesn't track discounts separately
            net_sales = gross_sales - discount
            
            # Italian VAT (IVA) - typically 22%
            vat_rate = 0.22
            tax = net_sales * vat_rate / (1 + vat_rate)  # Extract VAT from gross
            net_sales_before_tax = net_sales - tax
            
            line_total = amount
            
            # Payment method
            payment_type = txn.get("payment_type", "CARD")
            if payment_type.upper() in ["CARD", "CONTACTLESS"]:
                payment_type = "CARD"
            else:
                payment_type = "CASH"
            
            transaction = {
                "date": date_str,
                "transaction_id": txn_id,
                "product_id": f"sumup_{txn_id}",
                "product_name": product_name,
                "category": "Vendita",
                "quantity": 1,
                "unit_price": round(amount, 2),
                "gross_sales": round(gross_sales, 2),
                "discount": round(discount, 2),
                "net_sales": round(net_sales_before_tax, 2),
                "tax": round(tax, 2),
                "line_total": round(line_total, 2),
                "payment_type": payment_type,
                "tip_amount": float(txn.get("tip_amount", 0))
            }
            
            converted_transactions.append(transaction)
        
        return pd.DataFrame(converted_transactions)
    
    def generate_mock_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Generate realistic mock Italian retail data for testing"""
        print("🇮🇹 Generazione dati mock per commercio italiano...")
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days + 1
        
        # Mock Italian retail products
        products_data = [
            {"product_id": "sumup_caffe", "product_name": "Caffè Espresso", "category": "Bevande", "cogs": 0.30, "unit_price": 1.20},
            {"product_id": "sumup_cappuccino", "product_name": "Cappuccino", "category": "Bevande", "cogs": 0.60, "unit_price": 1.80},
            {"product_id": "sumup_cornetto", "product_name": "Cornetto", "category": "Dolci", "cogs": 0.40, "unit_price": 1.50},
            {"product_id": "sumup_panino", "product_name": "Panino", "category": "Cibo", "cogs": 1.80, "unit_price": 4.50},
            {"product_id": "sumup_gelato", "product_name": "Gelato", "category": "Dolci", "cogs": 0.80, "unit_price": 3.00},
            {"product_id": "sumup_acqua", "product_name": "Acqua Minerale", "category": "Bevande", "cogs": 0.25, "unit_price": 1.00},
            {"product_id": "sumup_vino", "product_name": "Bicchiere di Vino", "category": "Alcolici", "cogs": 1.50, "unit_price": 5.00},
        ]
        
        # Generate transactions (Italian retail patterns)
        transactions = []
        txn_id = 10000
        
        for day in range(days):
            current_date = start + timedelta(days=day)
            date_str = current_date.date().isoformat()
            
            # Italian business patterns - more transactions during lunch and evening
            # Weekend days have different patterns
            is_weekend = current_date.weekday() >= 5
            
            if is_weekend:
                daily_txns = 25 + (day % 15)  # 25-40 transactions on weekends
            else:
                daily_txns = 35 + (day % 20)  # 35-55 transactions on weekdays
            
            for _ in range(daily_txns):
                txn_id += 1
                
                # Random product with Italian preferences
                product = products_data[txn_id % len(products_data)]
                quantity = 1 if txn_id % 4 != 0 else 2  # Mostly single items
                
                gross_sales = product["unit_price"] * quantity
                discount = 0.0 if txn_id % 15 != 0 else gross_sales * 0.05  # Small discounts occasionally
                net_sales_before_vat = gross_sales - discount
                
                # Italian VAT (IVA) - 22% for most items, 10% for food
                if product["category"] in ["Cibo", "Bevande"]:
                    vat_rate = 0.10  # Reduced rate for food/beverages
                else:
                    vat_rate = 0.22  # Standard rate
                
                tax = net_sales_before_vat * vat_rate
                line_total = net_sales_before_vat + tax
                
                # Payment type - Italy still uses cash frequently
                payment_type = "CARD" if txn_id % 3 != 0 else "CASH"
                
                # Tips are less common in Italy
                tip = 0.0 if txn_id % 20 != 0 else round(0.20, 2)  # Small tips occasionally
                
                transaction = {
                    "date": date_str,
                    "transaction_id": f"sumup_{txn_id}",
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "unit_price": product["unit_price"],
                    "gross_sales": round(gross_sales, 2),
                    "discount": round(discount, 2),
                    "net_sales": round(net_sales_before_vat, 2),
                    "tax": round(tax, 2),
                    "line_total": round(line_total, 2),
                    "payment_type": payment_type,
                    "tip_amount": tip
                }
                
                transactions.append(transaction)
        
        # Generate refunds (lower rate for Italian retail)
        refunds = []
        refund_transactions = transactions[::40]  # Every 40th transaction (2.5% refund rate)
        
        for i, txn in enumerate(refund_transactions):
            refunds.append({
                "original_transaction_id": txn["transaction_id"],
                "refund_date": txn["date"],
                "refund_amount": txn["line_total"],
                "refund_id": f"sumup_reso_{i}",
                "reason": ["Prodotto difettoso", "Cliente insoddisfatto", "Errore di cassa"][i % 3]
            })
        
        # Generate payouts (SumUp pays out daily)
        payouts = []
        for day in range(days):
            current_date = start + timedelta(days=day)
            date_str = current_date.date().isoformat()
            
            # Sum up card transactions for this day
            daily_card_sales = sum(
                txn["line_total"] + txn["tip_amount"]
                for txn in transactions 
                if txn["date"] == date_str and txn["payment_type"] == "CARD"
            )
            
            if daily_card_sales > 0:
                # SumUp's fees in Europe: 1.95% + €0.25 per transaction
                card_txns_count = sum(1 for txn in transactions if txn["date"] == date_str and txn["payment_type"] == "CARD")
                fees = daily_card_sales * 0.0195 + (card_txns_count * 0.25)
                net_payout = daily_card_sales - fees
                
                payouts.append({
                    "covering_sales_date": date_str,
                    "gross_card_volume": round(daily_card_sales, 2),
                    "processor_fees": round(fees, 2),
                    "net_payout_amount": round(net_payout, 2),
                    "payout_date": (current_date + timedelta(days=1)).date().isoformat()
                })
        
        return {
            "transactions": pd.DataFrame(transactions),
            "refunds": pd.DataFrame(refunds),
            "payouts": pd.DataFrame(payouts),
            "products": pd.DataFrame(products_data)
        }