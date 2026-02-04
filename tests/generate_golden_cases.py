"""
Generate golden test cases by running current pricing engine on sample data.
This captures current behavior as a regression baseline.
"""
import pandas as pd
import sys
import os

# Add parent to path so we can import pricing_engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pricing_engine import PricingEngine

def generate_golden_cases():
    engine = PricingEngine()
    
    # Explicit test accounts with known behaviors
    accounts_to_test = [
        '1730',      # Default account from app.py
        '99999999',  # Non-existent account (should resolve to MSRP)
    ]
    
    # Try to add accounts from mapping data
    if 'Match Type' in engine.program_map.columns:
        account_matches = engine.program_map[engine.program_map['Match Type'] == 'account']['Match Value'].dropna().tolist()
        accounts_to_test.extend(account_matches[:3])
    
    if 'Account Number' in engine.group_members.columns:
        group_accounts = engine.group_members['Account Number'].dropna().unique().tolist()
        accounts_to_test.extend(group_accounts[:3])
    
    # Remove duplicates while preserving order
    accounts_to_test = list(dict.fromkeys(accounts_to_test))
    
    # Get sample SKUs - mix of those with tier prices and MSRP-only
    catalog = engine.catalog
    
    # SKUs with BRONZE_Price (should have tier pricing)
    skus_with_tier = catalog[catalog['BRONZE_Price'].notna()].index.tolist()[:5]
    
    # SKUs without any tier price (MSRP fallback)
    tier_cols = ['BRONZE_Price', 'SILVER_Price', 'GOLD_Price', 'PLATINUM_Price']
    existing_tier_cols = [c for c in tier_cols if c in catalog.columns]
    if existing_tier_cols:
        skus_msrp_only = catalog[catalog[existing_tier_cols].isna().all(axis=1)].index.tolist()[:5]
    else:
        skus_msrp_only = catalog.index.tolist()[:5]
    
    test_skus = list(dict.fromkeys(skus_with_tier + skus_msrp_only))
    
    print(f"Accounts to test: {accounts_to_test}")
    print(f"SKUs to test: {test_skus}")
    print()
    
    # Generate test cases
    cases = []
    for account in accounts_to_test:
        tier = engine.get_account_tier(str(account))
        for sku in test_skus:
            for qty in [1, 10]:  # Test single and bulk
                result = engine.calculate_quote(str(account), {sku: qty})
                if result['Lines']:
                    line = result['Lines'][0]
                    cases.append({
                        'account': account,
                        'sku': sku,
                        'qty': qty,
                        'expected_tier': tier,
                        'expected_unit_price': line['Unit Price'],
                        'expected_source': line['Source'],
                        'description': line['Description']
                    })
    
    # Write to CSV
    df = pd.DataFrame(cases)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'golden_cases.csv')
    df.to_csv(output_path, index=False)
    print(f"Generated {len(cases)} golden test cases")
    print(f"Output: {output_path}")
    print()
    print("Sample cases:")
    print(df.head(10).to_string(index=False))

if __name__ == "__main__":
    generate_golden_cases()
