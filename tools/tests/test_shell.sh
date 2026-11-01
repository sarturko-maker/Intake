#!/usr/bin/env bash
# test_shell.sh: shell-level checks of the tools in tools/.
# Usage: bash tools/tests/test_shell.sh
# Checks: every wrapper in tools/ that exists (--help exits 0 and mentions Usage and Fallback; executable;
#   LF only; a FALLBACK= line); hash-files output format; history-copy naming; skills-sync --check on a
#   temporary workspace, and on this workspace once its mirror has been generated.
# Exit: 0 all passed, 1 a check failed.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$here/../.." && pwd -P)"
TOOLS="$ROOT/tools"
PASS=0
FAIL=0
SKIP=0
ok() { PASS=$((PASS + 1)); echo "ok - $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL - $1"; }
skip() { SKIP=$((SKIP + 1)); echo "skip - $1"; }
check() { if [ "$1" = 0 ]; then ok "$2"; else bad "$2"; fi; }
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test_shell.XXXXXX")" || exit 1
trap 'rm -rf "$TMP"' EXIT
unset INTAKE_ROOT

# ---------------------------------------------------------------- every wrapper
EXPECTED="scan-changes unpack-email place-email new-matter msg2eml hash-files history-copy lint-facts lint-received budget-update index-rebuild tooling-setup skills-sync work-bundle"
for name in $EXPECTED; do
  [ -f "$TOOLS/$name" ] || skip "$name: not present in tools/"
done
CR="$(printf '\r')"
for f in "$TOOLS"/*; do
  [ -f "$f" ] || continue
  name="${f##*/}"
  case "$name" in *.*) continue ;; esac            # README.md, msg2eml.ps1
  head -n 1 "$f" | grep -q '^#!.*bash' || continue
  out="$(bash "$f" --help 2>&1)"
  rc=$?
  r=1
  [ "$rc" = 0 ] && printf '%s' "$out" | grep -q 'Usage' && printf '%s' "$out" | grep -q 'Fallback' && r=0
  check "$r" "$name --help exits 0 and mentions Usage and Fallback"
  r=1; [ -x "$f" ] && r=0
  check "$r" "$name is executable"
  r=0; grep -q "$CR" "$f" && r=1
  check "$r" "$name has LF line endings only"
  r=1; grep -q '^FALLBACK=' "$f" && r=0
  check "$r" "$name has a FALLBACK= line"
done

# ---------------------------------------------------------------- hash-files
if [ -f "$TOOLS/hash-files" ]; then
  printf 'abc' > "$TMP/a b.txt"
  printf '' > "$TMP/empty.txt"
  out="$(bash "$TOOLS/hash-files" "$TMP/a b.txt" "$TMP/empty.txt" 2>&1)"
  rc=$?
  want="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  $TMP/a b.txt
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  $TMP/empty.txt"
  r=1; [ "$rc" = 0 ] && [ "$out" = "$want" ] && r=0
  check "$r" "hash-files prints '<sha256>  <path>' per file"
  [ "$r" = 0 ] || printf '  got: %s\n' "$out"
  out="$(cd "$TMP" && bash "$TOOLS/hash-files" "a b.txt" 2>&1)"
  r=1; printf '%s\n' "$out" | grep -qE '^[0-9a-f]{64}  a b\.txt$' && r=0
  check "$r" "hash-files keeps a relative path as given"
else
  skip "hash-files checks: tool not present"
fi

