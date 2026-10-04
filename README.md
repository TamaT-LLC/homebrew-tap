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

openpath の Stable を公開すると、その Release に cask（`openpath.rb`）と `SHA256SUMS` が添付されます。
この tap の GitHub Actions は 1 時間ごとに openpath の最新の Stable を確認し、新しい版があれば添付の cask を検証してから `Casks/openpath.rb` を置き換えます。
そのため、Stable の公開から tap への反映までには、最大で 1 時間程度かかります。

反映する前に、次のことを確かめます。

- ZIP と `openpath.rb` の SHA256 が、Release の `SHA256SUMS` と一致すること
- cask の `version` が tag と一致し、`sha256` がその ZIP と一致すること
- cask の `url` が、その Stable の ZIP を指していること
- `brew style` と `brew audit --cask` を通ること

1 つでも合わなければ反映せず、ワークフローを失敗にします。

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
- A GitHub Actions workflow checks the latest openpath stable release about once an hour. It verifies the attached cask against `SHA256SUMS`, the tag, and the ZIP, runs `brew style` and `brew audit --cask`, and only then updates `Casks/openpath.rb`.
