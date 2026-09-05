#!/usr/bin/env bash
# Fail if the translation catalogues are out of date.
#
# Both modes regenerate catalogues in the working tree and then restore
# them, so the tree must be clean under locale/ before we start —
# otherwise the restore would destroy uncommitted work.
set -euo pipefail

mode="${1:?usage: check_translations.sh extract|compile}"

if ! git diff --quiet -- locale || ! git diff --cached --quiet -- locale; then
    echo "locale/ has uncommitted changes." >&2
    echo "Commit or stash them, then try again." >&2
    exit 1
fi

restore() { git checkout -- locale 2>/dev/null || true; }
trap restore EXIT

case "$mode" in
extract)
    # --add-location=file keeps the source file name but drops the line
    # number, so reformatting or moving code inside a file does not
    # churn every catalogue.
    uv run python manage.py makemessages --all --no-obsolete \
        --add-location=file \
        --ignore=.venv --ignore=docs --ignore=tests >/dev/null
    # POT-Creation-Date is rewritten on every run and means nothing, so
    # it is the one difference that does not count.
    drift="$(git diff -U0 -- locale |
        grep -E '^[+-]' |
        grep -vE '^(\+\+\+|---)' |
        grep -vE '^[+-]"POT-Creation-Date:' || true)"
    hint="uv run python manage.py makemessages --all --no-obsolete \\
    --add-location=file --ignore=.venv --ignore=docs --ignore=tests"
    ;;
compile)
    uv run python manage.py compilemessages --ignore=.venv >/dev/null
    drift="$(git status --porcelain -- locale || true)"
    hint="uv run python manage.py compilemessages --ignore=.venv"
    ;;
*)
    echo "usage: check_translations.sh extract|compile" >&2
    exit 2
    ;;
esac

if [ -n "$drift" ]; then
    echo "Translation catalogues are out of date (${mode})." >&2
    echo "$drift" | head -20 >&2
    echo >&2
    echo "Run:  ${hint}" >&2
    echo "and commit the result." >&2
    exit 1
fi
