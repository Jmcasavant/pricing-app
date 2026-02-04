"""
Streamlit UI for the Pricing Calculation System - Enhanced Edition.

Features:
- Tabbed interface for Quote, Catalog, Rules, and System Info
- Editable cart with data grid
- Bulk SKU entry
- Export to Excel/CSV
- Visual analytics (savings, coverage)
"""
import streamlit as st
import pandas as pd
import sys
import io
from pathlib import Path
from datetime import datetime

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from pricing_tool.engine import PricingEngine, Request
from pricing_tool.config.settings import get_settings


st.set_page_config(
    page_title="Pricing Calculation System",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def get_engine():
    """Get cached engine instance."""
    return PricingEngine()


@st.cache_resource
def get_settings_cached():
    """Get cached settings."""
    return get_settings()


try:
    engine = get_engine()
    settings = get_settings_cached()
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()


# ============================================================================
# CUSTOM CSS & STYLING
# ============================================================================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1 {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-weight: 700;
        }
        .stMetric {
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 5px;
            border-left: 5px solid #ff4b4b;
        }
        [data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR: Account Configuration
# ============================================================================
with st.sidebar:
    st.header("👤 Customer Context")
    
    with st.container(border=True):
        account_id = st.text_input("Account Number", value="1730", key="account_input")
        
        try:
            active_tier = engine.get_account_tier(account_id)
            
            # Tier Badge Color Logic
            tier_color = "gray"
            if active_tier == "GOLD": tier_color = "gold"
            elif active_tier == "PLATINUM": tier_color = "blue"
            elif active_tier == "SILVER": tier_color = "silver"
            elif active_tier == "BRONZE": tier_color = "orange"
            
            st.markdown(f"**Current Tier:**")
            st.markdown(f":{tier_color}[**{active_tier}**]")
            
        except Exception as e:
            st.error(f"Error resolving tier: {e}")
            active_tier = "MSRP"

    # Show tier resolution trace
    with st.expander("🔍 Resolution Details"):
        _, trace = engine.get_account_tier_with_trace(account_id)
        for step, desc, val in trace:
            if val:
                st.caption(f"**{step}**: {desc} = `{val}`")
            else:
                st.caption(f"**{step}**: {desc}")

    st.divider()

    # Rules status
    if engine.rule_matcher.loaded:
        st.success(f"🔧 **{len(engine.rule_matcher.rules)} Rules Active**")
    else:
        st.warning("⚠️ No rules loaded")


# ============================================================================
# MAIN CONTENT: TABBED INTERFACE
# ============================================================================
st.title("Pricing Calculation System")
st.caption(f"v1.0 | Pricing Engine Active | {datetime.now().strftime('%Y-%m-%d')}")

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Quote Builder", "📚 Catalog", "🔧 Rules", "📊 System"])


# ============================================================================
# TAB 1: NEW QUOTE
# ============================================================================
with tab1:
    # Initialize cart
    if 'cart' not in st.session_state:
        st.session_state.cart = {}
    
    col1, col2 = st.columns([1.8, 1.2], gap="large")
    
    with col1:
        st.subheader("Add Items")
        
        # Method 1: SKU Search
        with st.container(border=True):
            st.markdown("##### 🔍 Quick Add")
            available_skus = engine.catalog.index.tolist()
            labels = [
                f"{s} | {engine.catalog.loc[s, 'Description']}" 
                if pd.notna(engine.catalog.loc[s, 'Description']) 
                else f"{s} | (No Description)" 
                for s in available_skus
            ]
            
            selected_option = st.selectbox("Search Product", options=labels, key="sku_search", label_visibility="collapsed", placeholder="Type to search SKU or Description...")
            selected_sku = selected_option.split(" | ")[0] if selected_option else None
            
            c1, c2 = st.columns([1, 4])
            with c1:
                quantity = st.number_input("Qty", min_value=1, value=1, step=1, key="single_qty")
            with c2:
                st.write("")
                st.write("")
                if st.button("➕ Add to Quote", type="primary"):
                    if selected_sku:
                        st.session_state.cart[selected_sku] = st.session_state.cart.get(selected_sku, 0) + quantity
                        st.rerun()
        
        # Method 2: Bulk Entry
        with st.expander("📋 Bulk Item Entry"):
            st.caption("Paste SKUs (one per line) or `SKU, QTY` format:")
            bulk_text = st.text_area(
                "Bulk SKU Entry",
                height=100,
                placeholder="84314503F, 10\n1908106, 5",
                label_visibility="collapsed"
            )
            
            if st.button("Processing Batch"):
                if bulk_text.strip():
                    lines = bulk_text.strip().split('\n')
                    added_count = 0
                    for line in lines:
                        line = line.strip()
                        if not line: continue
                        
                        if ',' in line:
                            parts = line.split(',')
                            sku = parts[0].strip()
                            try: qty = int(parts[1].strip())
                            except: qty = 1
                        else:
                            sku = line; qty = 1
                        
                        if sku in engine.catalog.index:
                            st.session_state.cart[sku] = st.session_state.cart.get(sku, 0) + qty
                            added_count += 1
                    
                    if added_count > 0:
                        st.success(f"Added {added_count} items")
                        st.rerun()
                    else:
                        st.warning("No valid SKUs found")

    with col2:
        st.subheader("Quote Summary")
        
        with st.container(border=True):
            if st.session_state.cart:
                # Calculate quote
                request = Request(account_id=account_id, items=st.session_state.cart)
                result = engine.calculate(request)
                
                # Top Level Metrics
                m1, m2 = st.columns(2)
                m1.metric("Total", f"${result.total:,.2f}")
                m2.metric("Items", sum(st.session_state.cart.values()))
                
                st.divider()
                st.caption(f"**Applied Tier:** {result.tier}")
                
                # Savings Logic
                msrp_total = sum(
                    float(engine.catalog.loc[line.sku, 'MSRP']) * line.quantity 
                    for line in result.lines 
                    if line.sku in engine.catalog.index and pd.notna(engine.catalog.loc[line.sku, 'MSRP'])
                )
                
                if msrp_total > result.total:
                    savings = msrp_total - result.total
                    savings_pct = (savings / msrp_total) * 100
                    st.markdown(f":green[**You Save: ${savings:,.2f} ({savings_pct:.1f}%)**]")
                
                # Warnings
                if result.warnings:
                    for warning in result.warnings:
                        st.warning(warning)
                
                st.divider()
                
                # Actions
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    # Export Data
                    export_df = pd.DataFrame([{
                        'SKU': line.sku,
                        'Description': line.description,
                        'Quantity': line.quantity,
                        'Unit Price': line.unit_price,
                        'Ext Price': line.extended_price,
                        'Tier': line.tier_used
                    } for line in result.lines])
                    
                    st.download_button(
                        "📥 CSV",
                        data=export_df.to_csv(index=False),
                        file_name=f"quote_{account_id}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with btn_col2:
                    if st.button("🗑️ Clear", use_container_width=True):
                        st.session_state.cart = {}
                        st.rerun()
            else:
                st.info("🛒 Cart is empty")
                st.caption("Search or paste SKUs to begin building a quote.")

    # Editable Cart Table (Full Width)
    if st.session_state.cart:
        st.markdown("### 📝 Edit Line Items")
        
        # Build editable dataframe
        cart_data = []
        for sku, qty in st.session_state.cart.items():
            desc = engine.catalog.loc[sku, 'Description'] if sku in engine.catalog.index else "Unknown"
            cart_data.append({
                'SKU': sku,
                'Description': desc,
                'Quantity': qty
            })
        
        edited_df = st.data_editor(
            pd.DataFrame(cart_data),
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "SKU": st.column_config.TextColumn("SKU", disabled=True),
                "Description": st.column_config.TextColumn("Description", disabled=True),
                "Quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1)
            },
            hide_index=True,
            key="cart_editor"
        )
        
        if st.button("💾 Update Quantities"):
            new_cart = {row['SKU']: row['Quantity'] for _, row in edited_df.iterrows() if row['Quantity'] > 0}
            st.session_state.cart = new_cart
            st.rerun()
        
        st.divider()
        
        # Detailed Line Breakdown
        with st.expander("📊 View Detailed Pricing Breakdown"):
            display_data = []
            for line in result.lines:
                display_data.append({
                    'SKU': line.sku,
                    'Description': line.description,
                    'Qty': line.quantity,
                    'Unit Price': f"${line.unit_price:.2f}",
                    'Ext Price': f"${line.extended_price:.2f}",
                    'Tier': line.tier_used,
                    'Rules': ", ".join(line.rules_applied) if line.rules_applied else ""
                })
            
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)


