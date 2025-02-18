#!/usr/bin/env bash

set -e

PLATFORM="$1"
if [ -z "${PLATFORM}" ]; then
    echo "Usage: build.sh platform"
fi

case "$PLATFORM" in
  linux-x86_64)
    echo Building for Linux x86_64
    PEX_SCIE_PLATFORM=linux-x86_64
    PEX_PLATFORM=manylinux_2_17_x86_64-cp-3.12-cp312
    ;;
  linux-aarch64 | linux-arm64)
    echo Building for Linux aarch64/arm64
    PEX_SCIE_PLATFORM=linux-aarch64
    PEX_PLATFORM=manylinux_2_17_aarch64-cp-3.12-cp312
    ;;
  macos-x86_64)  
    echo Building for macOS x86_64
    PEX_SCIE_PLATFORM=macos-x86_64
    PEX_PLATFORM=macosx-11.0-x86_64-cp-312-cp312
    ;;
  macos-aarch64 | macos-arm64)  
    echo Building for macOS aarch64/arm64
    PEX_SCIE_PLATFORM=macos-aarch64
    PEX_PLATFORM=macosx-12.0-arm64-cp-312-cp312
    ;;
  *)
    echo "Unknown platform: \"$platform\". See build script for details."
    exit 1
    ;;
esac

pex . $(pipenv requirements | pip freeze) \
  -m con-espressione \
  -o dist/con-espressione \
  --scie eager \
  --scie-only \
  --scie-name-style platform-file-suffix \
  --scie-platform "$PEX_SCIE_PLATFORM" \
  --platform "$PEX_PLATFORM" \
  -v