# ---------------------------------------------------------------- history-copy
if [ -f "$TOOLS/history-copy" ]; then
  mkdir -p "$TMP/hc/m"
  echo "one" > "$TMP/hc/m/matter.md"
  p1="$(cd "$TMP/hc" && bash "$TOOLS/history-copy" m/matter.md)"
  rc1=$?
  p2="$(cd "$TMP/hc" && bash "$TOOLS/history-copy" m/matter.md)"
  re='^m/history/matter\.[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}(-[0-9]+)?\.md$'
  r=1
  [ "$rc1" = 0 ] && printf '%s\n' "$p1" | grep -qE "$re" && [ -f "$TMP/hc/$p1" ] && cmp -s "$TMP/hc/$p1" "$TMP/hc/m/matter.md" && r=0
  check "$r" "history-copy names the copy history/<stem>.<YYYY-MM-DD_HHMMSS>.md"
  r=1
  printf '%s\n' "$p2" | grep -qE "$re" && [ "$p1" != "$p2" ] && [ -f "$TMP/hc/$p2" ] && r=0
  check "$r" "history-copy never overwrites an earlier copy"
  out="$(cd "$TMP/hc" && bash "$TOOLS/history-copy" m/missing.md)"
  rc=$?
  r=1; [ "$rc" = 0 ] && [ "$out" = "no file: m/missing.md" ] && r=0
  check "$r" "history-copy prints 'no file: <path>' and exits 0 for a missing file"
  echo "x" > "$TMP/hc/m/notes"
  p3="$(cd "$TMP/hc" && bash "$TOOLS/history-copy" m/notes)"
  r=1; printf '%s\n' "$p3" | grep -qE '^m/history/notes\.[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}(-[0-9]+)?\.md$' && r=0
  check "$r" "history-copy gives a name without extension the .md ending, as common.history_copy does"
else
  skip "history-copy checks: tool not present"
fi

# ---------------------------------------------------------------- skills-sync --check
if [ -f "$TOOLS/skills-sync" ]; then
  W="$TMP/ws"
  mkdir -p "$W/tools" "$W/skills/operations/demo-skill/templates" "$W/skills/commercial/demo-review"
  cp "$TOOLS/skills-sync" "$W/tools/"
  echo "# rules" > "$W/RULES.md"
  echo "# demo skill" > "$W/skills/operations/demo-skill/SKILL.md"
  echo "template" > "$W/skills/operations/demo-skill/templates/t.md"
  echo "# demo review" > "$W/skills/commercial/demo-review/SKILL.md"
  INTAKE_ROOT="$W" bash "$W/tools/skills-sync" --check >/dev/null 2>&1
  rc=$?
  r=1; [ "$rc" = 1 ] && r=0
  check "$r" "skills-sync --check exits 1 before the mirror exists"
  INTAKE_ROOT="$W" bash "$W/tools/skills-sync" >/dev/null 2>&1
  check "$?" "skills-sync mirrors skills/ to .claude/skills/"
  r=1
  [ -f "$W/.claude/skills/demo-skill/templates/t.md" ] && [ -f "$W/.claude/skills/demo-review/SKILL.md" ] && \
    [ "$(cat "$W/.claude/skills/.generated")" = "Generated by tools/skills-sync from skills/. Do not edit." ] && r=0
  check "$r" "skills-sync copies whole skill folders and writes the .generated marker"
  INTAKE_ROOT="$W" bash "$W/tools/skills-sync" --check >/dev/null 2>&1
  check "$?" "skills-sync --check exits 0 when the mirror matches"
  echo "hand edit" >> "$W/.claude/skills/demo-skill/SKILL.md"
  INTAKE_ROOT="$W" bash "$W/tools/skills-sync" --check >/dev/null 2>&1
  rc=$?
  r=1; [ "$rc" = 1 ] && r=0
  check "$r" "skills-sync --check exits 1 after a hand edit in the mirror"
  r=1; grep -q "hand edit" "$W/.claude/skills/demo-skill/SKILL.md" && r=0
  check "$r" "skills-sync --check writes nothing"
  if [ -f "$ROOT/.claude/skills/.generated" ]; then
    out="$(bash "$TOOLS/skills-sync" --check 2>&1)"
    rc=$?
    check "$rc" "skills-sync --check: this workspace's mirror matches skills/"
    [ "$rc" = 0 ] || printf '%s\n' "$out" | sed 's/^/  /'
  else
    skip "skills-sync --check on this workspace: mirror not generated yet (run bash tools/skills-sync)"
  fi
else
  skip "skills-sync checks: tool not present"
fi

echo "test_shell: $PASS passed, $FAIL failed, $SKIP skipped"
[ "$FAIL" = 0 ]
