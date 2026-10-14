// End-to-end check of the real page in headless Chrome, with a photo as a fake webcam.
//
//   python -m drishti                      (in another window; Ollama running)
//   node tests/browser_check.mjs [--with-model]
//
// Needs Chrome (or set CHROME to its path), Node 22, and OpenCV for tests/fake_camera.py.
// Without --with-model it checks only what does not need the vision-language model:
// the dark-frame check, walk mode and live Find. With it, also a full description of a
// blurred frame, which takes a few seconds or, on a busy computer, a minute.
import { spawn, execFileSync } from "node:child_process";
import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const PAGE = process.env.DRISHTI_URL || "http://127.0.0.1:8000/";
const CHROME = process.env.CHROME || [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].find(existsSync);
const PYTHON = process.env.PYTHON || join(ROOT, process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const work = mkdtempSync(join(tmpdir(), "drishti-check-"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function fakeCamera(image, name, ...flags) {
  const out = join(work, `${name}.y4m`);
  execFileSync(PYTHON, [join(ROOT, "tests/fake_camera.py"), join(ROOT, image), out, ...flags]);
  return out;
}

// Open the page in Chrome with the given fake camera; returns helpers to drive it.
async function openPage(video) {
  const port = 9300 + Math.floor(Math.random() * 600);
  const chrome = spawn(CHROME, [
    "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(work, "profile-"))}`,
    "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
    `--use-file-for-fake-video-capture=${video}`, "--autoplay-policy=no-user-gesture-required",
    "--no-first-run", "about:blank",
  ], { stdio: "ignore" });
  let target;
  for (let i = 0; i < 75 && !target; i++) {
    await sleep(200);
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch {}
  }
  if (!target) throw new Error("Chrome did not start");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const pending = new Map();
  const calls = [];
  const errors = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result || msg.error); pending.delete(msg.id); }
    if (msg.method === "Network.requestWillBeSent" && msg.params.request.url.includes("/api/")) {
      let body = {};
      try { body = JSON.parse(msg.params.request.postData || "{}"); } catch {}
      calls.push({ path: new URL(msg.params.request.url).pathname, body });
    }
    if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
  });
  const send = (method, params = {}) => new Promise((r) => { const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true })).result?.value;
  await send("Network.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url: PAGE });
  await sleep(5000);  // page load and camera start
  return {
    calls, errors,
    key: async (key, code = key) => {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, text: key.length === 1 ? key : undefined });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key, code });
    },
    evaluate,
    spoken: () => calls.filter((c) => c.path === "/api/speak").map((c) => c.body.text),
    cards: () => evaluate(`[...document.querySelectorAll("#hazard-list li")].map((li) => li.getAttribute("aria-label"))`),
    close: () => { ws.close(); chrome.kill(); },
  };
}

const results = [];
async function check(name, video, run) {
  const page = await openPage(video);
  try {
    const problems = await run(page);
    if (page.errors.length) problems.push(`page errors: ${page.errors.join("; ")}`);
    results.push([name, problems]);
    console.log(`${problems.length ? "FAIL" : "PASS"}  ${name}${problems.length ? "\n      " + problems.join("\n      ") : ""}`);
  } finally {
    page.close();
  }
}

if (!CHROME) {
  console.error("Chrome not found. Set CHROME to its path.");
  process.exit(2);
}
try {
  await fetch(PAGE + "api/health");
} catch {
  console.error(`DrishtiAI is not running at ${PAGE}. Start it with: python -m drishti`);
  process.exit(2);
}

const cows = fakeCamera("eval/heldout/images/cows_road_delhi.jpg", "cows");

await check("a dark frame is not sent to the model, and the user is told", fakeCamera(
  "eval/heldout/images/cows_road_delhi.jpg", "dark", "--dark"), async (page) => {
  await page.key(" ", "Space");
  await sleep(2000);
  const problems = [];
  if (page.calls.some((c) => c.path === "/api/describe")) problems.push("the frame was sent to the model");
  if (!page.spoken().some((s) => /too dark/i.test(s))) problems.push(`not told it is dark; said ${JSON.stringify(page.spoken())}`);
  return problems;
});

await check("walk mode warns about the cows, with full sentences on the cards", cows, async (page) => {
  await page.key("w");
  await sleep(4000);
  const problems = [];
  const warned = page.spoken().join(" ");
  if (!/animal ahead, near/.test(warned)) problems.push(`no warning about the animal ahead; said ${JSON.stringify(page.spoken())}`);
  const cards = await page.cards();
  if (!cards.length || !cards.every((c) => /^Careful: /.test(c || ""))) problems.push(`cards: ${JSON.stringify(cards)}`);
  const checks = page.calls.filter((c) => c.path === "/api/detect").length;
  if (checks < 3) problems.push(`only ${checks} detector checks in 4 s`);
  return problems;
});

await check("walk mode says when it cannot see, instead of staying silent", fakeCamera(
  "eval/heldout/images/cows_road_delhi.jpg", "dark-walk", "--dark"), async (page) => {
  await page.key("w");
  await sleep(5000);
  const problems = [];
  if (!page.spoken().some((s) => /too dark/i.test(s))) problems.push(`said ${JSON.stringify(page.spoken())}`);
  return problems;
});

await check("live Find guides to a bicycle", fakeCamera("eval/images/sidewalk_obstruction.jpg", "bicycle"), async (page) => {
  await page.key("3");
  await sleep(300);
  await page.evaluate(`(() => { const box = document.getElementById("target"); box.value = "my bicycle"; box.blur(); })()`);
  await page.key(" ", "Space");
  await sleep(4000);
  const problems = [];
  if (!page.calls.some((c) => c.path === "/api/locate")) problems.push("live Find was not used");
  if (page.calls.some((c) => c.path === "/api/describe")) problems.push("the slow model was asked although the detector found it");
  if (!page.spoken().some((s) => /Bicycle ahead, near/.test(s))) problems.push(`said ${JSON.stringify(page.spoken())}`);
  return problems;
});

if (process.argv.includes("--with-model")) {
  await check("a blurred frame is described, with a warning that it is blurred", fakeCamera(
    "eval/heldout/images/cows_road_delhi.jpg", "blurred", "--blur"), async (page) => {
    await page.key(" ", "Space");
    for (let i = 0; i < 120 && !page.spoken().some((s) => /blurred/.test(s)); i++) await sleep(1000);
    const problems = [];
    const sent = page.calls.find((c) => c.path === "/api/describe");
    if (!sent || sent.body.blurry !== true) problems.push("the frame was not marked as blurred");
    if (!page.spoken().some((s) => /The picture is blurred/.test(s))) problems.push(`said ${JSON.stringify(page.spoken())}`);
    return problems;
  });
}

const failed = results.filter(([, problems]) => problems.length).length;
console.log(`\n${results.length - failed} of ${results.length} checks passed.`);
process.exit(failed ? 1 : 0);
