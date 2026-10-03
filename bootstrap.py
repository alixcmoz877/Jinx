#!/usr/bin/env python3
"""JinX X4G first-stage init: prepare DB, settings, locked inbound and nginx config.
Runs before every start. Idempotent: safe to run any number of times."""
import os, sys, secrets, string, subprocess, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import settings as S, inbound as IB, render, xraytpl as XT


def rnd(n):
    a = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(a) for _ in range(n))


def create_db(base):
    log("creating panel database (first run)")
    u = os.environ.get("JX_ADMIN_USER", "admin") or "admin"
    p = os.environ.get("JX_ADMIN_PASS", "admin") or "admin"
    try:
        subprocess.run([XUI_BIN, "setting", "-username", u, "-password", p, "-port", str(PANEL_PORT),
                        "-webBasePath", base, "-listenIP", "127.0.0.1"], cwd=os.path.dirname(XUI_BIN) or "/",
                       timeout=120, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        log("x-ui setting failed:", e)
    if not integrity_ok():
        # fallback: let x-ui create its own schema once, then stop it
        log("fallback: starting x-ui once to build schema")
        pr = subprocess.Popen([XUI_BIN], cwd=os.path.dirname(XUI_BIN) or "/")
        for _ in range(60):
            time.sleep(1)
            if integrity_ok(): break
        pr.terminate()
        try: pr.wait(15)
        except Exception: pr.kill()
        subprocess.run([XUI_BIN, "setting", "-username", u, "-password", p], cwd=os.path.dirname(XUI_BIN) or "/",
                       timeout=120, check=False)


def main():
    os.makedirs(DB_DIR, exist_ok=True); os.makedirs(BK_DIR, exist_ok=True); os.makedirs(RUN, exist_ok=True)
    try: os.makedirs("/var/log/x-ui", exist_ok=True)
    except OSError: pass
    st = load_state()

    # 1) stable secrets (survive redeploys because they live on the volume)
    base = os.environ.get("JX_PANEL_PATH") or st.get("base") or ("/jx-" + rnd(10) + "/")
    base = "/" + base.strip("/") + "/"
    # 2) database health
    if os.path.exists(DB) and not integrity_ok():
        log("database damaged -> restoring last good backup")
        if not restore_backup():
            log("no good backup; keeping damaged copy aside and starting fresh")
            os.replace(DB, DB + ".broken-%d" % int(time.time()))
    if not os.path.exists(DB):
        if not restore_backup():
            create_db(base)
    if not integrity_ok():
        log("FATAL: panel database could not be prepared"); sys.exit(1)

    ws = st.get("ws") or ("/jx-" + rnd(14))
    dom = domain(st)
    fast = turbo()
    st.update({"base": base, "ws": ws, "domain": dom, "region": region(), "turbo": fast, "nginx_safe": False})

    # 3) settings + inbound
    c = db()
    with c:
        c.execute("PRAGMA journal_mode=WAL")
        S.ensure(c, base, dom)
        XT.ensure(c, fast)
        iid, _ = IB.ensure(c, dom, ws, fast, st.get("clients"))
        snap = IB.snapshot(c, iid)
        if snap: st["clients"] = snap
    c.close()
    st["inbound_id"] = iid
    save_state(st)

    # 4) nginx + runtime files
    render.nginx(st)
    backup()

    url = ("https://%s%s" % (dom, base)) if dom else ("https://<your-railway-domain>%s" % base)
    bar = "=" * 60
    log(bar)
    log("JinX X4G is ready")
    log("Panel   :", url)
    log("Login   : admin / admin  (default; change it after first login)")
    log("Region  :", region() or "unknown", "| turbo:", "ON" if fast else "off")
    if not dom:
        log("NOTE: no public domain yet. Generate a domain (port 8080) in Railway > Networking;")
        log("      open the panel once (or redeploy) and it is picked up automatically.")
    log(bar)


if __name__ == "__main__":
    main()
