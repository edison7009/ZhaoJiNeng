#!/usr/bin/env bash
# ============================================================
#  zhaojineng CLI installer
#  Usage: curl -fsSL https://zhaojineng.com/install.sh | bash
# ============================================================
set -euo pipefail

BRAND="zhaojineng"
KIT_URL="https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/latest.tar.gz"
INSTALL_DIR="${HOME}/.${BRAND}"
BIN_DIR="${INSTALL_DIR}/bin"

echo ""
echo "  🦞 ${BRAND} CLI installer"
echo "  ========================="
echo ""

# --- Step 1: Install SkillHub CLI (Tencent COS mirror) ---
echo "  [1/3] Downloading SkillHub CLI from China mirror..."
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL "$KIT_URL" -o "$TMP_DIR/latest.tar.gz"
tar -xzf "$TMP_DIR/latest.tar.gz" -C "$TMP_DIR"

INSTALLER="$TMP_DIR/cli/install.sh"
if [[ ! -f "$INSTALLER" ]]; then
  echo "  ❌ Error: SkillHub installer not found." >&2
  exit 1
fi

echo "  [2/3] Installing SkillHub CLI..."
bash "$INSTALLER" "$@"

# --- Step 2: Create zhaojineng wrapper ---
echo "  [3/3] Setting up ${BRAND} command..."

mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/${BRAND}" << 'WRAPPER'
#!/usr/bin/env bash
# zhaojineng - China mirror wrapper for SkillHub / ClawHub
# https://zhaojineng.com

if ! command -v skillhub &>/dev/null; then
  echo "❌ SkillHub CLI not found. Please reinstall:"
  echo "   curl -fsSL https://zhaojineng.com/install.sh | bash"
  exit 1
fi

exec skillhub "$@"
WRAPPER

chmod +x "$BIN_DIR/${BRAND}"

# --- Step 3: Add to PATH ---
SHELL_NAME="$(basename "${SHELL:-bash}")"
PROFILE=""

case "$SHELL_NAME" in
  zsh)  PROFILE="$HOME/.zshrc" ;;
  bash)
    if [[ -f "$HOME/.bash_profile" ]]; then
      PROFILE="$HOME/.bash_profile"
    else
      PROFILE="$HOME/.bashrc"
    fi
    ;;
  fish) PROFILE="$HOME/.config/fish/config.fish" ;;
esac

PATH_LINE="export PATH=\"${BIN_DIR}:\$PATH\""

if [[ -n "$PROFILE" ]]; then
  if ! grep -qF "$BIN_DIR" "$PROFILE" 2>/dev/null; then
    echo "" >> "$PROFILE"
    echo "# ${BRAND} CLI" >> "$PROFILE"
    if [[ "$SHELL_NAME" == "fish" ]]; then
      echo "set -gx PATH ${BIN_DIR} \$PATH" >> "$PROFILE"
    else
      echo "$PATH_LINE" >> "$PROFILE"
    fi
  fi
fi

export PATH="${BIN_DIR}:$PATH"

echo ""
echo "  ✅ ${BRAND} CLI installed successfully!"
echo ""
echo "  Usage:"
echo "    ${BRAND} install <skill-name>    Install a skill"
echo "    ${BRAND} list                    List installed skills"
echo "    ${BRAND} search <keyword>        Search skills"
echo ""
echo "  Example:"
echo "    ${BRAND} install youtube-watcher"
echo ""
echo "  🔄 Please restart your terminal or run:"
echo "    source ${PROFILE:-~/.bashrc}"
echo ""
