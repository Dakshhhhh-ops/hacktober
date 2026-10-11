// Microphone capture for voice commands.
//
// The page finds where an utterance starts and ends, converts it to 16 kHz 16-bit mono,
// and hands it to a callback. Recognition itself happens on the DrishtiAI server (Vosk),
// not in the browser, because browser speech recognition sends audio to a cloud service.

export const TARGET_RATE = 16000;

// Root-mean-square loudness of a chunk of samples (0 to 1).
export function rms(samples) {
  let total = 0;
  for (let i = 0; i < samples.length; i++) total += samples[i] * samples[i];
  return Math.sqrt(total / samples.length);
}

// Float samples at any rate -> 16-bit samples at 16 kHz, by averaging neighbours.
export function downsample(samples, fromRate, toRate = TARGET_RATE) {
  const ratio = fromRate / toRate;
  const out = new Int16Array(Math.floor(samples.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(samples.length, Math.floor((i + 1) * ratio));
    let total = 0;
    for (let j = start; j < end; j++) total += samples[j];
    const value = Math.max(-1, Math.min(1, total / Math.max(1, end - start)));
    out[i] = Math.round(value * 32767);
  }
  return out;
}

// Decides where an utterance starts and ends from the loudness of each chunk.
// feed() returns "start", "end" or null. The threshold follows the background noise.
export class UtteranceDetector {
  constructor({ minLevel = 0.012, noiseFactor = 2.5, startChunks = 2, endMs = 700, maxMs = 6000, minMs = 250 } = {}) {
    Object.assign(this, { minLevel, noiseFactor, startChunks, endMs, maxMs, minMs });
    this.noise = minLevel / noiseFactor;
    this.speaking = false;
    this.loud = 0;
    this.quietMs = 0;
    this.lengthMs = 0;
  }

  get threshold() {
    return Math.max(this.minLevel, this.noise * this.noiseFactor);
  }

  feed(level, chunkMs) {
    const isLoud = level > this.threshold;
    if (!this.speaking) {
      if (!isLoud) {
        this.noise = this.noise * 0.95 + level * 0.05;  // slowly track the room's noise
        this.loud = 0;
        return null;
      }
      if (++this.loud < this.startChunks) return null;
      this.speaking = true;
      this.quietMs = 0;
      this.lengthMs = this.loud * chunkMs;
      return "start";
    }
    this.lengthMs += chunkMs;
    this.quietMs = isLoud ? 0 : this.quietMs + chunkMs;
    if (this.quietMs >= this.endMs || this.lengthMs >= this.maxMs) {
      const longEnough = this.lengthMs - this.quietMs >= this.minMs;
      this.speaking = false;
      this.loud = 0;
      return longEnough ? "end" : "discard";
    }
    return null;
  }
}

// Start listening. onUtterance(pcm: Int16Array) is called for each thing the person says.
// Returns a function that stops listening and releases the microphone.
export async function startListening(onUtterance, onStart = () => {}) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  });
  const context = new (window.AudioContext || window.webkitAudioContext)();
  await context.resume();
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const silent = context.createGain();
  silent.gain.value = 0;  // the node must be connected to run, but must not play the mic back

  const detector = new UtteranceDetector();
  const chunkMs = (4096 / context.sampleRate) * 1000;
  const preRoll = [];   // the last few quiet chunks, so the first sound of a word is kept
  let chunks = [];

  processor.onaudioprocess = (event) => {
    const samples = new Float32Array(event.inputBuffer.getChannelData(0));
    const wasSpeaking = detector.speaking;
    const change = detector.feed(rms(samples), chunkMs);
    if (change === "start") {
      chunks = [...preRoll, samples];
      onStart();
    } else if (wasSpeaking) {
      chunks.push(samples);
    }
    if (!detector.speaking) {
      preRoll.push(samples);
      if (preRoll.length > 3) preRoll.shift();
    }
    if (change === "end") {
      const joined = new Float32Array(chunks.reduce((n, c) => n + c.length, 0));
      let offset = 0;
      for (const chunk of chunks) { joined.set(chunk, offset); offset += chunk.length; }
      onUtterance(downsample(joined, context.sampleRate));
    }
    if (change === "end" || change === "discard") chunks = [];
  };

  source.connect(processor);
  processor.connect(silent);
  silent.connect(context.destination);

  return () => {
    processor.disconnect();
    source.disconnect();
    for (const track of stream.getTracks()) track.stop();
    context.close();
  };
}
