import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(os.getcwd()) / 'src'))

from pricing_tool.services.rules_service import RulesService, Rule
from pricing_tool.config.settings import get_settings

settings = get_settings()
service = RulesService(
    rules_csv_path=settings.rules_csv,
    compile_script_path=settings.project_root / 'src' / 'pricing_tool' / 'rules' / 'compile_rules.py',
    catalog_path=settings.master_catalog
)

rule = Rule(
    rule_id="AYF-25-OFF",
    name="AYF Direct: 25% Off MSRP",
    priority=10,
    account_group="DIRECT_AYF",
    action_type="discount_percent",
    action_value="25",
    start_date="2026-01-01",
    end_date="2099-12-31",
    notes="Standard AYF Discount Code: AYF25"
)

try:
    created = service.create_rule(rule)
    print(f"✅ Created rule: {created.rule_id}")
    
    # Reload engine
    from pricing_tool.api.state import engine
    engine.reload_data()
    print("✅ Engine reloaded")
    
except Exception as e:
    print(f"❌ Error: {e}")
