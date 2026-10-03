# ============================================================
#  JinX X4G  |  3X-UI v2.9.4 for Railway
#  In partnership with X4G
# ============================================================
FROM ghcr.io/mhsanaei/3x-ui:v2.9.4

ARG S6_OVERLAY_VERSION=3.2.0.2

ENV TZ=Asia/Tehran \
    XUI_DB_FOLDER=/etc/x-ui \
    XUI_ENABLE_FAIL2BAN=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    S6_KEEP_ENV=1 \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0 \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    S6_KILL_GRACETIME=8000 \
    S6_SERVICES_GRACETIME=8000 \
    S6_VERBOSITY=1

# 1) system packages + s6-overlay (process supervisor)
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
        apk add --no-cache nginx python3 sqlite tzdata xz ca-certificates curl; \
    else \
        apt-get update; \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nginx python3 sqlite3 tzdata xz-utils ca-certificates curl; \
        rm -rf /var/lib/apt/lists/*; \
    fi; \
    ARCH="$(uname -m)"; case "$ARCH" in x86_64|amd64) S6A=x86_64 ;; aarch64|arm64) S6A=aarch64 ;; *) S6A="$ARCH" ;; esac; \
    curl -fsSL --retry 5 -o /tmp/s6-noarch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz"; \
    curl -fsSL --retry 5 -o /tmp/s6-arch.tar.xz "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${S6A}.tar.xz"; \
    tar -C / -Jxpf /tmp/s6-noarch.tar.xz; \
    tar -C / -Jxpf /tmp/s6-arch.tar.xz; \
    rm -f /tmp/s6-*.tar.xz; \
    ln -sf /usr/share/zoneinfo/Asia/Tehran /etc/localtime; echo "Asia/Tehran" > /etc/timezone; \
    test -x /app/x-ui

# 2) JinX files (everything sits next to this Dockerfile)
COPY *.py init.sh nginx.conf.tpl sub.html lock.js /opt/jinx/

# 3) services: init -> x-ui, nginx, helper -> guardian (built here, nothing else to upload)
RUN set -eux; \
    find /opt/jinx -type f \( -name '*.sh' -o -name '*.py' -o -name '*.tpl' -o -name '*.js' -o -name '*.html' \) -exec sed -i 's/\r$//' {} +; \
    mkdir -p /opt/jinx/segno; \
    for m in init consts encoder helpers utils writers; do \
        t="$m.py"; [ "$m" = init ] && t="__init__.py"; \
        mv "/opt/jinx/segno-$m.py" "/opt/jinx/segno/$t"; \
    done; \
    chmod 755 /opt/jinx/*.sh /opt/jinx/*.py; \
    D=/etc/s6-overlay/s6-rc.d; \
    mkdir -p "$D/user/contents.d"; \
    for s in jx-init x-ui nginx jx-helper jx-guard; do \
        mkdir -p "$D/$s/dependencies.d"; touch "$D/$s/dependencies.d/base" "$D/user/contents.d/$s"; \
    done; \
    echo oneshot > "$D/jx-init/type"; \
    echo "/command/with-contenv /opt/jinx/init.sh" > "$D/jx-init/up"; \
    for s in x-ui nginx jx-helper jx-guard; do echo longrun > "$D/$s/type"; touch "$D/$s/dependencies.d/jx-init"; done; \
    touch "$D/jx-guard/dependencies.d/x-ui" "$D/jx-guard/dependencies.d/nginx"; \
    printf '#!/command/with-contenv sh\nulimit -n "$(ulimit -Hn 2>/dev/null || echo 65535)" 2>/dev/null || true\ncd /app || exit 1\nexec /app/x-ui\n' > "$D/x-ui/run"; \
    printf '#!/command/with-contenv sh\nulimit -n "$(ulimit -Hn 2>/dev/null || echo 65535)" 2>/dev/null || true\nexec nginx -c /run/jinx/nginx.conf -g "daemon off;"\n' > "$D/nginx/run"; \
    printf '#!/command/with-contenv sh\nexec python3 /opt/jinx/helper.py\n' > "$D/jx-helper/run"; \
    printf '#!/command/with-contenv sh\nexec python3 /opt/jinx/guard.py\n' > "$D/jx-guard/run"; \
    chmod 755 "$D"/*/run; \
    python3 -m py_compile /opt/jinx/*.py; rm -rf /opt/jinx/__pycache__; \
    python3 -c "import sys; sys.path.insert(0,'/opt/jinx'); import segno"; \
    nginx -v

EXPOSE 8080
ENTRYPOINT ["/init"]
CMD []
