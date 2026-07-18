#!/usr/bin/env bash
#
# Build and install the spotDL Flatpak locally (per-user).
#
# Usage:
#   ./packaging/flatpak/build.sh          # build + install + nothing else
#   ./packaging/flatpak/build.sh --run    # build + install + launch the app
#
set -euo pipefail

APP_ID="io.github.loafdaddy.SpotdlGnome"
RUNTIME_VERSION="48"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/${APP_ID}.yml"
BUILD_DIR="${SCRIPT_DIR}/build-dir"

if ! command -v flatpak-builder >/dev/null 2>&1; then
  echo "flatpak-builder is not installed."
  echo "On Fedora: sudo dnf install flatpak-builder"
  exit 1
fi

# Ensure Flathub is configured for the current user.
flatpak --user remote-add --if-not-exists flathub \
  https://flathub.org/repo/flathub.flatpakrepo

# Install the GNOME runtime + SDK the manifest builds against.
flatpak --user install -y flathub \
  "org.gnome.Platform//${RUNTIME_VERSION}" \
  "org.gnome.Sdk//${RUNTIME_VERSION}"

# Build and install into the user installation.
flatpak-builder --user --install --force-clean \
  "${BUILD_DIR}" "${MANIFEST}"

echo
echo "Installed ${APP_ID}."
echo "Launch it with: flatpak run ${APP_ID}"

if [[ "${1:-}" == "--run" ]]; then
  exec flatpak run "${APP_ID}"
fi
