# Sourced by the tool wrappers. Finds Python 3.8+ and sets PY.
# If none is found, prints the tool's FALLBACK text and exits 3.
# Usage inside a wrapper:
#   FALLBACK="what to do by hand"
#   . "$here/lib/find-python.sh"
#   exec $PY "$here/lib/x.py" "$@"
PY=""
for cand in python3 python "py -3"; do
  # shellcheck disable=SC2086
  if command -v ${cand%% *} >/dev/null 2>&1 && $cand -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
    PY="$cand"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.8 or later was not found on this machine, so this helper cannot run." >&2
  echo "Fallback: ${FALLBACK:-see the usage text at the top of this file and RULES.md (Tools).}" >&2
  echo "Record the fallback in WORKFLOW-LOG.md." >&2
  exit 3
fi
export PYTHONIOENCODING=utf-8
export PYTHONDONTWRITEBYTECODE=1
