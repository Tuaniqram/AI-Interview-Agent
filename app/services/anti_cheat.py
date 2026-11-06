"""Anti-cheat integrity guard (contract: docs/anti-cheat-guard.md).

Best-effort, non-fatal, flag-only. Gated by ``ANTI_CHEAT_GUARD_ENABLED``
(default OFF so developers keep testing with AI). When disabled, ``assess``
is a pass-through that returns ``None`` — zero LLM calls, zero state mutation.

Layers:
* heuristics — free per-answer signals (latency, text fingerprint, paste
  hint, cross-answer duplicate ratio, prompt-injection fold-in)
* LLM judge — one ``get_llm_service`` call per answer, only when enabled by
  ``ANTI_CHEAT_LLM_JUDGE`` and the answer is long enough; any failure skips
  the judge, never the guard.
"""

import logging
import re
import statistics
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

MIN_JUDGE_CHARS = 200

# Weights for the heuristic blend (renormalized over the signals that are
# actually present, so a missing latency never punishes an answer).
_HEURISTIC_WEIGHTS = {
    "latency": 0.10,
    "typing_rate": 0.20,
    "fingerprint": 0.15,
    "paste": 0.25,
    "focus": 0.20,
    "duplicate": 0.10,
    "cadence": 0.18,   # keystroke rhythm (transcription / superhuman speed)
    "pointer": 0.08,   # pointer leaving the focused window (second screen)
    "tamper": 0.15,    # heartbeat divergence (debugger / VM snapshot)
}

_JUDGE_BLEND_WEIGHT = 0.40  # judge share of the final score when it runs

_JUDGE_SYSTEM_PROMPT = (
    "You are an interview-integrity analyst. Judge only whether the candidate's "
    "answer text looks machine-generated or copied from an AI assistant. Return "
    "strict JSON: {\"ai_score\": int 0-100, \"reasons\": [string]}. "
    "ai_score 90+ = near-certain AI-written; 0-20 = clearly human. "
    "Prefer conservative scores; never convict on style alone."
)


def now_iso() -> str:
    """UTC ISO timestamp for ``question_asked_at`` / range checks (no tz ambiguity)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_enabled() -> bool:
    return bool(settings.ANTI_CHEAT_GUARD_ENABLED)


def latency_secs(question_asked_at) -> Optional[float]:
    """Seconds between question emission and answer intake. ``None`` when the
    timestamp is missing or unparseable (older sessions / manual resumes)."""
    if not question_asked_at:
        return None
    try:
        ts = datetime.fromisoformat(str(question_asked_at).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - ts).total_seconds(), 1)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Heuristics
# --------------------------------------------------------------------------- #

_FILLER_WORDS = ("um", "uh", "err", "hmm", "yeah, i", "you know", "i guess", "i think", "maybe", "kinda", "sorta")
_HTML_OR_CODE_MARKERS = ("```", "```python", "<div", "<p", "<html", "function ", "def ", "import ", "return ")
_MARKDOWN_MARKERS = ("##", "###", "**", "\\n- ", "\\n* ", "\\n1. ", "\\n2. ", "\\n3. ", "|", "---")


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if len(p.split()) >= 2]


def _burstiness_score(text: str) -> Optional[float]:
    """Uniform sentence lengths (low coefficient of variation) → machine-like.

    Returns 0–100, or None when the text is too short to judge.
    """
    sents = _sentences(text)
    if len(sents) < 2:
        return None
    lengths = [len(s.split()) for s in sents]
    mean = statistics.mean(lengths)
    if mean < 5:
        return None
    stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0.0
    cv = (stdev / mean) if mean else 1.0
    # cv ~1.2+ is human-typical; cv ~0.3–0.6 is model-typical.
    normalized = max(0.0, min(1.0, (1.2 - cv) / 0.9))
    return round(normalized * 100, 1)


def _formal_markers_score(text: str) -> float:
    """Absence of human disfluencies (filler/hedging) in a long answer → formal/AI."""
    lowered = text.lower()
    filler_hits = sum(1 for f in _FILLER_WORDS if f in lowered)
    if len(text.split()) < 60:
        return 0.0  # short answers: too noisy to infer
    if filler_hits == 0:
        return 65.0
    return max(0.0, 65.0 - 20.0 * filler_hits)


def _structure_density_score(text: str) -> float:
    """Bullet/markdown/code-block density — AI answers over-structure."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return 0.0
    bullet_lines = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*•]\\s", stripped) or re.match(r"^\\d+[.)]\\s", stripped):
            bullet_lines += 1
        elif stripped.startswith(("|", "```", "###", "##", "#")):
            bullet_lines += 1
    density = bullet_lines / len(lines)
    if density >= 0.5:
        return 95.0
    if density >= 0.25:
        return 60.0
    if density > 0:
        return 30.0
    return 0.0


