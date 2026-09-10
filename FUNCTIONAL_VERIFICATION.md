# ✅ Functional Verification Report — Document Analysis Pipeline

**Date:** 2026-09-10
**Test document:** `Sample_Freelance_Agreement_TEST.pdf` (6-page digital PDF, 9,414 chars) — a deliberately abusive freelance contract used as ground truth.
**Method:** drove the real production pipeline (extraction → chunk → embed → ChromaDB ingest → 6-agent LangGraph analysis → grounded Q&A) against the **live free-tier Gemini key**, measuring per-stage latency, accuracy vs. known clauses, and Gemini quota/rate-limit behavior.

---

## 1. Can it take, read, audit, find clauses, and give solutions? — YES ✅

| Capability | Result |
| :--- | :--- |
| **Document intake & OCR** | PyMuPDF extraction OK — 6 pages, digital text detected (no OCR needed). Multi-format path (PDF/scan/image/DOCX/txt) intact. |
| **Metadata / parties** | ✅ Correct: Client "Rajat Mehra (RMTech Solutions)", Provider "Anika Sharma", date "March 15, 2024", jurisdiction "India", type "Freelance Consulting Agreement". |
| **9-clause checklist** | ✅ 8/9 present detected correctly; `renewal_clauses` correctly flagged absent. (Minor: `indemnification` marked present where §6 is liability-shaped — the compliance agent then re-flags it, so no downstream miss.) |
| **Risk detection** | ✅ 8 risks, all real red flags caught: 5%/week compounding interest, unlimited liability on provider, IP assignment of out-of-scope work, court-order-defying confidentiality, one-sided termination, uncompensated scope creep — each HIGH/MEDIUM with a suggested revision **and** a negotiation tip. |
| **Statutory compliance** | ✅ 7 issues incl. usurious interest, illegal confidentiality (cannot contract out of court disclosure), IP overreach, missing dispute-resolution. |
| **Solutions / redlines** | ✅ Every risk carries a concrete `suggested_revision` + `negotiation_tip`; a 4.7 KB executive summary is generated. |
| **Grounded Q&A** | ✅ 3/3 accurate with chunk citations, including a **correct anti-hallucination refusal** when asked about a (non-existent) arbitration clause. |

**Accuracy: high** — no hallucinated clauses, no missed red flags, citations grounded to source chunks.

---

## 2. Timing (end-to-end, real Gemini calls)

| Stage | Latency |
| :--- | ---: |
| Text extraction | 0.76 s |
| Embedding + ChromaDB ingest | ~2.5 s |
| Agent 1 — Parsing | 1.5 s |
| Agent 2 — Clause extraction | 5.0 s |
| Agent 3 — Risk assessment | 7.3 s |
| Agent — Negotiation advisor | 5.5 s |
| Agent 4 — Compliance | 8.5 s |
| Agent 5 — Summary synthesis | 4.5 s |
| Q&A (per question) | 2.7–3.2 s |
| **Total wall time** | **~58 s** |

Full 6-agent analysis ≈ 42 s; consistent with the "under 60 s" design target.

---

## 3. Free-tier Gemini rate limits — FOUND & FIXED ✅

**Diagnosis.** The configured primary model `gemini-2.5-flash` is **quota-exhausted on this free-tier key** — a direct probe returned `429 You exceeded your current quota` on every call. Because the app tried it first on *every* agent call, the first run logged **8 rate-limit hits** and only completed by cascading to a healthy fallback (`gemini-3.1-flash-lite`).

Live model-health probe:

| Model | Status |
| :--- | :--- |
| `gemini-2.5-flash`, `gemini-3.5-flash` | ❌ 429 quota exhausted |
| `gemini-2.5-flash-lite` | ❌ 404 (not available for this key) |
| `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`, `gemini-flash-latest` | ✅ healthy & fast |

**Fix applied.** Made the primary model and both cascade lists (LLM + Vision OCR) lead with confirmed-healthy **lite** buckets (higher free-tier RPM), demoting the exhausted `*-flash` buckets to deep fallbacks:
- `backend/app/core/config.py` — default `GEMINI_MODEL` → `gemini-flash-lite-latest`
- `backend/app/services/llm_provider.py` — reordered `GEMINI_CASCADE_MODELS`
- `backend/app/services/pdf_extractor.py` — reordered `VISION_CASCADE_MODELS`

**Measured impact (same document, same key, before → after):**

| Metric | Before | After |
| :--- | ---: | ---: |
| Gemini 429 rate-limit hits | **8** | **0** |
| Wasted fallover round-trips | 8 | 0 |
| Parsing-agent latency | 5.3 s | 1.5 s |
| Total wall time | 69.3 s | 58.3 s |
| Daily quota used (this run) | — | 0.6 % of 1,500 |

Accuracy was **unchanged** (in fact 8 risks / 7 compliance issues vs 7/6) — the lite models were already carrying the successful load before the fix.

### Note on remaining quota pressure
The free-tier key still shares a daily cap (1,500 requests/day per bucket). One full analysis ≈ 6 calls, so ~250 analyses/day per healthy bucket, multiplied across the independent lite buckets in the cascade. The `/admin/ai-usage` endpoint reports live consumption and warns at 80%. If sustained volume exhausts the lite buckets too, the remaining mitigations are: (a) enable the in-memory dedup cache for repeat analyses, (b) reduce calls per analysis (the negotiation step could be merged into risk), or (c) add a second free-tier key and round-robin. No paid tier is required for portfolio/demo load.

**Owner action:** update the deployed Hugging Face Space secret `GEMINI_MODEL=gemini-flash-lite-latest` (local `.env` already updated) so production uses the healthy primary.
