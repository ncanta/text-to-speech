const apiBaseUrl = "http://localhost:8000";

const form = document.getElementById("tts-form");
const voiceSelect = document.getElementById("voice-select");
const textInput = document.getElementById("text-input");
const statusNode = document.getElementById("status");
const submitButton = document.getElementById("submit-button");
const audioPlayer = document.getElementById("audio-player");
const downloadButton = document.getElementById("download-button");

let currentAudioUrl = null;

function setStatus(message, tone = "default") {
  statusNode.textContent = message;
  statusNode.style.color = tone === "error" ? "#b42318" : tone === "success" ? "#176762" : "#5a6a72";
}

function buildVoiceOptions(groups) {
  voiceSelect.innerHTML = "";

  const sectionMap = [
    ["Female voices", groups.female_voices || []],
    ["Male voices", groups.male_voices || []],
  ];

  for (const [label, voices] of sectionMap) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = label;

    for (const voice of voices) {
      const option = document.createElement("option");
      option.value = voice.id;
      option.textContent = voice.name;
      if (voice.id === groups.default) {
        option.selected = true;
      }
      optgroup.appendChild(option);
    }

    voiceSelect.appendChild(optgroup);
  }
}

async function loadVoices() {
  setStatus("Loading voices...");

  try {
    const response = await fetch(`${apiBaseUrl}/voices`);
    if (!response.ok) {
      throw new Error(`Voice request failed: ${response.status}`);
    }

    const voices = await response.json();
    buildVoiceOptions(voices);
    setStatus("Voices ready.", "success");
  } catch (error) {
    setStatus(error.message, "error");
    submitButton.disabled = true;
  }
}

function releaseAudioUrl() {
  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl);
    currentAudioUrl = null;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const text = textInput.value.trim();
  if (!text) {
    setStatus("Enter some text first.", "error");
    return;
  }

  submitButton.disabled = true;
  downloadButton.hidden = true;
  setStatus("Generating speech...");
  releaseAudioUrl();

  try {
    const response = await fetch(`${apiBaseUrl}/text-to-speech`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        voice: voiceSelect.value,
      }),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: `Request failed: ${response.status}` }));
      throw new Error(errorBody.detail || "Speech generation failed.");
    }

    const audioBlob = await response.blob();
    currentAudioUrl = URL.createObjectURL(audioBlob);
    audioPlayer.src = currentAudioUrl;
    downloadButton.hidden = false;
    downloadButton.onclick = () => {
      const link = document.createElement("a");
      link.href = currentAudioUrl;
      link.download = "speech.wav";
      link.click();
    };

    await audioPlayer.play().catch(() => null);
    setStatus("Speech ready.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    submitButton.disabled = false;
  }
});

window.addEventListener("beforeunload", releaseAudioUrl);
loadVoices();