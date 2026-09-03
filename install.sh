#!/bin/bash
# Theme-GUI Installer for Hyprtk
# Creates venv, installs app, creates launcher scripts, installs desktop file
# Usage: ./install.sh          — install
#        ./install.sh --uninstall — remove everything

set -euo pipefail

APP_NAME="theme-gui"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
CACHE_DIR="$HOME/.cache/$APP_NAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Uninstall ──────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" || "${1:-}" == "-u" ]]; then
    echo ":: Uninstalling theme-gui..."

    rm -rf "$INSTALL_DIR"
    rm -f "$BIN_DIR/theme-gui"
    rm -f "$BIN_DIR/hyprtk-themer"
    rm -f "$APPS_DIR/hyprtk-themer.desktop"
    rm -rf "$CACHE_DIR"
    rm -rf "$HOME/.cache/theme-gui"
    update-desktop-database "$APPS_DIR" 2>/dev/null || true

    echo ":: Removed: $INSTALL_DIR"
    echo ":: Removed: $BIN_DIR/theme-gui"
    echo ":: Removed: $BIN_DIR/hyprtk-themer"
    echo ":: Removed: $APPS_DIR/hyprtk-themer.desktop"
    echo ":: Removed: $CACHE_DIR"
    echo ":: Removed: $HOME/.cache/theme-gui"
    echo ":: Done. theme-gui has been uninstalled."
    exit 0
fi

# ── Install ────────────────────────────────────────────────
echo ":: Installing theme-gui..."

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APPS_DIR"

# Copy source
cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/pyproject.toml" "$INSTALL_DIR/"

# Create venv and install
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR" --quiet 2>/dev/null || \
"$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR" --quiet

# Create launcher script (theme-gui)
cat > "$BIN_DIR/theme-gui" << LAUNCHER
#!/bin/bash
exec "$INSTALL_DIR/venv/bin/python3" -m theme_gui "\$@"
LAUNCHER
chmod +x "$BIN_DIR/theme-gui"

# Create wrapper script (hyprtk-themer) for desktop launcher
cat > "$BIN_DIR/hyprtk-themer" << 'WRAPPER'
#!/bin/bash
exec theme-gui "$@"
WRAPPER
chmod +x "$BIN_DIR/hyprtk-themer"

# Install desktop file
cp "$SCRIPT_DIR/hyprtk-themer.desktop" "$APPS_DIR/"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo ":: theme-gui installed to $BIN_DIR/theme-gui"
echo ":: hyprtk-themer desktop launcher installed"

# ── Build wallpaper cache ──────────────────────────────────
echo ":: Building wallpaper cache..."
WALLPAPER_DIR="${HOME}/Pictures/Wallpapers"
CACHE_DIR="${HOME}/.cache/theme-gui"
mkdir -p "$CACHE_DIR/thumbnails"

if [ -d "$WALLPAPER_DIR" ]; then
    "$INSTALL_DIR/venv/bin/python3" -c "
from pathlib import Path
from theme_gui.cache import build_index
build_index(Path('$WALLPAPER_DIR'), force=True)
print('   Cached', len(list(Path('$WALLPAPER_DIR').glob('*'))), 'entries')
" 2>/dev/null && echo ":: Wallpaper cache built" || echo ":: Cache build skipped (no images found)"
else
    echo ":: Wallpaper dir not found, skipping cache"
fi

echo ":: Run 'install.sh --uninstall' to remove"