# ============================================================================
# TAB 2: CATALOG EXPLORER
# ============================================================================
with tab2:
    st.subheader("📚 Master Catalog")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("Search Catalog", placeholder="Enter SKU or Description...", label_visibility="collapsed")
    with col2:
        tier_filter = st.selectbox("Tier", ["ALL", "BRONZE", "SILVER", "GOLD", "PLATINUM", "MSRP"], label_visibility="collapsed")
    with col3:
        show_priced_only = st.checkbox("Has Price Only", value=True)
    
    # ... (Keep existing logic, just improved wrapper above)
    catalog_display = engine.catalog.copy()
    if search_term:
        mask = (
            catalog_display.index.str.contains(search_term, case=False, na=False) |
            catalog_display['Description'].str.contains(search_term, case=False, na=False)
        )
        catalog_display = catalog_display[mask]
    
    if tier_filter == "ALL":
        cols_to_show = ['Description', 'MSRP', 'BRONZE_Price', 'SILVER_Price', 'GOLD_Price', 'PLATINUM_Price']
    elif tier_filter == "MSRP":
        cols_to_show = ['Description', 'MSRP']
    else:
        cols_to_show = ['Description', 'MSRP', f'{tier_filter}_Price']
    
    display_catalog = catalog_display[cols_to_show].copy()
    display_catalog.insert(0, 'SKU', display_catalog.index)
    
    if show_priced_only and tier_filter != "ALL" and tier_filter != "MSRP":
        price_col = f'{tier_filter}_Price'
        display_catalog = display_catalog[display_catalog[price_col].notna()]
    
    st.dataframe(display_catalog, use_container_width=True, height=600)
    st.caption(f"Total SKUs: {len(engine.catalog):,} | Visible: {len(display_catalog):,}")


