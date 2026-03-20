# Continuous Job Intake Assistant

This repository now focuses on **continuous job-intake automation with a required human review step**.
It can:

1. Tailor a truthful resume draft from a job description.
2. Export both an ATS-friendly PDF and a LaTeX source file.
3. Poll an Outlook inbox through Microsoft Graph for Handshake or employer application links.
4. Prepare per-job application packets for review instead of blind auto-submitting.

## Why the review step matters

The automation in this repo is intentionally designed to **prepare materials for your approval**, not submit applications without you seeing them.
That keeps the workflow aligned with truthful self-representation and gives you a chance to verify compensation, location,
work authorization, and any screening questions before submitting.

## Project layout

- `index.html`, `app.js`, `styles.css`: browser UI for one-off tailoring.
- `generate.py`: simple HTTP handler for the frontend.
- `resume_service.py`: resume tailoring, LaTeX generation, and JSON helpers.
- `pdf_renderer.py`: lightweight ATS-friendly PDF rendering.
- `outlook_watcher.py`: Outlook inbox polling plus reviewed application packet generation.
- `main.py`: CLI entry point for one-off tailoring or continuous inbox polling.

## Outlook inbox polling

The watcher uses the Microsoft Graph inbox endpoint with a bearer token you provide via:

```bash
export OUTLOOK_GRAPH_TOKEN=your_graph_token_here
```

Then start the continuous worker with:

```bash
python main.py watch-inbox \
  --resume-file resume.tex \
  --output-dir artifacts/outlook_jobs
```

Helpful flags:

- `--run-once`: poll one time and exit.
- `--poll-interval 300`: change the interval in seconds.
- `--max-messages 20`: inspect more recent emails each cycle.
- `--extra-context "highlight internships and API work"`: apply repeated tailoring guidance.

Each job packet folder contains:

- `tailored_resume.tex`
- `tailored_resume.pdf`
- `application_packet.json`
- `lead.json`

## One-off tailoring from files

```bash
python main.py tailor \
  --resume-file resume.tex \
  --job-file sample_job.txt \
  --output-pdf artifacts/tailored_resume.pdf \
  --output-tex artifacts/tailored_resume.tex \
  --output-json artifacts/result.json
```

## Frontend flow

Open the site, paste your current resume or LaTeX source, paste the job description, and the app will return:

- a tailored PDF,
- a tailored LaTeX file,
- a concise summary of changes,
- a review reminder before submission.

## Notes

- If `OPENAI_API_KEY` is present, the tailoring flow will try the OpenAI Responses API first and fall back to a deterministic local heuristic if that request fails.
- The prompt explicitly tells the model **not** to invent experience, credentials, or achievements.
- The Outlook worker currently extracts Handshake links first when present, then falls back to the first URL in the message.
- This repo prepares application materials; it does not promise reliable one-click submission across arbitrary employer sites.
