from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Optional

from .pdf_renderer import render_resume_pdf
from .resume_service import tailor_resume



def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="page-solver",
        description="Generate a tailored PDF resume from a pasted resume and job description.",
    )
    parser.add_argument("--resume-file", required=True, help="Path to a text file containing the current resume")
    parser.add_argument("--job-file", required=True, help="Path to a text file containing the target job description")
    parser.add_argument("--extra-context", default="", help="Optional extra context to help with tailoring")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model to use")
    parser.add_argument("--output-json", default="artifacts/result.json", help="Where to write the JSON result")
    parser.add_argument("--output-pdf", default="artifacts/tailored_resume.pdf", help="Where to write the generated PDF")
    return parser



def cli(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    resume_text = Path(args.resume_file).read_text(encoding="utf-8")
    job_text = Path(args.job_file).read_text(encoding="utf-8")

    tailored = tailor_resume(
        resume_text,
        job_text,
        extra_context=args.extra_context,
        model=args.model,
    )
    pdf_bytes = render_resume_pdf(tailored)

    output_json = Path(args.output_json)
    output_pdf = Path(args.output_pdf)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.write_bytes(pdf_bytes)
    output_json.write_text(
        json.dumps(
            {
                "name": tailored.name,
                "headline": tailored.headline,
                "contact": tailored.contact,
                "summary": tailored.summary,
                "skills": tailored.skills,
                "experience": [entry.__dict__ for entry in tailored.experience],
                "projects": [section.__dict__ for section in tailored.projects],
                "education": [section.__dict__ for section in tailored.education],
                "tailoring_notes": tailored.tailoring_notes,
                "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {output_pdf} and {output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
