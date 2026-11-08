#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/at/skills/glossary/path.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
H="$WORK/home"

fail() { echo "FAIL: $*" >&2; exit 1; }
assert_eq() { [ "$1" = "$2" ] || fail "$3: expected '$2', got '$1'"; }

make_repo() {
  local dir="$WORK/$1"
  mkdir -p "$dir" && git -C "$dir" init -q
  [ -z "${2:-}" ] || git -C "$dir" remote add origin "$2"
  echo "$dir"
}

path_for() { (cd "$1" && HOME="$H" bash "$SCRIPT"); }

test_ssh_remote() {
  assert_eq "$(path_for "$(make_repo a git@github.com:example-org/app.git)")" "$H/at-skills-data/github.com/example-org/app" "ssh remote"
}

test_https_remote() {
  assert_eq "$(path_for "$(make_repo b https://github.com/example-org/app)")" "$H/at-skills-data/github.com/example-org/app" "https remote"
}

test_https_remote_with_git_suffix_and_credentials() {
  assert_eq "$(path_for "$(make_repo c https://user@github.com/example-org/web.git)")" "$H/at-skills-data/github.com/example-org/web" "https remote with user and .git"
}

test_ssh_remote_with_port() {
  assert_eq "$(path_for "$(make_repo e ssh://git@github.com:2222/example-org/app.git)")" "$H/at-skills-data/github.com/example-org/app" "ssh remote with port"
}

test_no_remote_uses_folder_name() {
  assert_eq "$(path_for "$(make_repo scratch-repo)")" "$H/at-skills-data/local/scratch-repo" "no remote"
}

test_worktree_shares_the_main_checkout_path() {
  local main
  main="$(make_repo d git@github.com:example-org/api.git)"
  git -C "$main" -c user.name=t -c user.email=t@t commit -q --allow-empty -m init
  git -C "$main" worktree add -q "$WORK/d-wt" -b feature
  assert_eq "$(path_for "$WORK/d-wt")" "$H/at-skills-data/github.com/example-org/api" "worktree"
}

test_outside_a_repo_fails() {
  local status=0
  (cd "$WORK" && HOME="$H" bash "$SCRIPT") > /dev/null 2>&1 || status=$?
  assert_eq "$status" 1 "exit status outside a repo"
}

test_ssh_remote; echo "ok ssh remote"
test_https_remote; echo "ok https remote"
test_https_remote_with_git_suffix_and_credentials; echo "ok https with credentials"
test_ssh_remote_with_port; echo "ok ssh with port"
test_no_remote_uses_folder_name; echo "ok no remote"
test_worktree_shares_the_main_checkout_path; echo "ok worktree"
test_outside_a_repo_fails; echo "ok outside a repo"
echo "All glossary path tests passed."
