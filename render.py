"""Render nginx config from template + state."""
import os, re, socket, subprocess
from common import *


def _ipv6():
    if not socket.has_ipv6 or os.environ.get("JX_IPV6", "auto") == "off":
        return False
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        s.bind(("::", 0)); s.close()
        return True
    except OSError:
        return False


def _has_sub_filter():
    try:
        out = subprocess.run(["nginx", "-V"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10).stdout.decode()
        return "http_sub_module" in out
    except Exception:
        return False

TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nginx.conf.tpl")
OUT = os.path.join(RUN, "nginx.conf")


def nginx(st, safe=None):
    if safe is None:
        safe = bool(st.get("nginx_safe"))
    base = st["base"]
    fast = bool(st.get("turbo"))
    t = open(TPL, encoding="utf-8").read()
    rep = {
        "@@PORT@@": str(PUBLIC_PORT), "@@PANEL@@": str(PANEL_PORT), "@@SUB@@": str(SUB_PORT),
        "@@WSPORT@@": str(WS_PORT), "@@HELPER@@": str(HELPER_PORT), "@@WS@@": st["ws"],
        "@@BASE@@": base, "@@BASE_NOSLASH@@": base.rstrip("/"), "@@BASE_RE@@": re.escape(base),
        "@@IID@@": str(int(st.get("inbound_id") or 0)),
        "@@WCONN@@": "32768" if fast else "16384",
        "@@LOPTS@@": "" if safe else " reuseport backlog=4096",
        "@@SOCKKA@@": "" if safe else "    proxy_socket_keepalive on;\n",
        "@@LISTEN6@@": ("        listen [::]:%d default_server%s ipv6only=on;\n" % (PUBLIC_PORT, "" if safe else " reuseport backlog=4096")) if (_ipv6() and not safe) else "",
        "@@SUBFILTER@@": ("            sub_filter_once on;\n"
                          "            sub_filter '</body>' '<script src=\"/__jx/lock.js?v=1\" defer></script></body>';\n") if (_has_sub_filter() and not safe) else "",
        "@@TURBO_WS@@": "" if safe else ("proxy_buffer_size 64k; proxy_buffers 8 64k; proxy_busy_buffers_size 128k;" if fast
                                          else "proxy_buffer_size 32k; proxy_buffers 8 32k; proxy_busy_buffers_size 64k;"),
    }
    for k, v in rep.items():
        t = t.replace(k, v)
    assert "@@" not in t, "unrendered placeholder"
    os.makedirs(RUN, exist_ok=True)
    for d in ("ngx-body", "ngx-proxy", "ngx-fcgi", "ngx-uwsgi", "ngx-scgi"):
        os.makedirs("/tmp/" + d, exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(t)
    os.replace(tmp, OUT)
    return OUT


if __name__ == "__main__":
    # used by init.sh: "render.py --safe" rebuilds a minimal config if nginx rejects the full one
    import sys
    st = load_state()
    safe = "--safe" in sys.argv
    if safe:
        st["nginx_safe"] = True
        save_state(st)
    print(nginx(st, safe))
