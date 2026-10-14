// Frame quality checks. Run with: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { frameStats, judgeFrame } from "../web/quality.js";

const W = 40, H = 30;
const image = (pixel) => {
  const gray = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) gray[y * W + x] = pixel(x, y);
  return gray;
};
const judge = (pixel) => judgeFrame(frameStats(image(pixel), W, H));
// A scene with hard edges: 4-pixel squares of grey 60 and 200.
const checks = (x, y) => ((Math.floor(x / 4) + Math.floor(y / 4)) % 2 ? 200 : 60);

test("a sharp scene with normal light is fine", () => {
  assert.equal(judge(checks), "ok");
});

test("a dark frame is not sent", () => {
  assert.equal(judge((x, y) => Math.round(checks(x, y) * 0.12)), "dark");
});

test("a dark scene with bright lights in it is still described", () => {
  // Mostly black, with bright spots: low brightness but plenty of contrast and edges.
  assert.equal(judge((x, y) => (x % 10 < 2 && y % 10 < 2 ? 255 : 5)), "ok");
});

test("a covered lens or blank wall is not sent", () => {
  assert.equal(judge(() => 140), "uniform");
  assert.equal(judge((x) => 140 + (x % 2)), "uniform");
});

test("a smooth, edgeless frame counts as blurred", () => {
  assert.equal(judge((x, y) => 60 + 3 * x + 2 * y), "blurry");
});

test("the measurements", () => {
  const flat = frameStats(image(() => 100), W, H);
  assert.deepEqual(flat, { brightness: 100, contrast: 0, sharpness: 0 });
  const half = frameStats(image((x) => (x < W / 2 ? 0 : 200)), W, H);
  assert.equal(half.brightness, 100);
  assert.equal(half.contrast, 100);
  assert.ok(half.sharpness > 0);
});