def _fingerprint_score(text: str) -> float:
    """Combined instance of the machine-typical writing fingerprint."""
    parts = [
        p for p in (_burstiness_score(text), _formal_markers_score(text), _structure_density_score(text))
        if p is not None
    ]
    if not parts:
        return 0.0
    return round(sum(parts) / len(parts), 1)


def _latency_score(latency: Optional[float], text_len: int) -> Optional[float]:
    """Near-instant long answers = copy-paste. ``None`` when unknown."""
    if latency is None:
        return None
    if text_len < 120:
        return None  # short answers come fast even when legit
    if latency < 10:
        return 90.0
    if latency < 20:
        return 70.0
    if latency < 45:
        return 35.0
    return 10.0


def _typing_rate_score(latency: Optional[float], text_len: int) -> Optional[float]:
    """Chars-per-second vs human typing physics (~5–8 cps). ``None`` when
    unknown. A 400-char polished answer within 15s cannot be typed by a
    person — it was pasted or dictated by an assistant."""
    if latency is None or text_len < 120:
        return None
    cps = text_len / max(latency, 1.0)
    if cps >= 20:
        return 95.0
    if cps >= 12:
        return 85.0
    if cps >= 8:
        return 60.0
    return 0.0


def _typing_cadence_score(intervals) -> Optional[float]:
    """Keystroke-rhythm analysis from the client's inter-key log (contract §4.6).

    Two detectable patterns, both scored from the raw interval array:
    * superhuman sustained speed — mean inter-key interval < 125 ms (~8 cps)
      with low variance (no human pauses) → dictated or macro-driven;
    * transcription rhythm — fast bursts (many < 200 ms intervals) interrupted
      by periodic look-up pauses (1.2–8 s) at a consistent cadence, i.e. the
      burst/pause ratio stays in a narrow band across the whole answer.

    Returns 0–100 or None when the log is too short to judge.
    """
    if not intervals:
        return None
    vals = [float(v) for v in intervals if isinstance(v, (int, float)) and v >= 0]
    if len(vals) < 12:
        return None
    mean = statistics.mean(vals)
    burst = [v for v in vals if v < 200]
    pauses = [v for v in vals if 1200 <= v <= 8000]
    burst_ratio = len(burst) / len(vals)
    pause_ratio = len(pauses) / len(vals)

    if mean < 125 and burst_ratio > 0.8:
        return 92.0  # sustained > 8 cps, near-zero human hesitation
    if mean < 90 and burst_ratio > 0.9:
        return 95.0

    # Transcription: heavy bursts PLUS recurring look-up pauses, and the
    # pause cadence is consistent (low CV of pause intervals).
    if burst_ratio >= 0.6 and 0.04 <= pause_ratio <= 0.3 and len(pauses) >= 2:
        pause_cv = (statistics.stdev(pauses) / statistics.mean(pauses)) if pauses else 1.0
        if pause_cv <= 0.6:
            return 72.0
        return 55.0
    return 0.0


def _pointer_leaves_score(pointer_leaves) -> Optional[float]:
    """Pointer exiting the focused window = possible second-screen reading."""
    count = _to_int(pointer_leaves)
    if count <= 0:
        return None
    threshold = max(1, int(settings.ANTI_CHEAT_POINTER_LEAVE_THRESHOLD or 3))
    if count >= threshold * 2:
        return 90.0
    if count >= threshold:
        return 75.0
    return 45.0


def _tamper_gaps_score(heartbeat_gaps) -> Optional[float]:
    """rAF/wall-clock divergences: debugger breakpoints or VM snapshots."""
    count = _to_int(heartbeat_gaps)
    if count <= 0:
        return None
    if count >= 2:
        return 95.0
    return 85.0


def _paste_hint(text: str, paste_chars) -> bool:
    """Wholesale paste: enough clipboard chars to cover the answer, or perfect
    structure + abrupt lead-in on an otherwise informal session."""
    if paste_chars:
        pasted = _to_int(paste_chars)
        if pasted >= 0.8 * len(text) and pasted > 40:
            return True
    stripped = text.strip()
    if len(stripped) >= 200 and _structure_density_score(text) >= 60 and not re.search(r"[,.;]", stripped[:120]):
        return True
    return False


