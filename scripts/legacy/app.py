import streamlit as st
import pandas as pd
from pricing_engine import PricingEngine

st.set_page_config(page_title="Pricing Calculation System", layout="wide")

@st.cache_resource
def get_engine():
    return PricingEngine()

try:
    engine = get_engine()
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

st.title("Pricing Calculation System")
st.divider()

# Sidebar: Account Configuration
st.sidebar.header("Customer Information")
account_id = st.sidebar.text_input("Account Number", value="1730")
active_tier = engine.get_account_tier(account_id)
st.sidebar.text(f"Resolved Tier: {active_tier}")

# Main Layout
left_column, right_column = st.columns([2, 1])

with left_column:
    st.subheader("Add Items to Quote")
    
    available_skus = engine.catalog.index.tolist()
    labels = [f"{s} | {engine.catalog.loc[s, 'Description']}" if pd.notna(engine.catalog.loc[s, 'Description']) else f"{s} | (No Description)" for s in available_skus]
    
    selected_option = st.selectbox("Search by SKU or Description", options=labels)
    selected_sku = selected_option.split(" | ")[0]
    
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
    
    if st.button("Add Line Item"):
        if 'cart' not in st.session_state:
            st.session_state.cart = {}
        st.session_state.cart[selected_sku] = st.session_state.cart.get(selected_sku, 0) + quantity

    if 'cart' in st.session_state and st.session_state.cart:
        if st.button("Clear All Items"):
            st.session_state.cart = {}
            st.rerun()

with right_column:
    st.subheader("Quote Summary")
    if 'cart' in st.session_state and st.session_state.cart:
        result = engine.calculate_quote(account_id, st.session_state.cart)
        
        st.metric("Total Value", f"${result['Total']:,.2f}")
        st.text(f"Pricing Tier: {result['Tier']}")
        
        df_display = pd.DataFrame(result['Lines'])
        st.table(df_display[['SKU', 'Quantity', 'Unit Price', 'Total', 'Source']])
    else:
        st.info("No items currently in quote.")