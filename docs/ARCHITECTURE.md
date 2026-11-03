# Architecture
ChatGPT/MCP client --HTTPS--> FastAPI gateway -- SQLite
Linux agent -- outbound HTTPS polling/results --> gateway

The PC agent opens no inbound port. Each device has a unique random token; only its keyed digest is stored. One-time enrollment codes expire and are consumed once. Jobs move queued -> leased -> completed/failed; expired leases are requeued. The agent maps fixed operation names to local Python functions. No arbitrary shell or file operations exist.

File operations, project builds, Git actions, terminal access, and remote desktop control are future capabilities requiring separate path-scoped permissions, approvals, isolation, and threat modelling.
