import pytest
import sys
import os

# Add src to path for internal imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from pricing_tool.engine import PricingEngine, Request

@pytest.fixture(scope="module")
def engine():
    return PricingEngine()

def test_p2_rebate_date_gating(engine):
    """
    Verify P2 Instant Rebates stop after 2026-04-15.
    SKU: 193092002202 (Youth Zero 2)
    Rule: P2-YTH-Z2-10 ($10 rebate)
    """
    sku = "193092002202"
    account = "4883" 
    
    # 1. Before cutoff (rebate applied)
    req_active = Request(account_id=account, items={sku: 1}, request_date="2026-04-14")
    result_active = engine.calculate(req_active)
    
    # 2. After cutoff (rebate NOT applied)
    req_expired = Request(account_id=account, items={sku: 1}, request_date="2026-04-16")
    result_expired = engine.calculate(req_expired)
    
    assert len(result_active.lines) > 0, f"SKU {sku} not found in catalog"
    assert len(result_expired.lines) > 0, f"SKU {sku} not found in catalog"
    
    price_active = result_active.lines[0].unit_price
    price_expired = result_expired.lines[0].unit_price
    
    # Assert price difference is $10
    assert abs(price_expired - price_active - 10.0) < 0.01, \
        f"Expired price {price_expired} should be $10 more than active price {price_active}"
    assert "P2-YTH-Z2-10" in result_active.lines[0].rules_applied
    assert "P2-YTH-Z2-10" not in result_expired.lines[0].rules_applied

def test_bsn_override_date_gating(engine):
    """
    Verify BSN overrides stop after 2026-01-31.
    SKU: 2070003002202 (F7 Varsity)
    Rule: BSN-F7-VAR ($267 override)
    Account: 11730 (BSN group member)
    """
    sku = "2070003002202"
    account = "11730"
    
    # 1. Before cutoff (override applied)
    req_active = Request(account_id=account, items={sku: 1}, request_date="2026-01-30")
    result_active = engine.calculate(req_active)
    
    # 2. After cutoff (override NOT applied)
    req_expired = Request(account_id=account, items={sku: 1}, request_date="2026-02-02")
    result_expired = engine.calculate(req_expired)
    
    assert len(result_active.lines) > 0, f"SKU {sku} not found in catalog"
    assert len(result_expired.lines) > 0, f"SKU {sku} not found in catalog"
    
    price_active = result_active.lines[0].unit_price
    price_expired = result_expired.lines[0].unit_price
    
    assert price_active == 267.0
    assert price_expired != 267.0
    assert "BSN-F7-VAR" in result_active.lines[0].rules_applied
    assert "BSN-F7-VAR" not in result_expired.lines[0].rules_applied

def test_policy_resolution_bsn(engine):
    """Verify BSN account resolves to BSN program and gets Net 60 / FFA."""
    sku = "2070003002202"
    account = "11730" # BSN Group
    
    req = Request(account_id=account, items={sku: 1})
    result = engine.calculate(req)
    
    assert result.policy["active_program_id"] == "BSN"
    assert result.policy["terms"] == "Net 60"
    assert result.policy["freight"]["policy"] == "FFA"

def test_policy_resolution_sportsline(engine):
    """Verify account 4883 resolves to SPORTS_LINE and gets SFT Charge / Hold."""
    sku = "2070003002202"
    account = "4883" 
    
    req = Request(account_id=account, items={sku: 1})
    result = engine.calculate(req)
    
    assert result.policy["active_program_id"] == "SPORTS_LINE"
    assert result.policy["freight"]["policy"] == "18% SFT Charge"
    assert any(h["code"] == "HOLD_SPORTSLINE" for h in result.policy["holds"])

def test_policy_standard_totals(engine):
    """Verify STANDARD terms/freight change based on order total."""
    sku = "2070003002202" # MSRP ~ $499
    account = "99999" # Unknown account -> STANDARD
    
    # 1. Small order (< 1000)
    req_small = Request(account_id=account, items={sku: 1})
    result_small = engine.calculate(req_small)
    assert result_small.policy["terms"] == "Net 30"
    assert result_small.policy["freight"]["policy"] == "Customer Pays"
    
    # 2. Large order (>= 1750 for FFA)
    req_large = Request(account_id=account, items={sku: 5}) # ~ $2500
    result_large = engine.calculate(req_large)
    assert result_large.policy["terms"] == "Net 60"
    assert result_large.policy["freight"]["policy"] == "FFA"

def test_item_config_roundtrip(engine):
    """Verify item_configs are passed through to result lines."""
    sku = "2070003002202"
    config = {"shell_color": "matte_black", "facemask": "titanium_f7"}
    
    req = Request(
        account_id="99999", 
        items={sku: 1},
        item_configs={sku: config}
    )
    result = engine.calculate(req)
    
    assert len(result.lines) == 1
    assert result.lines[0].sku == sku
    assert result.lines[0].configuration == config
