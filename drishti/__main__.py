"""Start DrishtiAI.

    python -m drishti            # this computer only, http://127.0.0.1:8000
    python -m drishti --phone    # also reachable from a phone on the same network, over HTTPS
"""
import argparse
import secrets
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import uvicorn

from . import config, tts, vlm

CERT_DIR = config.ROOT / "certs"
PHONE_PORT = 8443
# Where Git for Windows keeps openssl when it is not on the PATH.
_OPENSSL_FALLBACKS = (
    r"C:\Program Files\Git\usr\bin\openssl.exe",
    r"C:\Program Files\Git\mingw64\bin\openssl.exe",
)


def lan_ip() -> str:
    """This machine's address on the local network (no packet is actually sent)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def _openssl() -> str | None:
    return shutil.which("openssl") or next((p for p in _OPENSSL_FALLBACKS if Path(p).exists()), None)


def ensure_certificate(ip: str) -> tuple[Path, Path]:
    """Create a self-signed certificate for this address if there is not one already.

    Phone browsers only allow camera access over HTTPS. The certificate is made on this
    machine and never leaves it; the phone shows a warning once because no authority
    signed it.
    """
    key, cert = CERT_DIR / f"{ip}-key.pem", CERT_DIR / f"{ip}-cert.pem"
    if key.exists() and cert.exists():
        return key, cert
    openssl = _openssl()
    if not openssl:
        sys.exit("Phone mode needs openssl to make a certificate. Install Git for Windows "
                 "(it includes openssl) or put openssl on the PATH, then try again.")
    CERT_DIR.mkdir(exist_ok=True)
    subprocess.run([
        openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30",
        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=DrishtiAI",
        "-addext", f"subjectAltName=IP:{ip},DNS:localhost",
    ], check=True, capture_output=True)
    return key, cert


def access_key() -> str:
    """The phone-mode access key, kept between runs so a phone that has it keeps working."""
    path = CERT_DIR / "access-key.txt"
    if path.exists() and path.read_text(encoding="utf-8").strip():
        return path.read_text(encoding="utf-8").strip()
    CERT_DIR.mkdir(exist_ok=True)
    key = secrets.token_urlsafe(16)
    path.write_text(key, encoding="utf-8")
    return key


def show_qr(url: str) -> None:
    """Print the link as a QR code and save it as an image. Optional: needs segno."""
    try:
        import segno
    except ImportError:
        print("  (Install segno to get a QR code: pip install segno)")
        return
    qr = segno.make(url, error="m")
    image = CERT_DIR / "phone-link.png"
    qr.save(image, scale=8, border=4)
    try:
        qr.terminal(compact=True)
    except UnicodeEncodeError:  # a console that cannot draw block characters
        pass
    print(f"  The QR code is also saved as {image}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start DrishtiAI.")
    parser.add_argument("--phone", action="store_true",
                        help="serve over HTTPS on the local network so a phone can be the camera")
    parser.add_argument("--port", type=int, help="port to listen on")
    args = parser.parse_args()
    # Show each line at once, also when the output is being written to a file.
    sys.stdout.reconfigure(line_buffering=True)

    _, message, fix = vlm.check_model()
    print(f"[model] {message} {fix}".rstrip())
    for lang in ("en", "hi"):
        # Loading a Piper voice takes a few seconds, so do it before the first request.
        print(f"[tts] {lang}: {tts.engine(lang) or 'no offline voice installed'}")

    if not args.phone:
        port = args.port or config.PORT
        print(f"Open http://{config.HOST}:{port} in your browser.")
        uvicorn.run("drishti.server:app", host=config.HOST, port=port, log_level="warning")
        return

    ip, port = lan_ip(), args.port or PHONE_PORT
    key, cert = ensure_certificate(ip)
    config.ACCESS_KEY = access_key()
    link = f"https://{ip}:{port}/?key={config.ACCESS_KEY}"
    print()
    print("PHONE MODE: the model still runs on this computer; the phone is the camera and speaker.")
    print("  1. Put the phone on the same network as this computer (the phone's own hotspot works).")
    print("  2. Scan this QR code with the phone's camera, or open this link on the phone:")
    print(f"     {link}")
    show_qr(link)
    print("  3. The browser warns that the certificate is not trusted, because it was made on")
    print("     this computer. Choose Advanced, then Proceed. Then allow the camera.")
    print("  If the page does not load, allow Python through the Windows firewall when asked.")
    print("  Only a device that opened this link can use the app; the phone remembers it for")
    print("  30 days. Keep the link private. To make a new one, delete certs/access-key.txt.")
    print()
    uvicorn.run("drishti.server:app", host="0.0.0.0", port=port, log_level="warning",
                ssl_keyfile=str(key), ssl_certfile=str(cert))


if __name__ == "__main__":
    main()
