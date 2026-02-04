# Avante Pricing Engine & Companion App

**Current Status: v1.0 (Period 2 Alignment)**
**Date:** February 4, 2026

## Project Overview
This project is a dual-stack application designed to manage complex B2B pricing logic for Certor Sports (Avante). It consists of a Python Pricing Engine (Backend) that processes rules and extensive catalog data, and a Next.js Frontend (Companion App) for sales reps to build orders and view pricing.

## Directory Structure

### src/pricing_tool/ (Backend / Core Logic)
The core Python package handling all business logic.
- **api/**: FastAPI routers (`main.py`, `rules_api.py`).
- **engine/**: The heart of the pricing logic (`pricing_engine.py`, `rule_matcher.py`).
- **policy/**: **[NEW]** Order-level policy logic.
  - `order_policy_engine.py`: Computes terms, freight, and holds.
  - `program_resolver.py`: Resolves Active Program ID (BSN, Sports Line, etc.).
- **rules/**: Rule management (`rules.csv`, `compile_rules.py`).

### frontend/ (Next.js Application)
Interactive web UI for users.
- **src/app/page.tsx**: Main "Order Builder" dashboard.
- **src/app/admin/rules/page.tsx**: Rules Administration interface.

---

## Current Status & Features

### 1. Order Policy Engine (Phase 1)
- **Program Resolution**: Waterfall mapping for accounts/groups to specific programs.
- **Smart Terms**: Dynamic calculation of Net 30/60/90 based on program and order total.
- **Freight Policies**: Automated freight charges (e.g., 18% SFT) and FFA (Free Freight Allowed) threshold enforcement.
- **Workflow Holds**: Automated hold flagging for specific order conditions.

### 2. Pricing Engine (Period 2)
- **Date Gating**: Rules now respect effective dating (Rebates end 4/15/26, BSN ends 1/31/26).
- **Item Configuration**: Support for custom line-level data (e.g., helmet colors) through the calculation lifecycle.
- **Traceability**: Full execution trace for every price resolved.

### 3. Rules Administration
- **Full CRUD**: Manage pricing rules via a premium high-density dark mode UI.
- **Live Testing**: Integrated "Rule Tester" for immediate validation against the live engine.

---

## Development Setup

### Backend (Python 3.10+)
1.  **Dependencies**: `pip install -r requirements.txt` (or install `fastapi`, `uvicorn`, `pandas`, `openpyxl`).
2.  **Start API**: `python scripts/run_api.py` (Runs on Port 8000).

### Frontend (Next.js)
1.  **Navigate**: `cd frontend`
2.  **Install**: `npm install`
3.  **Start Dev**: `npm run dev` (Runs on Port 3000).

---

## Known Issues / Notes
- **Data Files**: `Master_Catalog_Final.csv` and `Pricing Rules Starter 1.xlsx` must be present in the project root.
- **Rule Compilation**: Rules are compiled to `compiled_rules.json` for high performance. Use the Admin UI or `python src/pricing_tool/rules/compile_rules.py` to trigger.
