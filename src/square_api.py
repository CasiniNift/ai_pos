# src/square_api.py - Square POS API integration

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

class SquareAPIConnector:
    """Square POS API integration for fetching transaction data"""
    
    def __init__(self, access_token: str, environment: str = "sandbox"):
        """
        Initialize Square API connector
        
        Args:
            access_token: Square access token (sandbox or production)
            environment: "sandbox" or "production"
        """
        self.access_token = access_token
        self.environment = environment
        
        # Set base URL based on environment
        if environment == "sandbox":
            self.base_url = "https://connect.squareupsandbox.com"
        else:
            self.base_url = "https://connect.squareup.com"
        
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Square-Version": "2023-10-18"  # Latest API version
        }
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the API connection by fetching locations
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = requests.get(
                f"{self.base_url}/v2/locations",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                locations = response.json().get("locations", [])
                if locations:
                    location_names = [loc.get("name", "Unknown") for loc in locations]
                    return True, f"✅ Connected successfully! Found {len(locations)} location(s): {', '.join(location_names)}"
                else:
                    return True, "✅ Connected successfully! No locations found (normal for new sandbox accounts)"
            else:
                error_data = response.json()
                error_msg = error_data.get("errors", [{}])[0].get("detail", "Unknown error")
                return False, f"❌ Connection failed: {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "❌ Connection timeout. Please check your internet connection."
        except requests.exceptions.RequestException as e:
            return False, f"❌ Network error: {str(e)}"
        except Exception as e:
            return False, f"❌ Unexpected error: {str(e)}"
    
    def get_locations(self) -> List[Dict]:
        """Get all locations for this Square account"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/locations",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get("locations", [])
            else:
                print(f"Error fetching locations: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error fetching locations: {e}")
            return []
    
    def fetch_transactions(self, start_date: str, end_date: str, location_id: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch transactions from Square API
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            location_id: Optional specific location ID
            
        Returns:
            DataFrame with transactions in our standard format
        """
        try:
            # Get locations if not specified
            if not location_id:
                locations = self.get_locations()
                if not locations:
                    print("No locations found")
                    return pd.DataFrame()
                location_id = locations[0]["id"]  # Use first location
            
            # Convert dates to RFC3339 format
            start_datetime = f"{start_date}T00:00:00Z"
            end_datetime = f"{end_date}T23:59:59Z"
            
            # Build search query
            search_body = {
                "filter": {
                    "location_ids": [location_id],
                    "source_filter": {
                        "source_names": ["SQUARE_POS", "EXTERNAL_API", "ECOMMERCE_API"]
                    },
                    "time_range": {
                        "start_at": start_datetime,
                        "end_at": end_datetime
                    }
                },
                "sort": {
                    "sort_field": "CREATED_AT",
                    "sort_order": "ASC"
                }
            }
            
            # Search orders (Square's term for transactions)
            response = requests.post(
                f"{self.base_url}/v2/orders/search",
                headers=self.headers,
                json=search_body,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching transactions: {response.status_code} - {response.text}")
                return pd.DataFrame()
            
            orders = response.json().get("orders", [])
            print(f"Found {len(orders)} orders from Square API")
            
            # Convert to our standard format
            return self._convert_orders_to_transactions(orders)
            
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return pd.DataFrame()
    
    def _convert_orders_to_transactions(self, orders: List[Dict]) -> pd.DataFrame:
        """Convert Square orders to our transaction format"""
        transactions = []
        
        for order in orders:
            order_id = order.get("id", "")
            created_at = order.get("created_at", "")
            
            # Parse date
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = date_obj.date().isoformat()
            except:
                date_str = start_date  # Fallback
            
            # Process line items
            line_items = order.get("line_items", [])
            
            for i, item in enumerate(line_items):
                # Extract item details
                item_name = item.get("name", "Unknown Item")
                quantity = int(item.get("quantity", "1"))
                
                # Calculate pricing
                base_price_money = item.get("base_price_money", {})
                unit_price = float(base_price_money.get("amount", 0)) / 100  # Square uses cents
                
                gross_sales = unit_price * quantity
                
                # Handle discounts (simplified)
                total_discount_money = item.get("total_discount_money", {})
                discount = float(total_discount_money.get("amount", 0)) / 100
                
                net_sales = gross_sales - discount
                
                # Calculate tax (simplified)
                total_tax_money = item.get("total_tax_money", {})
                tax = float(total_tax_money.get("amount", 0)) / 100
                
                line_total = net_sales + tax
                
                # Create transaction record
                transaction = {
                    "date": date_str,
                    "transaction_id": order_id,
                    "product_id": item.get("uid", f"{order_id}_{i}"),
                    "product_name": item_name,
                    "category": item.get("category_name", "Unknown"),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "gross_sales": gross_sales,
                    "discount": discount,
                    "net_sales": net_sales,
                    "tax": tax,
                    "line_total": line_total,
                    "payment_type": "CARD",  # Most Square transactions are card
                    "tip_amount": 0.0  # Would need separate API call for tips
                }
                
                transactions.append(transaction)
        
        return pd.DataFrame(transactions)
    
    def fetch_products(self) -> pd.DataFrame:
        """Fetch product catalog from Square"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/catalog/list?types=ITEM",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching products: {response.status_code}")
                return pd.DataFrame()
            
            catalog_objects = response.json().get("objects", [])
            products = []
            
            for obj in catalog_objects:
                if obj.get("type") == "ITEM":
                    item_data = obj.get("item_data", {})
                    
                    product = {
                        "product_id": obj.get("id", ""),
                        "product_name": item_data.get("name", "Unknown"),
                        "category": item_data.get("category_name", "Unknown"),
                        "cogs": 0.0,  # Square doesn't provide COGS in basic API
                        "unit_price": 0.0  # Would need to get from variations
                    }
                    
                    # Try to get price from variations
                    variations = item_data.get("variations", [])
                    if variations:
                        variation_data = variations[0].get("item_variation_data", {})
                        price_money = variation_data.get("price_money", {})
                        product["unit_price"] = float(price_money.get("amount", 0)) / 100
                    
                    products.append(product)
            
            return pd.DataFrame(products)
            
        except Exception as e:
            print(f"Error fetching products: {e}")
            return pd.DataFrame()
    
    def generate_mock_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Generate realistic mock data for testing when no real data exists
        """
        print("🎭 Generating mock Square sandbox data...")
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days + 1
        
        # Mock products
        products_data = [
            {"product_id": "sq_coffee", "product_name": "Coffee", "category": "Beverage", "cogs": 0.80, "unit_price": 3.50},
            {"product_id": "sq_latte", "product_name": "Latte", "category": "Beverage", "cogs": 1.20, "unit_price": 4.50},
            {"product_id": "sq_sandwich", "product_name": "Sandwich", "category": "Food", "cogs": 2.50, "unit_price": 8.00},
            {"product_id": "sq_muffin", "product_name": "Muffin", "category": "Food", "cogs": 1.00, "unit_price": 3.00},
            {"product_id": "sq_tea", "product_name": "Tea", "category": "Beverage", "cogs": 0.50, "unit_price": 2.50},
        ]
        
        # Generate transactions
        transactions = []
        txn_id = 1000
        
        for day in range(days):
            current_date = start + timedelta(days=day)
            date_str = current_date.date().isoformat()
            
            # Generate 15-30 transactions per day
            daily_txns = 15 + (day % 16)  # Vary by day
            
            for _ in range(daily_txns):
                txn_id += 1
                
                # Random product
                product = products_data[txn_id % len(products_data)]
                quantity = 1 if txn_id % 4 != 0 else 2  # Mostly single items
                
                gross_sales = product["unit_price"] * quantity
                discount = 0.0 if txn_id % 10 != 0 else gross_sales * 0.1  # 10% discount sometimes
                net_sales = gross_sales - discount
                tax = net_sales * 0.08  # 8% tax
                line_total = net_sales + tax
                
                transaction = {
                    "date": date_str,
                    "transaction_id": f"sq_{txn_id}",
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
                    "tip_amount": round(0.5 if txn_id % 5 == 0 else 0.0, 2)
                }
                
                transactions.append(transaction)
        
        # Generate refunds (5% of transactions)
        refunds = []
        refund_transactions = transactions[::20]  # Every 20th transaction
        
        for i, txn in enumerate(refund_transactions):
            refunds.append({
                "original_transaction_id": txn["transaction_id"],
                "refund_date": txn["date"],
                "refund_amount": txn["line_total"],
                "refund_id": f"sq_refund_{i}",
                "reason": ["Customer complaint", "Wrong item", "Duplicate charge"][i % 3]
            })
        
        # Generate payouts (daily card settlements)
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
                fees = daily_card_sales * 0.029 + 0.30  # Square's typical fees
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


def test_square_integration():
    """Test function for Square API integration"""
    # This would use real sandbox credentials
    test_token = "YOUR_SANDBOX_ACCESS_TOKEN"
    
    connector = SquareAPIConnector(test_token, environment="sandbox")
    
    # Test connection
    success, message = connector.test_connection()
    print(f"Connection test: {message}")
    
    if success:
        # Test data fetching
        data = connector.generate_mock_data("2025-01-01", "2025-01-07")
        print(f"Generated mock data:")
        print(f"- Transactions: {len(data['transactions'])} rows")
        print(f"- Products: {len(data['products'])} rows")
        print(f"- Refunds: {len(data['refunds'])} rows")
        print(f"- Payouts: {len(data['payouts'])} rows")


if __name__ == "__main__":
    test_square_integration()