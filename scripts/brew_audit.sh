#!/usr/bin/env bash
# このチェックアウトを tamat-llc/tap として Homebrew に見せ、Casks/openpath.rb に
# brew style と brew audit --cask をかける（CI の `brew audit` job から使う）。
#
# Homebrew の Taps ディレクトリにシンボリックリンクを作るため、GitHub Actions の中でだけ動かす。
# 手元で style だけ確かめるときは、tap せずに `brew style Casks/openpath.rb` を使う。
set -euo pipefail

readonly TAP_USER="tamat-llc"
readonly TAP_REPOSITORY="homebrew-tap"
readonly CASK="${TAP_USER}/tap/openpath"
# --new は --strict と --online を含み、さらに署名と公証の audit（Gatekeeper の評価）を有効にする。
# 外部の tap では --signing を単独で指定できない（Homebrew 7 で廃止）ため、--new から有効にする。
# --new のうち github_repository は、homebrew/cask へ採用する条件（star・fork・watcher の数と、
# 作成から 30 日以上）を見るだけで、自社の tap には当てはまらないので外す。
readonly AUDIT_ARGS=(--cask --new --except github_repository)

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "error: Homebrew の Taps を書き換えるため、GitHub Actions の中でだけ実行します" >&2
  exit 1
fi

export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_ENV_HINTS=1

repo_root="$(cd "$(dirname "$0")/.." && pwd -P)"
taps_dir="$(brew --repository)/Library/Taps/${TAP_USER}"
tap_dir="${taps_dir}/${TAP_REPOSITORY}"

if [[ -e "${tap_dir}" || -L "${tap_dir}" ]]; then
  echo "error: ${tap_dir} が既にあります" >&2
  exit 1
fi
mkdir -p "${taps_dir}"
ln -s "${repo_root}" "${tap_dir}"

brew --version
brew style --cask "${CASK}"
brew audit "${AUDIT_ARGS[@]}" "${CASK}"
