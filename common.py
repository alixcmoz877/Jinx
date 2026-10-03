"""JinX X4G shared helpers (paths, logging, sqlite, service control)."""
import os, sys, time, json, sqlite3, subprocess, socket, shutil, glob

DB_DIR = os.environ.get("XUI_DB_FOLDER", "/etc/x-ui")
DB = os.path.join(DB_DIR, "x-ui.db")
BK_DIR = os.path.join(DB_DIR, "backups")
STATE = os.path.join(DB_DIR, ".jinx.json")
RUN = os.environ.get("JX_RUN", "/run/jinx")
XUI_BIN = os.environ.get("JX_XUI_BIN", "/app/x-ui")
SVC = os.environ.get("JX_SVC_DIR", "/run/service")

PANEL_PORT = 2053
SUB_PORT = 2096
WS_PORT = 10000
HELPER_PORT = 9100
PUBLIC_PORT = int(os.environ.get("PORT_INTERNAL", "8080"))
INBOUND_REMARK = "\U0001d5dd\U0001d5f6\U0001d5fb\U0001d5eb X4G"   # bold "JinX" + " X4G"
INBOUND_TAG = "inbound-127.0.0.1:%d" % WS_PORT
SUPPORT_URL = "https://t.me/Super_Jinx"
ANNOUNCE = "ارائه شده توسط جینکس • با حمایت آقای ایکس فورجی"


def log(*a):
    print("[jinx]", time.strftime("%H:%M:%S"), *a, flush=True)


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def db(timeout=15):
    c = sqlite3.connect(DB, timeout=timeout)
    c.execute("PRAGMA busy_timeout=15000")
    return c


def columns(c, table):
    return [r[1] for r in c.execute("PRAGMA table_info(%s)" % table)]


def integrity_ok(path=DB):
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        return False
    try:
        c = sqlite3.connect(path, timeout=15)
        r = c.execute("PRAGMA quick_check").fetchone()
        n = c.execute("SELECT count(*) FROM sqlite_master WHERE name in ('settings','inbounds','users')").fetchone()[0]
        c.close()
        return bool(r) and r[0] == "ok" and n == 3
    except Exception:
        return False


def backup(keep=8):
    """Online, consistent copy of the panel DB (safe while x-ui runs)."""
    if not integrity_ok():
        return None
    os.makedirs(BK_DIR, exist_ok=True)
    dst = os.path.join(BK_DIR, "x-ui-%s.db" % time.strftime("%Y%m%d-%H%M%S"))
    src = sqlite3.connect(DB, timeout=15)
    out = sqlite3.connect(dst)
    with out:
        src.backup(out)
    src.close(); out.close()
    if not integrity_ok(dst):
        os.remove(dst)
        return None
    files = sorted(glob.glob(os.path.join(BK_DIR, "x-ui-*.db")))
    for old in files[:-keep]:
        try: os.remove(old)
        except OSError: pass
    return dst


def latest_good_backup():
    for f in sorted(glob.glob(os.path.join(BK_DIR, "x-ui-*.db")), reverse=True):
        if integrity_ok(f):
            return f
    return None


def restore_backup():
    f = latest_good_backup()
    if not f:
        return False
    for ext in ("", "-wal", "-shm"):
        p = DB + ext
        if os.path.exists(p):
            try: shutil.move(p, p + ".broken")
            except OSError: pass
    shutil.copy2(f, DB)
    log("database restored from", os.path.basename(f))
    return True


def get_setting(c, key, default=None):
    r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r[0] if r else default


def set_setting(c, key, value):
    value = "" if value is None else str(value)
    if c.execute("SELECT 1 FROM settings WHERE key=?", (key,)).fetchone():
        c.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    else:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?)", (key, value))


def port_open(port, host="127.0.0.1", t=2.0):
    try:
        with socket.create_connection((host, port), timeout=t):
            return True
    except OSError:
        return False


def svc_restart(name):
    path = os.path.join(SVC, name)
    try:
        subprocess.run(["s6-svc", "-r", path], timeout=10, check=False)
        log("service restarted:", name)
    except Exception as e:
        log("restart failed", name, e)


def svc_signal(name, flag):
    """flag: -1 = SIGUSR1 (x-ui: restart xray only), -h = SIGHUP (x-ui: reload web+sub servers)."""
    try:
        subprocess.run(["s6-svc", flag, os.path.join(SVC, name)], timeout=10, check=False)
        log("service signalled:", name, flag)
    except Exception as e:
        log("signal failed", name, e)


def region():
    return os.environ.get("RAILWAY_REPLICA_REGION") or os.environ.get("RAILWAY_REGION") or ""


def turbo():
    v = os.environ.get("JX_TURBO", "auto").lower()
    if v in ("1", "true", "on", "yes"):
        return True
    if v in ("0", "false", "off", "no"):
        return False
    return region().startswith("europe-west4")


def domain(st=None):
    d = (os.environ.get("JX_DOMAIN") or os.environ.get("RAILWAY_PUBLIC_DOMAIN") or "").strip().lower()
    if not d and st:
        d = st.get("domain", "")
    return d.replace("https://", "").replace("http://", "").strip("/")
