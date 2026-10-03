"""Definition + enforcement of the locked inbound 'JinX X4G' (VLESS + WS, TLS at Railway edge)."""
import json, time
from common import *


def stream(dom, ws_path, fast):
    ext = []
    if dom:
        ext = [{"forceTls": "tls", "dest": dom, "port": 443, "remark": ""}]
    return {
        "network": "ws",
        "security": "none",
        "externalProxy": ext,
        "wsSettings": {
            "acceptProxyProtocol": False,
            "path": ws_path,
            "host": dom,
            "headers": {},
            "heartbeatPeriod": 20 if fast else 30,
        },
        "sockopt": {
            "tcpNoDelay": True,
            "tcpKeepAliveIdle": 25 if fast else 45,
            "tcpKeepAliveInterval": 10 if fast else 15,
            "tcpUserTimeout": 20000 if fast else 30000,
        },
    }


SNIFF = {"enabled": False, "destOverride": ["http", "tls", "quic", "fakedns"], "metadataOnly": False, "routeOnly": False}


def wanted(dom, ws_path, fast):
    return {
        "remark": INBOUND_REMARK,
        "enable": 1,
        "listen": "127.0.0.1",
        "port": WS_PORT,
        "protocol": "vless",
        "tag": INBOUND_TAG,
        "stream_settings": stream(dom, ws_path, fast),
    }


def _key(ss):
    """Fields that matter for connectivity; anything else may differ."""
    try:
        s = json.loads(ss) if isinstance(ss, str) else ss
        w = s.get("wsSettings", {})
        e = s.get("externalProxy") or []
        return (s.get("network"), s.get("security"), w.get("path"), w.get("host"),
                tuple((x.get("dest"), int(x.get("port", 0)), x.get("forceTls")) for x in e))
    except Exception:
        return None


def find(c):
    cols = columns(c, "inbounds")
    r = c.execute("SELECT id FROM inbounds WHERE tag=? OR remark=? ORDER BY id LIMIT 1", (INBOUND_TAG, INBOUND_REMARK)).fetchone()
    return (r[0] if r else None), cols


def ensure(c, dom, ws_path, fast, snapshot=None):
    """Returns (inbound_id, changed). Clients are never touched; if the inbound was deleted,
    it is recreated with the last known client list (snapshot)."""
    w = wanted(dom, ws_path, fast)
    iid, cols = find(c)
    ss = json.dumps(w["stream_settings"], ensure_ascii=False)
    if iid is None:
        # port conflict: another inbound squatting our port -> move it off
        c.execute("UPDATE inbounds SET enable=0 WHERE port=? AND listen IN ('127.0.0.1','','0.0.0.0')", (WS_PORT,))
        row = {
            "user_id": 1, "up": 0, "down": 0, "total": 0, "remark": w["remark"], "enable": 1,
            "expiry_time": 0, "listen": w["listen"], "port": w["port"], "protocol": w["protocol"],
            "settings": snapshot or json.dumps({"clients": [], "decryption": "none", "fallbacks": []}),
            "stream_settings": ss, "tag": w["tag"],
            "sniffing": json.dumps(SNIFF), "all_time": 0, "traffic_reset": "never", "last_traffic_reset_time": 0,
        }
        row = {k: v for k, v in row.items() if k in cols}
        q = "INSERT INTO inbounds(%s) VALUES(%s)" % (",".join(row), ",".join("?" * len(row)))
        cur = c.execute(q, list(row.values()))
        log("inbound created:", w["remark"])
        return cur.lastrowid, True
    cur = c.execute("SELECT remark,enable,listen,port,protocol,tag,stream_settings,settings FROM inbounds WHERE id=?", (iid,)).fetchone()
    changed = False
    fix = {}
    if cur[0] != w["remark"]: fix["remark"] = w["remark"]
    if int(cur[1] or 0) != 1: fix["enable"] = 1
    if (cur[2] or "") != w["listen"]: fix["listen"] = w["listen"]
    if int(cur[3] or 0) != w["port"]: fix["port"] = w["port"]
    if cur[4] != w["protocol"]: fix["protocol"] = w["protocol"]
    if cur[5] != w["tag"]: fix["tag"] = w["tag"]
    if _key(cur[6]) != _key(w["stream_settings"]): fix["stream_settings"] = ss
    try:
        st = json.loads(cur[7] or "{}")
        if not isinstance(st.get("clients"), list) or st.get("decryption") != "none":
            st.setdefault("clients", [])
            if not isinstance(st["clients"], list): st["clients"] = []
            st["decryption"] = "none"
            fix["settings"] = json.dumps(st, ensure_ascii=False)
    except Exception:
        pass  # never destroy client list on parse problems
    if fix:
        c.execute("UPDATE inbounds SET %s WHERE id=?" % ",".join("%s=?" % k for k in fix), list(fix.values()) + [iid])
        log("inbound repaired:", ", ".join(fix))
        changed = True
    return iid, changed


def snapshot(c, iid):
    try:
        r = c.execute("SELECT settings FROM inbounds WHERE id=?", (iid,)).fetchone()
        if r and r[0]:
            json.loads(r[0])
            return r[0]
    except Exception:
        pass
    return None
