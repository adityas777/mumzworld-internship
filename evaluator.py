"""
evaluator.py - Evaluation pipeline for the Moms Verdict Engine.

Runs 10 test cases with deterministic mock LLM responses,
checks pass/fail criteria, and prints a structured report.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from schema import ReviewInput, VerdictOutput
from verdict_engine import run_pipeline
from sample_data import DATASETS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Test case definition
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    name: str
    description: str
    dataset_key: str
    # Criteria functions: each takes VerdictOutput and returns (passed: bool, reason: str)
    criteria: list[Callable[[VerdictOutput], tuple[bool, str]]] = field(default_factory=list)
    # Mock LLM response to return (bypasses real API)
    mock_response: Optional[str] = None


# ---------------------------------------------------------------------------
# Mock LLM responses — realistic, deterministic, schema-compliant
# ---------------------------------------------------------------------------

MOCK_RESPONSES: dict[str, str] = {

    "positive_stroller": json.dumps({
        "verdict_en": "An exceptional stroller that delivers on comfort, durability, and ease of use — a top pick for new parents.",
        "verdict_ar": "عربة أطفال رائعة توفر راحة استثنائية ومتانة عالية، وهي خيار مثالي للأمهات الجدد.",
        "pros": ["Smooth ride on all terrains", "Easy to fold", "Large sun canopy", "Comfortable for baby", "Durable build quality"],
        "cons": ["Premium price point"],
        "common_issues": [],
        "sentiment_score": 0.93,
        "confidence": 0.91,
        "should_buy": True,
    }),

    "negative_formula": json.dumps({
        "verdict_en": "This formula caused significant digestive issues for many babies and is not recommended.",
        "verdict_ar": "تسببت هذه الحليبة في مشاكل هضمية خطيرة لكثير من الأطفال، ولا يُنصح باستخدامها.",
        "pros": [],
        "cons": ["Causes gas and bloating", "Doesn't dissolve properly", "Off-putting smell", "Poor packaging seal"],
        "common_issues": ["Digestive problems", "Constipation", "Baby refusal"],
        "sentiment_score": 0.07,
        "confidence": 0.88,
        "should_buy": False,
    }),

    "mixed_car_seat": json.dumps({
        "verdict_en": "A safe and comfortable car seat with a convenient 360° rotation, though installation complexity and bulk are notable drawbacks.",
        "verdict_ar": "مقعد سيارة آمن ومريح مع ميزة الدوران 360 درجة، لكنه يحتاج وقتاً للتركيب وحجمه كبير نسبياً.",
        "pros": ["360° rotation", "Extended rear-facing", "Comfortable padding", "Feels very safe"],
        "cons": ["Difficult installation", "Bulky size", "Tricky harness adjustment", "Cup holder broke"],
        "common_issues": ["Installation confusion", "Size in small cars"],
        "sentiment_score": 0.62,
        "confidence": 0.74,
        "should_buy": True,
    }),

    "contradictory_monitor": json.dumps({
        "verdict_en": "Reviews are highly divided on this monitor — experiences vary dramatically across units, suggesting quality inconsistency.",
        "verdict_ar": "الآراء متضاربة جداً حول هذا الجهاز، مما يشير إلى تفاوت في جودة المنتج بين وحدة وأخرى.",
        "pros": ["Clear video for some users", "Good range reported by some", "Easy setup for some"],
        "cons": ["Grainy night vision for others", "Short battery life reported", "Signal drops", "Audio static"],
        "common_issues": ["Inconsistent quality across units", "Battery performance varies"],
        "sentiment_score": 0.48,
        "confidence": 0.28,
        "should_buy": None,
    }),

    "spam_noisy": json.dumps({
        "verdict_en": None,
        "verdict_ar": None,
        "pros": [],
        "cons": [],
        "common_issues": [],
        "sentiment_score": 0.5,
        "confidence": 0.1,
        "should_buy": None,
    }),

    "sparse_reviews": json.dumps({
        "verdict_en": None,
        "verdict_ar": None,
        "pros": ["Baby enjoyed the product"],
        "cons": ["Price may not be justified"],
        "common_issues": [],
        "sentiment_score": 0.65,
        "confidence": 0.25,
        "should_buy": None,
    }),

    "vague_reviews": json.dumps({
        "verdict_en": None,
        "verdict_ar": None,
        "pros": ["Fast delivery", "Nice packaging"],
        "cons": [],
        "common_issues": [],
        "sentiment_score": 0.6,
        "confidence": 0.18,
        "should_buy": None,
    }),

    "multilingual_diapers": json.dumps({
        "verdict_en": "Highly praised diapers with excellent leak protection, softness, and good value — a reliable choice for newborns.",
        "verdict_ar": "حفاضات تحظى بإشادة واسعة لحمايتها الممتازة من التسرب ونعومتها ومناسبتها لحساسية جلد الأطفال.",
        "pros": ["No leaks overnight", "Soft on skin", "No rashes", "Good absorbency", "Correct sizing"],
        "cons": [],
        "common_issues": [],
        "sentiment_score": 0.91,
        "confidence": 0.87,
        "should_buy": True,
    }),

    "sizing_issue_shoes": json.dumps({
        "verdict_en": "Cute and well-made shoes, but the sizing runs significantly small — order at least 2 sizes up.",
        "verdict_ar": "أحذية جميلة وذات جودة جيدة، لكن المقاسات أصغر بكثير من المعتاد — يُنصح بطلب مقاسين أكبر.",
        "pros": ["Cute design", "Soft material", "Good quality"],
        "cons": ["Sizing runs very small", "Inaccurate size chart"],
        "common_issues": ["Sizing 1.5–2 sizes too small"],
        "sentiment_score": 0.55,
        "confidence": 0.82,
        "should_buy": True,
    }),

    "safety_concern_toy": json.dumps({
        "verdict_en": "This toy poses serious safety risks for infants due to paint chipping and small parts — do not purchase for babies.",
        "verdict_ar": "هذه اللعبة تشكل خطراً حقيقياً على سلامة الرضع بسبب تقشر الطلاء وانفصال الأجزاء الصغيرة — لا يُنصح بشرائها للأطفال.",
        "pros": ["Colorful and visually appealing"],
        "cons": ["Paint chips off", "Small parts detach", "Chemical smell", "Not safe for mouthing babies"],
        "common_issues": ["Paint peeling", "Choking hazard", "Chemical odor"],
        "sentiment_score": 0.08,
        "confidence": 0.92,
        "should_buy": False,
    }),
}


# ---------------------------------------------------------------------------
# Criteria helpers
# ---------------------------------------------------------------------------

def sentiment_above(threshold: float):
    def check(out: VerdictOutput):
        passed = out.sentiment_score >= threshold
        return passed, f"sentiment_score {out.sentiment_score:.2f} {'≥' if passed else '<'} {threshold}"
    return check

def sentiment_below(threshold: float):
    def check(out: VerdictOutput):
        passed = out.sentiment_score <= threshold
        return passed, f"sentiment_score {out.sentiment_score:.2f} {'≤' if passed else '>'} {threshold}"
    return check

def confidence_above(threshold: float):
    def check(out: VerdictOutput):
        passed = out.confidence >= threshold
        return passed, f"confidence {out.confidence:.2f} {'≥' if passed else '<'} {threshold}"
    return check

def confidence_below(threshold: float):
    def check(out: VerdictOutput):
        passed = out.confidence <= threshold
        return passed, f"confidence {out.confidence:.2f} {'≤' if passed else '>'} {threshold}"
    return check

def should_buy_is(expected: Optional[bool]):
    def check(out: VerdictOutput):
        passed = out.should_buy == expected
        return passed, f"should_buy={out.should_buy} (expected {expected})"
    return check

def verdict_not_null():
    def check(out: VerdictOutput):
        passed = out.verdict_en is not None and out.verdict_ar is not None
        return passed, f"verdict_en={'set' if out.verdict_en else 'null'}, verdict_ar={'set' if out.verdict_ar else 'null'}"
    return check

def verdict_is_null():
    def check(out: VerdictOutput):
        passed = out.verdict_en is None and out.verdict_ar is None
        return passed, f"verdict_en={'null' if out.verdict_en is None else 'set'}, verdict_ar={'null' if out.verdict_ar is None else 'set'}"
    return check

def has_pros():
    def check(out: VerdictOutput):
        passed = len(out.pros) > 0
        return passed, f"pros count: {len(out.pros)}"
    return check

def has_cons():
    def check(out: VerdictOutput):
        passed = len(out.cons) > 0
        return passed, f"cons count: {len(out.cons)}"
    return check

def has_common_issues():
    def check(out: VerdictOutput):
        passed = len(out.common_issues) > 0
        return passed, f"common_issues count: {len(out.common_issues)}"
    return check

def arabic_verdict_present():
    def check(out: VerdictOutput):
        # Check for Arabic Unicode range
        has_arabic = out.verdict_ar is not None and any(
            "\u0600" <= c <= "\u06FF" for c in (out.verdict_ar or "")
        )
        return has_arabic, f"verdict_ar Arabic chars: {'yes' if has_arabic else 'no'}"
    return check


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

TEST_CASES: list[TestCase] = [
    TestCase(
        name="TC-01: Positive Reviews",
        description="Strongly positive stroller reviews → high sentiment, high confidence, should_buy=True",
        dataset_key="positive_stroller",
        mock_response=MOCK_RESPONSES["positive_stroller"],
        criteria=[
            sentiment_above(0.8),
            confidence_above(0.7),
            should_buy_is(True),
            verdict_not_null(),
            has_pros(),
            arabic_verdict_present(),
        ],
    ),
    TestCase(
        name="TC-02: Negative Reviews",
        description="Strongly negative formula reviews → low sentiment, should_buy=False",
        dataset_key="negative_formula",
        mock_response=MOCK_RESPONSES["negative_formula"],
        criteria=[
            sentiment_below(0.2),
            confidence_above(0.7),
            should_buy_is(False),
            verdict_not_null(),
            has_cons(),
            has_common_issues(),
        ],
    ),
    TestCase(
        name="TC-03: Mixed Sentiment",
        description="Mixed car seat reviews → mid sentiment, moderate confidence",
        dataset_key="mixed_car_seat",
        mock_response=MOCK_RESPONSES["mixed_car_seat"],
        criteria=[
            sentiment_above(0.4),
            sentiment_below(0.8),
            confidence_above(0.5),
            has_pros(),
            has_cons(),
        ],
    ),
    TestCase(
        name="TC-04: Contradictory Reviews",
        description="Directly contradictory monitor reviews → low confidence, should_buy=None",
        dataset_key="contradictory_monitor",
        mock_response=MOCK_RESPONSES["contradictory_monitor"],
        criteria=[
            confidence_below(0.4),
            should_buy_is(None),
            has_pros(),
            has_cons(),
        ],
    ),
    TestCase(
        name="TC-05: Spam / Noisy Input",
        description="Mostly spam reviews → very low confidence, null verdicts",
        dataset_key="spam_noisy",
        mock_response=MOCK_RESPONSES["spam_noisy"],
        criteria=[
            confidence_below(0.3),
            verdict_is_null(),
            should_buy_is(None),
        ],
    ),
    TestCase(
        name="TC-06: Very Few Reviews",
        description="Only 2 reviews → low confidence, null verdict enforced by pipeline",
        dataset_key="sparse_reviews",
        mock_response=MOCK_RESPONSES["sparse_reviews"],
        criteria=[
            confidence_below(0.35),
            verdict_is_null(),
            should_buy_is(None),
        ],
    ),
    TestCase(
        name="TC-07: Vague / Missing Info",
        description="Reviews mention delivery/packaging only → low confidence, null verdict",
        dataset_key="vague_reviews",
        mock_response=MOCK_RESPONSES["vague_reviews"],
        criteria=[
            confidence_below(0.3),
            verdict_is_null(),
            should_buy_is(None),
        ],
    ),
    TestCase(
        name="TC-08: Multilingual (Arabic + English)",
        description="Mixed Arabic/English diaper reviews → Arabic verdict present, high sentiment",
        dataset_key="multilingual_diapers",
        mock_response=MOCK_RESPONSES["multilingual_diapers"],
        criteria=[
            sentiment_above(0.8),
            confidence_above(0.7),
            should_buy_is(True),
            arabic_verdict_present(),
            verdict_not_null(),
        ],
    ),
    TestCase(
        name="TC-09: Single Dominant Issue",
        description="Sizing issue shoes → common_issues populated, moderate sentiment",
        dataset_key="sizing_issue_shoes",
        mock_response=MOCK_RESPONSES["sizing_issue_shoes"],
        criteria=[
            has_common_issues(),
            has_pros(),
            has_cons(),
            confidence_above(0.6),
        ],
    ),
    TestCase(
        name="TC-10: Safety Concern",
        description="Safety-critical toy reviews → very low sentiment, should_buy=False, common_issues present",
        dataset_key="safety_concern_toy",
        mock_response=MOCK_RESPONSES["safety_concern_toy"],
        criteria=[
            sentiment_below(0.2),
            confidence_above(0.7),
            should_buy_is(False),
            has_common_issues(),
            verdict_not_null(),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class CriterionResult:
    passed: bool
    reason: str

@dataclass
class TestResult:
    test_case: TestCase
    output: Optional[VerdictOutput]
    error: Optional[str]
    criterion_results: list[CriterionResult]

    @property
    def passed(self) -> bool:
        return self.error is None and all(c.passed for c in self.criterion_results)


def run_test_case(tc: TestCase) -> TestResult:
    """Execute a single test case and return its result."""
    dataset = DATASETS[tc.dataset_key]
    input_data = ReviewInput(
        product_name=dataset["product"],
        reviews=dataset["reviews"],
    )

    # Build mock function if a mock response is provided
    mock_fn = None
    if tc.mock_response is not None:
        mock_fn = lambda _product, _reviews: tc.mock_response  # noqa: E731

    try:
        output = run_pipeline(input_data, mock_llm_fn=mock_fn)
    except Exception as e:
        return TestResult(
            test_case=tc,
            output=None,
            error=str(e),
            criterion_results=[],
        )

    criterion_results = [
        CriterionResult(*criterion(output))
        for criterion in tc.criteria
    ]

    return TestResult(
        test_case=tc,
        output=output,
        error=None,
        criterion_results=criterion_results,
    )


def run_evaluation(verbose: bool = True) -> list[TestResult]:
    """Run all test cases and print a formatted report."""
    results: list[TestResult] = []

    print("\n" + "=" * 70)
    print("  MOMS VERDICT ENGINE — EVALUATION REPORT")
    print("=" * 70)

    for tc in TEST_CASES:
        result = run_test_case(tc)
        results.append(result)

        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status}  {tc.name}")
        print(f"       {tc.description}")

        if result.error:
            print(f"       ERROR: {result.error}")
        elif verbose and result.output:
            out = result.output
            print(f"       sentiment={out.sentiment_score:.2f}  confidence={out.confidence:.2f}  should_buy={out.should_buy}")
            print(f"       verdict_en: {out.verdict_en or '(null)'}")
            print(f"       verdict_ar: {out.verdict_ar or '(null)'}")
            print(f"       pros({len(out.pros)}) cons({len(out.cons)}) issues({len(out.common_issues)})")

        for cr in result.criterion_results:
            icon = "  ✓" if cr.passed else "  ✗"
            print(f"       {icon} {cr.reason}")

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("\n" + "=" * 70)
    print(f"  RESULTS: {passed}/{total} tests passed")
    print("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run_evaluation()
