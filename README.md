# Moms Verdict Engine

**Track: A**

---

## What I Built

The Moms Verdict Engine is an AI-powered review intelligence system built for Mumzworld. It takes 100–200 raw product reviews — noisy, repetitive, multilingual (English + Arabic) — and converts them into a single structured JSON verdict that tells a shopper exactly what they need to know: what's good, what's bad, recurring issues, a sentiment score, a confidence score, and a clear buy recommendation. The system is designed for e-commerce teams and shoppers who don't have time to read 150 reviews. It handles contradictory signals by lowering confidence rather than guessing, returns null fields when data is insufficient, and always outputs both an English and a natural Arabic verdict. The pipeline runs in five steps: preprocess → TF-IDF retrieval → LLM call (Groq / Llama 3.3 70B) → Pydantic validation → retry on failure.

---

## Prototype Access

**GitHub:** https://github.com/adityas777/mumzworld-internship

---

## Walkthrough

> 📹 **[Insert your 3-minute Loom link here]**
>
> The walkthrough covers: running the eval suite, analyzing a live product with the CLI, and a demo of the Streamlit UI with the multilingual diaper dataset.

---

## Setup Instructions

### Requirements
- Python 3.11+
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone the repo

```bash
git clone https://github.com/adityas777/mumzworld-internship.git
cd mumzworld-internship/project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
# macOS / Linux
export GROQ_API_KEY=your_key_here

# Windows CMD
set GROQ_API_KEY=your_key_here

# Windows PowerShell
$env:GROQ_API_KEY="your_key_here"
```

### 4. Run the eval suite (no API key needed)

```bash
python main.py --eval
```

Expected output: `RESULTS: 10/10 tests passed`

### 5. Analyze reviews via CLI

```bash
python main.py --reviews "Great stroller!" "Easy to fold" "Baby loves it" "Worth every penny" --product "Bugaboo Fox 3"
```

Get raw JSON:
```bash
python main.py --reviews "Broke after one week" "Terrible quality" "Do not buy" --json-out
```

### 6. Launch the Streamlit UI

```bash
python -m streamlit run app.py
```

Opens at `http://localhost:8501`. Pick a dataset from the sidebar dropdown and click Analyze.

---

## Output Schema

```json
{
  "verdict_en": "One-sentence English verdict or null",
  "verdict_ar": "حكم بالعربية أو null",
  "pros": ["list of positives"],
  "cons": ["list of negatives"],
  "common_issues": ["recurring problems"],
  "sentiment_score": 0.0,
  "confidence": 0.0,
  "should_buy": true
}
```

`should_buy` is `null` when confidence is too low or reviews are too contradictory. `verdict_en` and `verdict_ar` are `null` when fewer than 3 substantive reviews exist.

---

## Project Structure

```
project/
├── main.py           # CLI entry point
├── verdict_engine.py # 5-step pipeline
├── schema.py         # Pydantic I/O models
├── evaluator.py      # 10-case eval suite
├── sample_data.py    # 10 review datasets
├── app.py            # Streamlit UI
├── requirements.txt
├── EVALS.md          # Full eval report with pass/fail tables
└── TRADEOFFS.md      # Engineering decisions and failure modes
```

---

## Deliverables

- `EVALS.md` — 10 test cases with expected vs. actual output, criteria tables, and coverage notes
- `TRADEOFFS.md` — 8 engineering decisions with reasoning, tradeoffs, and upgrade paths

---

## AI Usage Note

Built with **Kiro AI** (IDE agent) for scaffolding, implementation, and iteration across all files. Used **Groq API** with `llama-3.3-70b-versatile` as the inference backend for structured JSON generation and bilingual verdict output. **Claude** (via Kiro) was used for prompt design, schema validation logic, and eval case authoring. No code was copy-pasted from external sources — all logic was written and verified in-session.
