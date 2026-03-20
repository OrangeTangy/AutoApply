from __future__ import annotations

import base64
import json
from http.server import BaseHTTPRequestHandler

from page_solver.pdf_renderer import render_resume_pdf
from page_solver.resume_service import tailor_resume


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON payload."})
            return

        current_resume = str(payload.get("currentResume", "")).strip()
        job_description = str(payload.get("jobDescription", "")).strip()
        extra_context = str(payload.get("extraContext", "")).strip()
        model = str(payload.get("model", "gpt-4.1-mini")).strip() or "gpt-4.1-mini"

        if not current_resume or not job_description:
            self._send_json(400, {"error": "Both currentResume and jobDescription are required."})
            return

        try:
            tailored = tailor_resume(
                current_resume,
                job_description,
                extra_context=extra_context,
                model=model,
            )
            pdf_bytes = render_resume_pdf(tailored)
        except Exception as exc:  # surface operational failures to the frontend
            self._send_json(500, {"error": str(exc)})
            return

        self._send_json(
            200,
            {
                "resume": {
                    "name": tailored.name,
                    "headline": tailored.headline,
                    "contact": tailored.contact,
                    "summary": tailored.summary,
                    "skills": tailored.skills,
                    "experience": [entry.__dict__ for entry in tailored.experience],
                    "projects": [section.__dict__ for section in tailored.projects],
                    "education": [section.__dict__ for section in tailored.education],
                    "tailoringNotes": tailored.tailoring_notes,
                },
                "pdfBase64": base64.b64encode(pdf_bytes).decode("utf-8"),
                "fileName": f"{(tailored.name or 'tailored_resume').replace(' ', '_').lower()}_tailored_resume.pdf",
            },
        )
