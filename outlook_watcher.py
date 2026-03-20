from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request

from resume_service import ApplicationPacket, JobLead, packet_to_json, render_resume_latex, save_json, tailor_resume
from pdf_renderer import render_resume_pdf

DEFAULT_GRAPH_ROOT = 'https://graph.microsoft.com/v1.0'
URL_PATTERN = re.compile(r'https?://[^\s"\'<>]+')


class OutlookPollingError(RuntimeError):
    pass


class OutlookHandshakeWatcher:
    def __init__(self, token: str, graph_root: str = DEFAULT_GRAPH_ROOT):
        self.token = token
        self.graph_root = graph_root.rstrip('/')

    def _request_json(self, path: str) -> dict:
        req = request.Request(
            f'{self.graph_root}{path}',
            headers={
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/json',
            },
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))
        except error.HTTPError as exc:
            raise OutlookPollingError(f'Graph request failed with HTTP {exc.code}: {exc.reason}') from exc
        except (error.URLError, json.JSONDecodeError) as exc:
            raise OutlookPollingError(f'Unable to reach Microsoft Graph: {exc}') from exc

    def fetch_messages(self, limit: int = 10) -> list[dict]:
        query = parse.urlencode(
            {
                '$top': str(limit),
                '$orderby': 'receivedDateTime desc',
                '$select': 'id,subject,receivedDateTime,body,bodyPreview,webLink',
            }
        )
        payload = self._request_json(f'/me/mailFolders/inbox/messages?{query}')
        return list(payload.get('value', []))

    def extract_job_leads(self, messages: Iterable[dict]) -> list[JobLead]:
        leads: list[JobLead] = []
        for message in messages:
            body = ((message.get('body') or {}).get('content') or '')
            preview = message.get('bodyPreview') or ''
            urls = [url.rstrip(').,') for url in URL_PATTERN.findall(body + '\n' + preview)]
            if not urls:
                continue
            handshake_urls = [url for url in urls if 'joinhandshake.com' in url or 'app.joinhandshake.com' in url]
            candidate_urls = handshake_urls or urls[:1]
            description = re.sub(r'<[^>]+>', ' ', body)
            subject = message.get('subject') or 'Job lead'
            role = subject.split(' at ')[0].strip() if ' at ' in subject else subject
            company = subject.split(' at ')[1].strip() if ' at ' in subject else 'Target Company'
            for index, url in enumerate(candidate_urls, start=1):
                leads.append(
                    JobLead(
                        lead_id=f"{message.get('id', 'msg')}-{index}",
                        source='outlook',
                        subject=subject,
                        received_at=message.get('receivedDateTime', ''),
                        source_url=url,
                        company=company,
                        role=role,
                        description=description[:12000],
                        email_id=message.get('id', ''),
                        email_web_link=message.get('webLink', ''),
                    )
                )
        return leads



def _slug(value: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', value.lower()).strip('-')
    return slug or 'job'



def load_seen_ids(state_path: Path) -> set[str]:
    if not state_path.exists():
        return set()
    try:
        payload = json.loads(state_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return set()
    return set(payload.get('seen_ids', []))



def save_seen_ids(state_path: Path, seen_ids: set[str]) -> None:
    save_json(state_path, {'seen_ids': sorted(seen_ids)})



def build_application_packet(base_resume: str, lead: JobLead, extra_context: str = '', model: str = 'gpt-4.1-mini') -> ApplicationPacket:
    tailored = tailor_resume(base_resume, lead.description or lead.subject, extra_context=extra_context, model=model)
    latex_resume = render_resume_latex(tailored, source_resume=base_resume)
    cover_note = [
        f'Review the posting for {lead.role} at {lead.company} before submitting anything.',
        'Use the attached tailored resume as a draft and confirm every bullet remains factual.',
        f'Application source: {lead.source_url}',
    ]
    checklist = [
        'Open the Handshake or employer application page.',
        'Verify work authorization, location, compensation, and required years of experience.',
        'Compile the LaTeX resume and preview the PDF for formatting issues.',
        'Submit manually after final review.',
    ]
    return ApplicationPacket(
        company=lead.company,
        role=lead.role,
        source_url=lead.source_url,
        resume=tailored,
        latex_resume=latex_resume,
        cover_note=cover_note,
        review_checklist=checklist,
    )



def save_application_packet(output_dir: Path, lead: JobLead, packet: ApplicationPacket) -> dict[str, str]:
    folder = output_dir / f'{_slug(lead.company)}-{_slug(lead.role)}'
    folder.mkdir(parents=True, exist_ok=True)
    latex_path = folder / 'tailored_resume.tex'
    pdf_path = folder / 'tailored_resume.pdf'
    json_path = folder / 'application_packet.json'
    lead_path = folder / 'lead.json'

    latex_path.write_text(packet.latex_resume, encoding='utf-8')
    pdf_path.write_bytes(render_resume_pdf(packet.resume))
    save_json(json_path, packet_to_json(packet))
    save_json(lead_path, asdict(lead))

    return {
        'folder': str(folder),
        'latex': str(latex_path),
        'pdf': str(pdf_path),
        'packet': str(json_path),
        'lead': str(lead_path),
    }



def poll_outlook_and_prepare_packets(
    resume_path: str | Path,
    output_dir: str | Path,
    state_path: str | Path,
    poll_interval: int = 300,
    max_messages: int = 10,
    run_once: bool = False,
    extra_context: str = '',
    model: str = 'gpt-4.1-mini',
) -> int:
    token = os.getenv('OUTLOOK_GRAPH_TOKEN', '').strip()
    if not token:
        raise OutlookPollingError('OUTLOOK_GRAPH_TOKEN is required to poll Outlook via Microsoft Graph.')

    resume_text = Path(resume_path).read_text(encoding='utf-8')
    output_dir = Path(output_dir)
    state_path = Path(state_path)
    watcher = OutlookHandshakeWatcher(token=token)
    seen_ids = load_seen_ids(state_path)

    while True:
        messages = watcher.fetch_messages(limit=max_messages)
        leads = watcher.extract_job_leads(messages)
        new_leads = [lead for lead in leads if lead.lead_id not in seen_ids]

        for lead in new_leads:
            packet = build_application_packet(resume_text, lead, extra_context=extra_context, model=model)
            paths = save_application_packet(output_dir, lead, packet)
            print(f"Prepared reviewed application packet for {lead.role} at {lead.company}: {paths['folder']}")
            seen_ids.add(lead.lead_id)

        save_seen_ids(state_path, seen_ids)

        if run_once:
            return len(new_leads)
        time.sleep(max(poll_interval, 30))
