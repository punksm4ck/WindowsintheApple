#!/usr/bin/env zsh
# =============================================================================
# WindowsintheApple — Shell Compatibility Layer v2
# =============================================================================
# Adds Linux + Windows terminal commands that work natively on macOS.
#
# Install (one time):
#   echo 'source ~/Scripts/WindowsintheApple/shell_compat.sh' >> ~/.zshrc
#   source ~/Scripts/WindowsintheApple/shell_compat.sh
# =============================================================================

[[ "$(uname -s)" != "Darwin" ]] && return 0

# ── Package management ────────────────────────────────────────────────────────
# apt/dnf/pacman → Homebrew, implemented as FUNCTIONS (not aliases) so they
# never get interpreted as brew package names during shell init.

apt() {
    case "$1" in
        install)   shift; brew install "$@" ;;
        remove)    shift; brew uninstall "$@" ;;
        uninstall) shift; brew uninstall "$@" ;;
        update)    brew update && brew upgrade ;;
        upgrade)   brew upgrade ;;
        search)    shift; brew search "$@" ;;
        show)      shift; brew info "$@" ;;
        info)      shift; brew info "$@" ;;
        list)      brew list ;;
        *)         brew "$@" ;;
    esac
}

apt-get()  { apt "$@"; }
dnf()      { apt "$@"; }
pacman()   { apt "$@"; }
yum()      { apt "$@"; }
zypper()   { apt "$@"; }

# ── System info ───────────────────────────────────────────────────────────────

free() {
    vm_stat | awk '
      /Pages free/      { free=$3+0 }
      /Pages active/    { active=$3+0 }
      /Pages inactive/  { inactive=$3+0 }
      /Pages wired/     { wired=$4+0 }
      END {
        page = 4096
        total = (free + active + inactive + wired) * page / 1048576
        used  = (active + wired) * page / 1048576
        avail = free * page / 1048576
        printf "              total        used        free\n"
        printf "Mem:    %10.0f %11.0f %11.0f (MB)\n", total, used, avail
      }'
}

lsmem() {
    sysctl hw.memsize | awk '{printf "Total RAM: %.2f GB\n", $2/1073741824}'
}

nproc() {
    sysctl -n hw.logicalcpu
}

lscpu() {
    sysctl -a 2>/dev/null | grep -E "^machdep\.cpu|^hw\.cpu|^hw\.logical|^hw\.physical"
}

lsblk() {
    diskutil list
}

# ── Networking ────────────────────────────────────────────────────────────────

ip() {
    case "$1" in
        addr|a)   ifconfig ;;
        link|l)   networksetup -listallhardwareports ;;
        route|r)  netstat -rn ;;
        neigh|n)  arp -a ;;
        *)        echo "ip: use ifconfig / netstat on macOS" ;;
    esac
}

ss() {
    netstat -tuln "$@"
}

# ── Systemd → launchd / brew services ────────────────────────────────────────

systemctl() {
    case "$1" in
        start)    shift; brew services start "$@" ;;
        stop)     shift; brew services stop "$@" ;;
        restart)  shift; brew services restart "$@" ;;
        status)   shift; brew services info "$@" ;;
        enable)   shift; brew services start "$@" ;;
        disable)  shift; brew services stop "$@" ;;
        list)     brew services list ;;
        *)        echo "systemctl: mapped to 'brew services' on macOS" ;;
    esac
}

service() {
    local name="$1"
    case "$2" in
        start)   brew services start "$name" ;;
        stop)    brew services stop "$name" ;;
        restart) brew services restart "$name" ;;
        status)  brew services info "$name" ;;
        *)       echo "service: use 'brew services' on macOS" ;;
    esac
}

# ── File / directory aliases ──────────────────────────────────────────────────

alias df='df -h'
alias ll='ls -lhG'
alias la='ls -lahG'
alias l='ls -lhG'
alias grep='grep --color=auto'
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'

# xdg-open → open
alias xdg-open='open'

# wget-style download (uses curl if wget not installed)
if ! command -v wget &>/dev/null; then
    wget() { curl -O --progress-bar "$@"; }
fi

# realpath (built-in on macOS 12.3+, fallback for older)
if ! command -v realpath &>/dev/null; then
    realpath() { python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$1"; }
fi

# locate → Spotlight
alias locate='mdfind'
alias updatedb='mdimport ~'

# cls / c → clear  (Windows + shorthand muscle memory)
alias cls='clear'
alias c='clear'

# which → show all matches
alias which='which -a'

# sudo alias propagation
alias sudo='sudo '

# ── History ───────────────────────────────────────────────────────────────────
HISTSIZE=50000
SAVEHIST=50000

# ── Done ──────────────────────────────────────────────────────────────────────
echo "  ✔  WindowsintheApple shell compat loaded"
