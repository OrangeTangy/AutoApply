# Resume Tailor for Vercel

A small web app you can deploy to Vercel that lets a user:

1. Paste their current resume.
2. Paste a target job description.
3. Generate a tailored resume with OpenAI.
4. Download the result as a PDF.

## What changed

This project is now built as a **publishable web app**, not a browser-auto-apply bot. The main flow is:

- a static frontend (`index.html`, `app.js`, `styles.css`)
- a Vercel Python serverless function (`api/generate.py`)
- shared Python helpers for prompting the LLM and rendering the PDF (`page_solver/`)

## Stack

- **Frontend:** plain HTML/CSS/JS
- **Backend:** Vercel Python Runtime via `api/generate.py`
- **LLM:** OpenAI Responses API
- **PDF generation:** built-in lightweight PDF renderer

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
export OPENAI_API_KEY=your_key_here
```

If you want to run the full Vercel experience locally, install the Vercel CLI and use:

```bash
vercel dev
```

The Vercel Python Runtime docs say your serverless functions live in the root `api/` directory, and the example local workflow is `vercel dev`. See the official docs for details: <https://vercel.com/docs/functions/runtimes/python>. The `vercel.json` file is used here only to configure the function duration and the `/api/generate` rewrite. See also: <https://vercel.com/docs/project-configuration/vercel-json>.

## Deploy to Vercel

1. Push this repo to GitHub.
2. Import the repo into Vercel.
3. Set the environment variable `OPENAI_API_KEY` in the Vercel project settings.
4. Deploy.

Once deployed, the site serves the form from `/` and the resume-generation API from `/api/generate`.

## App usage

1. Paste your current resume into the left textarea.
2. Paste the target job description into the right textarea.
3. Optionally add extra context like “keep it to one page” or “emphasize backend API work.”
4. Click **Generate tailored PDF**.
5. Download the generated PDF from the result card.

## Local CLI helper

There is also a local CLI for development/testing:

```bash
python -m page_solver.main \
  --resume-file sample_resume.txt \
  --job-file sample_job.txt \
  --output-pdf artifacts/tailored_resume.pdf \
  --output-json artifacts/result.json
```

## API contract

`POST /api/generate`

Request body:

```json
{
  "currentResume": "full pasted resume text",
  "jobDescription": "full pasted job description",
  "extraContext": "optional guidance",
  "model": "gpt-4.1-mini"
}
```

Response body:

```json
{
  "resume": {
    "name": "Jane Doe",
    "headline": "Senior Backend Engineer",
    "contact": ["jane@example.com", "Austin, TX"],
    "summary": ["..."],
    "skills": ["Python", "FastAPI"],
    "experience": [],
    "projects": [],
    "education": [],
    "tailoringNotes": ["..."]
  },
  "pdfBase64": "...",
  "fileName": "jane_doe_tailored_resume.pdf"
}
```

## Notes

- The prompt explicitly tells the model not to invent experience or credentials.
- The generated PDF is a clean, ATS-friendly layout built with a lightweight pure-Python PDF renderer.
- Because this is designed for Vercel serverless functions, keep requests reasonably sized.
