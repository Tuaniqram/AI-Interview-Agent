import os
import sys
import time
import argparse
from pathlib import Path

import httpx
from fpdf import FPDF


API_URL = os.getenv("API_URL", "http://localhost:8000")
OUTPUT_DIR = Path("output")

PAGE_W = 210
PAGE_H = 297
MARGIN = 20
BODY_W = PAGE_W - 2 * MARGIN


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, "Nova AI -- Internal Knowledge Base", align="C")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 30, 30)
        self.cell(0, 9, title)
        self.ln(6)
        self.set_draw_color(70, 130, 200)
        self.set_line_width(0.6)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.ln(4)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        text = text.replace("\u2014", "--").replace("\u2013", "-")
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        x0 = self.get_x()
        self.cell(6, 5.5, " -")
        self.multi_cell(0, 5.5, text)
        self.set_x(x0)

    def bold_text(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5.5, text)
        self.ln(1)


def make_company_overview():
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, "Nova AI -- Company Overview")
    pdf.ln(12)

    pdf.section_title("Mission & Vision")
    pdf.body_text(
        "Nova AI is on a mission to democratize artificial intelligence by building tools that make "
        "machine learning accessible, reproducible, and impactful for every organization. We envision "
        "a world where AI-assisted decision-making is as standard as spreadsheet analysis."
    )

    pdf.section_title("History")
    pdf.body_text(
        "Founded in 2023 by Dr. Elena Vasquez (CEO) and Marcus Chen (CTO), Nova AI emerged from "
        "research at Stanford's AI Lab. The company secured $12M in seed funding from Amplify Partners "
        "in early 2024 and launched its first product, Nova Interview, in Q3 2024. As of 2026, "
        "Nova AI serves over 800 enterprise customers across North America, Europe, and APAC."
    )

    pdf.section_title("Core Values")
    pdf.bullet("Transparency -- Every decision, model, and metric is documented and auditable.")
    pdf.bullet("Excellence -- We hold ourselves to the highest standards of engineering and ethics.")
    pdf.bullet("Inclusivity -- Our products are designed for diverse teams and global audiences.")
    pdf.bullet("Innovation -- We invest 20% of engineering time in exploratory research.")

    pdf.section_title("Product Lineup")
    pdf.bold_text("Nova Interview -- AI-powered technical interview platform with real-time voice, code evaluation, and structured scoring.")
    pdf.bold_text("Nova Assess -- Automated skills assessment for pre-screening candidates at scale.")
    pdf.bold_text("Nova Learn -- Adaptive learning paths generated from interview gap analysis.")
    pdf.bold_text("Nova Insights -- Analytics dashboard for hiring teams to track pipelines and trends.")
    pdf.ln(4)

    pdf.section_title("Key Statistics (2026)")
    pdf.bullet("800+ enterprise customers")
    pdf.bullet("50,000+ interviews conducted monthly")
    pdf.bullet("99.95% platform uptime")
    pdf.bullet("45 full-time employees across 3 offices")

    return pdf


