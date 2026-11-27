"""Thin client for any OpenAI-compatible chat endpoint (Apertus via CSCS/Keera, HF router, vLLM).

If LLM_BASE_URL is not set, a deterministic mock is used so the pipeline and UI can be
developed offline. Mock output is always labelled model="mock".
"""
import json
import re
import time

import httpx

from . import config


class LLMError(RuntimeError):
    pass


def chat(messages, temperature=0.2, max_tokens=1200, json_mode=False):
    """Return the assistant text for a list of {role, content} messages."""
    if config.USE_MOCK_LLM:
        return _mock(messages, json_mode)
    body = {
        "model": config.LLM_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"}
    last = None
    for attempt in range(4):
        try:
            r = httpx.post(f"{config.LLM_BASE_URL}/chat/completions", json=body,
                           headers=headers, timeout=config.LLM_TIMEOUT)
            if r.status_code in (429, 500, 502, 503, 504):
                raise LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, LLMError) as e:
            last = e
            time.sleep(2 ** attempt)
    raise LLMError(f"LLM call failed after retries: {last}")


def model_name():
    return "mock" if config.USE_MOCK_LLM else config.LLM_NAME


def parse_json(text):
    """Extract the first JSON object from a model answer (models like to add prose)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unterminated JSON object in model output")


# --------------------------------------------------------------------------- mock
_KEYWORDS = ["suva", "uvg", "laa", "unfall", "accident", "unfallversicherung", "assurance-accidents",
             "kausalzusammenhang", "causalité", "integritätsentschädigung", "invalidenrente",
             "taggeld", "indemnités journalières", "berufskrankheit", "maladie professionnelle"]


def _mock(messages, json_mode):
    user = messages[-1]["content"]
    low = user.lower()
    hits = [k for k in _KEYWORDS if k in low]
    if json_mode:
        score = min(95, 15 + 12 * len(hits))
        return json.dumps({
            "score": score,
            "title_de": "[Mock] Urteil zu " + (", ".join(hits[:2]) or "Sozialversicherungsrecht"),
            "title_fr": "[Mock] Arrêt concernant " + (", ".join(hits[:2]) or "droit des assurances sociales"),
            "explanation_de": f"[Mock] {len(hits)} Suva-relevante Stichworte gefunden: {', '.join(hits) or 'keine'}.",
            "explanation_fr": f"[Mock] {len(hits)} mots-clés pertinents pour la Suva: {', '.join(hits) or 'aucun'}.",
            "tags": [h.capitalize() for h in hits[:5]] or ["Sozialversicherung"],
            "suva_party": "suva" in low,
        })
    m = re.search(r"<judgement>(.*?)</judgement>", user, re.S)
    body = (m.group(1) if m else user).strip()
    sentences = re.split(r"(?<=[.!?])\s+", body)
    return "[Mock-Zusammenfassung / résumé fictif] " + " ".join(sentences[:4])[:900]
