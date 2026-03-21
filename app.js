const form = document.getElementById('resume-form');
const statusEl = document.getElementById('status');
const submitButton = document.getElementById('submitButton');
const resultSection = document.getElementById('result');
const resultName = document.getElementById('resultName');
const resultHeadline = document.getElementById('resultHeadline');
const summaryList = document.getElementById('summaryList');
const notesList = document.getElementById('notesList');
const skillsText = document.getElementById('skillsText');
const downloadLink = document.getElementById('downloadLink');
const downloadTexLink = document.getElementById('downloadTexLink');
const latexPreview = document.getElementById('latexPreview');
const reviewBanner = document.getElementById('reviewBanner');

function renderList(target, items) {
  target.innerHTML = '';
  (items || []).forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    target.appendChild(li);
  });
}

function base64ToBlob(base64, type) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i += 1) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  return new Blob([new Uint8Array(byteNumbers)], { type });
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  statusEl.textContent = 'Generating reviewed application materials…';
  resultSection.classList.add('hidden');

  const payload = {
    currentResume: document.getElementById('currentResume').value,
    jobDescription: document.getElementById('jobDescription').value,
    extraContext: document.getElementById('extraContext').value,
  };

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Failed to generate resume.');
    }

    const pdfBlob = base64ToBlob(data.pdfBase64, 'application/pdf');
    const pdfUrl = URL.createObjectURL(pdfBlob);
    const texBlob = base64ToBlob(data.latexBase64, 'application/x-tex');
    const texUrl = URL.createObjectURL(texBlob);
    const latexText = atob(data.latexBase64);

    resultName.textContent = data.resume.name || 'Tailored resume';
    resultHeadline.textContent = data.resume.headline || '';
    skillsText.textContent = (data.resume.skills || []).join(', ');
    renderList(summaryList, data.resume.summary);
    renderList(notesList, data.resume.tailoringNotes);
    downloadLink.href = pdfUrl;
    downloadLink.download = data.fileName || 'tailored_resume.pdf';
    downloadTexLink.href = texUrl;
    downloadTexLink.download = data.latexFileName || 'tailored_resume.tex';
    latexPreview.textContent = latexText;
    reviewBanner.textContent = data.reviewRequired
      ? 'Review required: confirm the LaTeX and PDF are factual before you submit anywhere.'
      : '';
    resultSection.classList.remove('hidden');
    statusEl.textContent = 'Done — your reviewed PDF and LaTeX draft are ready.';
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});
