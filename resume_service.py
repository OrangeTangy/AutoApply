from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable
from urllib import error, request

STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'in', 'into', 'is', 'it', 'of', 'on', 'or', 'that',
    'the', 'to', 'with', 'will', 'your', 'you', 'our', 'we', 'their', 'they', 'this', 'those', 'these', 'about', 'have',
    'has', 'had', 'using', 'use', 'used', 'over', 'under', 'within', 'across', 'through', 'than', 'can', 'may', 'should',
}


@dataclass
class ExperienceEntry:
    role: str = ''
    company: str = ''
    dates: str = ''
    bullets: list[str] = field(default_factory=list)


@dataclass
class ResumeSection:
    heading: str = ''
    items: list[str] = field(default_factory=list)


@dataclass
class TailoredResume:
    name: str = 'Tailored Resume'
    headline: str = ''
    contact: list[str] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    experience: list[ExperienceEntry] = field(default_factory=list)
    projects: list[ResumeSection] = field(default_factory=list)
    education: list[ResumeSection] = field(default_factory=list)
    tailoring_notes: list[str] = field(default_factory=list)


@dataclass
class ApplicationPacket:
    company: str
    role: str
    source_url: str
    resume: TailoredResume
    latex_resume: str
    cover_note: list[str]
    review_checklist: list[str]


@dataclass
class JobLead:
    lead_id: str
    source: str
    subject: str
    received_at: str
    source_url: str
    company: str
    role: str
    description: str
    email_id: str = ''
    email_web_link: str = ''


def _normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _extract_name(lines: list[str]) -> str:
    if not lines:
        return 'Tailored Resume'
    first = lines[0]
    return first[:80]


def _extract_contact(lines: list[str]) -> list[str]:
    contacts: list[str] = []
    for line in lines[:5]:
        if '@' in line or re.search(r'\b\d{3}[-.)\s]?\d{3}[-.\s]?\d{4}\b', line) or 'linkedin.com' in line.lower():
            contacts.extend(part.strip() for part in re.split(r'[|•]', line) if part.strip())
    return contacts[:4]


def _keyword_candidates(text: str) -> list[str]:
    words = re.findall(r'[A-Za-z][A-Za-z0-9+#./-]{2,}', text)
    counts = Counter(word for word in words if word.lower() not in STOPWORDS)
    ordered = [word for word, _ in counts.most_common(30)]
    seen: set[str] = set()
    results: list[str] = []
    for word in ordered:
        key = word.lower()
        if key not in seen:
            seen.add(key)
            results.append(word)
    return results


def _extract_job_title(job_description: str) -> str:
    lines = _normalize_lines(job_description)
    for line in lines[:8]:
        if len(line.split()) <= 10:
            return line
    return 'Target Role'


def _extract_company(job_description: str) -> str:
    match = re.search(r'(?i)(?:about|at|join)\s+([A-Z][A-Za-z0-9& .-]{2,})', job_description)
    if match:
        return match.group(1).strip(' .')
    return 'Target Company'


def _pick_matching_lines(resume_lines: Iterable[str], job_description: str, limit: int = 4) -> list[str]:
    keywords = {word.lower() for word in _keyword_candidates(job_description)}
    scored: list[tuple[int, str]] = []
    for line in resume_lines:
        lowered = line.lower()
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score:
            scored.append((score, line))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    selected: list[str] = []
    for _, line in scored:
        if line not in selected:
            selected.append(line)
        if len(selected) >= limit:
            break
    return selected


def _fallback_tailor_resume(current_resume: str, job_description: str, extra_context: str = '') -> TailoredResume:
    lines = _normalize_lines(current_resume)
    resume = TailoredResume(
        name=_extract_name(lines),
        headline=_extract_job_title(job_description),
        contact=_extract_contact(lines),
    )
    matching_lines = _pick_matching_lines(lines[1:], job_description)
    job_keywords = _keyword_candidates(job_description)
    resume.skills = job_keywords[:12]
    resume.summary = [
        'Tailored from the source resume without adding new employers, dates, or credentials.',
        f'Aligned emphasis toward {resume.headline.lower()} requirements using language found in the job post.',
    ]
    if extra_context:
        resume.summary.append(f'Additional direction applied: {extra_context.strip()}')

    experience_bullets = matching_lines or lines[1:5]
    resume.experience = [
        ExperienceEntry(
            role='Relevant Experience Highlights',
            company='',
            dates='',
            bullets=experience_bullets[:6],
        )
    ]
    resume.projects = [
        ResumeSection(
            heading='Keyword Alignment',
            items=[f'Priority terms from the posting: {", ".join(job_keywords[:8]) or "No strong keywords extracted."}'],
        )
    ]
    resume.education = [ResumeSection(heading='Source Preservation', items=['Review the tailored LaTeX before submitting any application.'])]
    resume.tailoring_notes = [
        'This draft is intended for applicant review before any submission.',
        'Verify every claim still matches your real experience and the target posting.',
        f'Highest-priority company inferred from job text: {_extract_company(job_description)}.',
    ]
    return resume



