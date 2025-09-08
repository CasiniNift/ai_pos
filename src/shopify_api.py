# src/shopify_api.py - Shopify POS API integration

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

class ShopifyAPIConnector:
    """Shopify API integration for fetching transaction data"""
    
    def __init__(self, shop_name: str, access_token: str):
        """
        Initialize Shopify API connector
        
        Args:
            shop_name: Your Shopify shop name (e.g., 'my-store' for my-store.myshopify.com)
            access_token: Shopify private app access token
        """
        self.shop_name = shop_name
        self.access_token = access_token
        
        # Set base URL
        self.base_url = f"https://{shop_name}.myshopify.com/admin/api/2023-10"
        
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the API connection by fetching shop info
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = requests.get(
                f"{self.base_url}/shop.json",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                shop_data = response.json().get("shop", {})
                shop_name = shop_data.get("name", "Unknown")
                return True, f"✅ Connected to '{shop_name}' successfully!"
            else:
                error_data = response.json()
                error_msg = error_data.get("errors", "Unknown error")
                return False, f"❌ Connection failed: {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "❌ Connection timeout. Please check your internet connection."
        except requests.exceptions.RequestException as e:
            return False, f"❌ Network error: {str(e)}"
        except Exception as e:
            return False, f"❌ Unexpected error: {str(e)}"
    
    def fetch_transactions(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch orders from Shopify API
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with transactions in our standard format
        """
        try:
            # Convert dates to Shopify format
            start_datetime = f"{start_date}T00:00:00Z"
            end_datetime = f"{end_date}T23:59:59Z"
            
            # Fetch orders
            params = {
                "status": "any",
                "created_at_min": start_datetime,
                "created_at_max": end_datetime,
                "limit": 250  # Max per request
            }
            
            response = requests.get(
                f"{self.base_url}/orders.json",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching orders: {response.status_code} - {response.text}")
                return pd.DataFrame()
            
            orders = response.json().get("orders", [])
            print(f"Found {len(orders)} orders from Shopify API")
            
            # Convert to our standard format
            return self._convert_orders_to_transactions(orders)
            
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return pd.DataFrame()
    
    def _convert_orders_to_transactions(self, orders: List[Dict]) -> pd.DataFrame:
        """Convert Shopify orders to our transaction format"""
        transactions = []
        
        for order in orders:
            order_id = order.get("id", "")
            created_at = order.get("created_at", "")
            
            # Parse date
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = date_obj.date().isoformat()
            except:
                date_str = "2025-01-01"  # Fallback
            
            # Process line items
            line_items = order.get("line_items", [])
            
            for item in line_items:
                # Extract item details
                item_name = item.get("title", "Unknown Item")
                quantity = int(item.get("quantity", 1))
                unit_price = float(item.get("price", 0))
                
                gross_sales = unit_price * quantity
                
                # Handle discounts
                total_discount = float(order.get("total_discounts", 0))
                item_discount = total_discount * (gross_sales / float(order.get("subtotal_price", gross_sales))) if gross_sales > 0 else 0
                
                net_sales = gross_sales - item_discount
                
                # Calculate tax
                tax_lines = item.get("tax_lines", [])
                item_tax = sum(float(tax.get("price", 0)) for tax in tax_lines)
                
                line_total = net_sales + item_tax
                
                # Determine payment type
                payment_type = "CARD"  # Most Shopify orders are card
                
                transaction = {
                    "date": date_str,
                    "transaction_id": str(order_id),
                    "product_id": str(item.get("product_id", f"{order_id}_{item.get('id')}")),
                    "product_name": item_name,
                    "category": item.get("vendor", "Unknown"),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "gross_sales": round(gross_sales, 2),
                    "discount": round(item_discount, 2),
                    "net_sales": round(net_sales, 2),
                    "tax": round(item_tax, 2),
                    "line_total": round(line_total, 2),
                    "payment_type": payment_type,
                    "tip_amount": 0.0  # Shopify doesn't typically handle tips
                }
                
                transactions.append(transaction)
        
        return pd.DataFrame(transactions)
    
    def fetch_products(self) -> pd.DataFrame:
        """Fetch product catalog from Shopify"""
        try:
            response = requests.get(
                f"{self.base_url}/products.json?limit=250",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching products: {response.status_code}")
                return pd.DataFrame()
            
            products = response.json().get("products", [])
            product_list = []
            
            for product in products:
                variants = product.get("variants", [])
                for variant in variants:
                    product_entry = {
                        "product_id": str(variant.get("id", "")),
                        "product_name": product.get("title", "Unknown"),
                        "category": product.get("product_type", "Unknown"),
                        "cogs": 0.0,  # Shopify doesn't provide COGS in basic API
                        "unit_price": float(variant.get("price", 0))
                    }
                    product_list.append(product_entry)
            
            return pd.DataFrame(product_list)
            
        except Exception as e:
            print(f"Error fetching products: {e}")
            return pd.DataFrame()
    
    def generate_mock_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Generate realistic mock e-commerce data for testing"""
        print("🛍️ Generating mock Shopify e-commerce data...")
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days + 1
        
        # Mock e-commerce products
        products_data = [
            {"product_id": "shopify_tshirt", "product_name": "T-Shirt", "category": "Apparel", "cogs": 8.00, "unit_price": 25.00},
            {"product_id": "shopify_hoodie", "product_name": "Hoodie", "category": "Apparel", "cogs": 15.00, "unit_price": 55.00},
            {"product_id": "shopify_mug", "product_name": "Coffee Mug", "category": "Accessories", "cogs": 4.00, "unit_price": 18.00},
            {"product_id": "shopify_hat", "product_name": "Baseball Cap", "category": "Accessories", "cogs": 6.00, "unit_price": 22.00},
            {"product_id": "shopify_sticker", "product_name": "Sticker Pack", "category": "Accessories", "cogs": 1.50, "unit_price": 8.00},
        ]
        
        # Generate transactions (fewer per day for e-commerce)
        transactions = []
        order_id = 5000
        
        for day in range(days):
            current_date = start + timedelta(days=day)
            date_str = current_date.date().isoformat()
            
            # Generate 3-12 orders per day (typical for small e-commerce)
            daily_orders = 3 + (day % 10)
            
            for _ in range(daily_orders):
                order_id += 1
                
                # Random number of items per order (1-3)
                items_in_order = 1 + (order_id % 3)
                
                for _ in range(items_in_order):
                    # Random product
                    product = products_data[order_id % len(products_data)]
                    quantity = 1 if order_id % 3 != 0 else 2  # Usually single items
                    
                    gross_sales = product["unit_price"] * quantity
                    discount = 0.0 if order_id % 8 != 0 else gross_sales * 0.15  # 15% discount sometimes
                    net_sales = gross_sales - discount
                    tax = net_sales * 0.0875  # ~8.75% sales tax
                    line_total = net_sales + tax
                    
                    transaction = {
                        "date": date_str,
                        "transaction_id": f"shopify_{order_id}",
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
        
        # Generate refunds (3% of transactions)
        refunds = []
        refund_transactions = transactions[::33]  # Every 33rd transaction
        
        for i, txn in enumerate(refund_transactions):
            refunds.append({
                "original_transaction_id": txn["transaction_id"],
                "refund_date": txn["date"],
                "refund_amount": txn["line_total"],
                "refund_id": f"shopify_refund_{i}",
                "reason": ["Defective item", "Wrong size", "Customer changed mind"][i % 3]
            })
        
        # Generate payouts (Shopify pays out daily)
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
                fees = daily_card_sales * 0.029 + 0.30  # Shopify Payments typical fees
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