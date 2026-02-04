"""
Pricing Engine v2 - Core pricing resolution logic with traceability.

Migrated from the original pricing_engine.py with added:
- Structured Result/LineItem dataclass output
- Execution trace for every resolution step
- Warning collection for fallbacks and anomalies
- Rules layer integration for specials and discounts
- Backward-compatible legacy dict output
"""
import pandas as pd
import os
from typing import Optional

from ..config.settings import get_settings, Settings
from .models import Request, LineItem, Result
from .rule_matcher import RuleMatcher


class PricingEngine:
    """
    Core pricing engine that resolves prices using Account → Tier → Price pipeline.
    
    Resolution order:
    1. Check Program Map for direct account → tier mapping
    2. Check Group Members for account → group, then group → tier
    3. Fall back to MSRP tier
    4. Apply any matching rules (set_tier, discounts, overrides)
    5. For each SKU: use [TIER]_Price column, fall back to MSRP if missing
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize engine with catalog, mapping data, and rules."""
        self.settings = settings or get_settings()
        
        catalog_path = self.settings.master_catalog
        rules_path = self.settings.rules_excel
        
        if not catalog_path.exists():
            raise FileNotFoundError(
                f"Master_Catalog_Final.csv not found at {catalog_path}. "
                "Execute build_catalog.py first."
            )
        
        if not rules_path.exists():
            raise FileNotFoundError(
                f"Pricing Rules Starter 1.xlsx not found at {rules_path}."
            )
        
        # Load master catalog
        self.catalog = pd.read_csv(
            catalog_path, 
            index_col='SKU', 
            dtype={'SKU': str}
        )
        
        # Load account mapping logic
        self.program_map = pd.read_excel(
            rules_path, 
            sheet_name='Program Map', 
            dtype=str
        )
        
        # [NEW] Load CSV overrides
        import pathlib
        src_path = pathlib.Path(__file__).parent.parent.parent
        program_map_csv = src_path / "pricing_tool/data/program_map.csv"
        if program_map_csv.exists():
            csv_map = pd.read_csv(program_map_csv, dtype=str)
            self.program_map = pd.concat([self.program_map, csv_map], ignore_index=True)
        
        # Normalize program map
        for col in self.program_map.columns:
            self.program_map[col] = self.program_map[col].astype(str).str.strip()

        self.group_members = pd.read_excel(
            rules_path, 
            sheet_name='Group Members', 
            dtype=str
        )
        
        # [NEW] Load CSV override if exists (for rapid updates)
        csv_map_path = src_path / "pricing_tool/data/group_members.csv"
        if csv_map_path.exists():
            csv_groups = pd.read_csv(csv_map_path, dtype=str)
            self.group_members = pd.concat([self.group_members, csv_groups], ignore_index=True)
            
        # [NEW] Load Account Intel overrides
        self.account_intel = pd.DataFrame(columns=['Match Value', 'Freight', 'Terms', 'Notes'])
        account_intel_csv = src_path / "pricing_tool/data/account_intel.csv"
        if account_intel_csv.exists():
            self.account_intel = pd.read_csv(account_intel_csv, dtype=str)
            for col in self.account_intel.columns:
                self.account_intel[col] = self.account_intel[col].astype(str).str.strip()

        # Load compiled rules (optional - may not exist yet)
        self.rule_matcher = RuleMatcher(self.settings.compiled_rules)
    
    def reload_data(self):
        """Reload all CSV/Excel data and rules from disk."""
        self.__init__(self.settings)
    
    def get_account_intel(self, account_id: str) -> dict:

        """Resolve Freight and Terms for an account/group."""
        account_id = str(account_id).strip()
        
        # 1. Try exact account ID
        match = self.account_intel[self.account_intel['Match Value'] == account_id]
        if not match.empty:
            return match.iloc[0].to_dict()
        
        # 2. Try groups
        account_groups = self.group_members[
            self.group_members['Account Number'] == account_id
        ]['Group ID'].unique()
        
        if len(account_groups) > 0:
            match = self.account_intel[self.account_intel['Match Value'].isin(account_groups)]
            if not match.empty:
                return match.iloc[0].to_dict()
        
        # 3. Fallback to MSRP
        match = self.account_intel[self.account_intel['Match Value'] == 'MSRP']
        if not match.empty:
            return match.iloc[0].to_dict()
            
        return {"Freight": "Unknown", "Terms": "Unknown", "Notes": ""}
    
    def get_account_tier(self, account_id: str) -> str:
        """
        Resolve the pricing tier for a specific account ID.
        
        Returns tier name (e.g., "GOLD", "PLATINUM") or "MSRP" as fallback.
        """
        account_id = str(account_id).strip()
        
        # Check for exact account match in Program Map
        exact_match = self.program_map[
            self.program_map['Match Value'] == account_id
        ]
        if not exact_match.empty:
            return exact_match.iloc[0]['Program ID']
        
        # Check for group membership match
        account_groups = self.group_members[
            self.group_members['Account Number'] == account_id
        ]['Group ID'].unique()
        
        if len(account_groups) > 0:
            group_match = self.program_map[
                self.program_map['Match Value'].isin(account_groups)
            ]
            if not group_match.empty:
                return group_match.iloc[0]['Program ID']
        
        return "MSRP"
    
    def get_account_tier_with_trace(self, account_id: str) -> tuple[str, list]:
        """
        Resolve tier with trace of resolution steps.
        
        Returns (tier_name, trace_steps).
        """
        account_id = str(account_id).strip()
        trace = []
        
        trace.append(("Account Lookup", f"Resolving tier for account {account_id}", None))
        
        # Check for exact account match
        exact_match = self.program_map[
            self.program_map['Match Value'] == account_id
        ]
        if not exact_match.empty:
            tier = exact_match.iloc[0]['Program ID']
            trace.append(("Direct Match", "Found direct account → tier mapping", tier))
            return tier, trace
        
        trace.append(("Direct Match", "No direct account mapping found", None))
        
        # Check for group membership
        account_groups = self.group_members[
            self.group_members['Account Number'] == account_id
        ]['Group ID'].unique()
        
        if len(account_groups) > 0:
            trace.append(("Group Lookup", f"Account belongs to groups", ", ".join(account_groups)))
            
            group_match = self.program_map[
                self.program_map['Match Value'].isin(account_groups)
            ]
            if not group_match.empty:
                tier = group_match.iloc[0]['Program ID']
                trace.append(("Group → Tier", f"Group mapped to tier", tier))
                return tier, trace
        else:
            trace.append(("Group Lookup", "No group memberships found", None))
        
        trace.append(("Fallback", "Using MSRP fallback", "MSRP"))
        return "MSRP", trace
    
    def calculate_quote(self, account_id: str, cart_items: dict) -> dict:
        """
        Calculate line items and totals (legacy dict format for backward compatibility).
        
        Args:
            account_id: Customer account number
            cart_items: Dict of {SKU: quantity}
            
        Returns:
            Legacy dict with Account, Tier, Total, Lines keys
        """
        result = self.calculate(Request(account_id=account_id, items=cart_items))
        return result.to_legacy_dict()
    
    def calculate(self, request: Request) -> Result:
        """
        Calculate quote with full traceability.
        
        Args:
            request: Request dataclass with account and items
            
        Returns:
            Result dataclass with lines, trace, and warnings
        """
        # Resolve tier with trace
        tier, tier_trace = self.get_account_tier_with_trace(request.account_id)
        
        result = Result(
            account_id=request.account_id,
            tier=tier,
            total=0.0,
            lines=[],
            intel=self.get_account_intel(request.account_id)
        )
        
        # Add tier resolution trace
        for step, desc, val in tier_trace:
            result.add_trace(step, desc, val)
        
        # Process each line item
        for sku, qty in request.items.items():
            line = self._calculate_line(sku, qty, tier, request.account_id)
            if line:
                result.lines.append(line)
                result.total += line.extended_price
                
                # Bubble up line warnings
                for warning in line.warnings:
                    if warning not in result.warnings:
                        result.add_warning(warning)
        
        return result
    
    def _calculate_line(self, sku: str, qty: int, tier: str, account_id: str = "") -> Optional[LineItem]:
        """Calculate a single line item with trace and rule application."""
        sku = str(sku).strip()
        account_id = str(account_id).strip()
        
        if sku not in self.catalog.index:
            return None
        
        # Resolve account groups once for the whole line
        group_str = None
        if account_id:
            account_groups = self.group_members[
                self.group_members['Account Number'] == account_id
            ]['Group ID'].unique()
            if len(account_groups) > 0:
                group_str = ",".join(account_groups)

        # Handle potential duplicates by taking first entry
        product_data = self.catalog.loc[[sku]].head(1).iloc[0]
        
        # Create line item
        line = LineItem(
            sku=sku,
            description=product_data['Description'] if pd.notna(product_data['Description']) else "N/A",
            quantity=qty,
            unit_price=0.0,
            extended_price=0.0,
            tier_used=tier,
            source="",
        )
        
        line.add_trace("SKU Lookup", f"Found product in catalog", sku)
        if group_str:
            line.add_trace("Context", "Account Groups", group_str)
        
        # Find all matching rules
        matching_rules = []
        if self.rule_matcher.loaded and account_id:
            matching_rules = self.rule_matcher.find_matching_rules(
                account_id=account_id,
                account_group=group_str,
                sku=sku,
                qty=qty
            )

        # Check for tier-level rules first (set_tier action)
        effective_tier = tier
        for rule in matching_rules:
            if rule.action_type == 'set_tier':
                effective_tier = str(rule.action_value)
                line.tier_used = effective_tier
                line.rules_applied.append(rule.rule_id)
                line.add_trace("Rule Applied", f"{rule.name} ({rule.rule_id})", f"tier → {effective_tier}")
                break  # Only apply first set_tier rule
        
        tier_column = f"{effective_tier}_Price"
        
        # Try tier price first
        if tier_column in product_data and pd.notna(product_data[tier_column]):
            line.unit_price = float(product_data[tier_column])
            line.source = "Contract"
            line.add_trace("Price Resolution", f"Using {effective_tier} tier price", f"${line.unit_price:.2f}")
        else:
            # Fall back to MSRP
            line.unit_price = float(product_data['MSRP'])
            line.source = "MSRP"
            line.tier_used = "MSRP"
            line.add_trace("Price Resolution", f"No {effective_tier} price, using MSRP fallback", f"${line.unit_price:.2f}")
            line.add_warning(f"MSRP fallback used for SKU {sku}")
        
        # Apply price-modifying rules
        for rule in matching_rules:
            if rule.action_type in ('override_unit_price', 'discount_percent', 'discount_amount', 'price_floor'):
                new_price, _, traces = self.rule_matcher.apply_rule_to_price(
                    rule=rule,
                    base_price=line.unit_price,
                    current_tier=line.tier_used
                )
                
                # Always apply and track the rule if it was processed
                line.unit_price = new_price
                line.source = "Rule"
                line.rules_applied.append(rule.rule_id)
                for trace_msg in traces:
                    line.add_trace("Rule Applied", trace_msg, f"${new_price:.2f}")
        
        line.extended_price = line.unit_price * qty
        line.add_trace("Extension", f"Quantity {qty} × ${line.unit_price:.2f}", f"${line.extended_price:.2f}")
        
        return line
