"""
main.py - CLI entry point for the Moms Verdict Engine.

Usage:
  # Run evaluation suite (no API key needed):
  python main.py --eval

  # Analyze reviews from a JSON file:
  python main.py --input reviews.json --product "Bugaboo Fox 3"

  # Analyze inline reviews:
  python main.py --reviews "Great product!" "Loved it" "Worth the price"

  # Use a specific model:
  python main.py --input reviews.json --model openai/gpt-4o-mini
"""

import argparse
import json
import logging
import sys

from schema import ReviewInput, VerdictOutput
from verdict_engine import run_pipeline, DEFAULT_MODEL
from evaluator import run_evaluation


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def print_verdict(verdict: VerdictOutput, product_name: str = "") -> None:
    """Pretty-print the verdict to stdout."""
    print("\n" + "=" * 60)
    if product_name:
        print(f"  VERDICT: {product_name}")
    else:
        print("  VERDICT")
    print("=" * 60)

    print(f"\n  English:  {verdict.verdict_en or '(insufficient data)'}")
    print(f"  Arabic:   {verdict.verdict_ar or '(insufficient data)'}")
    print(f"\n  Sentiment:  {verdict.sentiment_score:.2f} / 1.00")
    print(f"  Confidence: {verdict.confidence:.2f} / 1.00")
    print(f"  Should Buy: {verdict.should_buy}")

    if verdict.pros:
        print("\n  Pros:")
        for p in verdict.pros:
            print(f"    + {p}")

    if verdict.cons:
        print("\n  Cons:")
        for c in verdict.cons:
            print(f"    - {c}")

    if verdict.common_issues:
        print("\n  Common Issues:")
        for i in verdict.common_issues:
            print(f"    ! {i}")

    print("\n" + "=" * 60)


def load_reviews_from_file(path: str) -> tuple[list[str], str]:
    """
    Load reviews from a JSON file.
    Accepts two formats:
      - {"product": "...", "reviews": ["...", ...]}
      - ["...", "..."]  (plain list)
    Returns (reviews, product_name).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data, ""
    elif isinstance(data, dict):
        reviews = data.get("reviews", [])
        product = data.get("product", "")
        return reviews, product
    else:
        raise ValueError("Input file must be a JSON array or object with 'reviews' key.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Moms Verdict Engine — AI-powered review intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--eval", action="store_true", help="Run the evaluation suite.")
    mode.add_argument("--input", metavar="FILE", help="Path to JSON file with reviews.")
    mode.add_argument("--reviews", nargs="+", metavar="REVIEW", help="Inline review strings.")

    parser.add_argument("--product", default="", help="Product name (optional).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model ID.")
    parser.add_argument("--json-out", action="store_true", help="Output raw JSON instead of formatted text.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()
    setup_logging(args.verbose)

    # ── Evaluation mode ──────────────────────────────────────────────────────
    if args.eval:
        results = run_evaluation(verbose=True)
        failed = [r for r in results if not r.passed]
        return 0 if not failed else 1

    # ── Analysis mode ────────────────────────────────────────────────────────
    try:
        if args.input:
            reviews, product_name = load_reviews_from_file(args.input)
            product_name = args.product or product_name
        else:
            reviews = args.reviews
            product_name = args.product

        input_data = ReviewInput(product_name=product_name or None, reviews=reviews)

    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading input: {e}", file=sys.stderr)
        return 1

    try:
        verdict = run_pipeline(input_data, model=args.model)
    except RuntimeError as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        return 1

    if args.json_out:
        print(verdict.model_dump_json(indent=2))
    else:
        print_verdict(verdict, product_name=product_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
