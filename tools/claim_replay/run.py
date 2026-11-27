"""Replay saved simulated interviews through the deterministic claim matcher and compare it with the LLM's claim ledger.

No LLM calls and nothing written to the database: it reads the transcripts the interview simulator saved
(``tools/interview_sim/out/**/<persona>.json``), re-finds every figure in the answers with
``app.agents.reasoning.claim_matcher``, groups them by meaning, and compares the resulting conflicts with the conflicts the
LLM path recorded during the run.

    venv/Scripts/python.exe tools/claim_replay/run.py                       # all saved runs, default thresholds
    venv/Scripts/python.exe tools/claim_replay/run.py --thresholds 0.45 0.55 0.65
    venv/Scripts/python.exe tools/claim_replay/run.py --lexical             # no embedding model (word overlap only)

Writes ``tools/claim_replay/out/report.md`` (tables plus every disagreement with both sentences) and ``summary.json``.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.agents.reasoning.claim_ledger import parse_value  # noqa: E402
from app.agents.reasoning.claim_matcher import (  # noqa: E402
    DEFAULT_THRESHOLD,
    STRONG_THRESHOLD,
    assign_metric_keys,
    cosine,
    detect_code_conflicts,
    extract_figures,
    lexical_similarity,
    mask_numbers,
)

OUT = Path(__file__).resolve().parent / "out"
PERSONAS = ("strong", "bluffer", "weak", "awkward")


def load_runs(pattern: str) -> list[dict]:
    runs = []
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a half-written transcript is skipped
            continue
        if not isinstance(data, dict) or not data.get("turns") or "brain" not in data:
            continue
        brain = data["brain"] or {}
        if brain.get("claim_ledger") is None:
            continue  # runs from before the claim ledger existed (plan step 5)
        runs.append({
            "path": str(Path(path).resolve().relative_to(ROOT)),
            "persona": data.get("persona") or Path(path).stem,
            "answers": [str(t.get("answer") or "") for t in data["turns"]],
            "ledger": brain.get("claim_ledger") or [],
            "conflicts": brain.get("claim_conflicts") or [],
        })
    return runs


class EmbeddingSimilarity:
    """Cosine similarity of sentence embeddings (all-MiniLM-L6-v2, the model the app already uses), cached per text."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
        self.cache: dict[str, list[float]] = {}

    def warm(self, texts: list[str]) -> None:
        todo = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if todo:
            for text, vec in zip(todo, self.model.encode(todo, batch_size=64, show_progress_bar=False)):
                self.cache[text] = [float(x) for x in vec]

    def __call__(self, a: str, b: str) -> float:
        self.warm([a, b])
        return cosine(self.cache[a], self.cache[b])


def _numbers(value_text: str) -> set[float]:
    p = parse_value(value_text or "")
    return {round(p.number, 6)} if p.number is not None else set()


def _close(xs: set[float], ys: set[float]) -> bool:
    return any(abs(x - y) <= max(abs(x), abs(y)) * 0.01 for x in xs for y in ys)


def _pair(conflict: dict) -> tuple[int, int]:
    first = (conflict.get("first") or {}).get("question_number")
    second = (conflict.get("second") or {}).get("question_number")
    return (int(first or 0), int(second or 0))


def _same_conflict(a: dict, b: dict) -> bool:
    """Same two answers and at least one matching figure."""
    if set(_pair(a)) != set(_pair(b)):
        return False
    na = _numbers((a.get("first") or {}).get("value_text")) | _numbers((a.get("second") or {}).get("value_text"))
    nb = _numbers((b.get("first") or {}).get("value_text")) | _numbers((b.get("second") or {}).get("value_text"))
    return not na or not nb or _close(na, nb)


