// DrishtiAI page logic: camera capture, describe requests, speech playback, shortcuts.
import { THUMB_SIZE, toGray, frameDifference, shouldDescribe } from "./gate.js";

const TEXT = {
  en: {
    mode: "Mode", surroundings: "Surroundings", read: "Read", find: "Find",
    findLabel: "What are you looking for?", describe: "Describe now", stop: "Stop speech",
    auto: "Auto-monitor (experimental)", volume: "Volume", warning: "Warning",
    raw: "Model output (JSON)",
    autoNote: "Auto-monitor only looks again when the picture changes. It can miss things. It is not continuous hazard detection.",
    fallbackNote: "Rough description. The model's structured answer was invalid, so no hazards could be checked.",
    disclaimer: "DrishtiAI is an experimental aid. It can be wrong or miss hazards. It does not replace a cane, a guide dog or a human guide.",
    ready: "Ready. Press Space to describe.", looking: "Looking…", speaking: "Speaking…",
    spoken: "Done.", stopped: "Speech stopped.", queued: "One moment, finishing the current look.",
    nothingNew: "Nothing new to say.", modeNow: "Mode:", autoOn: "Auto-monitor on.", autoOff: "Auto-monitor off.",
    needTarget: "Type what you are looking for, then press Enter.",
    noCamera: "No camera. Allow camera access in the browser, then reload the page.",
    cameraStarting: "The camera is still starting. Try again in a moment.",
    serverDown: "The DrishtiAI server is not responding. Restart it with: python -m drishti",
    noVoice: "No offline voice is installed, so this was not spoken:",
    playFailed: "The audio could not be played, so this was not spoken:",
    modelReady: "ready (local)", languageName: "English",
    languageLabel: "Language: English. Press to switch to Hindi.",
  },
  hi: {
    mode: "मोड", surroundings: "आसपास", read: "पढ़ो", find: "खोजो",
    findLabel: "आप क्या खोज रहे हैं?", describe: "अभी बताओ", stop: "आवाज़ रोको",
    auto: "ऑटो-निगरानी (प्रयोगात्मक)", volume: "आवाज़", warning: "चेतावनी",
    raw: "मॉडल का उत्तर (JSON)",
    autoNote: "ऑटो-निगरानी तभी दोबारा देखती है जब तस्वीर बदलती है। इससे चीज़ें छूट सकती हैं। यह लगातार ख़तरा पहचानने की सुविधा नहीं है।",
    fallbackNote: "मोटा विवरण। मॉडल का उत्तर सही ढाँचे में नहीं था, इसलिए ख़तरों की जाँच नहीं हो सकी।",
    disclaimer: "DrishtiAI एक प्रयोगात्मक सहायक है। यह ग़लत हो सकता है या ख़तरे छोड़ सकता है। यह छड़ी, गाइड डॉग या इंसानी मदद की जगह नहीं ले सकता।",
    ready: "तैयार। बताने के लिए Space दबाएँ।", looking: "देख रहा हूँ…", speaking: "बोल रहा हूँ…",
    spoken: "हो गया।", stopped: "आवाज़ रोक दी।", queued: "एक पल, अभी देख रहा हूँ।",
    nothingNew: "कुछ नया नहीं है।", modeNow: "मोड:", autoOn: "ऑटो-निगरानी चालू।", autoOff: "ऑटो-निगरानी बंद।",
    needTarget: "लिखें कि क्या खोजना है, फिर Enter दबाएँ।",
    noCamera: "कैमरा नहीं मिला। ब्राउज़र में कैमरे की अनुमति दें, फिर पेज दोबारा खोलें।",
    cameraStarting: "कैमरा अभी चालू हो रहा है। थोड़ी देर में फिर कोशिश करें।",
    serverDown: "DrishtiAI सर्वर जवाब नहीं दे रहा। इसे दोबारा चलाएँ: python -m drishti",
    noVoice: "ऑफ़लाइन आवाज़ इंस्टॉल नहीं है, इसलिए यह बोला नहीं गया:",
    playFailed: "ऑडियो नहीं चल सका, इसलिए यह बोला नहीं गया:",
    modelReady: "तैयार (लोकल)", languageName: "हिन्दी",
    languageLabel: "भाषा: हिन्दी। अंग्रेज़ी के लिए दबाएँ।",
  },
};

const $ = (id) => document.getElementById(id);
const els = {
  video: $("video"), cameraNote: $("camera-note"), modelState: $("model-state"),
  findRow: $("find-row"), target: $("target"), describe: $("describe"), stop: $("stop"),
  language: $("language"), languageName: $("language-name"), auto: $("auto"), volume: $("volume"),
  status: $("status"), hazards: $("hazards"), hazardList: $("hazard-list"),
  fallbackNote: $("fallback-note"), spoken: $("spoken"), meta: $("meta"), raw: $("raw"),
  modeButtons: [...document.querySelectorAll("[data-mode]")],
};

