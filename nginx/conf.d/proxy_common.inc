# Shared reverse-proxy headers. Included by each API location block in
# default.conf. Named .inc (not .conf) on purpose: nginx.conf does
# `include conf.d/*.conf`, and if this were a .conf file it would get
# loaded a second time at the http block level by that same glob.
proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout 5s;
proxy_send_timeout 30s;
proxy_read_timeout 30s;
