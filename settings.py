"""Panel + subscription settings that make everything work on Railway out of the box."""
from common import *


def wanted(base, dom):
    sub_uri = ("https://%s/sub/" % dom) if dom else ""
    return {
        "webListen": "127.0.0.1", "webPort": str(PANEL_PORT), "webBasePath": base,
        "webDomain": "", "webCertFile": "", "webKeyFile": "",
        "subEnable": "true", "subListen": "127.0.0.1", "subPort": str(SUB_PORT), "subPath": "/sub/",
        "subDomain": "", "subCertFile": "", "subKeyFile": "", "subURI": sub_uri,
        "subJsonEnable": "false",
        "timeLocation": "Asia/Tehran",
    }


SOFT = {  # only set when empty, so the admin can still change them
    "subTitle": INBOUND_REMARK, "subUpdates": "12", "subEncrypt": "true", "subShowInfo": "true",
    "subSupportUrl": SUPPORT_URL, "subProfileUrl": SUPPORT_URL, "subAnnounce": ANNOUNCE,
    "remarkModel": "-ieo", "tgBotEnable": "false",
}


def ensure(c, base, dom):
    changed = []
    for k, v in wanted(base, dom).items():
        if get_setting(c, k) != v:
            set_setting(c, k, v); changed.append(k)
    for k, v in SOFT.items():
        if not get_setting(c, k):
            set_setting(c, k, v)
    if changed:
        log("settings enforced:", ", ".join(changed))
    return changed
