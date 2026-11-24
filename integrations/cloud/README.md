# BEAN guest HTTPS ingress

This configuration exposes only the existing guest API, not the owner Core service,
private SQLite journals, Ollama or SSH. No second model or server is required.

On the authorized server, install Caddy from its supported package source if it is
not installed. Confirm the selected public hostname resolves to this server and
that ports 80/443 are available. Set BEAN_PUBLIC_HOST to that hostname in the
Caddy systemd service environment (not a URL), then include the supplied Caddyfile
in the existing Caddy configuration. Do not overwrite other virtual hosts.
Validate the resulting configuration and reload Caddy. Keep the Python gateway
bound to 127.0.0.1:8765.

From the repository root, after the HTTPS endpoint is accessible:

```sh
python integrations/cloud/verify_gateway.py https://YOUR-HOST --write docs/cloud-endpoint.json
```

The verifier requires trusted HTTPS, the actual Pages CORS origin and JSON
preflight, native orbit results, a real local-model response and receipt, and
client-owned memory semantics. Only then does it write the endpoint file.
Commit that generated public configuration and publish the Pages site.
The existing talk.html automatically reads it on first visit.

Acceptance: open the published talk.html in a fresh browser profile, check that
no manual address is needed, send a message, and confirm a real receipt appears
and survives a page reload via IndexedDB. Do not describe the service as publicly
connected until this succeeds. Rollback: remove the new virtual host and reload
Caddy, and revert the published endpoint config; leave the existing Core and
local inference services intact.
