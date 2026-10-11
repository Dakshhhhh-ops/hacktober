"""A stand-in for Ollama, for working on the web page without the real model.

    python tests/fake_ollama.py           # listens on 127.0.0.1:11435
    OLLAMA_URL=http://127.0.0.1:11435 OLLAMA_MODEL=STAND-IN-not-a-real-model python -m drishti

It returns the same canned scene for every image and does not look at the picture, so
every answer is labelled as test data. It is NEVER used by the evaluation
script or for any reported result.
"""
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

SCENE = {
    "hazards": [
        {"what": "TEST DATA, not real: stairs", "where": "ahead", "distance": "near"},
        {"what": "TEST DATA, not real: open door", "where": "left", "distance": "mid"},
    ],
    "objects": [{"what": "chair", "where": "left"}],
    "text": ["TEST DATA, not real: EXIT"],
    "summary": "This is canned test data. No vision model looked at the camera.",
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # /api/tags: pretend every model is installed
        self._send({"models": [{"name": "STAND-IN-not-a-real-model:latest"}]})

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        time.sleep(0.5)
        scene = dict(SCENE)
        if "find_result" in request.get("format", {}).get("properties", {}):
            scene["find_result"] = {"status": "found", "where": "on the left, near the door"}
        self._send({"message": {"role": "assistant", "content": json.dumps(scene)}})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Fake Ollama on http://127.0.0.1:11435 (canned answers, for UI work only)")
    HTTPServer(("127.0.0.1", 11435), Handler).serve_forever()
