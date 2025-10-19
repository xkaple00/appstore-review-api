# app/nlp/recommender_llm.py
"""
Generates actionable recommendations for the development team
USING ONLY negative user reviews (no keywords).

- Works with small local chat/instruct models from Hugging Face.
- Uses tokenizer chat templates when available.
- Forces JSON-array output and robustly extracts it.
- If JSON fails, retries with a bullet-list prompt and converts to JSON.

Env:
  RECS_LLM_MODEL (default: "Qwen/Qwen2.5-1.5B-Instruct")
"""

from __future__ import annotations

import os
import json
import threading
from typing import List

from transformers import pipeline


# ---------------------------- Pipeline Singleton ---------------------------- #

_LOCK = threading.Lock()
_PIPE = None  # transformers.Pipeline


def _get_generator():
    """
    Build a text-generation pipeline once.
    Default model is a small, instruction-tuned chat model that behaves better
    than TinyLlama for following formatting constraints.
    """
    global _PIPE
    with _LOCK:
        if _PIPE is None:
            model = os.getenv("RECS_LLM_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
            # Keep init minimal for broad compatibility (CPU-friendly).
            _PIPE = pipeline(
                task="text-generation",
                model=model,
                tokenizer=model,
            )
    return _PIPE


# ------------------------------ Prompt Builders ----------------------------- #

_SYS = (
    "ROLE: Senior product analyst for a mobile app.\n"
    "TASK: Read the NEGATIVE_REVIEWS and produce 3–5 ACTIONABLE recommendations "
    "for the DEVELOPMENT TEAM.\n"
    "STYLE: Imperative, concise (≤ 18 words each), specific. Do NOT quote or repeat user text.\n"
    "OUTPUT: STRICTLY a JSON array of strings. No extra text, no markdown."
)

_JSON_PROMPT = """{system}

NEGATIVE_REVIEWS (for analysis only—DO NOT QUOTE OR REPEAT):
{reviews}

Now output ONLY a JSON array of 3–5 short, actionable recommendations.
Example:
["Clarify trial cancellation flow in-app","Fix unexpected charges during onboarding","Reduce crashes on login"]
"""

# Fallback prompt if JSON extraction fails once:
_BULLET_PROMPT = """{system}

NEGATIVE_REVIEWS (for analysis only):
{reviews}

Output EXACTLY 5 short, actionable recommendations for the dev team,
each on its own line starting with "- ". No other text.
Example:
- Improve cancellation clarity before trial ends
- Prevent unexpected charges during onboarding
- Reduce login crashes on older devices
- Optimize performance on slow networks
- Streamline account recovery and support escalation
"""


def _build_prompt_from_reviews(pipe, reviews_block: str, mode: str = "json") -> str:
    """
    Use chat template when available; otherwise fall back to plain strings.
    """
    system = _SYS
    if mode == "json":
        user = _JSON_PROMPT.format(system=system, reviews=reviews_block)
    else:
        user = _BULLET_PROMPT.format(system=system, reviews=reviews_block)

    tok = getattr(pipe, "tokenizer", None)
    if tok is not None and hasattr(tok, "apply_chat_template"):
        # Format using the model's chat template for better adherence.
        messages = [
            {"role": "system", "content": _SYS},
            {"role": "user", "content": user},
        ]
        try:
            return tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            # Fall back to plain prompt on template errors
            return f"{_SYS}\n\n{user}"
    else:
        return f"{_SYS}\n\n{user}"


# -------------------------- Output Parsing Utilities ------------------------ #

def _extract_json_array(text: str) -> str | None:
    """
    Extract the first balanced JSON array from text (handles nested brackets and strings).
    """
    start = text.find("[")
    if start == -1:
        return None

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for s in items:
        t = str(s).strip()
        key = t.lower().rstrip(".")
        if key and key not in seen:
            seen.add(key)
            out.append(t.rstrip("."))
    return out


def _format_reviews_block(negative_texts: List[str], per_item_chars: int = 240, max_items: int = 10) -> str:
    """
    Make a compact, representative block of review bullets:
    - Head + tail to diversify content when lots of reviews exist.
    """
    texts = [t.strip() for t in negative_texts if t and t.strip()]
    if not texts:
        return "(none)"
    sample = texts[:max_items] if len(texts) <= max_items else texts[: max_items // 2] + texts[-(max_items // 2):]
    return "\n- " + "\n- ".join(x[:per_item_chars] for x in sample)


# ---------------------------- Public Entry Point ---------------------------- #

def generate_recommendations_from_reviews(negative_texts: List[str]) -> List[str]:
    """
    Main entry point:
      Input: list of negative review texts
      Output: 3–5 concise, imperative recommendations as a Python list[str]
    """
    # Guard: no negatives
    if not negative_texts:
        return ["No sufficiently negative feedback found to generate recommendations."]

    pipe = _get_generator()
    reviews_block = _format_reviews_block(negative_texts)

    # First attempt: strict JSON array
    prompt = _build_prompt_from_reviews(pipe, reviews_block, mode="json")
    out = pipe(
        prompt,
        max_new_tokens=220,
        do_sample=False,            # deterministic
        temperature=0.1,            # keep outputs focused if sampling is enabled elsewhere
        top_p=0.9,
        num_return_sequences=1,
        return_full_text=False,     # don't echo the prompt
    )[0]["generated_text"]

    blob = _extract_json_array(out)
    if blob:
        try:
            arr = json.loads(blob)
            if isinstance(arr, list):
                arr = [str(x) for x in arr]
                arr = _dedupe_keep_order(arr)[:5]
                if 3 <= len(arr) <= 5:
                    return arr
        except Exception:
            pass

    # Second attempt: bullet list, then convert to JSON
    prompt2 = _build_prompt_from_reviews(pipe, reviews_block, mode="bullets")
    out2 = pipe(
        prompt2,
        max_new_tokens=200,
        do_sample=False,
        temperature=0.1,
        top_p=0.9,
        num_return_sequences=1,
        return_full_text=False,
    )[0]["generated_text"]

    # Extract lines starting with "- "
    lines = [ln.strip()[2:].strip().rstrip(".") for ln in out2.splitlines() if ln.strip().startswith("- ")]
    lines = [ln for ln in lines if len(ln.split()) >= 3]  # basic quality gate
    lines = _dedupe_keep_order(lines)[:5]
    if lines:
        return lines

    # Final fallback (very rare): generic but useful actions
    return [
        "Reduce crashes and errors in top user flows",
        "Clarify pricing, trials and cancellation inside the app",
        "Improve login and account recovery reliability",
        "Optimize performance on older devices and slow networks",
        "Tighten billing, refunds and support escalation paths",
    ]
