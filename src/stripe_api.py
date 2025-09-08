# src/stripe_api.py - Stripe API integration

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

class StripeAPIConnector:
    """Stripe API integration for fetching payment data"""
    
    def __init__(self, api_key: str):
        """
        Initialize Stripe API connector
        
        Args:
            api_key: Stripe secret key (sk_test_... for test mode, sk_live_... for live)
        """
        self.api_key = api_key
        self.base_url = "https://api.stripe.com/v1"
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Determine environment
        self.environment = "test" if api_key.startswith("sk_test_") else "live"
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the API connection by fetching account info
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = requests.get(
                f"{self.base_url}/account",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                account_data = response.json()
                business_name = account_data.get("business_profile", {}).get("name", "Unknown Business")
                country = account_data.get("country", "Unknown")
                return True, f"✅ Connected to '{business_name}' ({country}) successfully!"
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return False, f"❌ Connection failed: {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "❌ Connection timeout. Please check your internet connection."
        except requests.exceptions.RequestException as e:
            return False, f"❌ Network error: {str(e)}"
        except Exception as e:
            return False, f"❌ Unexpected error: {str(e)}"
    
    def fetch_transactions(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch charges from Stripe API
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with transactions in our standard format
        """
        try:
            # Convert dates to Unix timestamps
            start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_timestamp = int(datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp())
            
            # Fetch charges
            params = {
                "created[gte]": start_timestamp,
                "created[lte]": end_timestamp,
                "limit": 100,
                "expand[]": "data.payment_intent"
            }
            
            response = requests.get(
                f"{self.base_url}/charges",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching charges: {response.status_code} - {response.text}")
                return pd.DataFrame()
            
            charges = response.json().get("data", [])
            print(f"Found {len(charges)} charges from Stripe API")
            
            # Convert to our standard format
            return self._convert_charges_to_transactions(charges)
            
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return pd.DataFrame()
    
    def _convert_charges_to_transactions(self, charges: List[Dict]) -> pd.DataFrame:
        """Convert Stripe charges to our transaction format"""
        transactions = []
        
        for charge in charges:
            charge_id = charge.get("id", "")
            created_timestamp = charge.get("created", 0)
            
            # Parse date
            try:
                date_obj = datetime.fromtimestamp(created_timestamp)
                date_str = date_obj.date().isoformat()
            except:
                date_str = "2025-01-01"  # Fallback
            
            # Extract charge details
            amount = float(charge.get("amount", 0)) / 100  # Stripe uses cents
            description = charge.get("description", "Unknown Item")
            
            # Handle metadata for product info
            metadata = charge.get("metadata", {})
            product_name = metadata.get("product_name", description)
            category = metadata.get("category", "Unknown")
            quantity = int(metadata.get("quantity", "1"))
            
            unit_price = amount / quantity if quantity > 0 else amount
            gross_sales = amount
            
            # Calculate fees
            balance_transaction_id = charge.get("balance_transaction")
            fees = float(charge.get("application_fee_amount", 0)) / 100 if charge.get("application_fee_amount") else amount * 0.029 + 0.30
            
            # No discounts in basic Stripe charges
            discount = 0.0
            net_sales = gross_sales - discount
            
            # Tax handling (simplified)
            tax = net_sales * 0.08  # Assume 8% tax
            line_total = net_sales + tax
            
            # Payment type
            payment_method = charge.get("payment_method_details", {}).get("type", "card")
            payment_type = "CARD" if payment_method == "card" else "OTHER"
            
            transaction = {
                "date": date_str,
                "transaction_id": charge_id,
                "product_id": metadata.get("product_id", charge_id),
                "product_name": product_name,
                "category": category,
                "quantity": quantity,
                "unit_price": round(unit_price, 2),
                "gross_sales": round(gross_sales, 2),
                "discount": round(discount, 2),
                "net_sales": round(net_sales, 2),
                "tax": round(tax, 2),
                "line_total": round(line_total, 2),
                "payment_type": payment_type,
                "tip_amount": 0.0  # Would need to be in metadata
            }
            
            transactions.append(transaction)
        
        return pd.DataFrame(transactions)
    
    def fetch_products(self) -> pd.DataFrame:
        """Fetch product catalog from Stripe Products API"""
        try:
            response = requests.get(
                f"{self.base_url}/products?limit=100",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching products: {response.status_code}")
                return pd.DataFrame()
            
            products = response.json().get("data", [])
            product_list = []
            
            for product in products:
                # Get prices for this product
                price_response = requests.get(
                    f"{self.base_url}/prices?product={product['id']}&limit=10",
                    headers=self.headers,
                    timeout=10
                )
                
                if price_response.status_code == 200:
                    prices = price_response.json().get("data", [])
                    for price in prices:
                        product_entry = {
                            "product_id": product.get("id", ""),
                            "product_name": product.get("name", "Unknown"),
                            "category": product.get("metadata", {}).get("category", "Unknown"),
                            "cogs": 0.0,  # Stripe doesn't provide COGS
                            "unit_price": float(price.get("unit_amount", 0)) / 100 if price.get("unit_amount") else 0.0
                        }
                        product_list.append(product_entry)
            
            return pd.DataFrame(product_list)
            
        except Exception as e:
            print(f"Error fetching products: {e}")
            return pd.DataFrame()
    
    def generate_mock_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Generate realistic mock payment processing data for testing"""
        print("💳 Generating mock Stripe payment data...")
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days + 1
        
        # Mock service/digital products
        products_data = [
            {"product_id": "stripe_subscription", "product_name": "Monthly Subscription", "category": "Service", "cogs": 5.00, "unit_price": 29.99},
            {"product_id": "stripe_course", "product_name": "Online Course", "category": "Digital", "cogs": 10.00, "unit_price": 199.00},
            {"product_id": "stripe_ebook", "product_name": "E-book", "category": "Digital", "cogs": 2.00, "unit_price": 19.99},
            {"product_id": "stripe_consultation", "product_name": "1-Hour Consultation", "category": "Service", "cogs": 0.00, "unit_price": 150.00},
            {"product_id": "stripe_template", "product_name": "Design Template", "category": "Digital", "cogs": 1.00, "unit_price": 49.99},
        ]
        
        # Generate transactions (services have fewer daily transactions)
        transactions = []
        charge_id = 8000
        
        for day in range(days):
            current_date = start + timedelta(days=day)
            date_str = current_date.date().isoformat()
            
            # Generate 2-8 transactions per day (typical for service business)
            daily_txns = 2 + (day % 7)
            
            for _ in range(daily_txns):
                charge_id += 1
                
                # Random product
                product = products_data[charge_id % len(products_data)]
                quantity = 1  # Services are usually quantity 1
                
                gross_sales = product["unit_price"] * quantity
                discount = 0.0 if charge_id % 12 != 0 else gross_sales * 0.20  # 20% discount sometimes
                net_sales = gross_sales - discount
                tax = net_sales * 0.06  # Lower tax rate for digital services
                line_total = net_sales + tax
                
                transaction = {
                    "date": date_str,
                    "transaction_id": f"ch_{charge_id}",
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "category": product["category"],
                    "quantity": quantity,
                    "unit_price": product["unit_price"],
                    "gross_sales": round(gross_sales, 2),
                    "discount": round(discount, 2),
                    "net_sales": round(net_sales, 2),
                    "tax": round(tax, 2),
                    "line_total": round(line_total, 2),
                    "payment_type": "CARD",
                    "tip_amount": 0.0
                }
                
                transactions.append(transaction)
        
        # Generate refunds (2% of transactions - lower for services)
        refunds = []
        refund_transactions = transactions[::50]  # Every 50th transaction
        
        for i, txn in enumerate(refund_transactions):
            refunds.append({
                "original_transaction_id": txn["transaction_id"],
                "refund_date": txn["date"],
                "refund_amount": txn["line_total"],
                "refund_id": f"re_{i}",
                "reason": ["Service not delivered", "Customer cancellation", "Technical issue"][i % 3]
            })
        
        # Generate payouts (Stripe pays out daily or weekly)
        payouts = []
        for day in range(days):
            current_date = start + timedelta(days=day)
            date_str = current_date.date().isoformat()
            
            # Sum up card transactions for this day
            daily_card_sales = sum(
                txn["line_total"] 
                for txn in transactions 
                if txn["date"] == date_str and txn["payment_type"] == "CARD"
            )
            
            if daily_card_sales > 0:
                fees = daily_card_sales * 0.029 + 0.30  # Stripe's standard fees
                net_payout = daily_card_sales - fees
                
                payouts.append({
                    "covering_sales_date": date_str,
                    "gross_card_volume": round(daily_card_sales, 2),
                    "processor_fees": round(fees, 2),
                    "net_payout_amount": round(net_payout, 2),
                    "payout_date": (current_date + timedelta(days=2)).date().isoformat()  # Stripe has 2-day payout delay
                })
        
        return {
            "transactions": pd.DataFrame(transactions),
            "refunds": pd.DataFrame(refunds),
            "payouts": pd.DataFrame(payouts),
            "products": pd.DataFrame(products_data)
        }