"""
verdict_engine.py - Core pipeline for the Moms Verdict Engine.

Pipeline:
  1. Clean & preprocess reviews
  2. (Optional) Retrieve top-K most informative reviews via TF-IDF
  3. Call LLM (Groq) to generate structured JSON
  4. Validate with Pydantic
  5. Retry on failure (up to MAX_RETRIES)
"""

import json
import logging
import os
import re
import time
from typing import Optional

import requests
from pydantic import ValidationError

from schema import ReviewInput, VerdictOutput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model choice: llama-3.3-70b-versatile — Groq's best multilingual model, very fast inference.
# Fallback: mixtral-8x7b-32768 for longer context windows.
DEFAULT_MODEL = os.getenv("VERDICT_MODEL", "llama-3.3-70b-versatile")

MAX_RETRIES = 3
TOP_K_REVIEWS = 40          # Max reviews sent to LLM after retrieval
MIN_REVIEWS_FOR_VERDICT = 3  # Below this → low confidence, null verdict


# ---------------------------------------------------------------------------
# Step 1: Preprocessing
# ---------------------------------------------------------------------------

def clean_review(text: str) -> str:
    """
    Normalize a single review:
    - Collapse whitespace
    - Remove URLs, emails
    - Strip excessive punctuation
    - Keep Arabic and Latin characters
    """
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    # Collapse repeated punctuation (e.g., "!!!!" → "!")
    text = re.sub(r"([!?.]){2,}", r"\1", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preprocess_reviews(reviews: list[str]) -> list[str]:
    """Clean all reviews and remove near-duplicates (simple exact dedup after normalization)."""
    cleaned = [clean_review(r) for r in reviews]
    # Deduplicate by lowercased content
    seen: set[str] = set()
    unique: list[str] = []
    for r in cleaned:
        key = r.lower()
        if key not in seen and len(r) > 5:
            seen.add(key)
            unique.append(r)
    return unique


# ---------------------------------------------------------------------------
# Step 2: Top-K Retrieval (TF-IDF based, no external vector DB required)
# ---------------------------------------------------------------------------

def retrieve_top_k(reviews: list[str], k: int = TOP_K_REVIEWS) -> list[str]:
    """
    Select the most informative reviews using TF-IDF variance scoring.
    Reviews with higher average TF-IDF scores carry more unique information.
    Falls back to truncation if sklearn is unavailable.
    """
    if len(reviews) <= k:
        return reviews

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np

        vectorizer = TfidfVectorizer(max_features=500, stop_words=None)
        tfidf_matrix = vectorizer.fit_transform(reviews)
        # Score each review by mean TF-IDF weight (proxy for informativeness)
        scores = np.asarray(tfidf_matrix.mean(axis=1)).flatten()
        top_indices = scores.argsort()[-k:][::-1]
        return [reviews[i] for i in sorted(top_indices)]
    except ImportError:
        logger.warning("sklearn not available — using first %d reviews.", k)
        return reviews[:k]


# ---------------------------------------------------------------------------
# Step 3: LLM Call
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a product review analyst for Mumzworld, a leading Middle Eastern e-commerce platform for mothers and babies.

Your job: analyze a batch of product reviews and return a structured JSON verdict.

STRICT RULES:
- Base ALL claims only on the provided reviews. Do NOT invent facts.
- If reviews are contradictory, lower the confidence score.
- If there are fewer than 3 substantive reviews, return null for verdict fields and set confidence ≤ 0.3.
- verdict_ar must sound natural in Arabic — NOT a word-for-word translation of verdict_en.
- should_buy must be null if confidence < 0.4 or reviews are too contradictory.
- sentiment_score: 0.0 = extremely negative, 1.0 = extremely positive.
- confidence: reflects how consistent and numerous the reviews are.

Return ONLY valid JSON matching this schema — no markdown, no explanation:
{
  "verdict_en": string | null,
  "verdict_ar": string | null,
  "pros": [string],
  "cons": [string],
  "common_issues": [string],
  "sentiment_score": float,
  "confidence": float,
  "should_buy": boolean | null
}"""


def build_user_prompt(product_name: Optional[str], reviews: list[str]) -> str:
    product_line = f"Product: {product_name}\n\n" if product_name else ""
    reviews_block = "\n".join(f"- {r}" for r in reviews)
    return (
        f"{product_line}"
        f"Analyze the following {len(reviews)} product reviews and return the JSON verdict:\n\n"
        f"{reviews_block}"
    )


def call_llm(
    product_name: Optional[str],
    reviews: list[str],
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Call Groq API and return raw response text.
    Raises RuntimeError on HTTP or network failure.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Set it with: export GROQ_API_KEY=your_key  (or 'set' on Windows)"
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(product_name, reviews)},
        ],
        "temperature": 0.2,   # Low temp for consistent structured output
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected API response structure: {data}") from e


# ---------------------------------------------------------------------------
# Step 4 & 5: Parse, Validate, Retry
# ---------------------------------------------------------------------------

def extract_json(raw: str) -> dict:
    """
    Extract JSON from LLM response.
    Handles cases where the model wraps output in markdown code fences.
    """
    # Strip markdown fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    # Find the first { ... } block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response:\n{raw}")

    return json.loads(match.group())


def run_pipeline(
    input_data: ReviewInput,
    model: str = DEFAULT_MODEL,
    mock_llm_fn=None,
) -> VerdictOutput:
    """
    Full pipeline: preprocess → retrieve → LLM → validate → retry.

    Args:
        input_data: Validated ReviewInput
        model: Groq model identifier (default: llama-3.3-70b-versatile)
        mock_llm_fn: Optional callable(product_name, reviews) → str
                     Used in tests to bypass real API calls.

    Returns:
        VerdictOutput (validated Pydantic model)

    Raises:
        RuntimeError: If all retries fail validation
    """
    # Step 1: Clean
    cleaned = preprocess_reviews(input_data.reviews)
    logger.info("After preprocessing: %d reviews (from %d)", len(cleaned), len(input_data.reviews))

    # Step 2: Retrieve top-K
    selected = retrieve_top_k(cleaned, k=TOP_K_REVIEWS)
    logger.info("Selected %d reviews for LLM context.", len(selected))

    # Determine if we have enough data
    few_reviews = len(selected) < MIN_REVIEWS_FOR_VERDICT

    last_error: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("LLM call attempt %d/%d", attempt, MAX_RETRIES)

            # Step 3: Call LLM (or mock)
            if mock_llm_fn is not None:
                raw = mock_llm_fn(input_data.product_name, selected)
            else:
                raw = call_llm(input_data.product_name, selected, model=model)

            logger.debug("Raw LLM response:\n%s", raw)

            # Step 4: Parse JSON
            parsed = extract_json(raw)

            # Enforce low-confidence rules before validation
            if few_reviews:
                parsed["confidence"] = min(parsed.get("confidence", 0.3), 0.3)
                parsed["verdict_en"] = None
                parsed["verdict_ar"] = None
                parsed["should_buy"] = None

            # Step 5: Validate with Pydantic
            result = VerdictOutput(**parsed)
            return result

        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            last_error = e
            logger.warning("Attempt %d failed validation: %s", attempt, e)
            if attempt < MAX_RETRIES:
                time.sleep(1)  # Brief pause before retry
        except requests.HTTPError as e:
            raise RuntimeError(f"LLM API HTTP error: {e}") from e

    raise RuntimeError(
        f"All {MAX_RETRIES} attempts failed. Last error: {last_error}"
    )
