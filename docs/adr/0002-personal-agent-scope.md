# Scope: personal agent, single user

This repository ships a skill for a **personal agent** running on the user's own machine (Claude Code, Codex, Cursor, or a local CLI). One person, one credential set, a local config file, and an interactive terminal for `ccnu login`.

A campus agent serving many users from a server is explicitly out of scope for now. It would need per-user credential isolation, an out-of-band binding flow, server-side session management, rate limiting and audit. Those change the deployment shape, not the protocol client.

## Considered Options

- **Build a multi-tenant service now**: rejected for this iteration. It depends on the campus agent platform and on whether the university SSO offers OAuth to third-party apps; neither is decided yet.
- **Keep everything in the skill**: chosen. `ccnu_reservation/` stays a plain library so a service can wrap it later without forking the protocol code.

## Consequences

- Login stays interactive and local. Passwords never enter the conversation or the model context.
- Session tokens are cached locally per user; no server-side session store.
- The CLI remains the skill's API. No MCP or HTTP tool layer in this iteration.
- If a campus agent lands later, reuse `ccnu_reservation/` and add a service layer on top; the protocol, HMAC, AES and window rules stay where they are.
