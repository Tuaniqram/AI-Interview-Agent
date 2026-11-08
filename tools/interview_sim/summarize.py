"""Compare harness runs side by side.

    python tools/interview_sim/summarize.py tools/interview_sim/out/step0/*  [more run dirs or .json files...]

Run folders are searched recursively, so a ``--repeat`` run (``<run>/r1``, ``<run>/r2``, ...) can be passed as one folder.

Prints one block per (run, persona):
  verdict, decision score, coverage, mean per-answer score, unscored answers (counting the LAST answer too),
  ev_minus_turn (mean stored-evidence score minus mean per-answer score: how much evidence inflates the answers),
  contradictions (serious + claim conflicts), flag_review, demotion reason, challenge-mode share, generic fallback
  questions, question sources (once the engine records them), max and p95 turn seconds;
then a per-persona verdict tally across everything passed in.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

FALLBACK_MARKERS = (
    "let me dig into that", "give me the specifics: what data", "i'd like to understand your experience with",
    "now, about tech", "tell me about your experience with senior-level",
)

HIRE_SIDE = {"strong_hire", "hire", "lean_hire"}
# Step 6 gate: a reconcile question must stay neutral.
ACCUSING = ("contradict", "inconsistent", "you said something different")


def _mean(values):
    values = [float(v) for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


def _p95(values):
    values = sorted(float(v) for v in values if v is not None)
    if not values:
        return None
    return values[min(len(values) - 1, int(round(0.95 * (len(values) - 1))))]


def summarize(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    turns = d["turns"]
    rep = d.get("report") or {}
    hd = rep.get("hiring_decision") or {}
    ev = d.get("evidence_store") or []
    brain = d.get("brain") or {}

    answer_turns = [t for t in turns if not t.get("clarification")]
    scores = [t["score"] for t in answer_turns if t.get("score") is not None]
    # An answer is scored when it produced evidence. The final answer's response is the report (no per-answer
    # "evaluation"), so the turn's own "scored" flag can't be trusted for it: count questions without evidence.
    evidence_questions = {int(e.get("question_number") or 0) for e in ev if e.get("question_number")}
    unscored = max(0, len(answer_turns) - len(evidence_questions))

    modes = Counter(
        ((t.get("strategy") or {}).get("question_strategy") or {}).get("mode", "") for t in turns[:-1]
    )
    questions = [t["question"].lower() for t in turns]
    contradictions = brain.get("contradictions") or []
    serious = [c for c in contradictions if isinstance(c, dict) and c.get("severity") in ("high", "medium")]
    claim_conflicts = brain.get("claim_conflicts") or []
    sources = Counter(
        q.get("question_source") for q in (brain.get("questions_asked") or []) if q.get("question_source")
    )
    seconds = [t.get("seconds") for t in turns]
    turn_mean = _mean(scores)
    ev_mean = _mean(e.get("score") for e in ev)
    signals = [s for s in (brain.get("answer_signals") or []) if isinstance(s, dict)]
    asked = [q for q in (brain.get("questions_asked") or []) if isinstance(q, dict)]
    reconcilers = [q for q in asked if q.get("mode") == "RECONCILER"]
    reconcile_ids = [q.get("conflict_id") for q in reconcilers if q.get("conflict_id")]
    statuses = Counter(c.get("status") for c in claim_conflicts if isinstance(c, dict))
    unsub = (
        round(sum(1 for s in signals if s.get("verifiable") is False) / len(signals), 2) if signals else None
    )
    return {
        "run": path.parent.name if path.parent.name.startswith("r") and path.parent.name[1:].isdigit()
        else path.parent.name,
        "where": str(path.parent),
        "persona": d["persona"], "answers": len(answer_turns), "clarifications": len(turns) - len(answer_turns),
        "seconds": d["seconds"], "error": bool(d.get("error")),
        "verdict": rep.get("verdict"), "coverage": (rep.get("coverage") or {}).get("competency_coverage_ratio"),
        "decision_score": hd.get("decision_score"),
        "avg_score": turn_mean,
        "ev_minus_turn": round(ev_mean - turn_mean, 2) if ev_mean is not None and turn_mean is not None else None,
        "unscored": unscored,
        "serious_contradictions": len(serious),
        "claim_conflicts": len(claim_conflicts),
        "unsubstantiated_share": unsub,
        "reconcile_questions": len(reconcilers),
        "reconcile_repeats": len(reconcile_ids) - len(set(reconcile_ids)),
        "reconcile_accusing": sum(1 for q in reconcilers if any(w in str(q.get("text", "")).lower() for w in ACCUSING)),
        "conflict_statuses": dict(statuses),
        "admitted_gaps": sum(1 for s in signals if s.get("admitted_gap")),
        "flag_review": hd.get("flag_review"),
        "read_questions": len(((d.get("evidence_reading") or {}).get("per_question")) or {}),
        "read_risks": len(((d.get("evidence_reading") or {}).get("semantic_risks")) or []),
        "draft": hd.get("draft") or hd.get("draft_decision"),
        "adjustments": [a.get("rule") for a in (hd.get("adjustments") or []) if isinstance(a, dict)],
        # Step 3 gate: a verdict of insufficient_evidence or lower must never suggest an offer.
        "offer_mismatch": (
            rep.get("verdict") not in HIRE_SIDE
            and any("offer" in str(step).lower() for step in (hd.get("next_steps") or []))
        ),
        "demotion": hd.get("demotion_reason") or "",
        "difficulty_reached": (hd.get("signals") or {}).get("difficulty_reached"),
        "ownership": dict(Counter(e.get("ownership") for e in ev)),
        "complexity": dict(Counter(e.get("complexity") for e in ev)),
        "challenge_share": round(modes.get("challenge", 0) / max(1, sum(modes.values())), 2),
        "fallback_questions": sum(1 for q in questions if any(m in q for m in FALLBACK_MARKERS)),
        "question_sources": dict(sources),
        "max_turn_s": max((s for s in seconds if s is not None), default=None),
        "p95_turn_s": _p95(seconds),
    }


def _files(arg: str) -> list[Path]:
    p = Path(arg)
    if p.is_dir():
        return sorted(f for f in p.rglob("*.json") if f.name != "summary.json")
    return [p]


def main():
    rows = [summarize(f) for arg in sys.argv[1:] for f in _files(arg)]
    for r in rows:
        print(f"{r['where']:<52} {r['persona']:<8} verdict={r['verdict']} dscore={r['decision_score']} "
              f"cov={r['coverage']} diff={r['difficulty_reached']}{' CRASH' if r['error'] else ''}")
        print(f"{'':<61} answers={r['answers']} unscored={r['unscored']} clarif={r['clarifications']} "
              f"avg={r['avg_score']} ev_minus_turn={r['ev_minus_turn']}")
        print(f"{'':<61} unsub_share={r['unsubstantiated_share']} admitted_gaps={r['admitted_gaps']} "
              f"read_q={r['read_questions']} read_risks={r['read_risks']}")
        print(f"{'':<61} reconcile_q={r['reconcile_questions']} repeats={r['reconcile_repeats']} "
              f"accusing={r['reconcile_accusing']} conflict_status={r['conflict_statuses'] or '-'}")
        print(f"{'':<61} draft={r['draft']} adjustments={r['adjustments'] or '-'}"
              f"{' OFFER-MISMATCH' if r['offer_mismatch'] else ''}")
        print(f"{'':<61} contradictions={r['serious_contradictions']} claim_conflicts={r['claim_conflicts']} "
              f"flag={r['flag_review']} demotion={r['demotion'][:60]!r}")
        print(f"{'':<61} challenge={r['challenge_share']} fallbackQ={r['fallback_questions']} "
              f"sources={r['question_sources'] or '-'} p95={r['p95_turn_s']}s max={r['max_turn_s']}s")
        print(f"{'':<61} ownership={r['ownership']} complexity={r['complexity']}")

    tally: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        tally[r["persona"]][r["verdict"] if not r["error"] else "CRASH"] += 1
    if len(rows) > 1:
        print("\nverdict tally:")
        for persona, counts in sorted(tally.items()):
            hire_side = sum(n for v, n in counts.items() if v in HIRE_SIDE)
            parts = " ".join(f"{v}x{n}" for v, n in counts.most_common())
            print(f"  {persona:<8} {parts}   (hire-side {hire_side}/{sum(counts.values())})")


if __name__ == "__main__":
    main()
