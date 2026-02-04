from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# Trigger reload for CSV data - Strict IDs
import pandas as pd
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add src to path for internal imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from pricing_tool.engine import PricingEngine, Request
from pricing_tool.config.settings import get_settings
from pricing_tool.api.rules_api import router as rules_router
from pricing_tool.api.state import engine

app = FastAPI(
    title="Pricing Tool API",
    description="Backend API for the Modern Pricing & ERP Assistant",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include rules management API
app.include_router(rules_router)

# Include rules management API
app.include_router(rules_router)


class CalcRequest(BaseModel):
    account_id: str
    items: Dict[str, int]

@app.get("/")
async def root():
    return {"status": "online", "message": "Pricing Tool API Active"}

@app.post("/calculate")
async def calculate_quote(req: CalcRequest):
    try:
        request = Request(account_id=req.account_id, items=req.items)
        result = engine.calculate(request)
        # Use jsonable_encoder to handle dataclasses and potential numpy types
        from fastapi.encoders import jsonable_encoder
        return jsonable_encoder(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/catalog")
async def get_catalog(search: Optional[str] = None, account_id: Optional[str] = None):
    try:
        df = engine.catalog.copy()
        if search:
            mask = (
                df.index.str.contains(search, case=False, na=False) |
                df['Description'].str.contains(search, case=False, na=False)
            )
            df = df[mask]
        
        # Limit results
        if not search:
            df = df.head(100)
        else:
            df = df.head(200)

        # Basic JSON cleaning
        df = df.replace({float('nan'): None, float('inf'): None, float('-inf'): None})
        result = df.to_dict(orient="index")

        # If account_id provided, resolve real prices with rules
        if account_id:
            tier, _ = engine.get_account_tier_with_trace(account_id)
            for sku, data in result.items():
                line = engine._calculate_line(sku, 1, tier, account_id)
                if line:
                    data['YourPrice'] = line.unit_price
                    data['RuleApplied'] = len(line.rules_applied) > 0
                    data['TierUsed'] = line.tier_used
        
        return result
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/account/{account_id}/tier")
async def get_account_tier(account_id: str):
    try:
        tier, trace = engine.get_account_tier_with_trace(account_id)
        intel = engine.get_account_intel(account_id)
        return {
            "account_id": account_id,
            "tier": tier,
            "trace": trace,
            "intel": intel
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/status")
async def get_status():
    settings = get_settings()
    has_report = settings.build_report.exists()
    return {
        "engine_active": True,
        "rules_loaded": engine.rule_matcher.loaded,
        "rules_count": len(engine.rule_matcher.rules),
        "catalog_last_build": settings.build_report.stat().st_mtime if has_report else None
    }
