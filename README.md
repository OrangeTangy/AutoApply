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

## File setup and what to run

If you just cloned the repo, a practical local setup looks like this:

```text
AutoApply/
  README.md
  main.py
  generate.py
  resume_service.py
  outlook_watcher.py
  pdf_renderer.py
  index.html
  app.js
  styles.css
  resume.tex
  job.txt
  artifacts/
```

You need to create the following yourself before running the CLI:

- `resume.tex` or another resume file path: your master resume source
- `job.txt` if you want to test one-off tailoring from a saved job description
- `artifacts/` is optional to create manually because the CLI will create parent folders for output files automatically

For example, from the repo root:

```bash
cat > resume.tex <<'EOF'
Jane Doe
jane@example.com | Austin, TX | linkedin.com/in/janedoe
Backend engineer with Python, APIs, and cloud systems.
Built REST APIs in Python and FastAPI.
Improved test automation and CI pipelines.
EOF

cat > job.txt <<'EOF'
Backend Software Engineer at ExampleCo
Build Python APIs, improve CI/CD, and support cloud infrastructure.
Experience with SQL, AWS, and FastAPI is preferred.
EOF
```

Important:

- Run commands from the repository root, the same folder that contains `main.py`.
- The main runnable entry point is the CLI: `python main.py ...`.
- `generate.py` is an HTTP handler module for deployment wiring; it is not the primary local entry point by itself.
- The simplest way to verify everything works is to run the `tailor` command first.

## The fastest way to run it

If you want to confirm the project works with the least setup, do this:

```bash
python main.py tailor \
  --resume-file resume.tex \
  --job-file job.txt \
  --output-pdf artifacts/tailored_resume.pdf \
  --output-tex artifacts/tailored_resume.tex \
  --output-json artifacts/result.json
```

If that succeeds, open:

- `artifacts/tailored_resume.pdf`
- `artifacts/tailored_resume.tex`
- `artifacts/result.json`

That is the easiest end-to-end proof that the repo is set up correctly.

## Requirements

You should have:

- Python 3.10+ installed.
- A base resume file in plain text or LaTeX.
- Optional: `OPENAI_API_KEY` if you want model-assisted tailoring instead of the local heuristic fallback.
- Required for inbox polling: `OUTLOOK_GRAPH_TOKEN` with Microsoft Graph access to read your inbox.

Set environment variables like this:

```bash
export OPENAI_API_KEY=your_openai_key_here
export OUTLOOK_GRAPH_TOKEN=your_graph_token_here
```

If `OPENAI_API_KEY` is missing, the app still works using the built-in local tailoring logic.
If `OUTLOOK_GRAPH_TOKEN` is missing, the one-off `tailor` command still works, but `watch-inbox` will not.

## Quick start

### 1. Prepare your files

Create or locate:

- your current resume file, for example `resume.tex`
- a sample or real job description file, for example `job.txt`

Example `job.txt`:

```text
Backend Software Engineer at ExampleCo
Build Python APIs, improve CI/CD, and support cloud infrastructure.
Experience with SQL, AWS, and FastAPI is preferred.
```

### 2. Generate one tailored resume packet

Run:

```bash
python main.py tailor \
  --resume-file resume.tex \
  --job-file job.txt \
  --output-pdf artifacts/tailored_resume.pdf \
  --output-tex artifacts/tailored_resume.tex \
  --output-json artifacts/result.json
```

What this does:

- reads your current resume from `--resume-file`
- reads the target job description from `--job-file`
- generates a tailored resume structure
- writes a PDF, LaTeX file, and JSON summary into `artifacts/`

What you should review after it runs:

- `artifacts/tailored_resume.pdf`: final rendered resume draft
- `artifacts/tailored_resume.tex`: editable ATS-friendly LaTeX version
- `artifacts/result.json`: structured data, extracted skills, notes, and base64 PDF payload

### 3. Continuously watch your Outlook inbox

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

This command will:

- poll recent Outlook inbox messages
- extract Handshake links first when available
- fall back to the first detected URL in the email if no Handshake link is found
- create a per-job application packet for each new message lead
- remember processed message IDs in a state file so the same lead is not reprocessed every cycle

Helpful flags:

