// Scene-change gating. Run with: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { toGray, frameDifference, shouldDescribe } from "../web/gate.js";

const flat = (value, size = 256) => new Uint8Array(size).fill(value);
const ready = { threshold: 12, msSinceLast: 10_000, minIntervalMs: 4000, busy: false };

test("toGray turns RGBA pixels into one grey value each", () => {
  const gray = toGray(new Uint8ClampedArray([255, 255, 255, 255, 0, 0, 0, 255]));
  assert.deepEqual([...gray], [255, 0]);
});

test("identical frames have no difference", () => {
  assert.equal(frameDifference(flat(100), flat(100)), 0);
});

test("the difference is the mean absolute pixel change", () => {
  assert.equal(frameDifference(flat(100), flat(130)), 30);
  const half = flat(100);
  half.fill(200, 0, 128);
  assert.equal(frameDifference(flat(100), half), 50);
});

test("with no previous frame the scene counts as changed", () => {
  assert.equal(frameDifference(null, flat(100)), 255);
});

test("a changed scene is described", () => {
  assert.equal(shouldDescribe({ ...ready, difference: 30 }), true);
});

test("a scene below the threshold is not described", () => {
  assert.equal(shouldDescribe({ ...ready, difference: 5 }), false);
});

test("the minimum interval holds back even a big change", () => {
  assert.equal(shouldDescribe({ ...ready, difference: 200, msSinceLast: 1000 }), false);
});

test("nothing is sent while a request is in flight", () => {
  assert.equal(shouldDescribe({ ...ready, difference: 200, busy: true }), false);
});
