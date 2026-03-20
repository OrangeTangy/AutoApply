from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Optional

from outlook_watcher import poll_outlook_and_prepare_packets
from pdf_renderer import render_resume_pdf
from resume_service import render_resume_latex, tailor_resume



def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='auto-apply',
        description='Prepare reviewed resume/application packets from job descriptions or Outlook job emails.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    tailor = subparsers.add_parser('tailor', help='Generate a tailored PDF/LaTeX resume from local files.')
    tailor.add_argument('--resume-file', required=True, help='Path to the current resume text or LaTeX source')
    tailor.add_argument('--job-file', required=True, help='Path to a text file containing the target job description')
    tailor.add_argument('--extra-context', default='', help='Optional extra context to help with tailoring')
    tailor.add_argument('--model', default='gpt-4.1-mini', help='OpenAI model to use when OPENAI_API_KEY is set')
    tailor.add_argument('--output-json', default='artifacts/result.json', help='Where to write the JSON result')
    tailor.add_argument('--output-pdf', default='artifacts/tailored_resume.pdf', help='Where to write the generated PDF')
    tailor.add_argument('--output-tex', default='artifacts/tailored_resume.tex', help='Where to write the generated LaTeX')

    watch = subparsers.add_parser('watch-inbox', help='Poll Outlook inbox for Handshake/application links and prepare reviewed packets.')
    watch.add_argument('--resume-file', required=True, help='Path to the base LaTeX or text resume')
    watch.add_argument('--output-dir', default='artifacts/outlook_jobs', help='Directory for generated application packets')
    watch.add_argument('--state-file', default='artifacts/outlook_jobs/state.json', help='Where to store seen message ids')
    watch.add_argument('--poll-interval', type=int, default=300, help='Polling interval in seconds')
    watch.add_argument('--max-messages', type=int, default=10, help='How many recent inbox messages to inspect')
    watch.add_argument('--run-once', action='store_true', help='Process a single poll cycle and exit')
    watch.add_argument('--extra-context', default='', help='Optional tailoring instructions to apply to every packet')
    watch.add_argument('--model', default='gpt-4.1-mini', help='OpenAI model to use when OPENAI_API_KEY is set')
    return parser



def _run_tailor(args: argparse.Namespace) -> int:
    resume_text = Path(args.resume_file).read_text(encoding='utf-8')
    job_text = Path(args.job_file).read_text(encoding='utf-8')

    tailored = tailor_resume(
        resume_text,
        job_text,
        extra_context=args.extra_context,
        model=args.model,
    )
    latex_text = render_resume_latex(tailored, source_resume=resume_text)
    pdf_bytes = render_resume_pdf(tailored)

    output_json = Path(args.output_json)
    output_pdf = Path(args.output_pdf)
    output_tex = Path(args.output_tex)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.write_bytes(pdf_bytes)
    output_tex.write_text(latex_text, encoding='utf-8')
    output_json.write_text(
        json.dumps(
            {
                'name': tailored.name,
                'headline': tailored.headline,
                'contact': tailored.contact,
                'summary': tailored.summary,
                'skills': tailored.skills,
                'experience': [entry.__dict__ for entry in tailored.experience],
                'projects': [section.__dict__ for section in tailored.projects],
                'education': [section.__dict__ for section in tailored.education],
                'tailoring_notes': tailored.tailoring_notes,
                'latex': latex_text,
                'pdf_base64': base64.b64encode(pdf_bytes).decode('utf-8'),
            },
            indent=2,
        ),
        encoding='utf-8',
    )
    print(f'Wrote {output_pdf}, {output_tex}, and {output_json}')
    return 0



def cli(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == 'tailor':
        return _run_tailor(args)
    if args.command == 'watch-inbox':
        return poll_outlook_and_prepare_packets(
            resume_path=args.resume_file,
            output_dir=args.output_dir,
            state_path=args.state_file,
            poll_interval=args.poll_interval,
            max_messages=args.max_messages,
            run_once=args.run_once,
            extra_context=args.extra_context,
            model=args.model,
        )
    parser.error(f'Unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    raise SystemExit(cli())
