#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null || ! command -v ss >/dev/null; then
  if [[ $EUID != 0 ]]; then echo 'Run with sudo to install Python 3 and iproute2.' >&2; exit 1; fi
  apt-get update
  apt-get install -y python3 iproute2
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
  echo 'Python 3.10 or newer is required.' >&2
  exit 1
fi
exec python3 deckcraft/install_suite.py "$@"