const state = {
  mode: "surroundings",
  lang: "en",
  auto: false,
  busy: false,          // a describe request is in flight
  speaking: false,
  queuedManual: false,  // Space was pressed while a request was in flight
  cameraFailed: false,
  lastThumb: null,      // grey thumbnail of the last frame sent to the model
  lastCallAt: 0,
  threshold: 12,
  minIntervalMs: 4000,
  speechRun: 0,         // bumped to cancel whatever is being spoken
};

const audio = new Audio();
const frameCanvas = document.createElement("canvas");
const thumbCanvas = document.createElement("canvas");
thumbCanvas.width = thumbCanvas.height = THUMB_SIZE;

const t = (key) => TEXT[state.lang][key];

function setStatus(text, kind = "idle") {
  els.status.textContent = text;
  els.status.dataset.state = kind;
}

function applyLanguage() {
  document.documentElement.lang = state.lang;
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  els.languageName.textContent = t("languageName");
  els.language.setAttribute("aria-label", t("languageLabel"));
}

// ---- Camera -------------------------------------------------------------------

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 } },
      audio: false,
    });
    els.video.srcObject = stream;
    await els.video.play();
  } catch (err) {
    state.cameraFailed = true;
    els.cameraNote.hidden = false;
    els.cameraNote.textContent = t("noCamera");
    setStatus(t("noCamera"), "error");
  }
}

function currentThumb() {
  const ctx = thumbCanvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(els.video, 0, 0, THUMB_SIZE, THUMB_SIZE);
  return toGray(ctx.getImageData(0, 0, THUMB_SIZE, THUMB_SIZE).data);
}

// True once the camera is delivering frames.
const cameraReady = () => !state.cameraFailed && els.video.videoWidth > 0;

// A JPEG of the current frame, at most 768 px on its longer side (smaller is faster).
function captureFrame() {
  const scale = Math.min(1, 768 / Math.max(els.video.videoWidth, els.video.videoHeight));
  frameCanvas.width = Math.round(els.video.videoWidth * scale);
  frameCanvas.height = Math.round(els.video.videoHeight * scale);
  frameCanvas.getContext("2d").drawImage(els.video, 0, 0, frameCanvas.width, frameCanvas.height);
  return frameCanvas.toDataURL("image/jpeg", 0.8);
}

// ---- Describe -----------------------------------------------------------------

async function describe({ auto = false } = {}) {
  if (!cameraReady()) {
    if (!auto) setStatus(t(state.cameraFailed ? "noCamera" : "cameraStarting"), "error");
    return;
  }
  const target = els.target.value.trim();
  if (state.mode === "find" && !target) {
    if (!auto) {
      setStatus(t("needTarget"), "error");
      els.target.focus();
    }
    return;
  }
  if (state.busy) {
    // Never run two inferences at once. A manual press is remembered and runs next.
    if (!auto) {
      state.queuedManual = true;
      setStatus(t("queued"), "busy");
    }
    return;
  }

  state.busy = true;
  els.describe.setAttribute("aria-busy", "true");
  if (!auto) stopSpeech(false);
  setStatus(t("looking"), "busy");

  state.lastThumb = currentThumb();
  state.lastCallAt = performance.now();
  const started = performance.now();
  let data = null;
  try {
    const response = await fetch("/api/describe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: captureFrame(), mode: state.mode, lang: state.lang, target, auto }),
    });
    data = await response.json();
  } catch (err) {
    data = null;
  }
  const roundTripMs = performance.now() - started;
  state.busy = false;
  els.describe.removeAttribute("aria-busy");

  if (state.queuedManual) {
    // This answer is stale: the user asked again while it was in flight.
    state.queuedManual = false;
    describe();
    return;
  }
  if (!data || !data.status) {
    setStatus(t("serverDown"), "error");
    return;
  }
  if (data.status === "error") {
    setStatus([data.error.message, data.error.fix].filter(Boolean).join(" "), "error");
    return;
  }
  const hasSpeech = data.speech.hazards.length + data.speech.rest.length > 0;
  if (!hasSpeech) {
    // Automatic frame with nothing that was not already said recently.
    setStatus(t("nothingNew"), "done");
    return;
  }
  show(data, roundTripMs);
  await speak(data);
}

function show(data, roundTripMs) {
  els.hazardList.replaceChildren(...data.speech.hazards.map((sentence) => {
    const item = document.createElement("li");
    item.textContent = sentence;
    return item;
  }));
  els.hazards.hidden = data.speech.hazards.length === 0;
  els.fallbackNote.hidden = data.status !== "fallback";
  els.spoken.textContent = data.speech.rest.join("\n");
  els.spoken.lang = data.lang;
  const seconds = (ms) => (ms / 1000).toFixed(1) + " s";
  els.meta.textContent =
    `${data.model} · model ${seconds(data.inference_ms)} · round trip ${seconds(roundTripMs)}` +
    (data.retries ? ` · retries ${data.retries}` : "");
  els.raw.textContent = JSON.stringify(
    data.find_result ? { ...data.scene, find_result: data.find_result } : data.scene, null, 2);
}

// ---- Speech -------------------------------------------------------------------

