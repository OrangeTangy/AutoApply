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



```bash
python main.py tailor \
  --resume-file resume.tex \

  --output-pdf artifacts/tailored_resume.pdf \
  --output-tex artifacts/tailored_resume.tex \
  --output-json artifacts/result.json
```



Use those files like this:

- open `lead.json` to see the source link and email metadata
- open `application_packet.json` to review the generated summary, checklist, and notes
- edit `tailored_resume.tex` if you want to refine wording or formatting
- use `tailored_resume.pdf` as the submission-ready draft after your review

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
