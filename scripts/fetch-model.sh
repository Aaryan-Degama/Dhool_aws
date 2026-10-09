#!/usr/bin/env bash
# Download the screenshot reader's weights into vision/models/ (1.5 GB, not kept in git).
# Qwen3-VL-2B-Instruct, GGUF build by the Qwen team, Apache-2.0. Pinned to one revision and checked by hash,
# so every build gets byte-identical weights. Safe to re-run: finished files are skipped, partial ones resume.
set -euo pipefail
mkdir -p "$(dirname "$0")/../vision/models"
cd "$(dirname "$0")/../vision/models"
BASE=https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF/resolve/52d6c8ffea26cc873ac5ad116f8631268d7eb503
fetch() {
  if [ -f "$1" ] && echo "$2  $1" | sha256sum -c --status; then echo "$1: already here"; return; fi
  curl -fL -C - --retry 5 -o "$1" "$BASE/$1"
  echo "$2  $1" | sha256sum -c
}
fetch Qwen3VL-2B-Instruct-Q4_K_M.gguf 089d75c52f4b7ffc56ba998ffc50aae89fcafc755f9e7208aacca281dca6c2ae
fetch mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf f9a68fabba69c3b81e153367b2c7521030b0fa8bb0de400c9599c8e6725f9c82
