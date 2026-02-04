"""
Rule Compiler - Validates and compiles rules from CSV to JSON.

Reads rules.csv, validates against schema, and outputs compiled_rules.json.
"""
import csv
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class RuleMatch:
    """Match conditions for a rule."""
    account: Optional[str] = None
    account_group: Optional[str] = None
    sku: Optional[str] = None
    sku_prefix: Optional[str] = None
    brand: Optional[str] = None
    min_qty: Optional[int] = None
    max_qty: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    channel: Optional[str] = None


@dataclass
class RuleAction:
    """Action to take when rule matches."""
    type: str
    value: str | float


@dataclass
class Rule:
    """A compiled pricing rule."""
    rule_id: str
    name: str
    active: bool
    priority: int
    match: RuleMatch
    action: RuleAction
    notes: str = ""


VALID_ACTION_TYPES = {
    'set_tier',
    'override_unit_price', 
    'discount_percent',
    'discount_amount',
    'price_floor'
}


def parse_bool(value: str) -> bool:
    """Parse a boolean from CSV string."""
    return value.lower() in ('true', '1', 'yes', 'on')


def parse_optional_int(value: str) -> Optional[int]:
    """Parse optional integer."""
    if not value or value.strip() == '':
        return None
    return int(value)


def parse_optional_float(value: str) -> Optional[float]:
    """Parse optional float."""
    if not value or value.strip() == '':
        return None
    return float(value)


def parse_optional_str(value: str) -> Optional[str]:
    """Parse optional string (empty = None)."""
    if not value or value.strip() == '':
        return None
    return value.strip()


def validate_rule(row: dict, line_num: int) -> tuple[Optional[Rule], list[str]]:
    """
    Validate and parse a rule from a CSV row.
    
    Returns (rule, errors) - rule is None if validation failed.
    """
    errors = []
    
    # Required fields
    rule_id = parse_optional_str(row.get('rule_id', ''))
    if not rule_id:
        errors.append(f"Line {line_num}: rule_id is required")
        return None, errors
    
    name = parse_optional_str(row.get('name', '')) or rule_id
    active = parse_bool(row.get('active', 'false'))
    
    try:
        priority = int(row.get('priority', '50'))
    except ValueError:
        errors.append(f"Line {line_num}: priority must be an integer")
        return None, errors
    
    # Match conditions
    match = RuleMatch(
        account=parse_optional_str(row.get('account', '')),
        account_group=parse_optional_str(row.get('account_group', '')),
        sku=parse_optional_str(row.get('sku', '')),
        sku_prefix=parse_optional_str(row.get('sku_prefix', '')),
        brand=parse_optional_str(row.get('brand', '')),
        min_qty=parse_optional_int(row.get('min_qty', '')),
        max_qty=parse_optional_int(row.get('max_qty', '')),
        start_date=parse_optional_str(row.get('start_date', '')),
        end_date=parse_optional_str(row.get('end_date', '')),
        channel=parse_optional_str(row.get('channel', '')),
    )
    
    # Validate dates
    for date_field in ['start_date', 'end_date']:
        date_val = getattr(match, date_field)
        if date_val:
            try:
                datetime.fromisoformat(date_val)
            except ValueError:
                errors.append(f"Line {line_num}: {date_field} must be YYYY-MM-DD format")
    
    # Action
    action_type = parse_optional_str(row.get('action_type', ''))
    if not action_type:
        errors.append(f"Line {line_num}: action_type is required")
        return None, errors
    
    if action_type not in VALID_ACTION_TYPES:
        errors.append(f"Line {line_num}: invalid action_type '{action_type}', must be one of: {VALID_ACTION_TYPES}")
        return None, errors
    
    action_value_str = parse_optional_str(row.get('action_value', ''))
    if action_value_str is None:
        errors.append(f"Line {line_num}: action_value is required")
        return None, errors
    
    # Parse action value based on type
    if action_type == 'set_tier':
        action_value = action_value_str
    else:
        try:
            action_value = float(action_value_str)
        except ValueError:
            errors.append(f"Line {line_num}: action_value must be numeric for {action_type}")
            return None, errors
    
    action = RuleAction(type=action_type, value=action_value)
    notes = parse_optional_str(row.get('notes', '')) or ""
    
    if errors:
        return None, errors
    
    return Rule(
        rule_id=rule_id,
        name=name,
        active=active,
        priority=priority,
        match=match,
        action=action,
        notes=notes
    ), []


def compile_rules(
    rules_csv: Path,
    output_json: Path,
    verbose: bool = True
) -> tuple[bool, list[Rule], list[str]]:
    """
    Compile rules from CSV to JSON.
    
    Returns (success, rules, errors).
    """
    all_errors = []
    rules = []
    
    if not rules_csv.exists():
        all_errors.append(f"Rules file not found: {rules_csv}")
        return False, [], all_errors
    
    with open(rules_csv, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for line_num, row in enumerate(reader, start=2):  # +2 for 1-indexed header row
            rule, errors = validate_rule(row, line_num)
            
            if errors:
                all_errors.extend(errors)
            elif rule:
                rules.append(rule)
    
    if all_errors:
        if verbose:
            print("Validation errors:")
            for err in all_errors:
                print(f"  ❌ {err}")
        return False, rules, all_errors
    
    # Sort by priority (lower = higher priority)
    rules.sort(key=lambda r: r.priority)
    
    # Write compiled JSON
    output_data = {
        "compiled_at": datetime.now().isoformat(),
        "source_file": str(rules_csv),
        "total_rules": len(rules),
        "active_rules": sum(1 for r in rules if r.active),
        "rules": []
    }
    
    for rule in rules:
        rule_dict = {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "active": rule.active,
            "priority": rule.priority,
            "match": {k: v for k, v in asdict(rule.match).items() if v is not None},
            "action": {"type": rule.action.type, "value": rule.action.value},
            "notes": rule.notes
        }
        output_data["rules"].append(rule_dict)
    
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    if verbose:
        print(f"✅ Compiled {len(rules)} rules ({output_data['active_rules']} active)")
        print(f"   Output: {output_json}")
    
    return True, rules, []


def main():
    """CLI entry point."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    from src.pricing_tool.config.settings import get_settings
    
    settings = get_settings()
    rules_csv = settings.rules_csv
    output_json = settings.compiled_rules
    
    print("Compiling pricing rules...")
    success, rules, errors = compile_rules(rules_csv, output_json)
    
    if not success:
        print(f"\n❌ Compilation failed with {len(errors)} errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
