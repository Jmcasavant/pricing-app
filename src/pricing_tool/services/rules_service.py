"""
Rules Service - CRUD operations for pricing rules.
Handles reading/writing rules.csv and auto-compiling to JSON.
"""
import csv
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict, field
import re


@dataclass
class Rule:
    """Represents a pricing rule."""
    rule_id: str
    name: str
    active: bool = True
    priority: int = 50
    account: Optional[str] = None
    account_group: Optional[str] = None
    sku: Optional[str] = None
    sku_prefix: Optional[str] = None
    brand: Optional[str] = None
    min_qty: Optional[int] = None
    max_qty: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    channel: str = "all"
    action_type: str = "override_unit_price"
    action_value: str = ""
    notes: Optional[str] = None
    
    def to_csv_row(self) -> dict:
        """Convert to CSV row format."""
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'active': 'true' if self.active else 'false',
            'priority': str(self.priority),
            'account': self.account or '',
            'account_group': self.account_group or '',
            'sku': self.sku or '',
            'sku_prefix': self.sku_prefix or '',
            'brand': self.brand or '',
            'min_qty': str(self.min_qty) if self.min_qty else '',
            'max_qty': str(self.max_qty) if self.max_qty else '',
            'start_date': self.start_date or '',
            'end_date': self.end_date or '',
            'channel': self.channel or 'all',
            'action_type': self.action_type,
            'action_value': str(self.action_value),
            'notes': self.notes or '',
        }
    
    @classmethod
    def from_csv_row(cls, row: dict) -> 'Rule':
        """Create Rule from CSV row."""
        return cls(
            rule_id=row.get('rule_id', ''),
            name=row.get('name', ''),
            active=row.get('active', 'true').lower() == 'true',
            priority=int(row.get('priority', 50) or 50),
            account=row.get('account') or None,
            account_group=row.get('account_group') or None,
            sku=row.get('sku') or None,
            sku_prefix=row.get('sku_prefix') or None,
            brand=row.get('brand') or None,
            min_qty=int(row['min_qty']) if row.get('min_qty') else None,
            max_qty=int(row['max_qty']) if row.get('max_qty') else None,
            start_date=row.get('start_date') or None,
            end_date=row.get('end_date') or None,
            channel=row.get('channel', 'all'),
            action_type=row.get('action_type', 'override_unit_price'),
            action_value=row.get('action_value', ''),
            notes=row.get('notes') or None,
        )


