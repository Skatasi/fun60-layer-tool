# GitHubで公開・更新する手順

公開先は [Skatasi/fun60-layer-tool](https://github.com/Skatasi/fun60-layer-tool) です。README.md、fun60_layer_tool.py、.github/が同じ階層にある構成です。

本プロジェクトはGNU GPL v3.0を採用しています。配布時はLICENSEと著作権・参照元の記載を保持してください。

## 更新前の確認

公開リポジトリをcloneし、そのフォルダでPowerShellを開きます。個人用バックアップや診断ログが入った作業フォルダを丸ごと追加しないでください。

```powershell
git clone https://github.com/Skatasi/fun60-layer-tool.git
cd fun60-layer-tool
python fun60_layer_tool.py --version
python -m unittest -v
```

変更を加えたら、公開する内容を確認します。

```powershell
git add .
git status --short
git diff --cached --stat
git diff --cached
```

バックアップ、診断ログ、個人パスやシリアルがステージされていないことを確認します。`.gitignore`はJSON/JSONLとbackups/を除外します。強制追加したファイルや、以前から追跡済みのファイルには効きません。

## コミットとpush

```powershell
git commit -m "Update FUN60 Layer Tool documentation"
git push origin main
```

Gitの名前・メールが未設定の場合は、Gitが表示する案内に従って公開用の名前とメールを設定してください。認証情報やトークンをREADMEやログに書かないでください。外部からの変更提案はForkとPull Requestを利用します。

## 公開後の確認

- READMEと日本語版へのリンクが表示されることを確認。
- `.github/workflows/tests.yml`のテスト結果をActionsで確認。Windows/LinuxとPython 3.10〜3.13のオフラインテストです。実機へのアクセスは行いません。
- Releasesを作成する場合、v0.4の確認状況を明記し、再接続後の保持や他機種での動作を確認済みと書かないでください。

任意のリリース用タグ（同名タグがないことを確認して実行）：

```powershell
git tag v0.4
git push origin v0.4
```