async function fetchAudio(text, lang) {
  try {
    const response = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang }),
    });
    return response.ok ? await response.blob() : null;
  } catch (err) {
    return null;
  }
}

// Resolves true when the clip finished (or was stopped), false if it could not be played.
function play(blob) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(blob);
    const done = (ok) => {
      audio.onended = audio.onerror = audio.onpause = null;
      URL.revokeObjectURL(url);
      resolve(ok);
    };
    audio.onended = () => done(true);
    audio.onerror = () => done(false);
    audio.onpause = () => { if (!audio.ended) done(true); };
    audio.src = url;
    audio.volume = Number(els.volume.value);
    audio.play().catch(() => done(false));
  });
}

async function speak(data) {
  // Hazards are synthesised as their own clip so the warning starts as early as possible.
  const parts = [data.speech.hazards.join(" "), data.speech.rest.join(" ")].filter(Boolean);
  const run = ++state.speechRun;
  const clips = parts.map((text) => fetchAudio(text, data.lang));
  state.speaking = true;
  setStatus(t("speaking"), "speaking");

  let problem = "";
  for (const clip of clips) {
    const blob = await clip;
    if (run !== state.speechRun) return;  // stopped, or replaced by a newer description
    if (!blob) { problem = t("noVoice"); break; }
    const played = await play(blob);
    if (run !== state.speechRun) return;
    if (!played) { problem = t("playFailed"); break; }
  }
  state.speaking = false;
  // If it was not spoken, say so and put the text in the live region for screen readers.
  if (problem) setStatus(`${problem} ${parts.join(" ")}`, "error");
  else setStatus(t("spoken"), "done");
}

function stopSpeech(announce = true) {
  const wasSpeaking = state.speaking;
  state.speechRun++;
  state.speaking = false;
  audio.pause();
  if (announce && wasSpeaking) setStatus(t("stopped"), "idle");
}

// ---- Controls -----------------------------------------------------------------

function setMode(mode) {
  state.mode = mode;
  for (const button of els.modeButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  }
  els.findRow.hidden = mode !== "find";
  setStatus(`${t("modeNow")} ${t(mode)}`, "idle");
  if (mode === "find") els.target.focus();
}

function toggleLanguage() {
  state.lang = state.lang === "en" ? "hi" : "en";
  applyLanguage();
  setStatus(t("languageName"), "idle");
}

function toggleAuto() {
  state.auto = !state.auto;
  els.auto.setAttribute("aria-pressed", String(state.auto));
  setStatus(t(state.auto ? "autoOn" : "autoOff"), "idle");
}

// Experimental: look again only when the picture has changed enough.
function autoTick() {
  if (!state.auto || !cameraReady() || document.hidden) return;
  const go = shouldDescribe({
    difference: frameDifference(state.lastThumb, currentThumb()),
    threshold: state.threshold,
    msSinceLast: performance.now() - state.lastCallAt,
    minIntervalMs: state.minIntervalMs,
    busy: state.busy || state.speaking,
  });
  if (go) describe({ auto: true });
}

function onKeyDown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.target.matches("input[type='text'], textarea")) {
    // Typing: shortcuts are off. Enter describes, Escape leaves the field.
    if (event.key === "Enter") {
      event.preventDefault();
      describe();
    } else if (event.key === "Escape") {
      event.target.blur();
    }
    return;
  }
  const key = event.key.toLowerCase();
  if (key === " ") {
    event.preventDefault();  // Space always means "describe", whatever has focus
    if (!event.repeat) describe();
    return;
  }
  const actions = {
    "1": () => setMode("surroundings"),
    "2": () => setMode("read"),
    "3": () => setMode("find"),
    l: toggleLanguage,
    a: toggleAuto,
    escape: () => stopSpeech(),
  };
  if (actions[key]) {
    // Without this, "3" would also be typed into the Find box that it focuses.
    event.preventDefault();
    actions[key]();
  }
}

async function checkHealth() {
  try {
    const health = await (await fetch("/api/health")).json();
    state.threshold = health.change_threshold;
    state.minIntervalMs = health.min_interval_s * 1000;
    if (health.model_ok) {
      els.modelState.textContent = `${health.model} ${t("modelReady")}`;
      els.modelState.dataset.state = "ok";
    } else {
      els.modelState.textContent = health.model_message;
      els.modelState.dataset.state = "error";
      setStatus(`${health.model_message} ${health.model_fix}`, "error");
    }
  } catch (err) {
    els.modelState.textContent = t("serverDown");
    els.modelState.dataset.state = "error";
  }
}

for (const button of els.modeButtons) button.addEventListener("click", () => setMode(button.dataset.mode));
els.describe.addEventListener("click", () => describe());
els.stop.addEventListener("click", () => stopSpeech());
els.language.addEventListener("click", toggleLanguage);
els.auto.addEventListener("click", toggleAuto);
els.volume.addEventListener("input", () => { audio.volume = Number(els.volume.value); });
document.addEventListener("keydown", onKeyDown);

applyLanguage();
setStatus(t("ready"), "idle");
checkHealth();
startCamera();
setInterval(autoTick, 500);