def _duplicate_ratio(text: str, prior_answers: list[str]) -> float:
    """Best normalized-difflib match vs earlier answers in the same session."""
    best = 0.0
    target = _normalize(text)
    if not target:
        return 0.0
    for prev in prior_answers:
        prev_norm = _normalize(prev)
        if prev_norm:
            best = max(best, SequenceMatcher(None, target, prev_norm).ratio())
    return round(best, 3)


def _normalize(text: str) -> str:
    return re.sub(r"\\s+", " ", text.strip().lower())


def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def flagged_count(signals) -> int:
    """Number of flagged answers among stored integrity signals."""
    return sum(
        1
        for s in (signals or [])
        if isinstance(s, dict) and s.get("flagged")
    )


def max_flags() -> int:
    return int(settings.ANTI_CHEAT_MAX_FLAGS or 3)


def should_terminate(signals) -> bool:
    """Termination policy: guard enabled AND flagged answers >= max flags."""
    if not _is_enabled():
        return False
    limit = max_flags()
    return limit > 0 and flagged_count(signals) >= limit


# --------------------------------------------------------------------------- #
# LLM judge
# --------------------------------------------------------------------------- #

async def llm_judge(text: str, question: str) -> tuple[Optional[int], list[str]]:
    """One LLM call scoring AI-likelihood 0–100. Any failure ⇒ (None, [])."""
    try:
        from app.services.llm_service import get_llm_service
        from app.intelligence._helpers import parse_json

        prompt = (
            "Interview question: " + (question or "(unknown)") + "\\n\\n"
            "Candidate answer:\\n" + text[:3000]
        )
        svc = get_llm_service()
        raw = await svc.invoke(
            prompt,
            temperature=0.0,
            max_tokens=300,
            system_prompt=_JUDGE_SYSTEM_PROMPT,
            tier="cheap",
        )
        data = parse_json(raw)
        score = int(data.get("ai_score", 0))
        score = max(0, min(100, score))
        reasons = [str(r) for r in (data.get("reasons") or []) if str(r).strip()][:4]
        return score, reasons
    except Exception as e:  # noqa: BLE001 - judge is best-effort by design
        logger.warning(f"Anti-cheat LLM judge skipped: {e}")
        return None, []


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

