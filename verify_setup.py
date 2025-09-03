#!/usr/bin/env python3
"""
Simple verification for Mac - AI POS Cash Flow Assistant
"""

import os
import sys

def main():
    print("🍎 MacBook Air - AI POS Setup Check")
    print("=" * 40)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and api_key.startswith('sk-'):
        print(f"✅ OpenAI API key found")
        print(f"   Key: {api_key[:10]}...")
    else:
        print("❌ OpenAI API key not found or invalid")
        print("💡 Set with: export OPENAI_API_KEY='sk-your-key'")
        return False
    
    # Check basic imports
    try:
        import pandas
        print("✅ pandas installed")
    except ImportError:
        print("❌ pandas missing - install with: pip3 install pandas")
        return False
    
    try:
        import gradio
        print("✅ gradio installed")
    except ImportError:
        print("❌ gradio missing - install with: pip3 install gradio")
        return False
        
    try:
        import openai
        print("✅ openai installed")
    except ImportError:
        print("❌ openai missing - install with: pip3 install openai")
        return False
    
    # Check data files
    if os.path.exists('data/pos_transactions_week.csv'):
        print("✅ Sample data found")
    else:
        print("⚠️  Sample data missing - will generate automatically")
    
    print("\n🚀 Ready to run: python3 src/app.py")
    return True

if __name__ == "__main__":
    main()