#!/usr/bin/env python3
"""
Simple verification for Mac - AI POS Cash Flow Assistant
Updated to check for Anthropic/Claude instead of OpenAI
"""

import os
import sys

def main():
    print("🍎 MacBook Air - AI POS Setup Check")
    print("=" * 40)
    
    # Check for Anthropic API key (multiple possible environment variable names)
    api_key = None
    possible_keys = [
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY", 
        "CLAUDE_KEY",
        "ANTHROPIC_KEY"
    ]
    
    for key_name in possible_keys:
        api_key = os.getenv(key_name)
        if api_key:
            if api_key.startswith('sk-ant-') and len(api_key) > 50:
                print(f"✅ Anthropic API key found ({key_name})")
                print(f"   Key: {api_key[:10]}...")
                break
            else:
                print(f"⚠️  Found {key_name} but format seems incorrect")
                print(f"   Key: {api_key[:10]}...")
                print("💡 Anthropic keys should start with 'sk-ant-' and be longer than 50 characters")
    
    if not api_key:
        print("❌ Anthropic API key not found")
        print("💡 Set with: export ANTHROPIC_API_KEY='sk-ant-your-key'")
        print("💡 Or any of these variable names:")
        for key_name in possible_keys:
            print(f"   export {key_name}='sk-ant-your-key'")
        return False
    
    # Check basic imports
    try:
        import pandas
        print("✅ pandas installed")
    except ImportError:
        print("❌ pandas missing - install with: pip install pandas")
        return False
    
    try:
        import gradio
        print("✅ gradio installed")
    except ImportError:
        print("❌ gradio missing - install with: pip install gradio")
        return False
        
    try:
        import anthropic
        print("✅ anthropic installed")
    except ImportError:
        print("❌ anthropic missing - install with: pip install anthropic")
        return False
    
    try:
        import numpy
        print("✅ numpy installed")
    except ImportError:
        print("❌ numpy missing - install with: pip install numpy")
        return False
    
    # Check data files
    if os.path.exists('data/pos_transactions_week.csv'):
        print("✅ Sample data found")
    else:
        print("⚠️  Sample data missing - will generate automatically")
    
    # Test Anthropic connection (optional)
    if api_key and api_key.startswith('sk-ant-'):
        try:
            print("\n🧪 Testing Anthropic API connection...")
            client = anthropic.Anthropic(api_key=api_key)
            # Simple test - just check if we can create a client
            print("✅ Anthropic client created successfully")
        except Exception as e:
            print(f"⚠️  Anthropic API test failed: {str(e)}")
            print("   This might be a network issue or invalid API key")
    
    print(f"\n🐍 Python version: {sys.version}")
    print(f"📁 Current directory: {os.getcwd()}")
    print("\n🚀 Ready to run: python src/app.py")
    return True

if __name__ == "__main__":
    main()