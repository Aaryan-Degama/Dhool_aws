#!/usr/bin/env bash
# sam build, passing the host's proxy (if any) into the container build without writing it to the image
# or to your Docker settings. Behind a campus proxy a plain `sam build` cannot reach PyPI.
set -euo pipefail
if [ -n "${HTTPS_PROXY:-}" ]; then
  export DOCKER_CONFIG="$(mktemp -d)"
  trap 'rm -rf "$DOCKER_CONFIG"' EXIT
  python3 -c 'import json, os; json.dump({"proxies": {"default": {"httpProxy": os.environ.get("HTTP_PROXY", ""), "httpsProxy": os.environ["HTTPS_PROXY"], "noProxy": os.environ.get("NO_PROXY", "")}}}, open(os.environ["DOCKER_CONFIG"] + "/config.json", "w"))'
fi
"$(dirname "$0")/fetch-model.sh"  # the screenshot reader's weights, if they are not here yet
sam build "$@"