def make_product_documentation():
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, "Nova AI -- Product Documentation")
    pdf.ln(12)

    pdf.section_title("Nova Interview Architecture")
    pdf.body_text(
        "Nova Interview is built on a microservices architecture with the following core components: "
        "the Interview Orchestrator (LangGraph-based state machine), the Voice Service (WebSocket "
        "real-time audio with ElevenLabs TTS and Whisper STT), the Evaluation Engine (LLM-graded "
        "scoring across technical and behavioral dimensions), and the Knowledge Base (RAG pipeline "
        "with Pinecone vector store for company-specific context)."
    )

    pdf.section_title("Key Features")
    pdf.bold_text("Multi-mode Interviews:")
    pdf.body_text(
        "Candidates can choose between voice-only, chat-only, or mixed-mode interviews. "
        "Voice interviews use WebSocket streaming with sub-500ms latency."
    )
    pdf.bold_text("Adaptive Questioning:")
    pdf.body_text(
        "The engine dynamically adjusts question difficulty based on candidate performance. "
        "Strong answers trigger deeper follow-ups; weak answers trigger scaffolding hints."
    )
    pdf.bold_text("Structured Scorecards:")
    pdf.body_text(
        "Every interview produces a standardized scorecard across 6 competencies: "
        "problem-solving, technical knowledge, communication, system design, coding, and culture fit."
    )
    pdf.bold_text("Batch Processing:")
    pdf.body_text(
        "Enterprise plans support concurrent interview sessions with automatic load balancing "
        "across LLM providers (OpenRouter, Groq, OpenAI)."
    )

    pdf.section_title("Integration API")
    pdf.body_text(
        "Nova AI exposes RESTful APIs for ATS integration (Greenhouse, Lever, Workday), "
        "single sign-on (Google OAuth, Microsoft Entra), and webhook-based event notification. "
        "The API supports CSV/JSON export of interview results and scorecard data."
    )

    pdf.section_title("Security & Compliance")
    pdf.bullet("SOC 2 Type II certified (audit completed February 2026)")
    pdf.bullet("GDPR compliant with data residency in US, EU, and APAC regions")
    pdf.bullet("All candidate data encrypted at rest (AES-256) and in transit (TLS 1.3)")
    pdf.bullet("Role-based access control with audit logging for all administrative actions")

    return pdf


def make_engineering_practices():
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, "Nova AI -- Engineering Practices")
    pdf.ln(12)

    pdf.section_title("Development Workflow")
    pdf.body_text(
        "We follow a trunk-based development model with short-lived feature branches (max 3 days). "
        "Every branch must pass a CI pipeline that includes type checking (mypy), linting (ruff), "
        "unit tests (pytest, 80% coverage minimum), and integration tests before merging to main."
    )

    pdf.section_title("Code Review Standards")
    pdf.bullet("Every PR requires at least one approval from a senior engineer on the team.")
    pdf.bullet("Reviews must be completed within 24 hours during business days.")
    pdf.bullet("PRs larger than 400 lines require a design doc and sync review meeting.")
    pdf.bullet("All feedback must be constructive and reference specific line numbers.")
    pdf.bullet("Automated checks must pass before human review begins.")

    pdf.section_title("Tech Stack")
    pdf.bold_text("Backend:")
    pdf.body_text("Python 3.12, FastAPI, LangGraph, SQLAlchemy (async), PostgreSQL (Supabase), Redis, Pinecone")
    pdf.bold_text("Frontend:")
    pdf.body_text("React 19, TypeScript, Tailwind CSS, Vite, React Router v7")
    pdf.bold_text("AI/ML:")
    pdf.body_text("OpenRouter (primary LLM provider), Groq (fallback), LangChain, sentence-transformers, Whisper")
    pdf.bold_text("Infrastructure:")
    pdf.body_text("Docker, GitHub Actions (CI/CD), Vercel (frontend), Render (backend), Supabase (DB + auth)")

    pdf.section_title("Deployment Process")
    pdf.body_text(
        "Deployments happen automatically on merge to main after a 10-minute smoke test window. "
        "Production deploys use a blue-green strategy with zero downtime. Rollbacks are automated "
        "if error rates exceed 1% within 5 minutes of deploy."
    )

    pdf.section_title("Monitoring & Observability")
    pdf.body_text(
        "We use structured logging (JSON) shipped to a central log aggregator. Key metrics "
        "(p95 latency, error rate, token usage, cost-per-interview) are tracked via a custom "
        "dashboard with PagerDuty alerts on thresholds. Every service exposes a /health endpoint "
        "with dependency status."
    )

    return pdf


