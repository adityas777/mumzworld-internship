"""
app.py - Streamlit UI for the Moms Verdict Engine.

Run with:
  streamlit run app.py
"""

import json
import os

import streamlit as st

from schema import ReviewInput
from verdict_engine import run_pipeline, DEFAULT_MODEL
from sample_data import DATASETS

st.set_page_config(
    page_title="Moms Verdict Engine",
    page_icon="👶",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Sidebar — configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input(
        "OpenRouter API Key",
        value=os.getenv("OPENROUTER_API_KEY", ""),
        type="password",
        help="Get a key at openrouter.ai",
    )
    model = st.text_input("Model", value=DEFAULT_MODEL)
    use_mock = st.checkbox(
        "Use mock LLM (no API key needed)",
        value=not bool(api_key),
        help="Uses pre-built responses from the eval suite for demo purposes.",
    )

    st.divider()
    st.header("📦 Load Sample Dataset")
    sample_key = st.selectbox("Dataset", options=["(none)"] + list(DATASETS.keys()))

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
st.title("👶 Moms Verdict Engine")
st.caption("AI-powered review intelligence for Mumzworld")

product_name = st.text_input("Product Name (optional)", placeholder="e.g. Bugaboo Fox 3 Stroller")

# Load sample data if selected
default_reviews = ""
if sample_key != "(none)":
    dataset = DATASETS[sample_key]
    product_name = dataset["product"]
    default_reviews = "\n".join(dataset["reviews"])

reviews_text = st.text_area(
    "Paste reviews here (one per line)",
    value=default_reviews,
    height=250,
    placeholder="Great product!\nDelivery was fast.\nBaby loves it...",
)

analyze_btn = st.button("🔍 Analyze Reviews", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
if analyze_btn:
    reviews = [r.strip() for r in reviews_text.splitlines() if r.strip()]

    if not reviews:
        st.warning("Please enter at least one review.")
        st.stop()

    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key

    # Build mock function if needed
    mock_fn = None
    if use_mock and sample_key != "(none)":
        from evaluator import MOCK_RESPONSES
        mock_response = MOCK_RESPONSES.get(sample_key)
        if mock_response:
            mock_fn = lambda _p, _r: mock_response  # noqa: E731
        else:
            st.warning("No mock response for this dataset. Using real API.")

    try:
        input_data = ReviewInput(
            product_name=product_name or None,
            reviews=reviews,
        )

        with st.spinner("Analyzing reviews..."):
            verdict = run_pipeline(input_data, model=model, mock_llm_fn=mock_fn)

    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    # ── Results ──────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Verdict")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sentiment", f"{verdict.sentiment_score:.0%}")
    with col2:
        st.metric("Confidence", f"{verdict.confidence:.0%}")
    with col3:
        buy_label = "✅ Yes" if verdict.should_buy is True else ("❌ No" if verdict.should_buy is False else "❓ Unclear")
        st.metric("Should Buy?", buy_label)

    # Confidence bar
    st.progress(verdict.confidence, text=f"Confidence: {verdict.confidence:.0%}")

    # Sentiment bar (color via custom styling)
    sentiment_color = (
        "🟢" if verdict.sentiment_score >= 0.7
        else "🟡" if verdict.sentiment_score >= 0.4
        else "🔴"
    )
    st.write(f"{sentiment_color} Sentiment score: **{verdict.sentiment_score:.2f}**")

    st.divider()

    col_en, col_ar = st.columns(2)
    with col_en:
        st.markdown("**🇬🇧 English Verdict**")
        st.info(verdict.verdict_en or "_Insufficient data for a verdict._")
    with col_ar:
        st.markdown("**🇸🇦 Arabic Verdict**")
        st.info(verdict.verdict_ar or "_بيانات غير كافية._")

    st.divider()

    col_pros, col_cons = st.columns(2)
    with col_pros:
        st.markdown("**✅ Pros**")
        if verdict.pros:
            for p in verdict.pros:
                st.write(f"• {p}")
        else:
            st.write("_None identified_")

    with col_cons:
        st.markdown("**❌ Cons**")
        if verdict.cons:
            for c in verdict.cons:
                st.write(f"• {c}")
        else:
            st.write("_None identified_")

    if verdict.common_issues:
        st.divider()
        st.markdown("**⚠️ Common Issues**")
        for issue in verdict.common_issues:
            st.warning(f"• {issue}")

    # Raw JSON expander
    with st.expander("🔧 Raw JSON Output"):
        st.code(verdict.model_dump_json(indent=2), language="json")
