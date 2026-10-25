#!/usr/bin/env bash
# deploy/install_claude.sh  v5.1
# v5.1  2026-10-25  OTV5 r13 (BOOT.12) — OT_CLAUDE_SETTINGS_REPLACE=1 REPLACES a box's existing ~/.claude/settings.json with
#       the chosen template, keeping the old file as settings.json.pre-<UTC stamp>. Without it an existing file is left as
#       it is (unchanged), so a box built before OTV5 - SOFI, 2026-10-25, with the deny-less settings - could not be moved
#       to the observe-only settings by re-running this. The login is never touched.
# v5.0  2026-10-25  OTV5 r7 (SPLIT.1) — HEADER RESET AT THE LINEAGE SPLIT. Every entry below this line is the predecessor's history (cited by its own prefix); from here each change to this file counts v5.1, v5.2, ...
#
# v1.2  2026-10-24  CD.1 — THE SETTINGS NAME THE REPOSITORY FROM deploy/origin.conf: {{ORIGIN_REPO}} in the template is
#       rendered at install (sed), so a tree copied into a new repository trusts the new origin, not the old one.
#       OT_CLAUDE_SETTINGS=pull-only installs deploy/claude-user-settings-pull-only.json the same way.
#
# v1.1  2026-09-24  OTV4TEST r133 — ~/.local/bin goes on PATH for login shells
#       (~/.bashrc, once). Anthropic's installer warns it is missing on a fresh
#       box; tools/claude_boot.py never needed it (it resolves the binary by path)
#       but the operator typing `claude` over SSH did.
# v1.0  2026-09-24  OTV4TEST r132 — CLAUDE CODE ON A FRESH BOX, PINNED, WITH ITS
#       OWN LOGIN. The operator: "after the first boot on a fresh instance, I want
#       Claude to come up with it in a remote control session and look everything
#       over", "Can we add the Claude authentication into the bootstrap's secret
#       file that I upload?" and "freeze every software version".
#
# 🔑 CLAUDE IS NOT A PIP PACKAGE, SO IT IS NOT IN requirements.txt. It is a
#    native binary installed by Anthropic's installer into ~/.local/bin, pinned
#    here to OT_CLAUDE_VERSION (the reference box's version) with the
#    auto-updater off in the user settings, so a fresh box runs what was tested.
#
# WHAT IT DOES — every step idempotent, safe to re-run by hand:
#   1. binary    ~/.local/bin/claude at exactly OT_CLAUDE_VERSION (else install it)
#   2. settings  ~/.claude/settings.json from deploy/claude-user-settings.json,
#                ONLY IF ABSENT (never overwrites a box's own settings). It holds
#                what a PROJECT file cannot: the auto-mode rules and
#                remoteControlAtStartup. The permissions ride in the repo's
#                committed .claude/settings.json.
#   3. login     CLAUDE_LOGIN_B64 (optional) — a base64 tar.gz of a DEDICATED
#                login's .credentials.json (+ .claude.json), made on the operator's
#                side with CLAUDE_CONFIG_DIR (see bootstrap.example.sh). Written
#                0600. ⚠️ NEVER PRINTED, and only those two member names are
#                accepted from the archive.
#   4. flags     pre-answers the first-run prompts in ~/.claude.json: onboarding,
#                trust for the repo directory, the Remote Control notice.
#                ⚠️ UNDOCUMENTED KEYS, read off the reference box; if a Claude
#                release renames them, the prompt simply appears once.
#   5. verify    `claude auth status` — rc 0 logged in, rc 1 not (measured on
#                2.1.281 with a must-fail control: an empty CLAUDE_CONFIG_DIR).
#
# ⚠️ IT NEVER FAILS THE INSTALL OVER THE LOGIN. A box without an agent still
#    trades (§29 — nothing agent-side is load-bearing). A missing or rejected
#    login is REPORTED with the one command that fixes it. Only a binary that
#    cannot be installed at the pinned version exits non-zero.
#
# Usage:  bash deploy/install_claude.sh
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${OT_CLAUDE_VERSION:-2.1.281}"
BIN="$HOME/.local/bin/claude"
# OT_CLAUDE_SETTINGS=pull-only installs the pull-only template (a box that never lands or pushes)
TEMPLATE="$DIR/deploy/claude-user-settings${OT_CLAUDE_SETTINGS:+-$OT_CLAUDE_SETTINGS}.json"
# The launch strips API-key variables (tools/claude_boot.py AUTH.1); so does
# the auth check, or a stray key would read as "logged in".
NOKEY=(env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN -u CLAUDE_API_KEY -u ANTHROPIC_BASE_URL)

say()  { echo "  claude: $*"; }

# ── 1. binary, pinned ───────────────────────────────────────────────────────
have="$("$BIN" --version 2>/dev/null | awk '{print $1}')"
if [ "$have" = "$VERSION" ]; then
    say "binary $VERSION already installed"
