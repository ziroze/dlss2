# Security
Before remote deployment: set unique high-entropy BRIDGE_ADMIN_TOKEN and BRIDGE_SECRET; keep .env out of Git; terminate TLS at a maintained reverse proxy; restrict ingress; patch dependencies; protect database backups; review audit events; revoke lost devices.

Limitations: single admin token, no roles/MFA/rate limiting/approval workflow, MCP shares admin credentials, and agent token remains in process memory. Changing BRIDGE_SECRET invalidates stored credential hashes and requires device re-enrollment.

Never add arbitrary shell execution, sudo, arbitrary path access, PTY streaming, or unattended destructive operations to this MVP. Implement narrow typed operations and tests instead.
