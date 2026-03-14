# ============================================================
#  zhaojineng CLI installer for Windows (PowerShell)
#  Usage: irm https://zhaojineng.com/install.ps1 | iex
# ============================================================
$ErrorActionPreference = "Stop"

$BRAND      = "zhaojineng"
$KIT_URL    = "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/install/latest.tar.gz"
$INSTALL_DIR = "$env:USERPROFILE\.$BRAND"
$BIN_DIR    = "$INSTALL_DIR\bin"

Write-Host ""
Write-Host "  🦞 $BRAND CLI installer (Windows)" -ForegroundColor Cyan
Write-Host "  ===============================" -ForegroundColor Cyan
Write-Host ""

# --- Check prerequisites ---
function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

if (-not (Test-Command "curl.exe")) {
    Write-Host "  [!] curl.exe not found. Please use Windows 10 1803+ or install curl manually." -ForegroundColor Red
    exit 1
}

# --- Step 1: Download SkillHub CLI (Tencent COS mirror) ---
Write-Host "  [1/3] Downloading SkillHub CLI from China mirror..." -ForegroundColor Yellow

$TMP_DIR = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $TMP_DIR | Out-Null

try {
    $tarPath = "$TMP_DIR\latest.tar.gz"
    curl.exe -fsSL $KIT_URL -o $tarPath

    if (-not (Test-Path $tarPath)) {
        Write-Host "  ❌ Download failed." -ForegroundColor Red
        exit 1
    }

    # Extract using tar (available in Windows 10 1803+)
    if (Test-Command "tar") {
        tar -xzf $tarPath -C $TMP_DIR
    } else {
        Write-Host "  ❌ tar command not found. Please use Windows 10 1803+ or later." -ForegroundColor Red
        exit 1
    }

    # --- Step 2: Run SkillHub installer ---
    Write-Host "  [2/3] Installing SkillHub CLI..." -ForegroundColor Yellow

    $skillhubInstaller = "$TMP_DIR\cli\install.sh"
    if (-not (Test-Path $skillhubInstaller)) {
        Write-Host "  ❌ SkillHub installer not found in package." -ForegroundColor Red
        exit 1
    }

    # Try WSL first, then Git Bash
    if (Test-Command "wsl") {
        $linuxPath = wsl wslpath -u $skillhubInstaller.Replace('\', '/')
        wsl bash $linuxPath
    } elseif (Test-Command "bash") {
        bash $skillhubInstaller
    } else {
        Write-Host "  ❌ No bash environment found (WSL or Git Bash required)." -ForegroundColor Red
        Write-Host "  💡 Please install WSL: https://learn.microsoft.com/windows/wsl/install" -ForegroundColor Yellow
        Write-Host "     Or install Git for Windows: https://git-scm.com/download/win" -ForegroundColor Yellow
        exit 1
    }

} finally {
    Remove-Item -Recurse -Force $TMP_DIR -ErrorAction SilentlyContinue
}

# --- Step 3: Add to PATH ---
Write-Host "  [3/3] Setting up $BRAND command..." -ForegroundColor Yellow

New-Item -ItemType Directory -Path $BIN_DIR -Force | Out-Null

$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$BIN_DIR*") {
    [Environment]::SetEnvironmentVariable("PATH", "$BIN_DIR;$currentPath", "User")
    $env:PATH = "$BIN_DIR;$env:PATH"
    Write-Host "  ✅ Added $BIN_DIR to PATH" -ForegroundColor Green
}

Write-Host ""
Write-Host "  ✅ $BRAND CLI installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Usage:" -ForegroundColor White
Write-Host "    $BRAND install <skill-name>    Install a skill" -ForegroundColor Gray
Write-Host "    $BRAND list                    List installed skills" -ForegroundColor Gray
Write-Host "    $BRAND search <keyword>        Search skills" -ForegroundColor Gray
Write-Host ""
Write-Host "  Example:" -ForegroundColor White
Write-Host "    $BRAND install youtube-watcher" -ForegroundColor Gray
Write-Host ""
Write-Host "  🔄 Please restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
Write-Host ""
