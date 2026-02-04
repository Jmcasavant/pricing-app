import pandas as pd
import os

class PricingEngine:
    def __init__(self):
        catalog_path = 'Master_Catalog_Final.csv'
        rules_path = 'Pricing Rules Starter 1.xlsx'

        if not os.path.exists(catalog_path):
            raise FileNotFoundError("Master_Catalog_Final.csv not found. Execute build_catalog.py first.")
        
        if not os.path.exists(rules_path):
            raise FileNotFoundError("Pricing Rules Starter 1.xlsx not found.")

        # Load master data
        self.catalog = pd.read_csv(catalog_path, index_col='SKU', dtype={'SKU': str})
        
        # Load account mapping logic
        self.program_map = pd.read_excel(rules_path, sheet_name='Program Map', dtype=str)
        self.group_members = pd.read_excel(rules_path, sheet_name='Group Members', dtype=str)

    def get_account_tier(self, account_id):
        """
        Resolves the pricing tier for a specific account ID.
        """
        account_id = str(account_id).strip()
        
        # Exact account match
        exact_match = self.program_map[self.program_map['Match Value'] == account_id]
        if not exact_match.empty:
            return exact_match.iloc[0]['Program ID']
        
        # Group membership match
        account_groups = self.group_members[self.group_members['Account Number'] == account_id]['Group ID'].unique()
        if len(account_groups) > 0:
            group_match = self.program_map[self.program_map['Match Value'].isin(account_groups)]
            if not group_match.empty:
                return group_match.iloc[0]['Program ID']
        
        return "MSRP"

    def calculate_quote(self, account_id, cart_items):
        """
        Calculates line items and totals based on the resolved tier.
        """
        tier = self.get_account_tier(account_id)
        line_items = []
        grand_total = 0.0
        
        for sku, qty in cart_items.items():
            if sku in self.catalog.index:
                # Handle potential duplicates by taking the first entry
                product_data = self.catalog.loc[[sku]].head(1).iloc[0]
                tier_column = f"{tier}_Price"
                
                if tier_column in product_data and pd.notna(product_data[tier_column]):
                    unit_price = float(product_data[tier_column])
                    source = "Contract"
                else:
                    unit_price = float(product_data['MSRP'])
                    source = "MSRP"
                
                line_total = unit_price * qty
                grand_total += line_total
                
                description = product_data['Description'] if pd.notna(product_data['Description']) else "N/A"
                
                line_items.append({
                    "SKU": sku,
                    "Description": description,
                    "Quantity": qty,
                    "Unit Price": unit_price,
                    "Total": line_total,
                    "Source": source
                })
                
        return {
            "Account": account_id,
            "Tier": tier,
            "Total": grand_total,
            "Lines": line_items
        }