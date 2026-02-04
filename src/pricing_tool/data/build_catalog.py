"""
Catalog Builder - Aggregates Shopify exports and tier price lists.

Migrated from the original build_catalog.py with added:
- Configuration-driven paths
- Build report generation
- Structured logging
"""
import pandas as pd
import os
import json
import hashlib
from datetime import datetime
from typing import Optional
from pathlib import Path

from ..config.settings import get_settings, Settings


def get_file_hash(path: Path) -> str:
    """Get SHA256 hash of a file."""
    if not path.exists():
        return ""
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def build_master_catalog(settings: Optional[Settings] = None, verbose: bool = True) -> dict:
    """
    Build the master catalog from Shopify export and tier price lists.
    
    Args:
        settings: Optional settings override
        verbose: Print progress messages
        
    Returns:
        Build report dictionary
    """
    settings = settings or get_settings()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "input_files": {},
        "metrics": {},
        "warnings": [],
        "errors": []
    }
    
    shopify_file = settings.shopify_export
    
    if not shopify_file.exists():
        msg = f"CRITICAL ERROR: {shopify_file} not found."
        report["errors"].append(msg)
        report["status"] = "failed"
        if verbose:
            print(msg)
        return report
    
    report["input_files"]["shopify_export"] = {
        "path": str(shopify_file),
        "hash": get_file_hash(shopify_file)
    }
    
    try:
        df_shopify = pd.read_csv(shopify_file, dtype={'Variant SKU': str})
        master = df_shopify[['Variant SKU', 'Title', 'Variant Price']].rename(
            columns={'Variant SKU': 'SKU', 'Title': 'Description', 'Variant Price': 'MSRP'}
        )
        master['SKU'] = master['SKU'].str.strip()
        master = master.dropna(subset=['SKU'])
        
        initial_count = len(master)
        report["metrics"]["initial_sku_count"] = initial_count
        
        # Remove duplicate SKUs, keeping rows with actual descriptions
        duplicates_before = master['SKU'].duplicated().sum()
        master = master.sort_values('Description', ascending=False).drop_duplicates('SKU')
        
        report["metrics"]["duplicates_removed"] = int(duplicates_before)
        if duplicates_before > 0 and verbose:
            print(f"Removed {duplicates_before} duplicate SKUs (kept rows with descriptions)")
            
    except Exception as e:
        msg = f"ERROR: Failed to process {shopify_file}. {e}"
        report["errors"].append(msg)
        report["status"] = "failed"
        if verbose:
            print(msg)
        return report
    
    # First, try to use catalogs_export.csv (Shopify B2B Catalog Export)
    # This contains comprehensive tier pricing from ERP
    catalogs_export_path = settings.project_root / 'catalogs_export.csv'
    tier_coverage = {}
    
    if catalogs_export_path.exists():
        report["input_files"]["catalogs_export"] = {
            "path": str(catalogs_export_path),
            "hash": get_file_hash(catalogs_export_path)
        }
        
        if verbose:
            print(f"Found catalogs_export.csv - using as primary tier pricing source")
        
        try:
            df_catalogs = pd.read_csv(catalogs_export_path, dtype={'SKU': str})
            
            # Pivot: each "Catalog Title" becomes a [TIER]_Price column
            for tier_name in df_catalogs['Catalog Title'].unique():
                tier_key = tier_name.upper()  # Normalize: Bronze -> BRONZE
                
                tier_data = df_catalogs[df_catalogs['Catalog Title'] == tier_name][['SKU', 'Fixed Price']].copy()
                tier_data = tier_data.rename(columns={'Fixed Price': f'{tier_key}_Price'})
                tier_data['SKU'] = tier_data['SKU'].astype(str).str.strip()
                tier_data = tier_data.dropna(subset=['SKU'])
                tier_data = tier_data[tier_data['SKU'] != '#N/A']  # Filter out invalid SKUs
                tier_data = tier_data.drop_duplicates('SKU')
                
                # Merge into master
                master = pd.merge(master, tier_data, on='SKU', how='left')
                
                # Count coverage
                priced_count = master[f'{tier_key}_Price'].notna().sum()
                tier_coverage[tier_key] = {
                    "priced_skus": int(priced_count),
                    "coverage_pct": round(priced_count / len(master) * 100, 1)
                }
                
                if verbose:
                    print(f"SUCCESS: Integrated {tier_key} from catalogs_export. Coverage: {tier_coverage[tier_key]['coverage_pct']}%")
                    
        except Exception as e:
            msg = f"ERROR: Failed to process catalogs_export.csv. {e}"
            report["warnings"].append(msg)
            if verbose:
                print(msg)
    else:
        # Fallback: use legacy tier CSV files (BRONZE.csv, SILVER.csv, etc.)
        if verbose:
            print("catalogs_export.csv not found - using legacy tier CSV files")
        
        tiers = list(settings.active_tiers)
        
        for tier in tiers:
            tier_path = settings.tier_files.get(tier)
            
            if tier_path and tier_path.exists():
                report["input_files"][f"{tier.lower()}_prices"] = {
                    "path": str(tier_path),
                    "hash": get_file_hash(tier_path)
                }
                
                try:
                    df_tier = pd.read_csv(tier_path, dtype={'ITEM_NBR': str})
                    df_tier = df_tier[['ITEM_NBR', 'PRICE']].rename(
                        columns={'ITEM_NBR': 'SKU', 'PRICE': f'{tier}_Price'}
                    )
                    df_tier['SKU'] = df_tier['SKU'].str.strip()
                    df_tier = df_tier.drop_duplicates('SKU')
                    
                    master = pd.merge(master, df_tier, on='SKU', how='left')
                    
                    # Count coverage
                    priced_count = master[f'{tier}_Price'].notna().sum()
                    tier_coverage[tier] = {
                        "priced_skus": int(priced_count),
                        "coverage_pct": round(priced_count / len(master) * 100, 1)
                    }
                    
                    if verbose:
                        print(f"SUCCESS: Integrated {tier} data. Coverage: {tier_coverage[tier]['coverage_pct']}%")
                        
                except Exception as e:
                    msg = f"ERROR: Processing {tier_path} failed. {e}"
                    report["warnings"].append(msg)
                    if verbose:
                        print(msg)
            else:
                report["warnings"].append(f"WARNING: {tier}.csv not found")
                if verbose:
                    print(f"WARNING: {tier}.csv not found")
    
    report["metrics"]["tier_coverage"] = tier_coverage
    report["metrics"]["final_sku_count"] = len(master)
    
    # Check for missing MSRP
    missing_msrp = master['MSRP'].isna().sum()
    report["metrics"]["missing_msrp"] = int(missing_msrp)
    if missing_msrp > 0:
        report["warnings"].append(f"{missing_msrp} SKUs have no MSRP")
    
    # Save master catalog
    output_path = settings.master_catalog
    master.to_csv(output_path, index=False)
    report["output_file"] = str(output_path)
    report["status"] = "success"
    
    if verbose:
        print(f"\nPROCESS COMPLETE: {output_path} generated with {len(master)} unique SKUs.")
    
    # Save build report
    report_path = settings.build_report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    if verbose:
        print(f"Build report saved to: {report_path}")
    
    return report


if __name__ == "__main__":
    build_master_catalog()
