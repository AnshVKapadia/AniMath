const form = document.getElementById("generate-form");
const promptInput = document.getElementById("prompt");
const submitButton = document.getElementById("submit-button");
const statusText = document.getElementById("status-text");
const resultPanel = document.getElementById("result-panel");
const errorPanel = document.getElementById("error-panel");
const videoPreview = document.getElementById("video-preview");
const codeOutput = document.getElementById("code-output");
const downloadLink = document.getElementById("download-link");

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Generating..." : "Generate animation";
  statusText.textContent = isLoading ? "Generating code and rendering video..." : "";
}

function showError(message) {
  errorPanel.textContent = message;
  errorPanel.classList.remove("hidden");
}

function clearError() {
  errorPanel.textContent = "";
  errorPanel.classList.add("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  resultPanel.classList.add("hidden");

  const prompt = promptInput.value.trim();
  if (!prompt) {
    showError("Enter a calculus visualization request before generating.");
    return;
  }

  setLoading(true);

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const payload = await response.json();

    if (!response.ok) {
      const detail = payload.detail;
      const message =
        typeof detail === "string"
          ? detail
          : detail?.error
            ? `${detail.error}\n\n${detail.details || ""}`
            : "Generation failed.";
      throw new Error(message);
    }

    videoPreview.src = payload.videoUrl;
    videoPreview.load();
    downloadLink.href = payload.videoUrl;
    codeOutput.textContent = payload.code;
    resultPanel.classList.remove("hidden");
    statusText.textContent = payload.repaired
      ? "Rendered after one automatic repair pass."
      : "Rendered successfully.";
  } catch (error) {
    showError(error instanceof Error ? error.message : "Generation failed.");
    statusText.textContent = "";
  } finally {
    setLoading(false);
  }
});