- `--run-once`: poll one time and exit.
- `--poll-interval 300`: change the interval in seconds.
- `--max-messages 20`: inspect more recent emails each cycle.
- `--extra-context "highlight internships and API work"`: apply repeated tailoring guidance.
- `--state-file artifacts/outlook_jobs/state.json`: override where processed lead IDs are stored.

Example one-shot inbox run for testing:

```bash
python main.py watch-inbox \
  --resume-file resume.tex \
  --output-dir artifacts/outlook_jobs \
  --run-once
```

### 4. Review the generated packet for each job

Each generated job folder contains:

- `tailored_resume.tex`
- `tailored_resume.pdf`
- `application_packet.json`
- `lead.json`

Typical folder shape:

```text
artifacts/outlook_jobs/
  exampleco-backend-software-engineer/
    tailored_resume.tex
    tailored_resume.pdf
    application_packet.json
    lead.json
```

Use those files like this:

- open `lead.json` to see the source link and email metadata
- open `application_packet.json` to review the generated summary, checklist, and notes
- edit `tailored_resume.tex` if you want to refine wording or formatting
- use `tailored_resume.pdf` as the submission-ready draft after your review

## Running the frontend vs. running the CLI

There are two different ways to use this repo:

### 1. CLI mode (recommended for local use)

Use the CLI when you want to run the project directly on your machine right now.
That means using commands like:

```bash
python main.py tailor ...
python main.py watch-inbox ...
```

This is the most direct and fully documented local workflow.

### 2. Frontend/API mode

The browser UI consists of:

- `index.html`
- `app.js`
- `styles.css`

That UI sends a request to `/api/generate`, which is backed by `generate.py`.
So for the browser flow to work, you need to serve the frontend and mount `generate.py` behind an `/api/generate` route in a compatible web/serverless environment.

In other words:

- if you want something you can run immediately from this repo, use the CLI
- if you want the browser experience, you need to deploy or locally wire the HTTP handler environment around `generate.py`
- there is no separate all-in-one local web-server command documented in this repo today; the CLI is the supported direct local path

## Frontend flow

The browser UI is meant for one-off generation when you want to paste content manually.

Open the site, paste your current resume or LaTeX source, paste the job description, and submit the form.
The app will return:

- a tailored PDF,
- a tailored LaTeX file,
- a concise summary of changes,
- a review reminder before submission,
- an inline LaTeX preview in the browser.

## Command reference

### `python main.py tailor`

Use this when you already have a job description and want one reviewed resume packet.

Main options:

- `--resume-file`: required path to your current resume text or LaTeX source
- `--job-file`: required path to the target job description text file
- `--extra-context`: optional additional tailoring instructions
- `--model`: OpenAI model name when `OPENAI_API_KEY` is set
- `--output-pdf`: where to write the generated PDF
- `--output-tex`: where to write the generated LaTeX
- `--output-json`: where to write the JSON payload

### `python main.py watch-inbox`

Use this when you want the tool to keep checking your Outlook inbox for new job emails.

Main options:

- `--resume-file`: required path to your base resume
- `--output-dir`: directory where per-job folders will be written
- `--state-file`: path to the processed-message state file
- `--poll-interval`: seconds between inbox polls
- `--max-messages`: how many recent inbox emails to inspect each cycle
- `--run-once`: do one cycle and exit
- `--extra-context`: repeated tailoring guidance applied to every job
- `--model`: OpenAI model name when `OPENAI_API_KEY` is set

## Typical workflow

A practical way to use this repo is:

1. Keep your master resume in `resume.tex`.
2. Test the tailoring pipeline with `python main.py tailor` on one job description.
3. Start the background watcher with `python main.py watch-inbox --resume-file resume.tex --output-dir artifacts/outlook_jobs`.
4. When a new Handshake or employer email arrives, open the generated folder for that job.
5. Review the `.tex`, `.pdf`, and `.json` artifacts.
6. Make any manual edits you want.
7. Submit the application yourself after verifying everything is accurate.

## Notes

- If `OPENAI_API_KEY` is present, the tailoring flow will try the OpenAI Responses API first and fall back to a deterministic local heuristic if that request fails.
- The prompt explicitly tells the model **not** to invent experience, credentials, or achievements.
- The Outlook worker currently extracts Handshake links first when present, then falls back to the first URL in the message.
- This repo prepares application materials; it does not promise reliable one-click submission across arbitrary employer sites.