else
    say "installing Claude Code $VERSION (found: ${have:-none})"
    if ! curl -fsSL https://claude.ai/install.sh | bash -s "$VERSION"; then
        say "🔴 installer failed"; exit 1
    fi
    have="$("$BIN" --version 2>/dev/null | awk '{print $1}')"
    if [ "$have" != "$VERSION" ]; then
        say "🔴 expected $VERSION at $BIN, found '${have:-nothing}'"; exit 1
    fi
    say "binary $VERSION installed at $BIN"
fi

# r133 — `claude` by name in the operator's shell; added once, never duplicated.
if ! grep -qs '\.local/bin' "$HOME/.bashrc"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    say "~/.local/bin added to PATH in ~/.bashrc"
fi

# ── 2. user settings, never overwritten ─────────────────────────────────────
mkdir -p "$HOME/.claude"
if [ -f "$HOME/.claude/settings.json" ] && [ "${OT_CLAUDE_SETTINGS_REPLACE:-0}" = "1" ] && [ -f "$TEMPLATE" ]; then
    # BOOT.12 (r13) — the old file is kept beside it, never deleted
    _bak="$HOME/.claude/settings.json.pre-$(date -u +%Y%m%dT%H%M%SZ)"
    cp -p "$HOME/.claude/settings.json" "$_bak"
    _origin="$( . "$DIR/deploy/origin.conf" && echo "$OT_ORIGIN_REPO" )"
    sed "s#{{ORIGIN_REPO}}#${_origin}#g" "$TEMPLATE" > "$HOME/.claude/settings.json"
    say "user settings REPLACED from $(basename "$TEMPLATE") (old kept as $(basename "$_bak"))"
elif [ -f "$HOME/.claude/settings.json" ]; then
    say "user settings present — left as they are"
elif [ -f "$TEMPLATE" ]; then
    # CD.1 — {{ORIGIN_REPO}} is rendered from deploy/origin.conf, the one place the repository is named
    _origin="$( . "$DIR/deploy/origin.conf" && echo "$OT_ORIGIN_REPO" )"
    sed "s#{{ORIGIN_REPO}}#${_origin}#g" "$TEMPLATE" > "$HOME/.claude/settings.json"
    say "user settings written from $(basename "$TEMPLATE") (origin ${_origin})"
else
    say "⚠️ template missing ($TEMPLATE) — no user settings written"
fi

# ── 3. the dedicated login ──────────────────────────────────────────────────
if [ -n "${CLAUDE_LOGIN_B64:-}" ]; then
    tmp="$(mktemp -d "$HOME/.claude-login.XXXXXX")"
    chmod 700 "$tmp"
    if printf '%s' "$CLAUDE_LOGIN_B64" | base64 -d 2>/dev/null \
         | tar -xzf - -C "$tmp" .credentials.json 2>/dev/null; then
        install -m 600 "$tmp/.credentials.json" "$HOME/.claude/.credentials.json"
        # .claude.json is optional in the archive (it carries the account
        # profile); extract it separately so its absence is not an error.
        printf '%s' "$CLAUDE_LOGIN_B64" | base64 -d 2>/dev/null \
            | tar -xzf - -C "$tmp" .claude.json 2>/dev/null || true
        if [ -f "$tmp/.claude.json" ] && [ ! -f "$HOME/.claude.json" ]; then
            install -m 600 "$tmp/.claude.json" "$HOME/.claude.json"
        elif [ -f "$tmp/.claude.json" ]; then
            # merge the account profile into an existing file; keep its flags
            python3 - "$tmp/.claude.json" "$HOME/.claude.json" <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
s = json.load(open(src)); d = json.load(open(dst))
for k in ("oauthAccount", "userID"):
    if k in s:
        d[k] = s[k]
json.dump(d, open(dst, "w"), indent=2)
PY
            chmod 600 "$HOME/.claude.json"
        fi
        say "login installed from CLAUDE_LOGIN_B64 (0600)"
    else
        say "⚠️ CLAUDE_LOGIN_B64 did not decode to an archive holding .credentials.json — ignored"
    fi
    command -v shred >/dev/null 2>&1 && find "$tmp" -type f -exec shred -u {} + 2>/dev/null
    rm -rf "$tmp"
else
    say "no CLAUDE_LOGIN_B64 — log in by hand (below)"
fi

# ── 4. first-run prompts, pre-answered ──────────────────────────────────────
python3 - "$HOME/.claude.json" "$DIR" <<'PY'
import json, os, sys
path, repo = sys.argv[1], sys.argv[2]
d = {}
if os.path.exists(path):
    try:
        d = json.load(open(path))
    except Exception:
        d = {}
d["hasCompletedOnboarding"] = True
d["remoteDialogSeen"] = True
d.setdefault("projects", {}).setdefault(repo, {})["hasTrustDialogAccepted"] = True
json.dump(d, open(path, "w"), indent=2)
os.chmod(path, 0o600)
PY
say "first-run prompts pre-answered for $DIR"

# ── 5. verify ───────────────────────────────────────────────────────────────
if "${NOKEY[@]}" "$BIN" auth status >/dev/null 2>&1; then
    say "✅ logged in"
else
    say "⚠️ NOT logged in. Fix once, by hand:  ssh in, run:  claude auth login"
    say "   then:  sudo systemctl start optbot-claude-boot.service"
fi
exit 0
