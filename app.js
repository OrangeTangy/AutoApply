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
  statusEl.textContent = 'Generating tailored resume…';
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

    const blob = base64ToBlob(data.pdfBase64, 'application/pdf');
    const pdfUrl = URL.createObjectURL(blob);

    resultName.textContent = data.resume.name || 'Tailored resume';
    resultHeadline.textContent = data.resume.headline || '';
    skillsText.textContent = (data.resume.skills || []).join(', ');
    renderList(summaryList, data.resume.summary);
    renderList(notesList, data.resume.tailoringNotes);
    downloadLink.href = pdfUrl;
    downloadLink.download = data.fileName || 'tailored_resume.pdf';
    resultSection.classList.remove('hidden');
    statusEl.textContent = 'Done — your tailored PDF is ready to download.';
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});
