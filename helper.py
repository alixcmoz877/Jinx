#!/usr/bin/env python3
"""JinX helper: health endpoint for Railway, QR images for the sub page, domain discovery."""
import os, sys, io, re, json, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs
from common import *

try:
    import segno
except Exception:  # QR is optional; page still works without it
    segno = None

HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")
SEEN = os.path.join(RUN, "seen-host")
_cache = {}


def _get(path, host, data=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PUBLIC_PORT, path), data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Host": host or "localhost", "X-Forwarded-Proto": "https",
                                          "Accept": "text/html,*/*", "User-Agent": "jinx-selftest"})
    try:
        r = urllib.request.urlopen(req, timeout=6)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()


def selftest(st):
    """Loads the panel page + its scripts/styles through nginx, like a browser would."""
    out = []
    base = st.get("base", "/")
    code, body = _get(base, domain(st))
    out.append("panel page    %s (%d bytes)" % (code, len(body)))
    if code != 200:
        return out
    html = body.decode("utf-8", "ignore")
    out.append("lock addon    %s" % ("OK" if "/__jx/lock.js" in html else "not injected"))
    refs = re.findall(r'(?:src|href)="([^"]+\.(?:js|css)[^"]*)"', html)
    bad, n = [], 0
    for ref in refs[:40]:
        if ref.startswith("http"):
            continue
        p = ref if ref.startswith("/") else base + ref
        n += 1
        c, b = _get(p, domain(st))
        if c != 200 or not b:
            bad.append("%s:%s" % (c, p.replace(base, "<base>/")))
    out.append("panel assets  %d/%d OK" % (n - len(bad), n))
    c2, b2 = _get(base + "getTwoFactorEnable", domain(st), data=b"")
    out.append("login api     %s %s" % (c2, b2[:60].decode("utf-8", "ignore")))
    out += ["  FAIL " + x for x in bad[:8]]
    return out
_lock = threading.Lock()


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/plain; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/health":
                ok = port_open(PANEL_PORT) and port_open(SUB_PORT)
                return self._send(200 if ok else 503, b"ok" if ok else b"starting")
            if u.path == "/status":
                st = load_state()
                rows = [
                    ("nginx", True),
                    ("panel", port_open(PANEL_PORT)),
                    ("subscription", port_open(SUB_PORT)),
                    ("xray", port_open(WS_PORT)),
                    ("database", integrity_ok()),
                    ("domain", bool(domain(st))),
                ]
                lines = ["JinX X4G status"] + ["%-13s %s" % (k, "OK" if v else "FAIL") for k, v in rows]
                lines += ["region        %s" % (region() or "unknown"), "turbo         %s" % ("ON" if turbo() else "off"),
                          "inbound id    %s" % st.get("inbound_id", "-")]
                if "deep" in q:
                    lines += selftest(st)
                return self._send(200, ("\n".join(lines) + "\n").encode(), extra={"Cache-Control": "no-store"})
            if u.path == "/qr":
                d = (q.get("d") or [""])[0]
                if not d or len(d) > 2900 or segno is None:
                    return self._send(400, b"bad")
                with _lock:
                    png = _cache.get(d)
                if png is None:
                    b = io.BytesIO()
                    segno.make(d, error="m", micro=False).save(b, kind="png", scale=8, border=0, dark="#000", light="#fff")
                    png = b.getvalue()
                    with _lock:
                        if len(_cache) > 256:
                            _cache.clear()
                        _cache[d] = png
                return self._send(200, png, "image/png", {"Cache-Control": "public, max-age=3600"})
            if u.path == "/seen":
                h = (q.get("h") or [""])[0].lower().split(":")[0]
                if HOST_RE.match(h) and not h.endswith(".railway.internal") and h not in ("localhost",):
                    try:
                        os.makedirs(RUN, exist_ok=True)
                        with open(SEEN, "w") as f:
                            f.write(h)
                    except OSError:
                        pass
                return self._send(204, b"")
        except Exception as e:
            log("helper error:", e)
            return self._send(500, b"error")
        return self._send(404, b"not found")


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", HELPER_PORT), H)
    srv.daemon_threads = True
    log("helper listening on", HELPER_PORT)
    srv.serve_forever()


if __name__ == "__main__":
    main()
