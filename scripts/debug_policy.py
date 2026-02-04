import sys
from pathlib import Path
import pandas as pd

# Add src to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from pricing_tool.policy.order_policy_engine import OrderPolicyEngine
from pricing_tool.engine.models import Request, Result

def debug():
    policy_dir = src_path / 'pricing_tool/policy'
    engine = OrderPolicyEngine(policy_dir)
    
    print("Loaded Rules:")
    print("Terms Rules Head:")
    print(engine.terms_rules.head())
    print("\nProgram Rules Head:")
    print(engine.program_resolver.rules_df.head())
    
    # Test Case: BSN Dated Terms
    print("\n--- Testing BSN Dated Terms ---")
    req = Request(
        account_id="11730",
        items={"2070003002202": 1},
        request_date="2026-01-15"
    )
    result = Result(account_id="11730", tier="BSN", total=499.0, lines=[])
    
    # Mock groups
    groups = ["BSN"]
    
    print(f"Resolving program for account {req.account_id} with groups {groups}")
    prog = engine.program_resolver.resolve_program(req.account_id, groups)
    print(f"Resolved Program: {prog}")
    
    print("Finding Terms matches...")
    matches = engine._find_best_matches(engine.terms_rules, prog, 499.0, "2026-01-15")
    print("Matches found:")
    print(matches)
    
    engine.apply_policies(req, result, groups)
    print("\nFinal Policy:")
    print(result.policy)

if __name__ == "__main__":
    debug()
