"""Generate the Nova AI knowledge-base PDFs + a sample candidate resume for the
E2E demo page (frontend/public/demo-assets/).

The Nova PDFs reuse the same builders as scripts/seed_org_documents.py so the
demo page can upload them through the real
POST /api/v1/orgs/{org_id}/documents endpoint and land in the organization's
Pinecone namespace.
"""
import argparse
import sys
from pathlib import Path

from fpdf import FPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_org_documents import GENERATORS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "frontend" / "public" / "demo-assets"


class ResumePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, "Jordan Rivera -- Senior Python Developer", align="C")
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
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
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


def build_resume() -> FPDF:
    pdf = ResumePDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 14, "Jordan Rivera")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "Senior Python Developer | jordan.rivera@example.com | +1 (415) 555-0192")
    pdf.ln(12)

    pdf.section_title("Summary")
    pdf.body_text(
        "Senior Python developer with 8 years of experience building production APIs and AI-powered "
        "products. Deep expertise in FastAPI, asynchronous PostgreSQL, and retrieval-augmented "
        "generation with Pinecone. Led the migration of a legacy Django monolith into a modular "
        "FastAPI service and designed an LLM-based interview scoring pipeline used for 10,000+ "
        "candidate evaluations."
    )

    pdf.section_title("Skills")
    for skill in [
        "Python, FastAPI, Pydantic, SQLAlchemy (async), Alembic",
        "PostgreSQL, Redis, RabbitMQ, Docker, Kubernetes",
        "Pinecone, sentence-transformers, RAG, vector search",
        "LLM integration (OpenAI, Anthropic), prompt engineering, structured output",
        "pytest, unit/integration testing, CI/CD (GitHub Actions)",
    ]:
        pdf.bullet(skill)
    pdf.ln(2)

    pdf.section_title("Experience")
    pdf.bold_text("Senior Backend Engineer -- DataForge AI (2021 -- Present)")
    for line in [
        "Designed and shipped an LLM evaluation service scoring structured responses on competency "
        "dimensions, with evidence extraction and composite score reconciliation.",
        "Built a document knowledge base pipeline: PDF ingestion, chunking, embedding, and "
        "per-organization Pinecone namespaces with strict data isolation.",
        "Reduced p95 API latency by 40% by moving to async SQLAlchemy sessions and connection pooling.",
    ]:
        pdf.bullet(line)
    pdf.ln(2)
    pdf.bold_text("Backend Engineer -- CloudScale Systems (2018 -- 2021)")
    for line in [
        "Built REST APIs with FastAPI and PostgreSQL; introduced JWT auth with refresh-token rotation.",
        "Wrote the internal testing framework used by 6 teams; raised backend coverage from 55% to 88%.",
    ]:
        pdf.bullet(line)
    pdf.ln(2)

    pdf.section_title("Education")
    pdf.body_text(
        "B.S. Computer Science, University of Washington (2014 -- 2018). Focus: distributed systems "
        "and machine learning."
    )

    pdf.section_title("Notable Projects")
    pdf.bullet(
        "InterviewInsights -- open-source interview analysis tool that extracts behavioral evidence "
        "from transcripts and maps it to competency rubrics."
    )
    pdf.bullet(
        "VectorSearch Playbook -- internal guide on chunking strategies and namespace design for "
        "multi-tenant RAG systems."
    )

    return pdf


def main():
    parser = argparse.ArgumentParser(description="Generate demo page assets (Nova PDFs + resume)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory")
    args = parser.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/2] Generating Nova AI knowledge docs into {out}...")
    for filename, gen in GENERATORS.items():
        path = out / filename
        pdf = gen()
        pdf.output(str(path))
        print(f"  Generated: {path.name} ({path.stat().st_size / 1024:.1f} KB)")

    print("[2/2] Generating sample resume...")
    resume = build_resume()
    resume_path = out / "jordan_rivera_resume.pdf"
    resume.output(str(resume_path))
    print(f"  Generated: {resume_path.name} ({resume_path.stat().st_size / 1024:.1f} KB)")

    print(f"\nDone. {len(GENERATORS) + 1} PDFs in {out}")


if __name__ == "__main__":
    main()
