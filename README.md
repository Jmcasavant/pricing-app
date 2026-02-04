# Avante Pricing Engine & Companion App

**Current Status: v0.5 (Rules Admin Release)**
**Date:** February 3, 2026

## Project Overview
This project is a dual-stack application designed to manage complex B2B pricing logic for Certor Sports (Avante). It consists of a Python Pricing Engine (Backend) that processes rules and extensive catalog data, and a Next.js Frontend (Companion App) for sales reps to build orders and view pricing.

## Directory Structure

### src/pricing_tool/ (Backend / Core Logic)
The core Python package handling all business logic.
- **api/**: FastAPI routers.
  - `rules_api.py`: Endpoints for CRUD operations on pricing rules.
- **engine/**: The heart of the pricing logic.
  - `calc.py`: Main calculation engine.
  - `rule_matcher.py`: Logic to match rules to order lines.
- **rules/**: Rule management.
  - `rules.csv`: Source of Truth for all pricing rules.
  - `compiled_rules.json`: High-performance JSON artifact generated from CSV.
- **services/**: Business logic layer.
  - `rules_service.py`: Handles validation, conflict detection, and CSV writing.

### frontend/ (Next.js Application)
Interactive web UI for users.
- **src/app/page.tsx**: Main "Order Builder" dashboard.
- **src/app/admin/rules/page.tsx**: **[NEW]** Rules Administration interface.
- **src/lib/rules-api.ts**: Frontend client for the Rules API.

### scripts/ (Utility)
- **run_api.py**: Entry point to start the FastAPI server (Port 8000).
- **legacy/**: Contains previous Streamlit-based application files (`app.py`, `pricing_engine.py`, etc.).

---

## Current Status & Features

### 1. Rules Administration
- **Full CRUD**: Create, Read, Update, Delete pricing rules via UI.
- **Visuals**: High-density dark mode ("Pro" aesthetic) matching the main dashboard.
- **Validation**: Real-time checking for conflicts and invalid inputs.
- **Testing**: Built-in "Rule Tester" to simulate price calculations immediately.

### 2. Pricing Engine
- **Source**: `rules.csv` is the primary database.
- **Compilation**: Rules are "compiled" into JSON for sub-millisecond lookups.
- **Logic**: Supports overrides, discounts (Amount/%), and price floors.

### 3. Order Builder (Frontend)
- **Grid Layout**: High-density table for rapid order entry.
- **Live Pricing**: Real-time calls to the backend engine.
- **Smart Features**: "Clear All", one-click copy, and rule source indicators.

---

## Known Issues / Notes
- **Browser Environment**: The internal browser tool is currently unavailable; visual verification relies on user screenshots.
- **Rule Updates**: Rules are auto-compiled on save, but heavily cached engine instances may need a restart if changes aren't immediate in the main app (though `run_api.py` typically handles this).

## Next Steps
1.  **Catalog Integration**: Deepen the link between `Master_Catalog` and the Rules engine for SKU validation.
2.  **Bulk Operations**: Add CSV import/export for bulk rule updates via the Admin UI.
3.  **Authentication**: Secure the Admin routes (currently open).