"""
Golden test cases for pricing engine regression testing.
These tests capture the expected behavior of the pricing engine and
should fail if pricing logic changes unexpectedly.
"""
import csv
import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pricing_engine import PricingEngine


@pytest.fixture(scope="module")
def engine():
    """Create a single engine instance for all tests."""
    return PricingEngine()


def load_golden_cases():
    """Load golden test cases from CSV."""
    cases_path = os.path.join(os.path.dirname(__file__), 'golden_cases.csv')
    
    if not os.path.exists(cases_path):
        pytest.skip(f"Golden cases file not found: {cases_path}. Run generate_golden_cases.py first.")
    
    cases = []
    with open(cases_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)
    
    return cases


@pytest.mark.parametrize("case", load_golden_cases(), ids=lambda c: f"{c['account']}-{c['sku']}-qty{c['qty']}")
def test_golden_case(engine, case):
    """Test that pricing matches expected golden case."""
    account = str(case['account'])
    sku = str(case['sku'])
    qty = int(case['qty'])
    expected_tier = case['expected_tier']
    expected_unit_price = float(case['expected_unit_price'])
    expected_source = case['expected_source']
    
    # Run pricing engine
    result = engine.calculate_quote(account, {sku: qty})
    
    # Assert tier resolution
    assert result['Tier'] == expected_tier, \
        f"Tier mismatch for account {account}: expected {expected_tier}, got {result['Tier']}"
    
    # Assert line item exists
    assert len(result['Lines']) == 1, \
        f"Expected 1 line item, got {len(result['Lines'])}"
    
    line = result['Lines'][0]
    
    # Assert unit price
    assert abs(line['Unit Price'] - expected_unit_price) < 0.01, \
        f"Price mismatch for {sku}: expected ${expected_unit_price:.2f}, got ${line['Unit Price']:.2f}"
    
    # Assert source
    assert line['Source'] == expected_source, \
        f"Source mismatch for {sku}: expected {expected_source}, got {line['Source']}"


def test_tier_resolution_msrp_fallback(engine):
    """Test that unknown accounts fall back to MSRP tier."""
    tier = engine.get_account_tier('NONEXISTENT_ACCOUNT_12345')
    assert tier == 'MSRP', f"Unknown account should resolve to MSRP, got {tier}"


def test_quote_calculates_totals(engine):
    """Test that quote totals are calculated correctly."""
    # Use any SKU from the catalog
    first_sku = engine.catalog.index[0]
    result = engine.calculate_quote('1730', {first_sku: 5})
    
    if result['Lines']:
        line = result['Lines'][0]
        expected_total = line['Unit Price'] * 5
        assert abs(line['Total'] - expected_total) < 0.01, \
            f"Line total mismatch: expected {expected_total}, got {line['Total']}"
