"""
NearBite — Personalized NYC Restaurant Discovery
Entry point: streamlit run app.py
"""

import streamlit as st

# Module imports (stubs — will be filled in by each team member)
from frontend.ui import render_search_bar, render_filters, render_results
from integration.api import search_restaurants

st.set_page_config(
    page_title="NearBite",
    page_icon="🍜",
    layout="wide",
)


def main():
    st.title("🍜 NearBite")
    st.subheader("Personalized NYC Restaurant Discovery")

    # --- Search bar ---
    query = render_search_bar()

    # --- Filters sidebar ---
    filters = render_filters()

    # --- Results ---
    if query:
        results = search_restaurants(query=query, filters=filters)
        render_results(results)
    else:
        st.info("Type a query above to get started — e.g. 'cheap spicy ramen near NYU'")


if __name__ == "__main__":
    main()
