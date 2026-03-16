"""Generate PDF from HTML with custom header/footer via Chrome DevTools Protocol.

Usage:
    python scripts/print_pdf.py <input.html> <output.pdf>

Requires Google Chrome installed. No external Python packages needed.
"""

import base64
import json
import os
import socket
import subprocess
import sys
import time
import struct
import hashlib
import secrets

# ── Configuration ──────────────────────────────────────────────────────────
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9223  # DevTools port

HEADER_TEMPLATE = """
<div style="width:100%; font-family:Segoe UI,Calibri,Arial,sans-serif; font-size:8px; padding:4px 10mm 6px 10mm; display:flex; justify-content:space-between; align-items:center; border-bottom:1.5px solid #1f3b5c; margin-bottom:8px;">
    <span style="font-weight:700; font-size:9px; color:#1f3b5c; letter-spacing:0.3px;">ZEBRA TECHNOLOGIES</span>
    <span style="color:#1f3b5c; font-size:7.5px;">get_status &mdash; RFD40 / RFD90 IoT Connector API Reference</span>
</div>
"""

FOOTER_TEMPLATE = """
<div style="width:100%; font-family:Segoe UI,Calibri,Arial,sans-serif; font-size:7px; padding:6px 10mm 4px 10mm; display:flex; justify-content:space-between; align-items:center; border-top:1px solid #d9dde3; margin-top:8px; color:#6b7a8d;">
    <span>API Version: V1.1 &nbsp;|&nbsp; Document Version: 1.0.0 &nbsp;|&nbsp; Last Updated: 2026-03-12</span>
    <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span> &nbsp;|&nbsp; Zebra Confidential</span>
</div>
"""

# ── WebSocket helpers (RFC 6455, no external deps) ─────────────────────────
def _ws_connect(host, port, path):
    """Open a raw WebSocket connection, return the socket."""
    sock = socket.create_connection((host, port), timeout=15)
    key = base64.b64encode(secrets.token_bytes(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += sock.recv(4096)
    if b"101" not in resp.split(b"\r\n")[0]:
        raise RuntimeError(f"WebSocket handshake failed:\n{resp.decode(errors='replace')}")
    return sock


def _ws_send(sock, data: str):
    payload = data.encode()
    frame = bytearray()
    frame.append(0x81)  # FIN + text
    mask_key = secrets.token_bytes(4)
    length = len(payload)
    if length < 126:
        frame.append(0x80 | length)
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack(">Q", length))
    frame.extend(mask_key)
    masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    frame.extend(masked)
    sock.sendall(frame)


def _ws_recv(sock):
    """Read one complete WebSocket frame (text). Handles fragmentation."""
    def read_exact(n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Connection closed")
            buf += chunk
        return buf

    header = read_exact(2)
    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    length = header[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", read_exact(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", read_exact(8))[0]
    if masked:
        mask_key = read_exact(4)
    payload = read_exact(length)
    if masked:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    if opcode == 0x08:
        raise ConnectionError("WebSocket closed by server")
    return payload.decode()


def cdp_call(sock, method, params=None, msg_id=1):
    """Send a CDP command and wait for its result."""
    msg = {"id": msg_id, "method": method}
    if params:
        msg["params"] = params
    _ws_send(sock, json.dumps(msg))
    while True:
        raw = _ws_recv(sock)
        data = json.loads(raw)
        if data.get("id") == msg_id:
            if "error" in data:
                raise RuntimeError(f"CDP error: {data['error']}")
            return data.get("result", {})


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/print_pdf.py <input.html> <output.pdf>")
        sys.exit(1)

    html_path = os.path.abspath(sys.argv[1])
    pdf_path = os.path.abspath(sys.argv[2])

    if not os.path.isfile(html_path):
        print(f"Input not found: {html_path}")
        sys.exit(1)

    file_url = "file:///" + html_path.replace("\\", "/").replace(" ", "%20")

    # Start Chrome with remote debugging
    user_data = os.path.join(os.environ.get("TEMP", "."), "chrome_pdf_profile")
    chrome = subprocess.Popen(
        [
            CHROME_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={user_data}",
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for DevTools to be ready
        ws_url = None
        for _ in range(30):
            time.sleep(0.5)
            try:
                conn = socket.create_connection(("127.0.0.1", CDP_PORT), timeout=2)
                req = f"GET /json HTTP/1.1\r\nHost: 127.0.0.1:{CDP_PORT}\r\n\r\n"
                conn.sendall(req.encode())
                resp = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                    if b"\r\n0\r\n" in resp or (b"\r\n\r\n" in resp and b"[" in resp):
                        break
                conn.close()
                body = resp.split(b"\r\n\r\n", 1)[1]
                # Handle chunked encoding
                if b"\r\n" in body and body[0:1] != b"[":
                    body = body.split(b"\r\n", 1)[1]
                targets = json.loads(body.split(b"\r\n0")[0] if b"\r\n0" in body else body)
                for t in targets:
                    if t.get("type") == "page":
                        ws_url = t["webSocketDebuggerUrl"]
                        break
                if ws_url:
                    break
            except (ConnectionRefusedError, OSError, json.JSONDecodeError):
                continue

        if not ws_url:
            print("Could not connect to Chrome DevTools")
            sys.exit(1)

        # Parse ws URL
        # ws://127.0.0.1:9223/devtools/page/XXXX
        ws_path = "/" + ws_url.split("/", 3)[3]

        sock = _ws_connect("127.0.0.1", CDP_PORT, ws_path)

        # Navigate to the HTML file
        cdp_call(sock, "Page.enable", msg_id=1)
        cdp_call(sock, "Page.navigate", {"url": file_url}, msg_id=2)
        time.sleep(2)  # Wait for page to load

        # Print to PDF with custom header/footer
        result = cdp_call(
            sock,
            "Page.printToPDF",
            {
                "landscape": False,
                "displayHeaderFooter": True,
                "headerTemplate": HEADER_TEMPLATE,
                "footerTemplate": FOOTER_TEMPLATE,
                "printBackground": True,
                "paperWidth": 8.27,   # A4 in inches
                "paperHeight": 11.69,
                "marginTop": 1.4,     # ~36mm for header clearance
                "marginBottom": 1.3,  # ~33mm for footer clearance
                "marginLeft": 0.55,
                "marginRight": 0.55,
                "preferCSSPageSize": False,
            },
            msg_id=3,
        )

        pdf_data = base64.b64decode(result["data"])
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(pdf_data)

        print(f"PDF written: {pdf_path} ({len(pdf_data):,} bytes)")
        sock.close()

    finally:
        chrome.terminate()
        chrome.wait(timeout=10)


if __name__ == "__main__":
    main()
