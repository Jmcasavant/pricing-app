"""
Rules API - FastAPI router for rule management.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from ..services.rules_service import RulesService, Rule, ValidationResult
from ..config.settings import get_settings
from .state import engine

router = APIRouter(prefix="/api/rules", tags=["rules"])

# Initialize service
settings = get_settings()
rules_service = RulesService(
    rules_csv_path=settings.rules_csv,
    compile_script_path=settings.project_root / 'src' / 'pricing_tool' / 'rules' / 'compile_rules.py',
    catalog_path=settings.master_catalog
)


# Pydantic models for API
class RuleCreate(BaseModel):
    """Request model for creating a rule."""
    rule_id: Optional[str] = None
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


class RuleUpdate(BaseModel):
    """Request model for updating a rule."""
    name: Optional[str] = None
    active: Optional[bool] = None
    priority: Optional[int] = None
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
    action_type: Optional[str] = None
    action_value: Optional[str] = None
    notes: Optional[str] = None


class RuleResponse(BaseModel):
    """Response model for a rule."""
    rule_id: str
    name: str
    active: bool
    priority: int
    account: Optional[str]
    account_group: Optional[str]
    sku: Optional[str]
    sku_prefix: Optional[str]
    brand: Optional[str]
    min_qty: Optional[int]
    max_qty: Optional[int]
    start_date: Optional[str]
    end_date: Optional[str]
    channel: str
    action_type: str
    action_value: str
    notes: Optional[str]


class ValidationResponse(BaseModel):
    """Response model for validation."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    matching_products: int


class TestRuleRequest(BaseModel):
    """Request model for testing rules."""
    account_id: str
    sku: str


class TestRuleResponse(BaseModel):
    """Response model for rule test."""
    matched_rules: list[dict]
    final_price: Optional[float]
    base_price: Optional[float]
    source: str


# Endpoints

@router.get("", response_model=list[RuleResponse])
async def list_rules(include_inactive: bool = True):
    """List all pricing rules."""
    rules = rules_service.list_rules(include_inactive=include_inactive)
    return [RuleResponse(**rule.__dict__) for rule in rules]


@router.get("/stats")
async def get_stats():
    """Get rule statistics."""
    return rules_service.get_stats()


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str):
    """Get a single rule by ID."""
    rule = rules_service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return RuleResponse(**rule.__dict__)


@router.post("", response_model=RuleResponse)
async def create_rule(rule_data: RuleCreate):
    """Create a new pricing rule."""
    rule = Rule(**rule_data.model_dump())
    
    # Validate first
    validation = rules_service.validate_rule(rule)
    if not validation.valid:
        raise HTTPException(status_code=400, detail={"errors": validation.errors})
    
    try:
        created = rules_service.create_rule(rule)
        return RuleResponse(**created.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: str, updates: RuleUpdate):
    """Update an existing rule."""
    # Use exclude_unset=True to only update fields provided in the request body,
    # including those explicitly set to None (null).
    update_dict = updates.model_dump(exclude_unset=True)
    
    try:
        updated = rules_service.update_rule(rule_id, update_dict)
        return RuleResponse(**updated.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete a rule."""
    try:
        rules_service.delete_rule(rule_id)
        return {"success": True, "message": f"Rule '{rule_id}' deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/validate", response_model=ValidationResponse)
async def validate_rule(rule_data: RuleCreate):
    """Validate a rule without saving."""
    rule = Rule(**rule_data.model_dump())
    result = rules_service.validate_rule(rule)
    return ValidationResponse(
        valid=result.valid,
        errors=result.errors,
        warnings=result.warnings,
        matching_products=result.matching_products
    )


@router.post("/compile")
async def compile_rules():
    """Force recompile of rules and reload engine."""
    success, output = rules_service.compile_rules()
    if success:
        engine.reload_data()
    return {
        "success": success,
        "output": output
    }


@router.post("/test", response_model=TestRuleResponse)
async def test_rules(request: TestRuleRequest):
    """Test which rules would match for an account + SKU using live engine."""
    # Get account's group using live engine
    account_groups = engine.group_members[
        engine.group_members['Account Number'] == request.account_id
    ]['Group ID'].unique()
    account_group = ','.join(account_groups) if len(account_groups) > 0 else None
    
    # Find matching rules
    matched = engine.rule_matcher.find_matching_rules(
        account_id=request.account_id,
        account_group=account_group,
        sku=request.sku,
        qty=1
    )
    
    # Get base price
    base_price = None
    tier = engine.get_tier(request.account_id)
    catalog_match = engine.master_catalog[engine.master_catalog['SKU'] == request.sku]
    if not catalog_match.empty:
        tier_col = f"{tier}_Price"
        if tier_col in catalog_match.columns:
            base_price = catalog_match.iloc[0].get(tier_col)
            if pd.isna(base_price):
                base_price = catalog_match.iloc[0].get('MSRP')
        else:
            base_price = catalog_match.iloc[0].get('MSRP')
    
    # Calculate final price
    final_price = base_price
    source = "Tier"
    
    if matched:
        for rule in matched:
            if rule.action_type == 'override_unit_price':
                final_price = float(rule.action_value)
                source = "Rule"
                break
    
    return TestRuleResponse(
        matched_rules=[
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "priority": r.priority,
                "action_type": r.action_type,
                "action_value": r.action_value,
                "match_reason": r.match_reason
            }
            for r in matched
        ],
        final_price=final_price,
        base_price=base_price,
        source=source
    )


# Import pandas for test endpoint
import pandas as pd
