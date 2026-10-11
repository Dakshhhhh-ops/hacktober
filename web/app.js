// DrishtiAI page logic: camera capture, describe requests, display, speech, shortcuts.
import { THUMB_SIZE, toGray, frameDifference, shouldDescribe } from "./gate.js";
import { startListening } from "./voice.js";

const TEXT = {
  en: {
    tagline: "An offline assistant that describes what is in front of you",
    mode: "Mode", surroundings: "Surroundings", read: "Read", find: "Find",
    surroundingsHint: "Hazards first, then one line about the scene",
    readHint: "Reads signs, labels and packaging",
    findHint: "Looks for one object you name",
    findLabel: "What are you looking for?", describe: "Describe now", stop: "Stop speech",
    auto: "Auto-monitor", volume: "Volume", warning: "Warning", live: "Live",
    seen: "Also seen", textRead: "Text read", findAnswer: "Search result", scene: "Scene",
    raw: "Model output (JSON)", languageHint: "switches language",
    autoNote: "Auto-monitor is experimental. It only looks again when the picture changes, so it can miss things. It is not continuous hazard detection.",
    fallbackNote: "Rough description. The model's structured answer was invalid, so no hazards could be checked.",
    disclaimer: "DrishtiAI is an experimental aid. It can be wrong or miss hazards. It does not replace a cane, a guide dog or a human guide.",
    ready: "Ready. Press Space to describe.", readyTouch: "Ready. Tap the picture to describe.",
    looking: "Looking…", speaking: "Speaking…",
    spoken: "Done.", stopped: "Speech stopped.", queued: "One moment, finishing the current look.",
    nothingNew: "Nothing new to say.", modeNow: "Mode:", autoOn: "Auto-monitor on.", autoOff: "Auto-monitor off.",
    needTarget: "Type what you are looking for, then press Enter.",
    noCamera: "No camera. Allow camera access in the browser, then reload the page.",
    cameraStarting: "The camera is still starting. Try again in a moment.",
    serverDown: "The DrishtiAI server is not responding. Restart it with: python -m drishti",
    noVoice: "No offline voice is installed, so this was not spoken:",
    playFailed: "The audio could not be played, so this was not spoken:",
    modelReady: "ready (local)", languageName: "English", languageNow: "Language: English.",
    voices: "Offline voices:", voiceMissing: "not installed (text only)",
    left: "Left", right: "Right", ahead: "Ahead", below: "Below",
    near: "near", mid: "mid distance", far: "far",
    modelTime: "model", roundTrip: "round trip", retries: "retries",
    tapHint: "Tap the picture to describe",
    voice: "Voice commands", heard: "Heard:", listening: "Listening…",
    voiceOn: "Voice commands on. Say describe, read, find, or stop.",
    voiceOff: "Voice commands off.", askTarget: "What are you looking for?",
    notUnderstood: "Sorry, I did not catch that.",
    noMic: "No microphone. Allow microphone access in the browser and try again.",
    noSpeechModel: "The offline speech model is not installed, so voice commands are unavailable.",
  },
  hi: {
    tagline: "ऑफ़लाइन सहायक जो बताता है कि आपके सामने क्या है",
    mode: "मोड", surroundings: "आसपास", read: "पढ़ो", find: "खोजो",
    surroundingsHint: "पहले ख़तरे, फिर आसपास के बारे में एक पंक्ति",
    readHint: "बोर्ड, लेबल और पैकेट पढ़ता है",
    findHint: "आपकी बताई एक चीज़ खोजता है",
    findLabel: "आप क्या खोज रहे हैं?", describe: "अभी बताओ", stop: "आवाज़ रोको",
    auto: "ऑटो-निगरानी", volume: "आवाज़", warning: "चेतावनी", live: "लाइव",
    seen: "यह भी दिखा", textRead: "पढ़ा गया पाठ", findAnswer: "खोज का नतीजा", scene: "दृश्य",
    raw: "मॉडल का उत्तर (JSON)", languageHint: "से भाषा बदलती है",
    autoNote: "ऑटो-निगरानी प्रयोगात्मक है। यह तभी दोबारा देखती है जब तस्वीर बदलती है, इसलिए चीज़ें छूट सकती हैं। यह लगातार ख़तरा पहचानने की सुविधा नहीं है।",
    fallbackNote: "मोटा विवरण। मॉडल का उत्तर सही ढाँचे में नहीं था, इसलिए ख़तरों की जाँच नहीं हो सकी।",
    disclaimer: "DrishtiAI एक प्रयोगात्मक सहायक है। यह ग़लत हो सकता है या ख़तरे छोड़ सकता है। यह छड़ी, गाइड डॉग या इंसानी मदद की जगह नहीं ले सकता।",
    ready: "तैयार। बताने के लिए Space दबाएँ।", readyTouch: "तैयार। बताने के लिए तस्वीर पर टैप करें।",
    looking: "देख रहा हूँ…", speaking: "बोल रहा हूँ…",
    spoken: "हो गया।", stopped: "आवाज़ रोक दी।", queued: "एक पल, अभी देख रहा हूँ।",
    nothingNew: "कुछ नया नहीं है।", modeNow: "मोड:", autoOn: "ऑटो-निगरानी चालू।", autoOff: "ऑटो-निगरानी बंद।",
    needTarget: "लिखें कि क्या खोजना है, फिर Enter दबाएँ।",
    noCamera: "कैमरा नहीं मिला। ब्राउज़र में कैमरे की अनुमति दें, फिर पेज दोबारा खोलें।",
    cameraStarting: "कैमरा अभी चालू हो रहा है। थोड़ी देर में फिर कोशिश करें।",
    serverDown: "DrishtiAI सर्वर जवाब नहीं दे रहा। इसे दोबारा चलाएँ: python -m drishti",
    noVoice: "ऑफ़लाइन आवाज़ इंस्टॉल नहीं है, इसलिए यह बोला नहीं गया:",
    playFailed: "ऑडियो नहीं चल सका, इसलिए यह बोला नहीं गया:",
    modelReady: "तैयार (लोकल)", languageName: "हिन्दी", languageNow: "भाषा: हिन्दी।",
    voices: "ऑफ़लाइन आवाज़ें:", voiceMissing: "इंस्टॉल नहीं (सिर्फ़ टेक्स्ट)",
    left: "बाईं ओर", right: "दाईं ओर", ahead: "सामने", below: "नीचे",
    near: "पास", mid: "थोड़ी दूर", far: "दूर",
    modelTime: "मॉडल", roundTrip: "कुल समय", retries: "दोबारा कोशिश",
    tapHint: "बताने के लिए तस्वीर पर टैप करें",
    voice: "आवाज़ से चलाएँ", heard: "सुना:", listening: "सुन रहा हूँ…",
    voiceOn: "आवाज़ से चलाना चालू। बोलें: बताओ, पढ़ो, बोतल कहां है, या बस।",
    voiceOff: "आवाज़ से चलाना बंद।", askTarget: "आप क्या खोज रहे हैं?",
    notUnderstood: "माफ़ कीजिए, समझ नहीं आया।",
    noMic: "माइक्रोफ़ोन नहीं मिला। ब्राउज़र में माइक्रोफ़ोन की अनुमति दें और फिर कोशिश करें।",
    noSpeechModel: "ऑफ़लाइन स्पीच मॉडल इंस्टॉल नहीं है, इसलिए आवाज़ से चलाना उपलब्ध नहीं है।",
  },
};
const ARROWS = { left: "←", right: "→", ahead: "↑", below: "↓" };