def compare_run(run: dict, similarity, threshold: float, strong: float) -> dict:
    figures = [f for qn, answer in enumerate(run["answers"], start=1) for f in extract_figures(answer, qn)]
    keyed = assign_metric_keys(figures, similarity, threshold, strong)
    code = detect_code_conflicts(keyed)
    by_key = defaultdict(list)
    for f in keyed:
        by_key[f["metric_key"]].append(f)

    llm_changed = [c for c in run["conflicts"] if c.get("kind") == "changed_value"]
    llm_words = [c for c in run["conflicts"] if c.get("kind") != "changed_value"]  # corrections, admitted inflation

    both, llm_only, code_only = [], [], []
    matched_code = set()
    for c in llm_changed:
        hit = next((i for i, k in enumerate(code) if i not in matched_code and _same_conflict(c, k)), None)
        if hit is None:
            llm_only.append(c)
        else:
            matched_code.add(hit)
            both.append((c, code[hit]))
    for i, k in enumerate(code):
        if i not in matched_code:
            # A code conflict that matches an LLM correction is agreement too, just recorded as another kind.
            if any(_same_conflict(w, k) for w in llm_words):
                both.append((next(w for w in llm_words if _same_conflict(w, k)), k))
            else:
                code_only.append(k)

    # Extraction coverage: LLM claims (with a number) that code also found in the same answer.
    llm_claims = [e for e in run["ledger"] if e.get("number") is not None]
    found = 0
    for e in llm_claims:
        same_answer = [f for f in figures if f["question_number"] == int(e.get("question_number") or 0)]
        if any(f["unit"] == e.get("unit") and _close({float(f["number"])}, {float(e["number"])}) for f in same_answer):
            found += 1

    def context(qn: int, value_text: str) -> str:
        nums = _numbers(value_text)
        for f in keyed:
            if f["question_number"] == qn and (not nums or _close({float(f["number"])}, nums)):
                return f["context"]
        for e in run["ledger"]:
            if int(e.get("question_number") or 0) == qn and _close(_numbers(e.get("value_text")), nums):
                return e.get("quote") or ""
        return ""

    def describe(c: dict, with_match: bool = False) -> dict:
        q1, q2 = _pair(c)
        out = {
            "kind": c.get("kind"),
            "metric_key": c.get("metric_key"),
            "first": {"q": q1, "value": (c.get("first") or {}).get("value_text"),
                      "sentence": context(q1, (c.get("first") or {}).get("value_text"))},
            "second": {"q": q2, "value": (c.get("second") or {}).get("value_text"),
                       "sentence": context(q2, (c.get("second") or {}).get("value_text"))},
        }
        if with_match:
            member = next((f for f in by_key.get(c.get("metric_key"), []) if f["question_number"] == q2), None)
            out["match"] = (member or {}).get("matched")
        return out

    return {
        "path": run["path"],
        "persona": run["persona"],
        "llm_claims": len(llm_claims),
        "llm_claims_found_by_code": found,
        "code_figures": len(figures),
        "llm_changed": len(llm_changed),
        "llm_word_conflicts": len(llm_words),
        "code_conflicts": len(code),
        "both": len(both),
        "llm_only": [describe(c) for c in llm_only],
        "code_only": [describe(c, with_match=True) for c in code_only],
        "llm_word_only": [describe(c) for c in llm_words if not any(_same_conflict(c, k) for k in code)],
    }


def summarize(results: list[dict]) -> dict:
    table = {}
    for persona in PERSONAS + ("all",):
        rows = [r for r in results if persona == "all" or r["persona"] == persona]
        if not rows:
            continue
        table[persona] = {
            "runs": len(rows),
            "llm_claims": sum(r["llm_claims"] for r in rows),
            "claims_found_by_code_pct": round(
                100 * sum(r["llm_claims_found_by_code"] for r in rows) / max(1, sum(r["llm_claims"] for r in rows)), 1),
            "code_figures": sum(r["code_figures"] for r in rows),
            "llm_changed_value": sum(r["llm_changed"] for r in rows),
            "llm_corrections_or_admissions": sum(r["llm_word_conflicts"] for r in rows),
            "code_conflicts": sum(r["code_conflicts"] for r in rows),
            "agree": sum(r["both"] for r in rows),
            "llm_only": sum(len(r["llm_only"]) for r in rows),
            "code_only": sum(len(r["code_only"]) for r in rows),
            "runs_with_any_conflict_llm": sum(1 for r in rows if r["llm_changed"] + r["llm_word_conflicts"] > 0),
            "runs_with_any_conflict_code": sum(1 for r in rows if r["code_conflicts"] > 0),
        }
    return table


