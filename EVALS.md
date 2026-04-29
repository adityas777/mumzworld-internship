# Evaluation Report — Moms Verdict Engine

All 10 test cases use deterministic mock LLM responses to validate pipeline logic independently of API availability. Results below reflect the latest run.

**Result: 10 / 10 passed**

---

## How the Eval System Works

Each test case defines:
- A named review dataset from `sample_data.py`
- A mock LLM response (realistic, schema-compliant JSON)
- A set of typed criteria functions that inspect the `VerdictOutput`

The pipeline runs in full (preprocessing → TF-IDF retrieval → mock LLM → Pydantic validation) for every case. Only the HTTP call is mocked — everything else is real.

Run it yourself:
```bash
python main.py --eval
```

---

## Test Cases

### TC-01: Positive Reviews
**Dataset:** Bugaboo Fox 3 Stroller (12 reviews, uniformly positive)
**Goal:** High sentiment, high confidence, clear buy recommendation, bilingual verdict.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| sentiment_score | ≥ 0.80 | 0.93 | ✅ |
| confidence | ≥ 0.70 | 0.91 | ✅ |
| should_buy | True | True | ✅ |
| verdict_en | not null | set | ✅ |
| verdict_ar | contains Arabic | yes | ✅ |
| pros | count > 0 | 5 | ✅ |

**verdict_en:** "An exceptional stroller that delivers on comfort, durability, and ease of use — a top pick for new parents."
**verdict_ar:** "عربة أطفال رائعة توفر راحة استثنائية ومتانة عالية، وهي خيار مثالي للأمهات الجدد."

---

### TC-02: Negative Reviews
**Dataset:** Generic Baby Formula Brand X (12 reviews, uniformly negative)
**Goal:** Low sentiment, high confidence, clear do-not-buy, cons and issues populated.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| sentiment_score | ≤ 0.20 | 0.07 | ✅ |
| confidence | ≥ 0.70 | 0.88 | ✅ |
| should_buy | False | False | ✅ |
| verdict_en | not null | set | ✅ |
| cons | count > 0 | 4 | ✅ |
| common_issues | count > 0 | 3 | ✅ |

**verdict_en:** "This formula caused significant digestive issues for many babies and is not recommended."
**verdict_ar:** "تسببت هذه الحليبة في مشاكل هضمية خطيرة لكثير من الأطفال، ولا يُنصح باستخدامها."

---

### TC-03: Mixed Sentiment
**Dataset:** Joie i-Spin 360 Car Seat (12 reviews, split positive/negative)
**Goal:** Mid-range sentiment, moderate confidence, both pros and cons present.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| sentiment_score | 0.40 – 0.80 | 0.62 | ✅ |
| confidence | ≥ 0.50 | 0.74 | ✅ |
| pros | count > 0 | 4 | ✅ |
| cons | count > 0 | 4 | ✅ |

**verdict_en:** "A safe and comfortable car seat with a convenient 360° rotation, though installation complexity and bulk are notable drawbacks."

---

### TC-04: Contradictory Reviews
**Dataset:** Infant Optics DXR-8 Baby Monitor (12 reviews, directly contradictory on every dimension)
**Goal:** Low confidence, should_buy forced to null, both sides represented.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| confidence | ≤ 0.40 | 0.28 | ✅ |
| should_buy | None | None | ✅ |
| pros | count > 0 | 3 | ✅ |
| cons | count > 0 | 4 | ✅ |

**verdict_en:** "Reviews are highly divided on this monitor — experiences vary dramatically across units, suggesting quality inconsistency."

**Key behavior:** The Pydantic `model_validator` enforces `should_buy = None` when `confidence < 0.4`, regardless of what the LLM returns.

---

### TC-05: Spam / Noisy Input
**Dataset:** Random Baby Toy (15 reviews: all-caps spam, single characters, URLs, paid review disclosures)
**Goal:** Very low confidence, null verdicts, no hallucinated pros/cons.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| confidence | ≤ 0.30 | 0.10 | ✅ |
| verdict_en | null | null | ✅ |
| verdict_ar | null | null | ✅ |
| should_buy | None | None | ✅ |

**Key behavior:** Preprocessing strips URLs and collapses noise. The LLM is instructed not to invent facts — with no signal, it returns nulls and minimal confidence.

---

