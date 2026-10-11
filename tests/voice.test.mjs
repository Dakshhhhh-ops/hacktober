// Microphone helpers. Run with: node --test tests/voice.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { rms, downsample, UtteranceDetector } from "../web/voice.js";

test("rms of silence is 0 and of a full-scale square wave is 1", () => {
  assert.equal(rms(new Float32Array(100)), 0);
  assert.equal(rms(new Float32Array(100).fill(1)), 1);
});

test("downsample from 48 kHz to 16 kHz keeps one third of the samples", () => {
  const out = downsample(new Float32Array(4800).fill(0.5), 48000);
  assert.equal(out.length, 1600);
  assert.equal(out[0], Math.round(0.5 * 32767));
});

test("downsample clips values outside -1..1", () => {
  const out = downsample(new Float32Array([2, 2, 2, -2, -2, -2]), 48000);
  assert.deepEqual([...out], [32767, -32767]);
});

// Feed a list of [level, repeat] pairs in 100 ms chunks and collect what the detector reports.
function run(detector, pattern) {
  const events = [];
  for (const [level, repeat] of pattern) {
    for (let i = 0; i < repeat; i++) {
      const event = detector.feed(level, 100);
      if (event) events.push(event);
    }
  }
  return events;
}

test("speech followed by silence is one utterance", () => {
  const events = run(new UtteranceDetector(), [[0.001, 5], [0.2, 6], [0.001, 8]]);
  assert.deepEqual(events, ["start", "end"]);
});

test("a single loud click does not start an utterance", () => {
  const events = run(new UtteranceDetector(), [[0.001, 5], [0.5, 1], [0.001, 10]]);
  assert.deepEqual(events, []);
});

test("a very short sound is discarded", () => {
  const events = run(new UtteranceDetector({ minMs: 400 }), [[0.001, 5], [0.2, 2], [0.001, 8]]);
  assert.deepEqual(events, ["start", "discard"]);
});

test("a long utterance is cut at the maximum length", () => {
  const events = run(new UtteranceDetector({ maxMs: 1000 }), [[0.001, 5], [0.2, 30]]);
  assert.equal(events[0], "start");
  assert.equal(events[1], "end");
});

test("the threshold rises in a noisy room", () => {
  const detector = new UtteranceDetector();
  const quiet = detector.threshold;
  run(detector, [[0.01, 200]]);
  assert.ok(detector.threshold > quiet);
  // Steady background noise at that level is not speech.
  assert.deepEqual(run(detector, [[0.01, 20]]), []);
});