# ============================================================================
# TAB 3: ACTIVE RULES
# ============================================================================
with tab3:
    st.subheader("🔧 Active Pricing Rules")
    # ... (Keep existing logic)
    if engine.rule_matcher.loaded and len(engine.rule_matcher.rules) > 0:
        rules_data = []
        for rule in engine.rule_matcher.rules:
            match = rule.get('match', {})
            conditions = ", ".join([f"{k}={v}" for k, v in match.items()])
            action = rule.get('action', {})
            
            rules_data.append({
                'ID': rule.get('rule_id'),
                'Priority': rule.get('priority'),
                'Conditions': conditions,
                'Action': f"{action.get('type')}: {action.get('value')}",
                'Notes': rule.get('notes')
            })
        st.dataframe(pd.DataFrame(rules_data), use_container_width=True, hide_index=True)
    else:
        st.info("No active rules.")

# ============================================================================
# TAB 4: SYSTEM INFO
# ============================================================================
with tab4:
    st.header("System Status")
    # ... (Keep existing logic)
    build_report_path = settings.build_report
    if build_report_path.exists():
        import json
        with open(build_report_path, 'r') as f:
            report = json.load(f)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SKUs Indexed", f"{report['metrics'].get('final_sku_count', 0):,}")
        c2.metric("Duplicates", f"{report['metrics'].get('duplicates_removed', 0):,}")
        c3.metric("Data Source", "catalogs_export.csv" if "catalogs_export" in report.get("input_files", {}) else "Legacy CSVs")
        c4.metric("Last Build", report.get('timestamp', '')[:10])

        st.divider()
        st.subheader("Tier Coverage")
        tier_coverage = report['metrics'].get('tier_coverage', {})
        cov_df = pd.DataFrame([
            {'Tier': k, 'SKUs': v['priced_skus'], 'Coverage': f"{v['coverage_pct']}%"}
            for k, v in tier_coverage.items()
        ])
        st.dataframe(cov_df, use_container_width=True, hide_index=True)
    
    if st.button("🔨 Rebuild Catalog", type="secondary"):
        with st.spinner("Rebuilding..."):
            import subprocess
            subprocess.run([sys.executable, 'scripts/build_all.py'], cwd=settings.project_root, capture_output=True)
            st.toast("Catalog rebuilt successfully!")
            st.rerun()