### TC-06: Very Few Reviews
**Dataset:** Organic Teething Biscuits (2 reviews only)
**Goal:** Pipeline enforces null verdict and confidence ≤ 0.30 regardless of LLM output.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| confidence | ≤ 0.35 | 0.25 | ✅ |
| verdict_en | null | null | ✅ |
| verdict_ar | null | null | ✅ |
| should_buy | None | None | ✅ |

**Key behavior:** `MIN_REVIEWS_FOR_VERDICT = 3` check in `run_pipeline` overrides LLM output — confidence is capped at 0.30 and verdict fields are set to null in code, not by the LLM.

---

### TC-07: Vague / Missing Product Info
**Dataset:** Unknown Baby Product (8 reviews mentioning only delivery speed and packaging)
**Goal:** No product-specific insights extractable → low confidence, null verdict.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| confidence | ≤ 0.30 | 0.18 | ✅ |
| verdict_en | null | null | ✅ |
| verdict_ar | null | null | ✅ |
| should_buy | None | None | ✅ |

---

### TC-08: Multilingual (Arabic + English)
**Dataset:** Pampers Premium Care Diapers (12 reviews, ~50% Arabic, ~50% English)
**Goal:** Arabic verdict is natural Arabic (not a translation), high sentiment, bilingual output.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| sentiment_score | ≥ 0.80 | 0.91 | ✅ |
| confidence | ≥ 0.70 | 0.87 | ✅ |
| should_buy | True | True | ✅ |
| verdict_ar | contains Arabic chars | yes | ✅ |
| verdict_en | not null | set | ✅ |

**verdict_en:** "Highly praised diapers with excellent leak protection, softness, and good value — a reliable choice for newborns."
**verdict_ar:** "حفاضات تحظى بإشادة واسعة لحمايتها الممتازة من التسرب ونعومتها ومناسبتها لحساسية جلد الأطفال."

---

### TC-09: Single Dominant Issue
**Dataset:** Baby Stride First Walker Shoes (10 reviews, all praising quality but flagging sizing)
**Goal:** common_issues captures the sizing problem, moderate sentiment, pros and cons both present.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| common_issues | count > 0 | 1 | ✅ |
| pros | count > 0 | 3 | ✅ |
| cons | count > 0 | 2 | ✅ |
| confidence | ≥ 0.60 | 0.82 | ✅ |

**verdict_en:** "Cute and well-made shoes, but the sizing runs significantly small — order at least 2 sizes up."

---

### TC-10: Safety Concern
**Dataset:** Colorful Stacking Rings Toy (10 reviews flagging paint chipping, choking hazard, chemical smell)
**Goal:** Very low sentiment, high confidence, should_buy=False, safety issues in common_issues.

| Criterion | Expected | Actual | Result |
|---|---|---|---|
| sentiment_score | ≤ 0.20 | 0.08 | ✅ |
| confidence | ≥ 0.70 | 0.92 | ✅ |
| should_buy | False | False | ✅ |
| common_issues | count > 0 | 3 | ✅ |
| verdict_en | not null | set | ✅ |

**verdict_en:** "This toy poses serious safety risks for infants due to paint chipping and small parts — do not purchase for babies."
**verdict_ar:** "هذه اللعبة تشكل خطراً حقيقياً على سلامة الرضع بسبب تقشر الطلاء وانفصال الأجزاء الصغيرة — لا يُنصح بشرائها للأطفال."

---

## Coverage Summary

| Category | TC | Pass |
|---|---|---|
| Positive signal | TC-01 | ✅ |
| Negative signal | TC-02 | ✅ |
| Mixed sentiment | TC-03 | ✅ |
| Contradictory reviews | TC-04 | ✅ |
| Spam / noise | TC-05 | ✅ |
| Sparse data | TC-06 | ✅ |
| Vague / no product info | TC-07 | ✅ |
| Multilingual (AR + EN) | TC-08 | ✅ |
| Single dominant issue | TC-09 | ✅ |
| Safety concern | TC-10 | ✅ |

---

## What Is and Isn't Tested

**Tested by the eval suite:**
- Full pipeline execution (preprocessing, TF-IDF retrieval, JSON parsing, Pydantic validation)
- Confidence enforcement rules (sparse reviews, contradictory signals)
- Null field logic
- Arabic character presence in verdict_ar
- Deduplication and list normalization in schema validators

**Not tested by the eval suite (requires live API):**
- Actual LLM output quality
- Arabic naturalness vs. direct translation
- Retry behavior on malformed LLM responses
- Rate limiting and timeout handling
- Token limit edge cases with 100–200 long reviews
