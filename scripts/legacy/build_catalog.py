import pandas as pd
import os

def build_master_catalog():
    shopify_file = 'products_export_1.csv'
    
    if not os.path.exists(shopify_file):
        print(f"CRITICAL ERROR: {shopify_file} not found.")
        return

    try:
        df_shopify = pd.read_csv(shopify_file, dtype={'Variant SKU': str})
        master = df_shopify[['Variant SKU', 'Title', 'Variant Price']].rename(
            columns={'Variant SKU': 'SKU', 'Title': 'Description', 'Variant Price': 'MSRP'}
        )
        master['SKU'] = master['SKU'].str.strip()
        master = master.dropna(subset=['SKU'])
        
        # FIX: Remove duplicate SKUs from the Shopify export first
        # We sort so that rows with actual descriptions stay on top
        master = master.sort_values('Description', ascending=False).drop_duplicates('SKU')
        
    except Exception as e:
        print(f"ERROR: Failed to process {shopify_file}. {e}")
        return

    tiers = ['BRONZE', 'SILVER', 'GOLD', 'PLATINUM']
    directory_files = os.listdir('.')
    
    for tier in tiers:
        match_file = next((f for f in directory_files if tier in f.upper() and f.endswith('.csv') and 'products_export' not in f), None)
        
        if match_file:
            try:
                df_tier = pd.read_csv(match_file, dtype={'ITEM_NBR': str})
                df_tier = df_tier[['ITEM_NBR', 'PRICE']].rename(columns={'ITEM_NBR': 'SKU', 'PRICE': f'{tier}_Price'})
                df_tier['SKU'] = df_tier['SKU'].str.strip()
                # Ensure tier data itself has no duplicates
                df_tier = df_tier.drop_duplicates('SKU')
                
                master = pd.merge(master, df_tier, on='SKU', how='left')
                print(f"SUCCESS: Integrated {tier} data.")
            except Exception as e:
                print(f"ERROR: Processing {match_file} failed. {e}")

    # Final save
    master.to_csv('Master_Catalog_Final.csv', index=False)
    print("\nPROCESS COMPLETE: Master_Catalog_Final.csv generated with unique SKUs.")

if __name__ == "__main__":
    build_master_catalog()