def make_onboarding_guide():
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, "Nova AI -- Onboarding Guide")
    pdf.ln(12)

    pdf.section_title("Welcome to Nova AI")
    pdf.body_text(
        "We're excited to have you on board! This guide will help you navigate your first weeks. "
        "Every new hire is assigned a buddy (a peer from your team) and a mentor (a senior IC or "
        "manager) to support your ramp-up."
    )

    pdf.section_title("First Week Checklist")
    pdf.bullet("Day 1 -- Setup workstation, install dev tools, meet your team, review the handbook.")
    pdf.bullet("Day 2 -- Complete security & compliance training (2 hours).")
    pdf.bullet("Day 3 -- Shadow onboarding buddy on a small task, explore the codebase.")
    pdf.bullet("Day 4 -- Submit your first small PR (documentation or test improvement).")
    pdf.bullet("Day 5 -- One-on-one with manager, review first-week goals and next sprint assignment.")

    pdf.section_title("Team Structure")
    pdf.body_text(
        "Nova AI has four engineering teams: Platform (core infrastructure, APIs, DevOps), "
        "AI/ML (LLM pipelines, evaluation, RAG), Frontend (React apps, design system), and "
        "Data (analytics, reporting, insights). Each team has a lead, 3-6 engineers, and a "
        "dedicated product manager. Cross-team collaboration happens through weekly syncs "
        "and an all-hands demo on Fridays."
    )

    pdf.section_title("Tools & Access")
    pdf.bullet("Slack -- primary communication (channel naming: #team-*, #proj-*)")
    pdf.bullet("GitHub -- all code, PRs, and project boards")
    pdf.bullet("Notion -- internal docs, runbooks, meeting notes")
    pdf.bullet("Linear -- task tracking and sprint planning")
    pdf.bullet("1Password -- team shared vaults and secrets")
    pdf.bullet("Vercel / Render -- deployment dashboards (admin only)")

    pdf.section_title("Engineering Ramp-Up Goals")
    pdf.body_text(
        "By week 2: submit 3+ PRs, understand the interview graph state machine. "
        "By week 4: own a small feature end-to-end, be on-call rotation ready. "
        "By week 8: lead a medium-sized project, participate in design reviews."
    )

    return pdf


def make_interview_rubrics():
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, "Nova AI -- Interview Scoring Rubrics")
    pdf.ln(12)

    pdf.section_title("Scoring Scale (1-10)")
    pdf.body_text(
        "All competencies are scored on a 1-10 scale. Scores are normalized across interviewers "
        "using an automated calibration model."
    )
    pdf.bullet("1-3: Below expectations -- significant gaps in knowledge or skill")
    pdf.bullet("4-5: Developing -- meets some expectations with notable gaps")
    pdf.bullet("6-7: Proficient -- solid foundation, meets role requirements")
    pdf.bullet("8-9: Advanced -- deep expertise, exceeds expectations")
    pdf.bullet("10: Exceptional -- world-class, rare depth and breadth")

    pdf.section_title("Competency: Problem Solving (Weight: 25%)")
    pdf.body_text(
        "Evaluates structured thinking, decomposition of complex problems, and ability to "
        "reason through ambiguity."
    )
    pdf.bullet("Clarity of approach -- How well does the candidate structure their solution?")
    pdf.bullet("Edge case handling -- Do they naturally consider boundary conditions?")
    pdf.bullet("Trade-off awareness -- Do they discuss time/space complexity or design trade-offs?")
    pdf.bullet("Iteration speed -- How quickly do they refine their initial approach?")

    pdf.section_title("Competency: Technical Knowledge (Weight: 25%)")
    pdf.body_text(
        "Depth and breadth of domain-specific knowledge relevant to the role."
    )
    pdf.bullet("Core CS fundamentals (data structures, algorithms, design patterns)")
    pdf.bullet("Language/framework proficiency relevant to the role")
    pdf.bullet("System design concepts (scalability, reliability, latency)")
    pdf.bullet("Ability to discuss recent industry trends and technologies")

    pdf.section_title("Competency: Communication (Weight: 15%)")
    pdf.body_text(
        "Clarity of explanation, active listening, and ability to articulate technical concepts."
    )
    pdf.bullet("Explains thought process clearly without prompting")
    pdf.bullet("Asks clarifying questions before diving into solutions")
    pdf.bullet("Adapts communication style to the audience")
    pdf.bullet("Provides constructive feedback in peer discussions")

    pdf.section_title("Competency: System Design (Weight: 20%)")
    pdf.body_text("Only assessed for senior roles (IC4+). Evaluates architectural thinking.")
    pdf.bullet("Requirements gathering -- identifying functional and non-functional requirements")
    pdf.bullet("High-level architecture -- components, data flow, APIs")
    pdf.bullet("Trade-off analysis -- justifying design decisions with alternatives")
    pdf.bullet("Scalability considerations -- load balancing, caching, sharding, replication")

    pdf.section_title("Competency: Coding (Weight: 10%)")
    pdf.body_text("Quality and correctness of code written during the interview.")
    pdf.bullet("Correctness -- solution passes provided test cases")
    pdf.bullet("Code quality -- readability, naming, modularity")
    pdf.bullet("Language idioms -- uses language features appropriately")
    pdf.bullet("Testing mindset -- writes or suggests test cases naturally")

    pdf.section_title("Competency: Culture Fit (Weight: 5%)")
    pdf.body_text("Alignment with Nova AI values and team dynamics.")
    pdf.bullet("Collaboration -- examples of working effectively in teams")
    pdf.bullet("Growth mindset -- openness to feedback and continuous learning")
    pdf.bullet("Inclusivity -- awareness and respect for diverse perspectives")

    return pdf


