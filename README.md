# TamaT LLC Homebrew Tap

日本語 | [English](#english)

TamaT LLC が公開している macOS アプリを Homebrew で配布するための tap です。
現在は [openpath](https://github.com/TamaT-LLC/openpath) の cask だけを提供しています。

| cask | 内容 | 動作環境 |
| --- | --- | --- |
| `openpath` | ファイル選択ダイアログにファジー検索のパレットを重ねるメニューバー常駐アプリ | macOS 14 (Sonoma) 以降、Apple Silicon / Intel |

## インストール

```bash
brew install --cask tamat-llc/tap/openpath
```

初回は tap の追加も同時に行われます。
入るのは openpath の Stable（Developer ID 署名と Apple の公証を済ませた正式版）です。

### 初回起動

openpath はアクセシビリティの許可が無いと動きません。
初めて起動すると案内のウインドウが出るので、「システム設定 > プライバシーとセキュリティ > アクセシビリティ」で openpath を許可してください。
使い方と設定は [openpath の README](https://github.com/TamaT-LLC/openpath#readme) を参照してください。

## 更新

```bash
brew upgrade --cask openpath
```

新しい Stable が tap に反映された後、`brew update`（多くの場合は自動）で Homebrew が新しい版を認識します。
更新と削除のときは、起動中の openpath を終了してから入れ替えます。

## 削除

```bash
brew uninstall --cask openpath
```

設定やログも消す場合は `--zap` を付けます。

```bash
brew uninstall --cask --zap openpath
```

`--zap` で消えるのは次の場所です。

- `~/.config/openpath`（設定ファイル）
- `~/Library/Application Support/openpath`
- `~/Library/Logs/openpath`
- `~/Library/Preferences/jp.tamat.openpath.plist`

アクセシビリティの許可の一覧に残った openpath の項目は、システム設定から削除してください。

## Preview は対象外

この tap が配るのは Stable（tag `vX.Y.Z`）だけです。
Preview（tag `preview-vX.Y.Z-N`）は ad-hoc 署名で公証を受けていない評価用の版なので、tap には反映しません。
Preview を試す場合は、[GitHub Releases](https://github.com/TamaT-LLC/openpath/releases) の ZIP を使ってください。

## 自動反映のしくみ

openpath の Stable を公開すると、openpath の Release ワークフローが GitHub App でこの tap に PR を出します。
PR は、Release に添付された cask（`openpath.rb`）で `Casks/openpath.rb` を置き換えるもので、tap の CI が通ると自動でマージされます。
App が出す PR は CI（`brew audit` / `release check`）で検証し、CodeRabbit の自動レビューの対象外です。

CI は次のことを確かめ、1 つでも合わなければマージしません。

- `brew style` と `brew audit --cask` を通ること（job `brew audit`）
- cask の版の Release が、draft でも prerelease でもない Stable であること（job `release check`、以下も同じ）
- ZIP と添付の `openpath.rb` の SHA256 が、Release の `SHA256SUMS` と一致すること
- tap の cask と添付の cask の `version`・`sha256`・`url` が、その Stable の tag と ZIP に一致すること
- PR で cask の版が main より古くならないこと

## メンテナー向け

main のルールセットでは、CI の `brew audit` と `release check` を必須チェックにします。
この 2 つの job 名は openpath の Release ワークフローと合わせているので、変えるときは両方のリポジトリをそろえてください。

`brew audit` job は、`brew audit --cask --new --except github_repository` を実行します。
`--new` は `--strict` と `--online` を含み、署名と公証の audit も有効にします。
外している `github_repository` は、homebrew/cask に採用する条件（star などの数と、作成から 30 日以上）を見る audit で、この tap には当てはまりません。

手元では、tap を追加せずに次の確認ができます。
`brew audit` は tap を必要とするため、CI に任せます。

```bash
HOMEBREW_NO_AUTO_UPDATE=1 brew style Casks/openpath.rb
python3 -m unittest discover -s tests -v
pyright
```

GitHub Actions の action は commit SHA で固定し、`.github/actions-policy.json` に記録します。
checkout では認証情報を残さず（`persist-credentials: false`）、ワークフローには読み取りの権限だけを与えます。

## ライセンス

[MIT License](LICENSE)

## English

This is the Homebrew tap for macOS apps published by TamaT LLC.
It currently provides a single cask, [openpath](https://github.com/TamaT-LLC/openpath), a menu bar app that adds a fuzzy search palette to file open dialogs (macOS 14 Sonoma or later, Apple Silicon and Intel).

```bash
brew install --cask tamat-llc/tap/openpath   # install
brew upgrade --cask openpath                 # update
brew uninstall --cask openpath               # uninstall
brew uninstall --cask --zap openpath         # also remove settings, logs, and preferences
```

- openpath needs the Accessibility permission. Allow it in System Settings > Privacy & Security > Accessibility on first launch.
- Only stable releases (tags `vX.Y.Z`, signed with Developer ID and notarized) are published here. Previews (`preview-vX.Y.Z-N`) are not; download them from GitHub Releases instead.
- When an openpath stable release is published, its release workflow opens a pull request here (through a GitHub App) that replaces `Casks/openpath.rb` with the cask attached to the release. It is merged automatically once CI passes: `brew audit` runs `brew style` and `brew audit --cask`, and `release check` verifies that the release is a stable one and that the cask matches its tag, its ZIP, and `SHA256SUMS`. Pull requests opened by the app are excluded from CodeRabbit's automatic reviews.
