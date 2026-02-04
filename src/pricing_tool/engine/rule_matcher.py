"""
Rule Matcher - Matches and applies pricing rules to line items.

Used by the pricing engine to apply specials and discounts
on top of the base tier pricing.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class MatchedRule:
    """A rule that matched with context."""
    rule_id: str
    name: str
    priority: int
    action_type: str
    action_value: str | float
    match_reason: str


class RuleMatcher:
    """
    Matches and applies pricing rules to line items.
    
    Rules are loaded from compiled_rules.json and matched against
    request context (account, sku, qty, date, etc.).
    """
    
    def __init__(self, compiled_rules_path: Optional[Path] = None):
        """Load compiled rules."""
        self.rules = []
        self.loaded = False
        
        if compiled_rules_path and compiled_rules_path.exists():
            self._load_rules(compiled_rules_path)
    
    def _load_rules(self, path: Path):
        """Load rules from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.rules = [r for r in data.get('rules', []) if r.get('active', False)]
            self.loaded = True
        except Exception as e:
            self.rules = []
            self.loaded = False
    
    def find_matching_rules(
        self,
        account_id: str,
        account_group: Optional[str],
        sku: str,
        qty: int,
        request_date: Optional[str] = None
    ) -> list[MatchedRule]:
        """
        Find all rules that match the given context.
        
        Returns rules sorted by priority (lower = higher priority).
        """
        if not self.loaded:
            return []
        
        matched = []
        today = request_date or datetime.now().strftime('%Y-%m-%d')
        
        for rule in self.rules:
            match = rule.get('match', {})
            rule_id = rule.get('rule_id', 'unknown')
            reasons = []
            
            # Account match
            if match.get('account'):
                if str(match['account']) != str(account_id):
                    # We don't trace every failure to keep output small, 
                    # but we track reasons during match
                    continue
                reasons.append(f"account={account_id}")
            
            # Account group match (Robust: check if any group matches)
            if match.get('account_group'):
                rule_grp = str(match['account_group']).strip()
                match_found = False
                if account_group:
                    # Split both by comma to handle multiple groups on either side
                    req_groups = [g.strip() for g in str(account_group).split(',')]
                    if rule_grp in req_groups:
                        match_found = True
                        reasons.append(f"group={rule_grp}")
                
                if not match_found:
                    continue
            
            # SKU match
            if match.get('sku'):
                if str(match['sku']) != str(sku) and match['sku'] != '*':
                    continue
                reasons.append(f"sku={sku}")
            
            # SKU prefix match
            if match.get('sku_prefix'):
                prefix = str(match['sku_prefix']).strip()
                if not str(sku).startswith(prefix):
                    continue
                reasons.append(f"sku_prefix={prefix}")
            
            # Quantity range
            if match.get('min_qty'):
                if qty < int(match['min_qty']):
                    continue
                reasons.append(f"qty>={match['min_qty']}")
            
            if match.get('max_qty'):
                if qty > int(match['max_qty']):
                    continue
                reasons.append(f"qty<={match['max_qty']}")
            
            # Date range
            if match.get('start_date'):
                if today < match['start_date']:
                    continue
                reasons.append(f"after {match['start_date']}")
            
            if match.get('end_date'):
                if today > match['end_date']:
                    continue
                reasons.append(f"before {match['end_date']}")
            
            # If we get here, the rule matches
            action = rule.get('action', {})
            matched.append(MatchedRule(
                rule_id=rule['rule_id'],
                name=rule.get('name', rule['rule_id']),
                priority=rule.get('priority', 50),
                action_type=action.get('type', ''),
                action_value=action.get('value', ''),
                match_reason=", ".join(reasons) if reasons else "default"
            ))
        
        # Sort by priority (lower = higher priority)
        matched.sort(key=lambda r: r.priority)
        return matched
    
    def apply_rule_to_price(
        self,
        rule: MatchedRule,
        base_price: float,
        current_tier: str
    ) -> tuple[float, str, list[str]]:
        """
        Apply a single rule to a price.
        
        Returns (new_price, new_tier, trace_messages).
        """
        traces = []
        new_tier = current_tier
        new_price = base_price
        
        if rule.action_type == 'set_tier':
            new_tier = str(rule.action_value)
            traces.append(f"Rule {rule.rule_id} set tier to {new_tier}")
            # Note: caller needs to re-lookup price for new tier
            return new_price, new_tier, traces
        
        elif rule.action_type == 'override_unit_price':
            new_price = float(rule.action_value)
            traces.append(f"Rule {rule.rule_id} set price to ${new_price:.2f}")
        
        elif rule.action_type == 'discount_percent':
            discount = float(rule.action_value) / 100.0
            new_price = base_price * (1 - discount)
            traces.append(f"Rule {rule.rule_id} applied {rule.action_value}% discount: ${base_price:.2f} → ${new_price:.2f}")
        
        elif rule.action_type == 'discount_amount':
            discount = float(rule.action_value)
            new_price = max(0, base_price - discount)
            traces.append(f"Rule {rule.rule_id} applied ${discount:.2f} discount: ${base_price:.2f} → ${new_price:.2f}")
        
        elif rule.action_type == 'price_floor':
            floor = float(rule.action_value)
            if base_price < floor:
                new_price = floor
                traces.append(f"Rule {rule.rule_id} enforced price floor: ${base_price:.2f} → ${new_price:.2f}")
            else:
                traces.append(f"Rule {rule.rule_id} price floor ${floor:.2f} not applied (price ${base_price:.2f} already above)")
        
        return new_price, new_tier, traces
