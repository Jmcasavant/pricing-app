"""
Order Policy Engine - Computes terms, freight, and holds for an order.
"""
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime
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
            df = pd.read_csv(path, dtype=str).fillna('')
            # Strip all strings and headers
            df.columns = [c.strip() for c in df.columns]
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            return df
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
        
        # Initialize Base Policy Output
        policy = {
            "active_program_id": program_id,
            "terms": {
                "code": "NET_30",
                "net_days": 30,
                "due_date": None,
                "notes": [],
                "needs_review": False,
                "review_reason": None
            },
            "freight": {
                "mode": "CUSTOMER_PAYS_CARRIER_RATE",
                "carrier_required": None,
                "bill_freight": True,
                "freight_amount": None,
                "ffa_percent": None
            },
            "holds": [],
            "adjustments": [],
            "constraints": {}
        }
        
        threshold_total = result.total  # Explicit definition: merch_subtotal
        
        # 1. Global Overrides
        if request.payment_method == "CC":
             policy["terms"]["code"] = "NET_IMMEDIATE"
             policy["terms"]["net_days"] = 0
             policy["terms"]["notes"].append("Credit Card Payment - Immediate Terms")

        # 2. Compute Terms (Program Specific)
        if policy["terms"]["code"] != "NET_IMMEDIATE":
             policy["terms"] = self._compute_terms(program_id, threshold_total, request)
        
        # 3. Compute Freight (Program Specific)
        policy["freight"] = self._compute_freight(program_id, threshold_total, request)
        
        # 4. Sports Line SFT Logic
        if program_id == "SPORTS_LINE":
            self._apply_sports_line_logic(policy, request, threshold_total)

        # 5. Compute Holds (Workflow)
        policy["holds"].extend(self._compute_holds(program_id, request))
        
        # 6. Trade-In Constraints
        if request.order_type in [25, 26]: # Trade-In
            policy["constraints"] = {
                "no_rebate_stacking": True,
                "no_discount_stacking": True
            }

        result.policy = policy

    def _compute_terms(self, program_id: str, total: float, request: Request) -> Dict[str, Any]:
        default = {
            "code": "NET_30",
            "net_days": 30,
            "due_date": None,
            "notes": ["Eligibility based on order_date, terms based on invoice_date"],
            "needs_review": False,
            "review_reason": None
        }
        
        if self.terms_rules.empty:
            return default
            
        matches = self._find_best_matches(self.terms_rules, program_id, total, request.request_date)
        if matches.empty:
             return default

        # Take best match (first one after sort in _find_best_matches?)
        # For now, strict specificity isn't fully implemented in helper, but typical precedence:
        # Program Match > Standard
        row = matches.iloc[0]
        
        code = row.get('terms_code', 'NET_30')
        
        result = default.copy()
        result["code"] = code
        result["notes"] = [] # Reset notes
        
        if code == "DATED":
            result["due_date"] = row.get("dated_due_date")
            result["net_days"] = None
        elif code == "CIA":
             result["net_days"] = 0
        else:
             # Try to parse net days from code or row
             try:
                 result["net_days"] = int(row.get('net_days', 30))
             except:
                 result["net_days"] = 30
        
        if row.get('needs_review', 'false').lower() == 'true':
            result["needs_review"] = True
            result["review_reason"] = row.get('review_reason')
            
        return result
        
    def _compute_freight(self, program_id: str, total: float, request: Request) -> Dict[str, Any]:
        default = {
            "mode": "CUSTOMER_PAYS_CARRIER_RATE",
            "carrier_required": None,
            "bill_freight": True,
            "freight_amount": None,
            "ffa_percent": None
        }
        
        if self.freight_rules.empty:
            return default
            
        # Match with Tier consideration
        matches = self._find_best_matches(self.freight_rules, program_id, total, request.request_date)
        
        # Filter by customer tier (Specific > Wildcard)
        if not matches.empty and 'customer_tier' in matches.columns:
            tier = str(request.customer_tier or "").upper()
            
            # Exact match
            tier_matches = matches[matches['customer_tier'] == tier]
            
            # Wildcard match (empty/NaN)
            wild_matches = matches[matches['customer_tier'].isna() | (matches['customer_tier'] == "")]
            
            if not tier_matches.empty:
                matches = tier_matches
            elif not wild_matches.empty:
                matches = wild_matches
            else:
                matches = pd.DataFrame() # No match found for tier logic
                
        if matches.empty:
            return default
            
        row = matches.iloc[0]
        mode_val = row.get('freight_mode', 'Customer Pays')
        bill_freight = str(row.get('bill_freight', 'true')).lower() == 'true'
        ffa_percent = float(row.get('ffa_percent', 0)) if row.get('ffa_percent') else None
        
        # Map CSV policy to API Mode
        api_mode = "CUSTOMER_PAYS_CARRIER_RATE"
        if mode_val == "FFA":
            api_mode = "FFA"
        elif mode_val == "Partial FFA":
            api_mode = "PARTIAL_FFA"
        elif mode_val == "Ex Works":
            api_mode = "EX_WORKS" # distinct form customer pays?
        elif "SFT" in mode_val:
             api_mode = "SFT_PERCENT"

        return {
            "mode": api_mode,
            "carrier_required": row.get('carrier_required'),
            "bill_freight": bill_freight,
            "freight_amount": None,
            "ffa_percent": ffa_percent
        }

    def _apply_sports_line_logic(self, policy: Dict, request: Request, total: float):
        # Default behavior: SFT Charge
        is_expedited = request.ship_method and any(x in str(request.ship_method).upper() for x in ["PRIORITY", "OVERNIGHT", "2DAY", "AIR"])
        
        if is_expedited:
            # Waive SFT, customer pays full freight
            policy["freight"]["mode"] = "CUSTOMER_PAYS_CARRIER_RATE"
            policy["freight"]["bill_freight"] = True
        else:
             # Apply SFT
             sft_amount = round(total * 0.18, 2)
             policy["adjustments"].append({
                 "code": "SFT_CHG",
                 "amount": sft_amount,
                 "description": "18% SFT Charge",
                 "taxable": False
             })
             policy["freight"]["bill_freight"] = False # Customer pays SFT, not carrier rate

    def _compute_holds(self, program_id: str, request: Request) -> list[Dict[str, Any]]:
        holds = []
        
        # 1. International Forwarder Check
        if request.ship_to_type and "INTERNATIONAL" in str(program_id).upper():
             # Logic: If International Program but NOT shipping to Forwarder? 
             # Or if just ship_to_type is international? Strict rules say verify ship_to_type
             if str(request.ship_to_type).upper() != "FORWARDER":
                  holds.append({
                      "code": "HOLD_INTL_FORWARDER_REQUIRED",
                      "message": "International orders must ship to a freight forwarder.",
                      "details": {"ship_to_type": request.ship_to_type}
                  })

        if self.workflow_rules.empty:
            return holds
            
        # Check CSV rule matches
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
                    "message": row['message'],
                    "details": {}
                })
                
        return holds

    def _find_best_matches(self, df: pd.DataFrame, program_id: str, total: float, request_date: Optional[str]) -> pd.DataFrame:
        """Filter rules by program, total, and effective date."""
        # 1. Program Filter
        matches = df[df['program_id'] == program_id].copy()
        if matches.empty:
            matches = df[df['program_id'] == 'STANDARD'].copy()
            
        if matches.empty:
            return matches

        # 2. Total Filter (Robust conversion)
        # Remove potential whitespace
        if 'min_total' in matches.columns:
            matches['min_total'] = matches['min_total'].astype(str).str.strip()
        if 'max_total' in matches.columns:
            matches['max_total'] = matches['max_total'].astype(str).str.strip()
            
        min_vals = pd.to_numeric(matches['min_total'], errors='coerce').fillna(0)
        max_vals = pd.to_numeric(matches['max_total'], errors='coerce').fillna(float('inf'))
        
        matches = matches[
            (min_vals <= total) & 
            (max_vals >= total)
        ]
        
        # 3. Date Filter
        if request_date:
            req_dt = str(request_date).strip()
            # Start Date
            if 'start_date' in matches.columns:
                 start_dates = matches['start_date'].astype(str).str.strip().replace({'nan': '', 'None': ''})
                 # Check where start_date is empty OR start_date <= req_dt
                 matches = matches[
                     (start_dates == '') | 
                     (start_dates.isna()) | 
                     (start_dates <= req_dt)
                 ]
            # End Date
            if 'end_date' in matches.columns:
                 end_dates = matches['end_date'].astype(str).str.strip().replace({'nan': '', 'None': ''})
                 # Check where end_date is empty OR end_date >= req_dt
                 matches = matches[
                     (end_dates == '') | 
                     (end_dates.isna()) | 
                     (end_dates >= req_dt)
                 ]
                 
        return matches
