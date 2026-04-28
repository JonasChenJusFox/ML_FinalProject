"""
frontend/components/comments_modal.py
Owner: Jonas Chen

Responsibilities:
- Renders a single global comments modal
- Displays review snippets for the currently selected restaurant
- Reads comment dialog state from Streamlit session state
- Prevents multiple dialogs from being opened in the same script run
"""

from __future__ import annotations

import html

import streamlit as st

from frontend.adapters import clean_text
from frontend.components.dialog_gate import can_open_dialog


def init_comments_modal_state() -> None:
    if "show_comments_modal" not in st.session_state:
        st.session_state.show_comments_modal = False

    if "comments_modal_restaurant_name" not in st.session_state:
        st.session_state.comments_modal_restaurant_name = ""

    if "comments_modal_reviews" not in st.session_state:
        st.session_state.comments_modal_reviews = []


def open_comments_modal(name: str, reviews: list) -> None:
    st.session_state.comments_modal_restaurant_name = name
    st.session_state.comments_modal_reviews = reviews or []
    st.session_state.show_comments_modal = True


def close_comments_modal() -> None:
    st.session_state.show_comments_modal = False
    st.session_state.comments_modal_restaurant_name = ""
    st.session_state.comments_modal_reviews = []


def render_comments_modal() -> None:
    init_comments_modal_state()

    if not st.session_state.get("show_comments_modal", False):
        return
    if not can_open_dialog("comments_modal"):
        return

    @st.dialog("Comments")
    def _dialog() -> None:
        name = st.session_state.get("comments_modal_restaurant_name", "Restaurant")
        reviews = st.session_state.get("comments_modal_reviews", [])

        st.subheader(name)

        if not reviews:
            st.write("No reviews available.")
        else:
            shown_any = False
            for idx, review in enumerate(reviews, start=1):
                if isinstance(review, dict):
                    text = clean_text(review.get("text", ""))
                else:
                    text = clean_text(str(review))

                if text:
                    shown_any = True
                    st.markdown(f"**Comment {idx}**")
                    safe_text = html.escape(text).replace("\n", "<br>")
                    st.markdown(
                        f"<div class='nb-comment-text'>{safe_text}</div>",
                        unsafe_allow_html=True,
                    )

                    if idx < len(reviews):
                        st.divider()

            if not shown_any:
                st.write("No reviews available.")

        if st.button("Close", key="comments_modal_close", use_container_width=True):
            close_comments_modal()
            st.rerun()

    _dialog()