const $ = (id) => document.getElementById(id);
const els = {
  video: $("video"), cameraFrame: $("camera-frame"), cameraNote: $("camera-note"),
  modelState: $("model-state"),
  modeBadge: $("mode-badge"), findRow: $("find-row"), target: $("target"),
  describe: $("describe"), stop: $("stop"), auto: $("auto"), volume: $("volume"),
  status: $("status"), hazards: $("hazards"), hazardList: $("hazard-list"),
  fallbackNote: $("fallback-note"), spokenLabel: $("spoken-label"), spoken: $("spoken"),
  objectsRow: $("objects-row"), objects: $("objects"), meta: $("meta"), raw: $("raw"),
  voiceState: $("voice-state"), voice: $("voice"), heard: $("heard"),
  modeButtons: [...document.querySelectorAll("[data-mode]")],
  langButtons: [...document.querySelectorAll("[data-lang]")],
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
  voices: null,         // { en: "piper" | "espeak-ng" | null, hi: ... } from the server
  health: null,
  last: null,           // the last answer shown, kept so it can be re-worded in another language
  stopListening: null,  // set while voice commands are on
  awaitingTarget: false, // "find" was said without naming the object
  heardDuringSpeech: false,
};

const audio = new Audio();
let audioUnlocked = false;

// A tenth of a second of silence as a WAV file (8 kHz, 16-bit, mono).
function silentClip() {
  const samples = 800;
  const view = new DataView(new ArrayBuffer(44 + samples * 2));
  const ascii = (offset, text) => [...text].forEach((ch, i) => view.setUint8(offset + i, ch.charCodeAt(0)));
  ascii(0, "RIFF"); view.setUint32(4, 36 + samples * 2, true); ascii(8, "WAVEfmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 8000, true); view.setUint32(28, 16000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  ascii(36, "data"); view.setUint32(40, samples * 2, true);
  return URL.createObjectURL(new Blob([view], { type: "audio/wav" }));
}

// Phone browsers only let a page play sound that started from a touch, and the real speech
// arrives seconds after the tap. Playing silence on the first touch unlocks the player.
function unlockAudio() {
  if (audioUnlocked) return;
  audioUnlocked = true;
  audio.src = silentClip();
  audio.play().catch(() => {});
}

// A short buzz on phones that support it (most Android browsers). Ignored elsewhere.
function vibrate(pattern) {
  if (navigator.vibrate) navigator.vibrate(pattern);
}
const frameCanvas = document.createElement("canvas");
const thumbCanvas = document.createElement("canvas");
thumbCanvas.width = thumbCanvas.height = THUMB_SIZE;

const t = (key) => TEXT[state.lang][key];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setStatus(text, kind = "idle") {
  els.status.textContent = text;
  els.status.dataset.state = kind;
}

async function postJson(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return response.json();
}

// ---- Language -----------------------------------------------------------------

function applyLanguage() {
  document.documentElement.lang = state.lang;
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  for (const button of els.langButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
  }
  els.modeBadge.textContent = t(state.mode);
  els.cameraFrame.setAttribute("aria-label", t("describe"));
  showVoices();
  showModel();
}

// Say which languages really have an offline voice installed.
function showVoices() {
  if (!state.voices) return;
  const describeVoice = (lang) => `${TEXT[lang].languageName}: ${state.voices[lang] || t("voiceMissing")}`;
  els.voiceState.textContent = `${t("voices")} ${describeVoice("en")} · ${describeVoice("hi")}`;
}

function showModel() {
  const health = state.health;
  if (!health) return;
  els.modelState.textContent = health.model_ok ? `${health.model} ${t("modelReady")}` : health.model_message;
  els.modelState.dataset.state = health.model_ok ? "ok" : "error";
}

async function setLanguage(lang) {
  if (lang === state.lang) return;
  state.lang = lang;
  applyLanguage();
  setStatus(t("languageNow"), "idle");
  if (!state.last) return;
  // Re-word the answer on screen in the new language. No new model call is needed.
  stopSpeech(false);
  const previous = state.last;
  try {
    const data = await postJson("/api/render", {
      scene: previous.scene, mode: previous.mode, lang, target: previous.target,
      find_result: previous.find_result, fallback: previous.status === "fallback",
    });
    if (!data.status || data.status === "error") return;
    show({ ...data, model: previous.model, inference_ms: previous.inference_ms, retries: previous.retries },
      previous.roundTripMs);
    await speak(data);
  } catch (err) {
    // The old answer stays on screen; the next description will use the new language.
  }
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
  if (!auto) vibrate(40);  // confirms the tap was registered
  els.describe.setAttribute("aria-busy", "true");
  if (!auto) stopSpeech(false);
  setStatus(t("looking"), "busy");

  state.lastThumb = currentThumb();
  state.lastCallAt = performance.now();
  const started = performance.now();
  let data = null;
  try {
    data = await postJson("/api/describe",
      { image: captureFrame(), mode: state.mode, lang: state.lang, target, auto });
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
  if (data.speech.hazards.length + data.speech.rest.length === 0) {
    // Automatic frame with nothing that was not already said recently.
    setStatus(t("nothingNew"), "done");
    return;
  }
  if (data.hazards.length > 0) vibrate([250, 120, 250]);  // a warning can be felt as well as heard
  show(data, roundTripMs);
  await speak(data);
}

// ---- Display ------------------------------------------------------------------

function hazardCard(card) {
  const item = el("li");
  const arrow = el("span", "arrow", ARROWS[card.where]);
  arrow.setAttribute("aria-hidden", "true");
  const body = el("div");
  body.append(
    el("span", "what", card.what),
    el("span", "where", `${t(card.where)} · ${t(card.distance)}`),
  );
  item.append(arrow, body);
  return item;
}

function show(data, roundTripMs) {
  state.last = { ...data, roundTripMs };

  els.hazardList.replaceChildren(...data.hazards.map(hazardCard));
  els.hazards.hidden = data.hazards.length === 0;
  els.fallbackNote.hidden = data.status !== "fallback";

  // The main answer: the text that was read, the search result, or the scene line.
  const kind = data.status === "fallback" ? "summary" : data.mode === "surroundings" ? "summary" : data.mode;
  els.spoken.textContent = data.speech.rest.join("\n");
  els.spoken.dataset.kind = kind;
  els.spoken.dataset.find = data.find_result ? data.find_result.status : "";
  els.spokenLabel.textContent = t({ read: "textRead", find: "findAnswer", summary: "scene" }[kind]);
  els.spokenLabel.hidden = data.speech.rest.length === 0;

  const showObjects = data.mode === "surroundings" && data.status === "ok" && data.objects.length > 0;
  els.objects.replaceChildren(...(showObjects ? data.objects.map((name) => el("li", "", name)) : []));
  els.objectsRow.hidden = !showObjects;

  const seconds = (ms) => (ms / 1000).toFixed(1) + " s";
  els.meta.textContent = data.inference_ms
    ? `${data.model} · ${t("modelTime")} ${seconds(data.inference_ms)} · ${t("roundTrip")} ${seconds(roundTripMs)}`
      + (data.retries ? ` · ${t("retries")} ${data.retries}` : "")
    : data.model;
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
  if (parts.length === 0) return;
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

function setMode(mode, { focus = true } = {}) {
  state.mode = mode;
  for (const button of els.modeButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  }
  els.modeBadge.textContent = t(mode);
  els.findRow.hidden = mode !== "find";
  setStatus(`${t("modeNow")} ${t(mode)}`, "idle");
  if (mode === "find" && focus) els.target.focus();
}

// ---- Voice commands -----------------------------------------------------------

// Speak one sentence that is not a scene description, such as a question or a notice.
function say(text) {
  return speak({ lang: state.lang, speech: { hazards: [], rest: [text] } });
}

async function onUtterance(pcm) {
  // What was captured while the app itself was talking is mostly its own voice.
  const duringSpeech = state.heardDuringSpeech || state.speaking;
  state.heardDuringSpeech = false;
  // Try the page's language first, then English, so "describe" also works in Hindi mode
  // and a missing Hindi speech model does not switch voice control off.
  const installed = (state.health && state.health.voice) || { en: true };
  const languages = [...new Set([state.lang, "en"])].filter((lang) => installed[lang]);
  let result = null;
  for (const lang of languages) {
    let attempt = null;
    try {
      const response = await fetch("/api/listen?lang=" + lang, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: pcm.buffer,
      });
      if (response.ok) attempt = await response.json();
    } catch (err) {
      break;
    }
    if (!attempt || !attempt.text) continue;
    if (!result) result = attempt;  // keep the first thing heard, in case nothing is a command
    if (attempt.command) { result = attempt; break; }
  }
  if (duringSpeech && (!result || result.command !== "stop")) return;
  els.heard.hidden = false;
  if (!result) {  // noise, or nothing recognisable
    els.heard.textContent = t("listening");
    return;
  }
  const understood = result.command || (state.awaitingTarget && result.target);
  els.heard.textContent = `${t("heard")} “${result.text}”` + (understood ? "" : ` · ${t("notUnderstood")}`);
  if (understood) runCommand(result);
}

function runCommand({ command, target }) {
  if (command === "stop") {
    state.awaitingTarget = false;
    stopSpeech();
  } else if (command === "describe") {
    setMode("surroundings", { focus: false });
    describe();
  } else if (command === "read") {
    setMode("read", { focus: false });
    describe();
  } else if (command === "find" || (state.awaitingTarget && target)) {
    setMode("find", { focus: false });
    if (!target) {
      state.awaitingTarget = true;
      say(t("askTarget"));
      return;
    }
    state.awaitingTarget = false;
    els.target.value = target;
    describe();
  } else if (command === "repeat") {
    if (state.last) speak(state.last);
  } else if (command === "hindi" || command === "english") {
    setLanguage(command === "hindi" ? "hi" : "en");
  }
}

async function toggleVoice() {
  if (state.stopListening) {
    state.stopListening();
    state.stopListening = null;
    state.awaitingTarget = false;
    els.voice.setAttribute("aria-pressed", "false");
    els.heard.hidden = true;
    setStatus(t("voiceOff"), "idle");
    return;
  }
  if (state.health && state.health.voice && !state.health.voice.hi && !state.health.voice.en) {
    setStatus(t("noSpeechModel"), "error");
    return;
  }
  try {
    state.stopListening = await startListening(onUtterance, () => {
      if (state.speaking) {
        state.heardDuringSpeech = true;
      } else {
        // Show that the microphone has picked something up, before it is recognised.
        els.heard.hidden = false;
        els.heard.textContent = t("listening");
      }
    });
  } catch (err) {
    setStatus(t("noMic"), "error");
    return;
  }
  els.voice.setAttribute("aria-pressed", "true");
  say(t("voiceOn"));
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
    l: () => setLanguage(state.lang === "en" ? "hi" : "en"),
    a: toggleAuto,
    v: toggleVoice,
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
    state.health = health;
    state.threshold = health.change_threshold;
    state.minIntervalMs = health.min_interval_s * 1000;
    state.voices = health.tts;
    showVoices();
    showModel();
    if (!health.model_ok) setStatus(`${health.model_message} ${health.model_fix}`, "error");
  } catch (err) {
    els.modelState.textContent = t("serverDown");
    els.modelState.dataset.state = "error";
  }
}

for (const button of els.modeButtons) button.addEventListener("click", () => setMode(button.dataset.mode));
for (const button of els.langButtons) button.addEventListener("click", () => setLanguage(button.dataset.lang));
els.describe.addEventListener("click", () => describe());
// The whole camera picture is a Describe button: a large target that needs no aiming.
els.cameraFrame.addEventListener("click", () => describe());
els.cameraFrame.addEventListener("keydown", (event) => {
  if (event.key === "Enter") describe();
});
document.addEventListener("pointerdown", unlockAudio, { capture: true });
document.addEventListener("keydown", unlockAudio, { capture: true });
els.stop.addEventListener("click", () => stopSpeech());
els.auto.addEventListener("click", toggleAuto);
els.voice.addEventListener("click", toggleVoice);
els.volume.addEventListener("input", () => { audio.volume = Number(els.volume.value); });
document.addEventListener("keydown", onKeyDown);

applyLanguage();
// On a touch screen the instruction is to tap, not to press a key.
setStatus(t(window.matchMedia("(pointer: coarse)").matches ? "readyTouch" : "ready"), "idle");
checkHealth();
startCamera();
setInterval(autoTick, 500);
