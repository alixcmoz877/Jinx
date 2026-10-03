"""Xray core template tuned for Railway: IPv4-first outbound (no IPv6 stalls), fast DNS, quick handshakes."""
import json
from common import *

DEFAULT = {
    "log": {"access": "none", "dnsLog": False, "error": "", "loglevel": "warning", "maskAddress": ""},
    "api": {"tag": "api", "services": ["HandlerService", "LoggerService", "StatsService"]},
    "inbounds": [{"tag": "api", "listen": "127.0.0.1", "port": 62789, "protocol": "tunnel", "settings": {"address": "127.0.0.1"}}],
    "outbounds": [
        {"tag": "direct", "protocol": "freedom", "settings": {"domainStrategy": "UseIPv4", "redirect": "", "noises": []}},
        {"tag": "blocked", "protocol": "blackhole", "settings": {}},
    ],
    "dns": {"servers": ["1.1.1.1", "8.8.8.8", "localhost"], "queryStrategy": "UseIPv4"},
    "policy": {
        "levels": {"0": {"statsUserDownlink": True, "statsUserUplink": True}},
        "system": {"statsInboundDownlink": True, "statsInboundUplink": True,
                   "statsOutboundDownlink": False, "statsOutboundUplink": False},
    },
    "routing": {"domainStrategy": "AsIs", "rules": [
        {"type": "field", "inboundTag": ["api"], "outboundTag": "api"},
        {"type": "field", "outboundTag": "blocked", "ip": ["geoip:private"]},
        {"type": "field", "outboundTag": "blocked", "protocol": ["bittorrent"]},
    ]},
    "stats": {},
    "metrics": {"tag": "metrics_out", "listen": "127.0.0.1:11111"},
}


def tune(cfg, fast):
    """Only adds speed settings; never removes anything the admin configured."""
    lv = cfg.setdefault("policy", {}).setdefault("levels", {}).setdefault("0", {})
    lv.setdefault("statsUserDownlink", True); lv.setdefault("statsUserUplink", True)
    lv.setdefault("handshake", 4); lv.setdefault("connIdle", 300)
    lv.setdefault("uplinkOnly", 1); lv.setdefault("downlinkOnly", 1)
    for o in cfg.get("outbounds", []):
        if o.get("protocol") == "freedom":
            s = o.setdefault("settings", {})
            if s.get("domainStrategy", "AsIs") == "AsIs":
                s["domainStrategy"] = "UseIPv4"
    cfg.setdefault("dns", {"servers": ["1.1.1.1", "8.8.8.8", "localhost"], "queryStrategy": "UseIPv4"})
    return cfg


def ensure(c, fast):
    raw = get_setting(c, "xrayTemplateConfig")
    try:
        cfg = json.loads(raw) if raw else json.loads(json.dumps(DEFAULT))
    except Exception:
        log("xray template unreadable -> using tuned default")
        cfg = json.loads(json.dumps(DEFAULT))
    new = json.dumps(tune(cfg, fast), ensure_ascii=False, indent=2)
    if new != raw:
        set_setting(c, "xrayTemplateConfig", new)
        log("xray core tuned:", "turbo" if fast else "standard")
        return True
    return False
