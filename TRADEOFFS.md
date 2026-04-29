# Tradeoffs — Moms Verdict Engine

Engineering decisions made during design and implementation, with reasoning and known consequences.

---

## 1. TF-IDF Retrieval vs. Embedding-Based Retrieval (FAISS)

**Decision:** Use TF-IDF scoring (sklearn) to select the top-40 most informative reviews when input exceeds that limit.

**Why:**
- Zero external dependencies — no vector DB, no embedding API call, no index to maintain
- Fast enough for 100–200 reviews (< 50ms)
- Sufficient for deduplication and noise reduction at this scale

**What you give up:**
- Semantic similarity — TF-IDF misses paraphrases ("doesn't leak" vs. "no leakage")
- Cross-lingual retrieval — Arabic and English reviews are scored independently by token frequency, not meaning
- At 500+ reviews, embedding-based retrieval would surface more representative samples

**When to upgrade:** If review volume exceeds ~500 per product, or if Arabic review quality noticeably degrades, swap in a multilingual embedding model (e.g., `intfloat/multilingual-e5-large`) with FAISS.

---

## 2. Low LLM Temperature (0.2)

**Decision:** Set `temperature=0.2` for all LLM calls.

**Why:**
- Structured JSON output is more reliable at low temperature
- Reduces hallucination risk — the model is less likely to invent product features
- Consistent scores across retries

**What you give up:**
- Arabic phrasing creativity — natural Arabic idioms require some variation; at 0.2 the output can feel slightly formal
- Edge case handling — occasionally the model produces overly conservative verdicts on ambiguous inputs

**Mitigation:** The system prompt explicitly instructs the model to write natural Arabic, not a direct translation. This partially compensates for the low temperature.

---

## 3. Mock LLM in Eval Suite vs. Live API Testing

**Decision:** All 10 eval test cases use deterministic mock responses instead of real API calls.

**Why:**
- Evals run instantly, offline, and for free
- Results are reproducible — no flakiness from model updates or rate limits
- Tests pipeline logic (preprocessing, validation, retry, null enforcement) independently of LLM quality

**What you give up:**
- No coverage of actual LLM output quality
- Arabic naturalness is not evaluated
- Retry behavior on malformed JSON is not exercised in the suite

**Mitigation:** The mock responses are realistic and schema-compliant, written to match what the real model produces. Live API testing is straightforward via `main.py --reviews ...`.

---

## 4. Retry on Validation Failure (3 attempts, 1s delay)

**Decision:** Retry the full LLM call up to 3 times if Pydantic validation or JSON parsing fails.

**Why:**
- LLMs occasionally wrap JSON in markdown fences or add trailing commentary
- `extract_json()` handles most of these cases, but retrying catches the rest
- 3 attempts is a reasonable ceiling before raising an explicit error

**What you give up:**
- Latency — worst case adds ~3 seconds to a failed request
- No exponential backoff — a fixed 1s delay is fine for occasional failures but not for sustained rate limiting

**When to upgrade:** Add exponential backoff with jitter (`min(2^attempt, 30)` seconds) for production use.

---

## 5. Groq + Llama 3.3 70B vs. GPT-4o / Gemini

**Decision:** Default to `llama-3.3-70b-versatile` via Groq API.

**Why:**
- Groq inference is significantly faster than OpenAI or OpenRouter (typically < 2s for this payload)
- Llama 3.3 70B has strong multilingual capability including Arabic
- Free tier is generous for prototyping

**What you give up:**
- GPT-4o produces more natural Arabic and handles ambiguous instructions better
- Groq has stricter rate limits than OpenRouter at scale
- Model availability on Groq can change — `llama-3.3-70b-versatile` may be deprecated

**Mitigation:** `DEFAULT_MODEL` is overridable via `VERDICT_MODEL` env var or `--model` CLI flag. Switching to `openai/gpt-4o-mini` via OpenRouter is a one-line change.

---

## 6. Pydantic v2 Model Validators for Business Rules

**Decision:** Enforce `should_buy = None` when `confidence < 0.2` inside a Pydantic `model_validator`, not in application logic.

**Why:**
- Business rules live at the schema boundary — they apply regardless of how the pipeline is called
- Prevents invalid states from propagating if the pipeline is used as a library
- Makes the constraint visible and testable at the schema level

**What you give up:**
- Slightly surprising behavior — callers who set `should_buy=True` with `confidence=0.1` will silently get `None` back
- The threshold (0.2) is hardcoded in the schema; changing it requires a schema update

---

## 7. Single-File Pipeline vs. Microservices

**Decision:** The entire pipeline runs in a single Python process (`verdict_engine.py`).

**Why:**
- Appropriate for a prototype — no operational overhead
- Easy to run locally, easy to debug
- Streamlit UI and CLI share the same code path

**What you give up:**
- No horizontal scaling — one slow LLM call blocks the process
- No async support — concurrent review batches would require `asyncio` or a task queue
- No caching — identical review sets hit the LLM every time

**When to upgrade:** For production, wrap `run_pipeline` in a FastAPI endpoint, add Redis caching keyed on a hash of the review set, and use `asyncio` + `httpx` for concurrent LLM calls.

---

## 8. Hardcoded `MIN_REVIEWS_FOR_VERDICT = 3`

**Decision:** Fewer than 3 substantive reviews after preprocessing forces null verdicts and confidence ≤ 0.30 in code, overriding whatever the LLM returns.

**Why:**
- Prevents overconfident verdicts from 1–2 reviews
- The threshold is enforced deterministically — not left to LLM judgment

**What you give up:**
- A single highly detailed review might genuinely warrant a verdict; the rule ignores that
- The threshold is arbitrary — 3 is a reasonable floor but not empirically derived

---

## Known Failure Modes

| Failure | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM returns markdown-wrapped JSON | Low (handled by `extract_json`) | Retry triggered | Already handled |
| LLM ignores null rules for sparse data | Low (overridden in pipeline) | None | Pipeline enforces nulls in code |
| Arabic verdict is a direct translation | Medium | Reduced naturalness | System prompt instructs against it; GPT-4o mitigates |
| Very long individual reviews hit token limits | Low at 40 reviews | Truncated context | Add per-review character cap if needed |
| Groq rate limit on burst traffic | Medium | 429 error, no retry | Add exponential backoff |
| Sophisticated spam passes preprocessing | Low-Medium | Inflated confidence | Add length/entropy filter to preprocessing |
