# src/ai_assistant.py - Claude Integration Layer with improved formatting

import os
import anthropic
from typing import Dict, Any, Optional
import pandas as pd
import json
from datetime import datetime, timedelta

class CashFlowAIAssistant:
    """AI-powered cash flow analysis assistant using Claude (Anthropic)"""
    
    def __init__(self, model=None, api_key=None):
        self.model = model or "claude-3-haiku-20240307"  # Fast and cost-effective
        self.api_key = api_key or self._get_claude_key()
        
        if self.api_key and self._validate_api_key(self.api_key):
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
            if not self.api_key:
                print("⚠️  No Claude API key found. Set ANTHROPIC_API_KEY environment variable.")
            else:
                print("⚠️  Invalid Claude API key format detected.")
    
    def _get_claude_key(self) -> Optional[str]:
        """Get Claude API key from environment variables"""
        possible_keys = [
            "ANTHROPIC_API_KEY",
            "CLAUDE_API_KEY",
            "CLAUDE_KEY"
        ]
        
        for key_name in possible_keys:
            api_key = os.getenv(key_name)
            if api_key:
                return api_key
        return None
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Basic validation of Claude API key format"""
        if not api_key:
            return False
        # Claude keys typically start with 'sk-ant-' and are longer
        if api_key.startswith('sk-ant-') and len(api_key) > 50:
            return True
        return False
    
    def set_api_key(self, api_key: str):
        """Update the API key and recreate client"""
        if self._validate_api_key(api_key):
            self.api_key = api_key
            self.client = anthropic.Anthropic(api_key=api_key)
            return True
        return False
    
    def is_available(self) -> bool:
        """Check if AI assistant is ready to use"""
        return self.client is not None and self.api_key is not None
    
    def _prepare_business_context(self, tx_data: pd.DataFrame, refunds_data: pd.DataFrame, 
                                 payouts_data: pd.DataFrame, products_data: pd.DataFrame) -> str:
        """Prepare business context from the data for the AI"""
        
        # Calculate key metrics
        total_transactions = len(tx_data['transaction_id'].unique())
        date_range = f"{tx_data['day'].min()} to {tx_data['day'].max()}"
        total_revenue = tx_data['line_total'].sum()
        total_discounts = tx_data['discount'].sum()
        total_refunds = refunds_data['refund_amount'].sum()
        total_processor_fees = payouts_data['processor_fees'].sum()
        
        # Top selling products
        top_products = tx_data.groupby('product_name')['quantity'].sum().head(3)
        
        # Payment method breakdown
        payment_breakdown = tx_data.groupby('payment_type')['line_total'].sum()
        
        context = f"""
BUSINESS DATA SUMMARY:
Period: {date_range}
Total Transactions: {total_transactions:,}
Total Revenue: €{total_revenue:,.2f}
Total Discounts Given: €{total_discounts:,.2f}
Total Refunds: €{total_refunds:,.2f}
Processor Fees: €{total_processor_fees:,.2f}

PAYMENT METHODS:
{payment_breakdown.to_string()}

TOP SELLING PRODUCTS:
{top_products.to_string()}