def make_api_reference():
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, "Nova AI -- Internal API Reference")
    pdf.ln(12)

    pdf.section_title("Base URL")
    pdf.body_text("All API endpoints are served under /api/v1/. Production: https://api.nova-ai.dev/api/v1/")

    pdf.section_title("Authentication")
    pdf.body_text(
        "Two authentication flows are supported:\n"
        "1. Organization users: JWT Bearer token obtained via POST /auth/login with email/password.\n"
        "2. Candidates: JWT Bearer token obtained via POST /candidates/login with interview code.\n"
        "All authenticated requests require the Authorization: Bearer header."
    )

    pdf.section_title("Key Endpoints")
    pdf.bold_text("POST /orgs/{org_id}/documents")
    pdf.body_text("Upload a knowledge document for the organization (PDF/DOCX/TXT/MD). Triggers the RAG pipeline automatically.")
    pdf.bold_text("GET /orgs/{org_id}/documents")
    pdf.body_text("List uploaded documents for the organization.")
    pdf.bold_text("GET /orgs/{org_id}/sessions")
    pdf.body_text("List interview sessions for the organization.")
    pdf.bold_text("POST /interviews/start")
    pdf.body_text("Start an interview session. Body: { org_id, job_role, mode }")
    pdf.bold_text("POST /interviews/{id}/respond")
    pdf.body_text("Submit a response (voice or text) during an active interview.")
    pdf.bold_text("GET /orgs/{id}/candidates/ranking")
    pdf.body_text("Get ranked candidate list for an organization, sorted by overall score.")

    pdf.section_title("Webhooks")
    pdf.body_text(
        "Nova AI fires webhooks for the following events: interview.completed, candidate.ranked, "
        "scorecard.ready. Configure webhook URLs in the Organization Settings panel. Payloads are "
        "signed with HMAC-SHA256 using your organization's webhook secret."
    )

    pdf.section_title("Rate Limits")
    pdf.body_text(
        "Standard tier: 1000 requests/hour per organization. Enterprise tier: 10000 requests/hour. "
        "Rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset) are included in every response."
    )

    return pdf