def _md_table(table: dict) -> list[str]:
    cols = ["runs", "llm_claims", "claims_found_by_code_pct", "code_figures", "llm_changed_value",
            "llm_corrections_or_admissions", "code_conflicts", "agree", "llm_only", "code_only",
            "runs_with_any_conflict_llm", "runs_with_any_conflict_code"]
    lines = ["| persona | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for persona, row in table.items():
        lines.append(f"| {persona} | " + " | ".join(str(row[c]) for c in cols) + " |")
    return lines


def _md_conflict(item: dict) -> list[str]:
    f, s = item["first"], item["second"]
    lines = [f"- **{item.get('metric_key')}** ({item.get('kind')}): Q{f['q']} `{f['value']}` vs Q{s['q']} `{s['value']}`"]
    if item.get("match"):
        m = item["match"]
        lines.append(f"  - matched: similarity {m['similarity']}, shared words {', '.join(m['shared_terms']) or '-'}")
    lines.append(f"  - Q{f['q']}: {f['sentence'] or '(sentence not found)'}")
    lines.append(f"  - Q{s['q']}: {s['sentence'] or '(sentence not found)'}")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", default=str(ROOT / "tools/interview_sim/out/**/*.json"), help="glob of saved transcripts")
    ap.add_argument("--thresholds", type=float, nargs="+", default=[DEFAULT_THRESHOLD])
    ap.add_argument("--strong", type=float, default=STRONG_THRESHOLD)
    ap.add_argument("--lexical", action="store_true", help="word-overlap similarity instead of embeddings")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    runs = load_runs(args.runs)
    if not runs:
        sys.exit("No saved runs with a claim ledger found.")
    if args.lexical:
        similarity = lexical_similarity
    else:
        similarity = EmbeddingSimilarity()
        similarity.warm([mask_numbers(f["window"]) for run in runs
                         for qn, a in enumerate(run["answers"], start=1) for f in extract_figures(a, qn)])

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary, report = {}, ["# Claim matcher replay", "",
                           f"{len(runs)} saved runs; similarity: {'word overlap' if args.lexical else 'all-MiniLM-L6-v2'};"
                           f" strong threshold {args.strong}.", "",
                           "`agree` = the same changed figure found by both. `llm_only` = changed figures only the LLM "
                           "path flagged. `code_only` = only the code matcher. Corrections and admitted inflation are "
                           "said in words, so only the LLM can see them; they are counted separately.", ""]
    detail_threshold = args.thresholds[len(args.thresholds) // 2]
    for threshold in args.thresholds:
        results = [compare_run(run, similarity, threshold, args.strong) for run in runs]
        table = summarize(results)
        summary[str(threshold)] = {"table": table, "runs": results}
        report += [f"## Threshold {threshold}", ""] + _md_table(table) + [""]
        print(f"\nthreshold {threshold}")
        for persona, row in table.items():
            print(f"  {persona:8} runs={row['runs']:>3} llm_changed={row['llm_changed_value']:>3} "
                  f"words={row['llm_corrections_or_admissions']:>3} code={row['code_conflicts']:>3} "
                  f"agree={row['agree']:>3} llm_only={row['llm_only']:>3} code_only={row['code_only']:>3} "
                  f"claims_found={row['claims_found_by_code_pct']}%")
        if threshold == detail_threshold:
            for label, key in (("Changed figures only the LLM flagged", "llm_only"),
                               ("Changed figures only the code matcher flagged", "code_only"),
                               ("Corrections / admissions (LLM only by design)", "llm_word_only")):
                report += [f"### {label} (threshold {threshold})", ""]
                for r in results:
                    if r[key]:
                        report.append(f"**{r['persona']}** `{r['path']}`")
                        for item in r[key]:
                            report += _md_conflict(item)
                        report.append("")
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    (out / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\nreport: {out / 'report.md'}")


if __name__ == "__main__":
    main()
