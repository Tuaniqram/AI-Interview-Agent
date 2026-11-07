"""Compare harness runs side by side.

    python tools/interview_sim/summarize.py tools/interview_sim/out/evfix/*  [more run dirs...]

Prints one line per (run, persona): verdict, coverage, answer scores, evidence quality (ownership /
complexity of the stored evidence), the share of turns spent in 'challenge' mode, turns that were
never scored, and questions that look like the generic fallback templates.
"""
import json
import sys
from collections import Counter
from pathlib import Path

FALLBACK_MARKERS = (
    "let me dig into that", "give me the specifics: what data", "i'd like to understand your experience with",
    "now, about tech", "tell me about your experience with senior-level",
)


def summarize(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    turns = d["turns"]
    rep = d.get("report") or {}
    ev = d.get("evidence_store") or []
    scores = [t["score"] for t in turns if t.get("score") is not None]
    modes = Counter(
        ((t.get("strategy") or {}).get("question_strategy") or {}).get("mode", "") for t in turns[:-1]
    )
    questions = [t["question"].lower() for t in turns]
    return {
        "run": path.parent.name, "persona": d["persona"], "answers": len(turns),
        "seconds": d["seconds"], "error": bool(d.get("error")),
        "verdict": rep.get("verdict"), "coverage": (rep.get("coverage") or {}).get("competency_coverage_ratio"),
        "decision_score": (rep.get("hiring_decision") or {}).get("decision_score"),
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "unscored": sum(1 for t in turns[:-1] if t.get("scored") is False),
        "ownership": dict(Counter(e.get("ownership") for e in ev)),
        "complexity": dict(Counter(e.get("complexity") for e in ev)),
        "challenge_share": round(modes.get("challenge", 0) / max(1, sum(modes.values())), 2),
        "fallback_questions": sum(1 for q in questions if any(m in q for m in FALLBACK_MARKERS)),
        "max_turn_s": max((t["seconds"] for t in turns), default=None),
    }


def main():
    rows = []
    for arg in sys.argv[1:]:
        for f in sorted(Path(arg).glob("*.json")) if Path(arg).is_dir() else [Path(arg)]:
            if f.name != "summary.json":
                rows.append(summarize(f))
    for r in rows:
        print(f"{r['run']:<16} {r['persona']:<8} answers={r['answers']} verdict={r['verdict']} cov={r['coverage']} "
              f"dscore={r['decision_score']} avg={r['avg_score']} unscored={r['unscored']} "
              f"challenge={r['challenge_share']} fallbackQ={r['fallback_questions']} maxturn={r['max_turn_s']}s"
              f"{' CRASH' if r['error'] else ''}")
        print(f"{'':<25} ownership={r['ownership']} complexity={r['complexity']}")


if __name__ == "__main__":
    main()