@dataclass
class ValidationResult:
    """Result of rule validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    matching_products: int = 0


class RulesService:
    """Service for managing pricing rules."""
    
    CSV_COLUMNS = [
        'rule_id', 'name', 'active', 'priority', 'account', 'account_group',
        'sku', 'sku_prefix', 'brand', 'min_qty', 'max_qty', 'start_date',
        'end_date', 'channel', 'action_type', 'action_value', 'notes'
    ]
    
    def __init__(self, rules_csv_path: Path, compile_script_path: Path, catalog_path: Optional[Path] = None):
        self.rules_csv_path = rules_csv_path
        self.compile_script_path = compile_script_path
        self.catalog_path = catalog_path
        self._catalog_skus: set[str] = set()
        self._load_catalog_skus()
    
    def _load_catalog_skus(self):
        """Load SKUs from master catalog for validation."""
        if self.catalog_path and self.catalog_path.exists():
            try:
                with open(self.catalog_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    self._catalog_skus = {row.get('SKU', '') for row in reader if row.get('SKU')}
            except Exception:
                pass
    
    def list_rules(self, include_inactive: bool = True) -> list[Rule]:
        """List all rules from CSV."""
        rules = []
        if not self.rules_csv_path.exists():
            return rules
        
        with open(self.rules_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('rule_id'):
                    continue
                rule = Rule.from_csv_row(row)
                if include_inactive or rule.active:
                    rules.append(rule)
        
        return rules
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a single rule by ID."""
        for rule in self.list_rules():
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def create_rule(self, rule: Rule, auto_compile: bool = True) -> Rule:
        """Create a new rule."""
        # Generate rule_id if not provided
        if not rule.rule_id:
            rule.rule_id = self._generate_rule_id(rule)
        
        # Check for duplicate
        if self.get_rule(rule.rule_id):
            raise ValueError(f"Rule with ID '{rule.rule_id}' already exists")
        
        # Append to CSV
        rules = self.list_rules()
        rules.append(rule)
        self._write_rules(rules)
        
        if auto_compile:
            self.compile_rules()
        
        return rule
    
    def update_rule(self, rule_id: str, updates: dict, auto_compile: bool = True) -> Rule:
        """Update an existing rule."""
        rules = self.list_rules()
        found = False
        
        for i, rule in enumerate(rules):
            if rule.rule_id == rule_id:
                # Apply updates
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                rules[i] = rule
                found = True
                break
        
        if not found:
            raise ValueError(f"Rule with ID '{rule_id}' not found")
        
        self._write_rules(rules)
        
        if auto_compile:
            self.compile_rules()
        
        return rules[i]
    
    def delete_rule(self, rule_id: str, auto_compile: bool = True) -> bool:
        """Delete a rule."""
        rules = self.list_rules()
        original_count = len(rules)
        rules = [r for r in rules if r.rule_id != rule_id]
        
        if len(rules) == original_count:
            raise ValueError(f"Rule with ID '{rule_id}' not found")
        
        self._write_rules(rules)
        
        if auto_compile:
            self.compile_rules()
        
        return True
    
    def validate_rule(self, rule: Rule) -> ValidationResult:
        """Validate a rule before saving."""
        result = ValidationResult(valid=True)
        
        # Required fields
        if not rule.name:
            result.errors.append("Name is required")
            result.valid = False
        
        if not rule.action_type:
            result.errors.append("Action type is required")
            result.valid = False
        
        if not rule.action_value:
            result.errors.append("Action value is required")
            result.valid = False
        
        # Validate action value is numeric for price actions
        if rule.action_type in ('override_unit_price', 'discount_amount', 'discount_percent', 'price_floor'):
            try:
                float(rule.action_value)
            except ValueError:
                result.errors.append(f"Action value must be a number for {rule.action_type}")
                result.valid = False
        
        # Validate dates
        if rule.start_date and rule.end_date:
            if rule.start_date > rule.end_date:
                result.errors.append("Start date must be before end date")
                result.valid = False
        
        # Warn if dates are in the past
        today = datetime.now().strftime('%Y-%m-%d')
        if rule.end_date and rule.end_date < today:
            result.warnings.append("Rule has expired (end date is in the past)")
        
        # Validate SKU exists in catalog
        if rule.sku and self._catalog_skus:
            if rule.sku not in self._catalog_skus:
                result.warnings.append(f"SKU '{rule.sku}' not found in Master Catalog")
        
        # Count matching products for prefix
        if rule.sku_prefix and self._catalog_skus:
            matches = sum(1 for sku in self._catalog_skus if sku.startswith(rule.sku_prefix))
            result.matching_products = matches
            if matches == 0:
                result.warnings.append(f"No products match SKU prefix '{rule.sku_prefix}'")
        
        # Check for potential conflicts
        if result.valid:
            conflicts = self._check_conflicts(rule)
            result.warnings.extend(conflicts)
        
        return result
    
    def _check_conflicts(self, rule: Rule) -> list[str]:
        """Check for rules that might conflict with this one."""
        warnings = []
        existing_rules = self.list_rules()
        
        for existing in existing_rules:
            if existing.rule_id == rule.rule_id:
                continue
            
            # Check for same account/group + SKU overlap
            account_match = (
                (rule.account and rule.account == existing.account) or
                (rule.account_group and rule.account_group == existing.account_group)
            )
            
            sku_match = (
                (rule.sku and rule.sku == existing.sku) or
                (rule.sku_prefix and existing.sku_prefix and 
                 (rule.sku_prefix.startswith(existing.sku_prefix) or 
                  existing.sku_prefix.startswith(rule.sku_prefix)))
            )
            
            if account_match and sku_match:
                warnings.append(
                    f"Potential conflict with rule '{existing.rule_id}' "
                    f"(priority {existing.priority} vs {rule.priority})"
                )
        
        return warnings
    
    def _generate_rule_id(self, rule: Rule) -> str:
        """Generate a unique rule ID."""
        base = ""
        if rule.account_group:
            base = rule.account_group.upper()[:4]
        elif rule.account:
            base = f"ACCT{rule.account}"
        else:
            base = "RULE"
        
        # Add SKU hint
        if rule.sku:
            base += f"-{rule.sku[:8]}"
        elif rule.sku_prefix:
            base += f"-{rule.sku_prefix[:6]}"
        
        # Ensure uniqueness
        existing_ids = {r.rule_id for r in self.list_rules()}
        candidate = base
        counter = 1
        while candidate in existing_ids:
            candidate = f"{base}-{counter}"
            counter += 1
        
        return candidate
    
    def _write_rules(self, rules: list[Rule]):
        """Write rules back to CSV."""
        with open(self.rules_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            for rule in rules:
                writer.writerow(rule.to_csv_row())
    
    def compile_rules(self) -> tuple[bool, str]:
        """Run the compile_rules.py script."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.compile_script_path)],
                capture_output=True,
                text=True,
                cwd=self.compile_script_path.parent.parent.parent.parent
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except Exception as e:
            return False, str(e)
    
    def get_stats(self) -> dict:
        """Get statistics about rules."""
        rules = self.list_rules()
        today = datetime.now().strftime('%Y-%m-%d')
        
        active = [r for r in rules if r.active]
        expired = [r for r in rules if r.end_date and r.end_date < today]
        by_group = {}
        for r in rules:
            group = r.account_group or r.account or 'Global'
            by_group[group] = by_group.get(group, 0) + 1
        
        return {
            'total': len(rules),
            'active': len(active),
            'inactive': len(rules) - len(active),
            'expired': len(expired),
            'by_group': by_group,
        }
