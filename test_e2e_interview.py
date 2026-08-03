"""
End-to-end test: v4 evidence-driven interview engine on the live backend.
Run: python test_e2e_interview.py
"""
import httpx
import json
import os
import sys
import time

BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8000")


def print_section(label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def main():
    client = httpx.Client(timeout=300.0)

    # 1. Start v4 interview
    print_section("1. START v4 INTERVIEW")
    payload = {
        "job_role": "Software Engineer",
        "style_name": os.environ.get("STYLE_NAME", "STANDARD"),
        "candidate_name": "Test Candidate",
        "candidate_headline": "Full Stack Developer with 5 years experience",
        "candidate_strengths": ["Python", "React", "System Design", "TypeScript"],
        "candidate_weaknesses": ["DevOps", "Mobile Development"],
    }
    resp = client.post(f"{BASE_URL}/interviews/v4/start", json=payload)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text[:500])
        sys.exit(1)

    data = resp.json()
    print(json.dumps(data, indent=2))
    session_id = data.get("session_id")
    if not session_id:
        print("ERROR: no session_id in response")
        sys.exit(1)

    # 2. Answer loop
    answers = [
        "I built a real-time analytics dashboard at my last company. "
        "We had 10k concurrent users and needed sub-100ms query times. "
        "I chose Apache Druid for the OLAP layer, Redis for caching, "
        "and implemented a WebSocket-based push architecture. "
        "The project reduced query latency from 2s to 50ms on 90% of queries.",

        "I once had a situation where a junior dev pushed broken migrations to production. "
        "I established a code review checklist that included: dry-run migrations first, "
        "a staging environment requirement, and automated linting in CI. "
        "I also mentored the dev through three paired coding sessions on database best practices. "
        "After that, we had zero migration-related incidents in 6 months.",

        "For system design, I prefer starting with requirements gathering — "
        "both functional and non-functional. Then I identify the read/write ratio, "
        "data volume, and consistency needs. I usually sketch a high-level architecture "
        "with load balancers, services, databases, and caches, then dive deeper "
        "into the bottlenecks. I always plan for failure modes and monitoring.",
    ]

    for i, answer in enumerate(answers):
        print_section(f"2.{i+1}. SUBMIT ANSWER {i+1}")
        resp = client.post(
            f"{BASE_URL}/interviews/v4/{session_id}/answer",
            json={"answer": answer},
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text[:500])
            break

        data = resp.json()

        eval_ = data.get('evaluation', {})
        nq = data.get('next_question', {}) or {}
        ev = data.get('evidence', {})
        hp = data.get('hypothesis_progress', {}) or {}
        hr = data.get('hiring_recommendation', {}) or {}

        print(f"  Question #:        {nq.get('number')}")
        print(f"  Score (composite): {eval_.get('composite')}")
        print(f"  Next question:     {(nq.get('text') or '')[:120]}")
        print(f"  Evidence total:    {ev.get('total')}")
        print(f"  Hypotheses:        {hp.get('total')} ({hp.get('statuses', {})})")
        print(f"  Contradictions:    {data.get('contradictions')}")
        print(f"  Hiring verdict:    {hr.get('verdict')} (conf: {hr.get('confidence')})")

        if data.get("interview_complete"):
            print("\n*** INTERVIEW COMPLETE ***")
            break

        time.sleep(1)

    # 3. Get final report
    print_section("3. FINAL REPORT")
    resp = client.get(f"{BASE_URL}/interviews/v4/{session_id}/report")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        report = resp.json()
        print(f"  Evaluation score:   {report.get('evaluation_score')}")
        print(f"  Questions answered: {report.get('question_number')}")
        print(f"  Competencies assessed: {report.get('competencies_assessed')}")
        print(f"  Total evidence:     {report.get('total_evidence')}")
        print(f"  Total hypotheses:   {report.get('total_hypotheses')}")
        print(f"  Contradictions:     {report.get('contradictions')}")
        print(f"  Hiring rec:         {report.get('hiring_recommendation')}")

        feedback = report.get("final_feedback", "")
        if feedback:
            print(f"\n  Final feedback ({len(feedback)} chars):")
            print(f"  {feedback[:800]}...")
        print(f"\n  Full report:")
        print(json.dumps(report, indent=2, default=str)[:3000])
    else:
        print(resp.text[:500])

    client.close()


if __name__ == "__main__":
    main()