def _call_openai_for_resume(current_resume: str, job_description: str, extra_context: str, model: str) -> TailoredResume | None:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None

    prompt = {
        'current_resume': current_resume,
        'job_description': job_description,
        'extra_context': extra_context,
        'instructions': [
            'Return JSON only.',
            'Tailor the resume truthfully.',
            'Do not invent employers, job titles, dates, degrees, certifications, metrics, or skills.',
            'Produce ATS-friendly bullets and a concise headline.',
        ],
        'schema': {
            'name': 'string',
            'headline': 'string',
            'contact': ['string'],
            'summary': ['string'],
            'skills': ['string'],
            'experience': [{'role': 'string', 'company': 'string', 'dates': 'string', 'bullets': ['string']}],
            'projects': [{'heading': 'string', 'items': ['string']}],
            'education': [{'heading': 'string', 'items': ['string']}],
            'tailoring_notes': ['string'],
        },
    }
    req = request.Request(
        'https://api.openai.com/v1/responses',
        data=json.dumps(
            {
                'model': model,
                'input': [
                    {
                        'role': 'user',
                        'content': [{'type': 'input_text', 'text': json.dumps(prompt)}],
                    }
                ],
                'text': {'format': {'type': 'json_object'}},
            }
        ).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    output_text = ''
    for item in payload.get('output', []):
        for content in item.get('content', []):
            if content.get('type') == 'output_text':
                output_text += content.get('text', '')
    if not output_text:
        return None
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError:
        return None

    return TailoredResume(
        name=parsed.get('name', 'Tailored Resume'),
        headline=parsed.get('headline', ''),
        contact=list(parsed.get('contact', [])),
        summary=list(parsed.get('summary', [])),
        skills=list(parsed.get('skills', [])),
        experience=[ExperienceEntry(**entry) for entry in parsed.get('experience', [])],
        projects=[ResumeSection(**section) for section in parsed.get('projects', [])],
        education=[ResumeSection(**section) for section in parsed.get('education', [])],
        tailoring_notes=list(parsed.get('tailoring_notes', [])),
    )



def tailor_resume(current_resume: str, job_description: str, extra_context: str = '', model: str = 'gpt-4.1-mini') -> TailoredResume:
    ai_result = _call_openai_for_resume(current_resume, job_description, extra_context, model)
    if ai_result is not None:
        return ai_result
    return _fallback_tailor_resume(current_resume, job_description, extra_context)



def render_resume_latex(resume: TailoredResume, source_resume: str = '') -> str:
    def escape(value: str) -> str:
        replacements = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
        }
        for src, target in replacements.items():
            value = value.replace(src, target)
        return value

    sections: list[str] = [
        r'\documentclass[11pt]{article}',
        r'\usepackage[margin=0.65in]{geometry}',
        r'\usepackage[hidelinks]{hyperref}',
        r'\usepackage{enumitem}',
        r'\setlist[itemize]{noitemsep, topsep=2pt, leftmargin=1.2em}',
        r'\pagestyle{empty}',
        r'\begin{document}',
        rf'{{\LARGE \textbf{{{escape(resume.name)}}}}}\\',
    ]
    if resume.headline:
        sections.append(rf'{escape(resume.headline)}\\')
    if resume.contact:
        sections.append(rf'{escape(" | ".join(resume.contact))}\\')

    def add_bullets(title: str, items: list[str]) -> None:
        if not items:
            return
        sections.extend([
            rf'\section*{{{escape(title)}}}',
            r'\begin{itemize}',
            *[rf'\item {escape(item)}' for item in items],
            r'\end{itemize}',
        ])

    add_bullets('Professional Summary', resume.summary)
    add_bullets('Core Skills', [', '.join(resume.skills)] if resume.skills else [])

    if resume.experience:
        sections.append(r'\section*{Professional Experience}')
        for entry in resume.experience:
            header = ' --- '.join(part for part in [entry.role, entry.company, entry.dates] if part)
            if header:
                sections.append(rf'\textbf{{{escape(header)}}}\\')
            sections.append(r'\begin{itemize}')
            sections.extend(rf'\item {escape(item)}' for item in entry.bullets)
            sections.append(r'\end{itemize}')

    for title, blocks in [('Projects', resume.projects), ('Education', resume.education)]:
        if not blocks:
            continue
        sections.append(rf'\section*{{{escape(title)}}}')
        for block in blocks:
            if block.heading:
                sections.append(rf'\textbf{{{escape(block.heading)}}}\\')
            sections.append(r'\begin{itemize}')
            sections.extend(rf'\item {escape(item)}' for item in block.items)
            sections.append(r'\end{itemize}')

    add_bullets('Tailoring Notes', resume.tailoring_notes)
    if source_resume.strip():
        sections.extend([
            r'\section*{Review Reminder}',
            r'Before submitting, compare this draft against your source LaTeX resume and remove anything inaccurate.',
        ])
    sections.append(r'\end{document}')
    return '\n'.join(sections) + '\n'



def packet_to_json(packet: ApplicationPacket) -> dict:
    return {
        'company': packet.company,
        'role': packet.role,
        'source_url': packet.source_url,
        'resume': asdict(packet.resume),
        'latex_resume': packet.latex_resume,
        'cover_note': packet.cover_note,
        'review_checklist': packet.review_checklist,
    }



def save_json(path: str | Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
