# Ship as a Python stdlib skill in its own repository

The reservation flow is small enough to live in a self-contained agent skill: `SKILL.md` plus a Python package invoked through `bin/ccnu`. The skill must work immediately after a directory copy, on any machine where the agent runs, without a toolchain or package install. We therefore use Python with only the standard library: `urllib`, `http.cookiejar`, `html.parser`, and a small AES-128-CBC implementation validated against NIST and OpenSSL vectors.

## Considered Options

- **Go CLI built from the existing client**: rejected. It requires a Go toolchain on every user's machine, and the skill install path has no build step.
- **requests + cryptography**: rejected. Every install path (skills.sh, git clone, Skills Manager) would gain a pip/venv step and a new failure branch, while the only crypto need is decrypting one small HMAC key.
- **Vendored AES**: chosen with published test vectors, because correctness is checkable and performance is irrelevant for a 32-byte payload.

## Consequences

- Installation is a directory copy; `bin/ccnu` resolves its own package path, so no global install is required.
- Protocol changes are code and test changes; `SKILL.md` never restates the protocol.
- On Windows, `zoneinfo` needs `tzdata`; the client falls back to a fixed +08:00 zone.
- The CLI is the skill's API: stable commands, stable JSON keys, typed `error.kind` values.