GENERATORS = {
    "nova_ai_company_overview.pdf": make_company_overview,
    "nova_ai_product_documentation.pdf": make_product_documentation,
    "nova_ai_engineering_practices.pdf": make_engineering_practices,
    "nova_ai_onboarding_guide.pdf": make_onboarding_guide,
    "nova_ai_interview_rubrics.pdf": make_interview_rubrics,
    "nova_ai_api_reference.pdf": make_api_reference,
}


def generate_pdfs(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, gen in GENERATORS.items():
        path = output_dir / filename
        pdf = gen()
        pdf.output(str(path))
        print(f"  Generated: {path} ({path.stat().st_size / 1024:.1f} KB)")
        paths.append(path)
    return paths


def upload_pdfs(org_id: str, api_url: str, token: str, pdf_paths: list[Path]):
    headers = {
        "Authorization": f"Bearer {token}",
    }
    results = []
    for path in pdf_paths:
        retries = 3
        last_err = None
        for attempt in range(retries):
            print(f"  Uploading {path.name} (attempt {attempt+1}/{retries})...", end=" ")
            try:
                with open(path, "rb") as f:
                    files = {"file": (path.name, f, "application/pdf")}
                    resp = httpx.post(
                        f"{api_url}/api/v1/orgs/{org_id}/documents",
                        headers=headers,
                        files=files,
                        timeout=180,
                    )
                if resp.is_success:
                    data = resp.json()
                    print(f"OK (doc_id={data.get('doc_id', '?')}, status={data.get('status', '?')})")
                    results.append((path.name, True, data.get("doc_id", "?")))
                    break
                elif resp.status_code == 502 and attempt < retries - 1:
                    print(f"502 (server cold-start, retrying in 15s...)")
                    time.sleep(15)
                    continue
                else:
                    print(f"FAILED ({resp.status_code}: {resp.text[:120]})")
                    results.append((path.name, False, resp.status_code))
                    break
            except Exception as e:
                last_err = str(e)
                if attempt < retries - 1:
                    print(f"ERROR ({e}), retrying in 15s...")
                    time.sleep(15)
                    continue
                print(f"ERROR ({e})")
                results.append((path.name, False, str(e)))
        else:
            if last_err:
                results.append((path.name, False, last_err))
        time.sleep(2)
    return results


def main():
    parser = argparse.ArgumentParser(description="Seed organization knowledge base documents")
    parser.add_argument("org_id", help="Organization ID (UUID) to upload to")
    parser.add_argument("--api-url", default=API_URL, help="Backend API base URL")
    parser.add_argument("--token", default=os.getenv("AUTH_TOKEN", ""), help="Bearer auth token")
    parser.add_argument("--output-dir", default="output", help="Temp directory for PDF generation")
    args = parser.parse_args()

    if not args.token:
        print("Error: --token is required. Set it via the argument or the AUTH_TOKEN env var.")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    print(f"[1/3] Generating PDFs...")
    pdf_paths = generate_pdfs(output_dir)

    print(f"\n  Warming up server...", end=" ")
    for i in range(6):
        try:
            r = httpx.get(f"{args.api_url}/api/v1/health", timeout=30)
            if r.is_success:
                print(f"OK (attempt {i+1})")
                break
        except Exception:
            pass
        print(f"retrying ({i+1}/6)...", end=" ")
        time.sleep(10)
    else:
        print("could not reach server, proceeding anyway")
    print()

    print(f"[2/3] Uploading to organization {args.org_id} at {args.api_url}...")
    results = upload_pdfs(args.org_id, args.api_url, args.token, pdf_paths)

    print(f"\n[3/3] Summary:")
    success = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    print(f"  Uploaded: {len(success)}/{len(results)}")
    for name, ok, detail in success:
        print(f"    OK  {name}  (doc_id={detail})")
    for name, ok, detail in failed:
        print(f"    FAIL {name}  ({detail})")

    print(f"\nDone. The RAG pipeline will process each uploaded file as a background task.")


if __name__ == "__main__":
    main()
