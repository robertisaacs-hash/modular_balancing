#!/usr/bin/env bash
set -euo pipefail

URL="${1:-https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple}"
CA="/c/Users/hrisaac/combined-ca.pem"

banner() { echo -e "\n==================== $* ====================\n"; }
curl_code() { curl -sS -o /dev/null -w "%{http_code}" --head "$@"; }

do_check() {
  local name="$1"; shift
  banner "$name"
  echo "URL: $URL"
  if [[ -f "$CA" ]]; then
    CODE="$(curl_code "$@" --cacert "$CA" "$URL")" || EC=$? || true
  else
    echo "NOTE: CA bundle not found at $CA — testing without --cacert"
    CODE="$(curl_code "$@" "$URL")" || EC=$? || true
  fi
  EC="${EC:-0}"
  echo "HTTP: $CODE   curl_exit: $EC"
  if [[ "$EC" -eq 0 && ( "$CODE" == 200 || "$CODE" == 401 ) ]]; then
    echo "RESULT: PASS"
  else
    echo "RESULT: FAIL"
  fi
  unset EC
}

# 1) Proxy 8080
export HTTP_PROXY="http://proxy.wal-mart.com:8080"
export HTTPS_PROXY="http://proxy.wal-mart.com:8080"
unset NO_PROXY no_proxy
do_check "Proxy via 8080" --proxy "$HTTP_PROXY"

# 2) Proxy 9080
export HTTP_PROXY="http://proxy.wal-mart.com:9080"
export HTTPS_PROXY="http://proxy.wal-mart.com:9080"
unset NO_PROXY no_proxy
do_check "Proxy via 9080" --proxy "$HTTP_PROXY"

# 3) Direct (bypass) for host
unset HTTP_PROXY HTTPS_PROXY
export NO_PROXY="pypi.ci.artifacts.walmart.com,nexus.prod.walmart.com"
export no_proxy="$NO_PROXY"
do_check "Direct (NO_PROXY for host)"
