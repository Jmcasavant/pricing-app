"""
Order Policy Engine - Computes terms, freight, and holds for an order.
"""
from typing import Optional, Dict, Any
import pandas as pd
from pathlib import Path
from .program_resolver import ProgramResolver
from ..engine.models import Request, Result

class OrderPolicyEngine:
    """
    Engine for computing order-level policies.
    """
    
    def __init__(self, policy_dir: Path):
        self.policy_dir = policy_dir
        self.program_resolver = ProgramResolver(policy_dir / 'program_rules.csv')
        self.terms_rules = self._load_csv('terms_rules.csv')
        self.freight_rules = self._load_csv('freight_rules.csv')
        self.workflow_rules = self._load_csv('workflow_rules.csv')
        
    def _load_csv(self, filename: str) -> pd.DataFrame:
        path = self.policy_dir / filename
        if path.exists():
            return pd.read_csv(path, dtype=str)
        return pd.DataFrame()

    def apply_policies(self, request: Request, result: Result, account_groups: list[str] = None):
        """
        Compute policies and update result.policy.
        """
        # Resolve Program using passed groups
        program_id = self.program_resolver.resolve_program(
            account_id=request.account_id,
            account_groups=account_groups or [],
            order_type=request.order_type
        )
        
        policy = {
            "active_program_id": program_id,
            "terms": "Net 30",
            "freight": {"policy": "Standard Freight"},
            "holds": []
        }
        
        # Compute Terms
        policy["terms"] = self._compute_terms(program_id, result.total)
        
        # Compute Freight
        policy["freight"] = self._compute_freight(program_id, result.total, request)
        
        # Compute Holds
        policy["holds"] = self._compute_holds(program_id, request)
        
        result.policy = policy

    def _compute_terms(self, program_id: str, total: float) -> str:
        if self.terms_rules.empty:
            return "Net 30"
            
        # Filter by program
        matches = self.terms_rules[self.terms_rules['program_id'] == program_id]
        if matches.empty:
            matches = self.terms_rules[self.terms_rules['program_id'] == 'STANDARD']
            
        # Filter by total range
        for _, row in matches.iterrows():
            min_t = float(row.get('min_total', 0))
            max_t = float(row.get('max_total', 9999999))
            if min_t <= total <= max_t:
                return row['terms_code']
                
        return "Net 30"
        
    def _compute_freight(self, program_id: str, total: float, request: Request) -> Dict[str, Any]:
        if self.freight_rules.empty:
            return {"policy": "Standard Freight"}
            
        matches = self.freight_rules[self.freight_rules['program_id'] == program_id]
        if matches.empty:
            matches = self.freight_rules[self.freight_rules['program_id'] == 'STANDARD']
            
        for _, row in matches.iterrows():
            min_t = float(row.get('min_total', 0))
            max_t = float(row.get('max_total', 9999999))
            if min_t <= total <= max_t:
                return {
                    "policy": row['freight_policy'],
                    "ffa_threshold": float(row.get('ffa_threshold', 0)) if row.get('ffa_threshold') else None,
                    "bill_freight": row.get('bill_freight', 'true').lower() == 'true'
                }
                
        return {"policy": "Standard Freight"}
        
    def _compute_holds(self, program_id: str, request: Request) -> list[Dict[str, str]]:
        holds = []
        if self.workflow_rules.empty:
            return holds
            
        # Check rule matches
        matches = self.workflow_rules[self.workflow_rules['program_id'].isin([program_id, 'ALL'])]
        for _, row in matches.iterrows():
            match_type = row.get('match_type')
            match_value = row.get('match_value')
            
            should_hold = False
            if match_type == 'always':
                should_hold = True
            elif match_type == 'ship_method':
                if request.ship_method == match_value:
                    should_hold = True
            
            if should_hold:
                holds.append({
                    "code": row['hold_code'],
                    "message": row['message']
                })
                
        return holds