PRODUCT CATALOG:
{products_data[['product_name', 'category', 'cogs', 'unit_price']].to_string()}
"""
        return context
    
    def _make_claude_request(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        """Make a request to Claude API"""
        if not self.is_available():
            return "AI Analysis Error: Claude API key not configured. Please add your API key to enable AI insights."
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            return f"AI Analysis Error: {str(e)}. Please check your Claude API key and try again."
    
    def _get_language_instruction(self, language: str) -> str:
        """Get language-specific instruction for AI responses"""
        instructions = {
            "italian": """Rispondi SEMPRE in italiano. Usa un tono professionale ma colloquiale, come se stessi consigliando direttamente un imprenditore italiano. 
            Struttura la tua risposta con paragrafi chiari e numerati quando appropriato. Usa terminologia finanziaria appropriata in italiano.
            Formatta la risposta con interruzioni di paragrafo chiare per migliorare la leggibilità.""",
            "spanish": """Responde SIEMPRE en español. Usa un tono profesional pero conversacional, como si estuvieras aconsejando directamente a un empresario español. 
            Estructura tu respuesta con párrafos claros y numerados cuando sea apropiado. Usa terminología financiera apropiada en español.
            Formatea la respuesta con saltos de párrafo claros para mejorar la legibilidad.""",
            "english": """Respond in English with a professional but conversational tone, like you're advising a business owner directly.
            Structure your response with clear, numbered paragraphs when appropriate. Format the response with clear paragraph breaks for readability."""
        }
        return instructions.get(language, instructions["english"])
    
    def analyze_cash_eaters(self, business_context: str, cash_eaters_data: Dict, language: str = "english") -> str:
        """AI analysis of what's eating cash flow"""
        
        language_instruction = self._get_language_instruction(language)
        system_prompt = f"You are an expert retail financial advisor who gives clear, actionable advice. {language_instruction}"
        
        user_prompt = f"""
Analyze the following business data and cash flow issues:

{business_context}

CASH FLOW ANALYSIS DATA:
Discounts: €{cash_eaters_data.get('discounts', 0):,.2f}
Refunds: €{cash_eaters_data.get('refunds', 0):,.2f}
Processor Fees: €{cash_eaters_data.get('processor_fees', 0):,.2f}

LOWEST MARGIN PRODUCTS:
{cash_eaters_data.get('low_margin_products', 'No data available')}

Provide a structured analysis answering "What's eating my cash flow?" Format your response with:

1. **Biggest cash drain assessment** (2-3 sentences)

2. **Specific actionable recommendations** (3-4 key points)

3. **Quick wins for this week** (immediate actions)

Use clear paragraph breaks between sections for readability.
"""
        
        return self._make_claude_request(system_prompt, user_prompt, max_tokens=600)
    
    def analyze_reorder_plan(self, business_context: str, reorder_data: Dict, budget: float, language: str = "english") -> str:
        """AI analysis of reorder recommendations"""
        
        language_instruction = self._get_language_instruction(language)
        system_prompt = f"You are an expert inventory management advisor for retail businesses. {language_instruction}"
        
        user_prompt = f"""
Based on this business data, analyze the reorder plan:

{business_context}

REORDER PLAN ANALYSIS:
Budget: €{budget:,.2f}
Remaining Budget: €{reorder_data.get('remaining_budget', 0):,.2f}

RECOMMENDED PURCHASES:
{reorder_data.get('purchase_plan', 'No recommendations available')}

Provide structured analysis for "What should I reorder with my budget?" Format with:

1. **Purchase plan assessment** (2-3 sentences on the overall strategy)

2. **Product prioritization rationale** (why these specific items)

3. **Expected ROI and cash flow impact** (quantified benefits where possible)

4. **Alternative strategies** (other options to consider)

Use clear paragraph breaks between sections. Be specific about financial impact.
"""
        
        return self._make_claude_request(system_prompt, user_prompt, max_tokens=600)
    
    def analyze_cash_liberation(self, business_context: str, clearance_data: Dict, language: str = "english") -> str:
        """AI analysis of cash liberation opportunities"""
        
        language_instruction = self._get_language_instruction(language)
        system_prompt = f"You are an expert at helping retailers optimize inventory and free up working capital. {language_instruction}"
        
        user_prompt = f"""
Analyze this clearance opportunity:

{business_context}

CASH LIBERATION ANALYSIS:
Estimated Extra Cash from Clearance: €{clearance_data.get('total_extra_cash', 0):,.2f}

SLOW-MOVING INVENTORY:
{clearance_data.get('slow_movers', 'No data available')}

Provide structured analysis for "How much cash can I free up?" Format with:

1. **Cash liberation potential assessment** (evaluation of the €{clearance_data.get('total_extra_cash', 0):,.2f} opportunity)

2. **Clearance strategy recommendations** (specific execution tactics)

3. **Timing considerations** (when and how to implement)

4. **Reinvestment strategy** (how to use the freed cash for maximum impact)

Use clear paragraph breaks between sections. Focus on practical execution steps.
"""
        
        return self._make_claude_request(system_prompt, user_prompt, max_tokens=600)
    
    def analyze_sales_impact(self, business_context: str, sales_drop_percent: float = 10, language: str = "english") -> str:
        """AI analysis of sales drop impact on runway"""
        
        language_instruction = self._get_language_instruction(language)
        system_prompt = f"You are an expert financial advisor specializing in retail cash flow management and crisis planning. {language_instruction}"
        
        user_prompt = f"""
Analyze the impact of a sales decline:

{business_context}

SCENARIO ANALYSIS:
Projected sales drop: {sales_drop_percent}%

Provide structured analysis for "If sales drop {sales_drop_percent}% next month, what's the impact on my cash runway?"

Format with:

1. **Immediate cash flow impact** (quantified impact assessment)

2. **Runway analysis** (how many weeks/months affected)

3. **Priority cost reductions** (which expenses to cut first)

4. **Mitigation strategies** (actions to minimize impact)

5. **Monitoring plan** (early warning signs to watch)

Use clear paragraph breaks between sections. Be specific about cash preservation timeline.
"""
        
        return self._make_claude_request(system_prompt, user_prompt, max_tokens=700)
    
    def generate_executive_insights(self, business_context: str) -> str:
        """Generate high-level executive insights"""
        
        system_prompt = "You are a senior business consultant providing executive-level retail insights."
        
        user_prompt = f"""
Provide a brief executive summary based on this business data:

{business_context}

Provide:
1. **Key business health indicators** (2-3 sentences)
2. **Top 2 opportunities for improvement**
3. **Critical action item for this week**

Keep it concise and executive-focused with clear paragraph breaks.
"""
        
        return self._make_claude_request(system_prompt, user_prompt, max_tokens=350)