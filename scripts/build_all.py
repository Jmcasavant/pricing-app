#!/usr/bin/env python
"""
Build pipeline - builds catalog and validates data.

Usage:
    python scripts/build_all.py
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from pricing_tool.data.build_catalog import build_master_catalog


def main():
    print("=" * 60)
    print("PRICING TOOL BUILD PIPELINE")
    print("=" * 60)
    print()
    
    # Build catalog
    print("[1/2] Building master catalog...")
    report = build_master_catalog(verbose=True)
    
    if report["status"] != "success":
        print("\n❌ BUILD FAILED")
        for error in report["errors"]:
            print(f"  ERROR: {error}")
        sys.exit(1)
    
    print()
    print("[2/2] Running golden tests...")
    
    # Run tests
    import subprocess
    test_result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/test_golden_cases.py', '-v', '--tb=short'],
        cwd=Path(__file__).parent.parent
    )
    
    if test_result.returncode != 0:
        print("\n❌ TESTS FAILED")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ BUILD COMPLETE")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  SKUs: {report['metrics']['final_sku_count']}")
    print(f"  Duplicates removed: {report['metrics']['duplicates_removed']}")
    print(f"  Missing MSRP: {report['metrics']['missing_msrp']}")
    print()
    print("Tier Coverage:")
    for tier, stats in report['metrics'].get('tier_coverage', {}).items():
        print(f"  {tier}: {stats['coverage_pct']}% ({stats['priced_skus']} SKUs)")


if __name__ == "__main__":
    main()
