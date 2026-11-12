# Prompts

Reusable LLM prompt templates for working with the cleaned paper text produced
by the pipeline (`transformed/<id>.txt` + `<id>.stats.json`).

**Placeholders** — substitute before sending:
`{title}`, `{abstract}`, `{text}` (cleaned body), `{stats}` (the stats JSON row).
`[FORMULA]` markers in `{text}` are intentional; leave them as-is.

Default model: `claude-opus-4-8` (swap per task — a smaller model like
`claude-haiku-5-5` is fine for classification/filtering).

---

## System prompt (shared)

```
You are a research-paper analysis assistant for PaperLM. You work from
GROBID-extracted, cleaned text, not the original PDF. Notes on the input:
- Math has been replaced by a literal [FORMULA] marker. Do not try to recover
  equations; treat [FORMULA] as "an equation was here."
- Inline citations and the references/acknowledgements/funding/appendix
  sections have been stripped, so you cannot cite sources or list references.
- Tables appear as captions only; their numeric grids are gone.
Ground every claim in the provided text. If the text does not support an
answer, say so rather than guessing.
```

---

## Summarize

```
Summarize this paper for a technical reader who has not read it.

Return:
1. One-sentence TL;DR.
2. Problem & motivation (2-3 sentences).
3. Approach / method (3-5 sentences).
4. Key results, with concrete numbers where the text gives them.
5. Limitations the authors state (omit if none are stated).

Title: {title}
Abstract: {abstract}

Body:
{text}
```

---

## Extract structured metadata

```
From the paper below, extract the following as strict JSON. Use null for any
field the text does not support — do not infer or fabricate.

{
  "problem": string,
  "contributions": string[],
  "methods": string[],
  "datasets": string[],
  "metrics": string[],
  "tasks": string[],
  "code_or_data_released": boolean | null
}

Title: {title}
Abstract: {abstract}

Body:
{text}
```

---

## Q&A over one paper

```
Answer the question using only the paper below. Quote the relevant passage,
then give the answer. If the paper does not address the question, reply exactly:
"Not covered in this paper."

Question: {question}

Title: {title}
Body:
{text}
```

---

## Topic / category classification

```
Classify this paper into the single best-fitting arXiv CS category (e.g.
cs.CL, cs.CV, cs.LG, cs.AI, cs.CR). Return JSON:
{ "category": string, "confidence": 0.0-1.0, "reason": string }

Title: {title}
Abstract: {abstract}
```

---

## Quality / pretraining-fit filter

Pairs with the stats row to decide whether a transformed paper is clean enough
to keep for pretraining.

```
Decide whether this extracted text is clean enough to include in a
pretraining corpus. Extraction stats (quality signals) are provided; low
alpha_ratio, high repeated_line_fraction, or a missing title/abstract suggest
a bad extraction.

Return JSON:
{ "keep": boolean, "reason": string, "issues": string[] }
Issues may include: garbled_text, truncated, ocr_noise, wrong_language,
mostly_formulas, boilerplate.

Stats: {stats}

Text (first portion):
{text}
```
