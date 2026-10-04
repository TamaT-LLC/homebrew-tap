# TamaT LLC Homebrew Tap

日本語 | [English](#english)

TamaT LLC のアプリと CLI を Homebrew で配布する tap です。
[openpath](https://github.com/TamaT-LLC/openpath) の cask と [depgraph](https://github.com/TamaT-LLC/depgraph-cli) の Formula を提供しています。

| cask | 内容 | 動作環境 |
| --- | --- | --- |
| `openpath` | ファイル選択ダイアログにファジー検索のパレットを重ねるメニューバー常駐アプリ | macOS 14 (Sonoma) 以降、Apple Silicon / Intel |

## depgraph のインストール

macOS（Apple Silicon / Intel）と Linux（ARM64 / x86-64）向けの公式ネイティブパッケージを導入します。
Linux は Ubuntu 24.04 の glibc 環境で検証します。

```bash
brew install tamat-llc/tap/depgraph
```

初回は tap の追加と depgraph Formula の信頼設定も行われます。
その後は tap 名を省略できます。

```bash
brew install depgraph
brew upgrade depgraph
brew uninstall depgraph
```

tap を追加済みでも信頼設定がない場合は、先に `brew trust --formula tamat-llc/tap/depgraph` を実行します。
Node.js 24 系は Homebrew が導入し、ランチャーがその実行ファイルを選びます。
Go・Rust の解析には、対象プロジェクトのツールチェーンとオフライン依存関係が必要です。
`depgraph-mcp` も入りますが、MCP / compiler-precise 解析には同じ版・ターゲットの検証済み compiler pack が追加で必要です。
導入手順は [depgraph の README](https://github.com/TamaT-LLC/depgraph-cli#readme) を参照してください。

Formula は公式アーカイブの全ファイルを変更せずに保持します。
CI は署名付き tag、成功した CI / Release、公開後証跡、4 ターゲットの SHA-256、版の後退がないことを検証します。
macOS / Linux の各 CPU で `brew install` と `brew test` を実行し、Web の解析と同梱ワーカーの整合性を確認します。

メンテナーは次のコマンドで新しい Stable の Formula を生成できます。
公開後証跡がない Release や、一部ターゲットが欠けている Release は拒否します。

```bash
python3 scripts/depgraph_release.py render --tag vX.Y.Z --base-formula Formula/depgraph.rb
python3 scripts/depgraph_release.py verify
```

## openpath のインストール

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

This is the Homebrew tap for apps and CLI tools published by TamaT LLC.
It provides the `depgraph` formula (macOS / Linux, ARM64 / x86-64) and the cask [openpath](https://github.com/TamaT-LLC/openpath), a menu bar app that adds a fuzzy search palette to file open dialogs (macOS 14 Sonoma or later, Apple Silicon and Intel).

```bash
brew install --cask tamat-llc/tap/openpath   # install
brew upgrade --cask openpath                 # update
brew uninstall --cask openpath               # uninstall
brew uninstall --cask --zap openpath         # also remove settings, logs, and preferences
```

- openpath needs the Accessibility permission. Allow it in System Settings > Privacy & Security > Accessibility on first launch.
- Only stable releases (tags `vX.Y.Z`, signed with Developer ID and notarized) are published here. Previews (`preview-vX.Y.Z-N`) are not; download them from GitHub Releases instead.
- When an openpath stable release is published, its release workflow opens a pull request here (through a GitHub App) that replaces `Casks/openpath.rb` with the cask attached to the release. It is merged automatically once CI passes: `brew audit` runs `brew style` and `brew audit --cask`, and `release check` verifies that the release is a stable one and that the cask matches its tag, its ZIP, and `SHA256SUMS`. Pull requests opened by the app are excluded from CodeRabbit's automatic reviews.

Install depgraph with `brew install tamat-llc/tap/depgraph` once; then use
`brew install depgraph`, `brew upgrade depgraph`, and `brew uninstall depgraph`.
If you already tapped the repository without trusting the formula, run
`brew trust --formula tamat-llc/tap/depgraph` first.
Node.js 24 is installed as a dependency and selected by the launchers. Existing
project toolchains/offline dependencies are needed for Go and Rust analysis.
MCP/compiler-precise analysis needs the matching verified compiler pack.
The formula preserves the entire native package; CI verifies signed tags,
successful CI/Release runs, public evidence, four archive digests, and rejects
downgrades. Installation and worker-integrity tests run on all four platforms.