async def assess(
    *,
    text: str,
    question: str = "",
    question_asked_at=None,
    paste_chars=None,
    focus_lost_count=None,
    prior_answers: Optional[list[str]] = None,
    answer_source: str = "",
    keystroke_intervals=None,
    first_key_ms=None,
    pointer_leaves=None,
    heartbeat_gaps=None,
) -> Optional[dict]:
    """Produce the per-answer integrity report, or ``None`` when the guard is
    disabled (contract §7: pass-through, zero cost). Never raises.

    ``answer_source`` (``"typing"``/``"voice"``) is optional client metadata.
    Voice-delivered answers can never be copy-pasted, so the typing-rate,
    cadence and paste signals are skipped for them — latency, focus loss, text
    fingerprint and the LLM judge still apply. On a voice-only frontend the
    backend simply receives ``answer_source: "voice"`` with zero paste/typing
    telemetry.

    Hardening signals (contract §4.6): ``keystroke_intervals``/``first_key_ms``
    (typing rhythm), ``pointer_leaves`` (second-screen reading) and
    ``heartbeat_gaps`` (debugger/VM tampering) are all optional — a client that
    sends none of them is judged on the classic signals alone.
    """
    if not _is_enabled():
        return None
    try:
        text = text or ""
        prior = prior_answers or []
        is_voice = str(answer_source or "").strip().lower() in ("voice", "mic")
        latency = latency_secs(question_asked_at)
        dup_ratio = _duplicate_ratio(text, prior)
        paste = False if is_voice else _paste_hint(text, paste_chars)
        focus = _to_int(focus_lost_count)

        from app.utils.input_sanitizer import detect_prompt_injection

        injections = detect_prompt_injection(text)

        # ---- heuristic blend (renormalized over present signals) ----
        subscores = {}
        lat = _latency_score(latency, len(text))
        if lat is not None:
            subscores["latency"] = lat
            if not is_voice:
                rate = _typing_rate_score(latency, len(text))
                if rate is not None:
                    subscores["typing_rate"] = rate
        if not is_voice:
            cadence = _typing_cadence_score(keystroke_intervals)
            if cadence is not None and cadence > 0:
                subscores["cadence"] = cadence
            first_key = _to_int(first_key_ms)
            # Long polished answer whose first keystroke was suspiciously late
            # relative to a short latency is impossible to type AND to look up
            # at once — mild corroboration, folded into cadence judgement only.
            if first_key and lat is not None and lat < 60 and first_key > lat * 1000:
                subscores["cadence"] = max(subscores.get("cadence", 0), 60.0)
        fp = _fingerprint_score(text)
        if fp > 0:
            subscores["fingerprint"] = fp
        if paste:
            subscores["paste"] = 85.0
        elif (not is_voice) and _to_int(paste_chars) > 0:
            subscores["paste"] = 45.0
        if focus >= 3:
            subscores["focus"] = 90.0
        elif focus == 2:
            subscores["focus"] = 70.0
        elif focus == 1:
            subscores["focus"] = 40.0
        if dup_ratio >= 0.9:
            subscores["duplicate"] = 95.0
        elif dup_ratio >= 0.75:
            subscores["duplicate"] = 75.0
        elif dup_ratio >= 0.6:
            subscores["duplicate"] = 50.0

        pointer = _pointer_leaves_score(pointer_leaves)
        if pointer is not None:
            subscores["pointer"] = pointer
        tamper = _tamper_gaps_score(heartbeat_gaps)
        if tamper is not None:
            subscores["tamper"] = tamper

        total_weight = sum(_HEURISTIC_WEIGHTS[k] for k in subscores)
        heuristic_score = (
            round(sum(subscores[k] * _HEURISTIC_WEIGHTS[k] for k in subscores) / total_weight)
            if total_weight > 0
            else 0
        )

        # ---- optional LLM judge blend ----
        judge_score = None
        judge_reasons: list[str] = []
        use_judge = bool(settings.ANTI_CHEAT_LLM_JUDGE) and len(text) >= MIN_JUDGE_CHARS
        if use_judge:
            judge_score, judge_reasons = await llm_judge(text, question)
        if judge_score is not None:
            score = round(heuristic_score * (1 - _JUDGE_BLEND_WEIGHT) + judge_score * _JUDGE_BLEND_WEIGHT)
        else:
            score = heuristic_score

        # Best-evidence-wins: the blend is renormalized, so a strong signal can
        # be diluted below threshold by weak style noise (e.g. a fingerprint
        # read on a two-sentence answer). A decisive signal — sustained machine
        # typing speed, tamper gaps — is hard evidence and must not be diluted.
        # The blend still aggregates corroboration; this only lifts the floor.
        strongest = max(subscores.values(), default=0)
        if strongest > score:
            score = round(strongest)

        reasons: list[str] = []
        if lat is not None and lat <= 20:
            reasons.append(f"answer submitted {latency}s after the question was shown")
        if subscores.get("typing_rate", 0) >= 60:
            reasons.append("answer arrived too fast to have been typed by a person")
        if subscores.get("cadence", 0) >= 90:
            reasons.append("keystroke rhythm exceeds human typing speed (sustained >8 cps, no pauses)")
        elif subscores.get("cadence", 0) >= 55:
            reasons.append("keystroke rhythm matches read-and-transcribe pattern (fast bursts with recurring look-up pauses)")
        if subscores.get("pointer", 0) >= 75:
            reasons.append(f"pointer left the browser window {_to_int(pointer_leaves)} times (possible second-screen reading)")
        if subscores.get("tamper", 0) > 0:
            reasons.append(f"session froze or was paused {_to_int(heartbeat_gaps)} time(s) — debugger or VM interference")
        if subscores.get("fingerprint", 0) >= 60:
            reasons.append("uniform machine-typical phrasing (uniform sentence rhythm, no disfluencies)")
        if paste:
            reasons.append("answer matches a wholesale clipboard paste (or paste-sized structure)")
        if focus >= 2:
            reasons.append(f"candidate lost focus {focus} times during this question")
        if dup_ratio >= 0.6:
            reasons.append(f"answer is {int(dup_ratio * 100)}% similar to an earlier answer in this session")
        reasons.extend(injections[:3])
        reasons.extend(judge_reasons)

        threshold = int(settings.ANTI_CHEAT_FLAG_THRESHOLD or 70)
        return {
            "score": score,
            "flagged": score >= threshold,
            "latency_secs": latency,
            "paste_hint": bool(paste),
            "focus_losses": focus,
            "duplicate_ratio": dup_ratio,
            "pointer_leaves": _to_int(pointer_leaves),
            "heartbeat_gaps": _to_int(heartbeat_gaps),
            "cadence_score": subscores.get("cadence"),
            "llm_ai_score": judge_score,
            "reasons": reasons,
        }
    except Exception as e:  # noqa: BLE001 - the guard must never break a turn
        logger.warning(f"Anti-cheat guard failed (non-fatal): {e}")
        return None