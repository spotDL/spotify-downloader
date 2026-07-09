# Caddy / reverse proxy

The spotDL container serves plain HTTP on port 8000. To put it on a public domain
with automatic HTTPS, terminate TLS at a reverse proxy in front of it. (In v4,
TLS was configured with client flags like `--enable-tls`; in v5 those were
removed — TLS lives at the proxy.)

## Caddy

[Caddy](https://caddyserver.com/) obtains and renews certificates automatically.
The stack ships an example at `deploy/Caddyfile.example`:

```caddy
spotdl.example.com {
    encode zstd gzip
    reverse_proxy localhost:8000
}
```

Point `spotdl.example.com`'s DNS at the host, run Caddy with that config, and it
will provision a certificate on first request.

## Efficient large-file delivery (optional)

Serving downloaded library files through the app process is fine for light use.
For heavy delivery you can have the proxy serve files directly using an internal
redirect. Set `SPOTDL_DOWNLOAD_X_ACCEL_PREFIX` on the server and add a matching
file-serving block to the proxy. For Caddy:

```caddy
spotdl.example.com {
    encode zstd gzip
    reverse_proxy localhost:8000

    # Serve library files directly when the app emits an internal-redirect
    # pointing under the configured prefix.
    handle @internal {
        root * /app/data
        file_server
    }
}
```

The server must be run with `SPOTDL_DOWNLOAD_X_ACCEL_PREFIX` set to the prefix
the proxy intercepts. Only enable this if you understand the path exposure; the
default (app-served files) needs no such configuration.

## Other proxies

Any reverse proxy works — nginx, Traefik, HAProxy. The only requirements are:

- forward to the container's port 8000;
- pass the real client IP in a header the server trusts. Set
  `SPOTDL_CLIENT_IP_HEADER` to that header (e.g. `cf-connecting-ip` behind
  Cloudflare, or `x-forwarded-for`) so rate limiting and request logs see the
  real client, not the proxy.

For a managed cloud deployment with Cloudflare in front, see
[Railway](railway.md).
