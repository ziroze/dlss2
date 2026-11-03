# Ziroze PC Bridge

Secure, outbound-only bridge between ChatGPT-compatible MCP clients and a Linux device agent.

## Current scope

This first implementation is a **read-only diagnostic MVP**:
- Admin API protected by a bootstrap bearer token.
- One-time, expiring device enrollment codes.
- Linux agent initiates outbound HTTPS polling; no inbound port is needed on the device.
- Device credentials are stored as hashes on the server and can be revoked.
- Jobs are restricted to named diagnostic operations; no arbitrary shell, PTY, sudo, package installation, or file browsing.
- SQLite persistence and an audit trail.
- MCP-compatible JSON-RPC endpoint exposing only safe diagnostic tools.

## Quick start (server)

Requires Python 3.11+.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set a long random BRIDGE_ADMIN_TOKEN and a unique BRIDGE_SECRET in .env
uvicorn bridge.main:app --host 127.0.0.1 --port 8000
```

The API listens on localhost by default. Put it behind a trusted HTTPS reverse proxy before remote use. Do not expose it publicly without TLS and a strong admin token.

## Enroll a Linux device

Create a one-time code using the admin API:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/enrollments \
  -H "Authorization: Bearer $BRIDGE_ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"label":"my-linux-pc"}'
```

On the device, install the agent dependencies and run:

```bash
pip install -r agent/requirements.txt
python -m agent.main --server https://YOUR-BRIDGE-HOST --code ONE_TIME_CODE
```

The agent makes outbound HTTPS requests only. For local testing, use `http://127.0.0.1:8000`.

## Admin API

- `GET /health`
- `POST /api/admin/enrollments`
- `GET /api/admin/devices`
- `POST /api/admin/devices/{device_id}/revoke`
- `POST /api/admin/jobs`
- `GET /api/admin/jobs/{job_id}`
- `GET /api/admin/audit`

All `/api/admin/*` routes require `Authorization: Bearer <BRIDGE_ADMIN_TOKEN>`.

## MCP

`POST /mcp` accepts JSON-RPC 2.0 requests with bearer authentication. It supports `initialize`, `ping`, `tools/list`, and `tools/call`. Tools are limited to:
- `list_devices`
- `get_device_status`
- `run_diagnostic` (allowlisted diagnostic name only)

Use the same admin bearer token for this initial single-owner deployment. A later release should add per-user MCP identities and approval workflows.

## Safety model

The server never accepts a shell command from an API or MCP caller. Jobs carry an enum-like diagnostic name and validated arguments. The agent maps those names to local Python functions. No remote file reads or writes are implemented. Revocation is checked on every poll and result submission.

## Development

```bash
pytest -q
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/SECURITY.md](docs/SECURITY.md).
