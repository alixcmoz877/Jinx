# JinX X4G - generated at boot by /opt/jinx/render.py. Do not edit here.
worker_processes auto;
worker_rlimit_nofile 65535;
pid /run/jinx/nginx.pid;
error_log /dev/stderr warn;

events {
    worker_connections @@WCONN@@;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    charset utf-8;
    access_log off;
    server_tokens off;
    sendfile on;
    tcp_nodelay on;
    tcp_nopush off;
    keepalive_timeout 75s;
    keepalive_requests 10000;
    client_max_body_size 64m;
    client_body_temp_path /tmp/ngx-body;
    proxy_temp_path /tmp/ngx-proxy;
    fastcgi_temp_path /tmp/ngx-fcgi;
    uwsgi_temp_path /tmp/ngx-uwsgi;
    scgi_temp_path /tmp/ngx-scgi;
    proxy_http_version 1.1;
@@SOCKKA@@    proxy_connect_timeout 10s;

    map $http_upgrade $conn_upgrade { default upgrade; '' close; }
    map $http_x_forwarded_proto $fwd_proto { default $http_x_forwarded_proto; '' https; }
    map $http_accept $jx_html { default 0; ~*text/html 1; }

    # panel-styled protection messages (follow the panel language cookie)
    map $cookie_lang $jx_lock {
        default '{"success":false,"msg":"این اینباند توسط سیستم محافظت می‌شود و امکان حذف یا ویرایش آن وجود ندارد.","obj":null}';
        ~^en    '{"success":false,"msg":"This inbound is protected by the system and cannot be deleted or edited.","obj":null}';
        ~^ru    '{"success":false,"msg":"Этот инбаунд защищён системой и не может быть удалён или изменён.","obj":null}';
        ~^zh    '{"success":false,"msg":"此入站受系统保护，无法删除或编辑。","obj":null}';
        ~^tr    '{"success":false,"msg":"Bu inbound sistem tarafından korunmaktadır ve silinemez veya düzenlenemez.","obj":null}';
    }
    map $cookie_lang $jx_off {
        default '{"success":false,"msg":"این بخش در نسخه‌ی Railway برای حفظ پایداری سرور غیرفعال است.","obj":null}';
        ~^en    '{"success":false,"msg":"This option is disabled on the Railway edition to keep the server stable.","obj":null}';
        ~^ru    '{"success":false,"msg":"Эта функция отключена в версии для Railway ради стабильности сервера.","obj":null}';
        ~^zh    '{"success":false,"msg":"为保证服务器稳定，Railway 版本已禁用此功能。","obj":null}';
        ~^tr    '{"success":false,"msg":"Sunucu kararlılığı için bu seçenek Railway sürümünde devre dışıdır.","obj":null}';
    }

    upstream jx_panel { server 127.0.0.1:@@PANEL@@; keepalive 16; }
    upstream jx_sub   { server 127.0.0.1:@@SUB@@;   keepalive 16; }
    upstream jx_xray  { server 127.0.0.1:@@WSPORT@@; keepalive 64; }
    upstream jx_help  { server 127.0.0.1:@@HELPER@@; keepalive 4; }

    server {
        listen 0.0.0.0:@@PORT@@ default_server@@LOPTS@@;
@@LISTEN6@@        server_name _;

        # ---------- health (Railway healthcheck) ----------
        location = /jx-health { proxy_pass http://jx_help/health; proxy_set_header Connection ""; }
        location = /jx-status { proxy_pass http://jx_help/status; proxy_set_header Connection ""; default_type text/plain; }

        # ---------- VLESS over WebSocket ----------
        location = @@WS@@ {
            if ($http_upgrade !~* websocket) { return 404; }
            proxy_pass http://jx_xray;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $conn_upgrade;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_buffering off;
            proxy_request_buffering off;
            proxy_read_timeout 1d;
            proxy_send_timeout 1d;
            @@TURBO_WS@@
        }

        # ---------- subscription ----------
        location ^~ /sub/ {
            if ($jx_html) { rewrite ^ /__jx_subpage last; }
            proxy_pass http://jx_sub;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $fwd_proto;
            proxy_set_header Connection "";
            add_header Cache-Control "no-store" always;
            add_header Access-Control-Expose-Headers "Subscription-Userinfo, Profile-Title, Profile-Update-Interval, Support-Url, Announce" always;
        }
        location = /__jx_subpage {
            internal;
            root /opt/jinx;
            try_files /sub.html @sub_native;
            default_type text/html;
            add_header Cache-Control "no-store" always;
            add_header X-Content-Type-Options nosniff always;
        }
        location @sub_native {
            proxy_pass http://jx_sub$request_uri;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto $fwd_proto;
            proxy_set_header Connection "";
        }
        location = /jx-qr { proxy_pass http://jx_help/qr$is_args$args; proxy_set_header Connection ""; expires 1h; }
        location = /__jx/lock.js { alias /opt/jinx/lock.js; default_type application/javascript; expires 1h; }
        location = /__jx_seen { proxy_pass http://jx_help/seen?h=$host; proxy_set_header Connection ""; }

        # ---------- panel ----------
        location ~ ^@@BASE_RE@@panel/(api/)?inbounds?/(del|update|setEnable)/@@IID@@/?$ {
            default_type application/json;
            return 200 $jx_lock;
        }
        location ~ ^@@BASE_RE@@panel/(api/)?server/(installXray|updatePanel|updateXray|stopXrayService)(/.*)?$ {
            default_type application/json;
            return 200 $jx_off;
        }
        location @@BASE@@ {
            proxy_pass http://jx_panel;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $fwd_proto;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $conn_upgrade;
            proxy_set_header Accept-Encoding "";
            proxy_read_timeout 300s;
@@SUBFILTER@@        }
        location = @@BASE_NOSLASH@@ { return 301 @@BASE@@; }

        # opening the bare domain goes straight to the panel login
        location = / { return 302 @@BASE@@; }

        # everything else stays invisible
        location / { return 404; }
    }
}
