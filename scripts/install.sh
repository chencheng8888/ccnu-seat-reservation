#!/bin/sh
# Optional: expose a global `ccnu` command. The skill itself does not need this.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
ln -sf "$ROOT/bin/ccnu" "$BIN_DIR/ccnu"
printf 'linked %s -> %s\n' "$BIN_DIR/ccnu" "$ROOT/bin/ccnu"
case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *) printf 'add %s to PATH to use `ccnu`\n' "$BIN_DIR" ;;
esac
