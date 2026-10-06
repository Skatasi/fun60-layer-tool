# FUN60 Layer Tool

[English](README.md) · [プロトコル詳細](docs/PROTOCOL.md) · [変更履歴](CHANGELOG.md)

MonsGeek FUN60 PROの **Fn+G/H/J/Kに、本体プロファイル0/1/2/3への切替を割り当てる非公式Pythonツール**です。

設定後はPythonを常駐させる必要はありません。切り替えるのは本体プロファイル全体で、QMKのレイヤーではありません。ファームウェアを書き換えるツールではなく、MonsGeek/Akkoの公式製品でもありません。

| 操作 | 内部プロファイル番号 | 公式画面が1始まりの場合 |
| --- | --- | --- |
| Fn+G | 0 | 1 |
| Fn+H | 1 | 2 |
| Fn+J | 2 | 3 |
| Fn+K | 3 | 4 |

切替先からも同じ操作を使えるよう、4プロファイルすべてのWindows用Fnテーブルに割り当てます。

## 対応機種と確認状況

| VID | PID | 内部機種ID | 状況 |
| --- | --- | --- | --- |
| `3151` | `5029` | `2600` | Windowsの1個体でv0.4の書込み、全Fnテーブルの読戻し、実際の切替、後続の設定一致を確認 |
| `3151` | `502F` | `2305` | 公開資料に基づく対応。こちらでは実機未検証 |

USB識別子と内部機種IDの組合せで判定します。商品名だけでは判定しません。

- Python **3.10以上**、`hidapi>=0.14,<0.16`。
- **USB有線モード・Windows用Fnテーブル限定**。Bluetooth、2.4GHzドングル、Mac用Fnテーブル、ISO、Ultraへの対応は保証しません。
- 実機報告の環境はWindows、Python 3.11、hidapi 0.15.0です。
- USB再接続後の保持と、公式ドライバ起動・保存後の保持は、報告上まだ明示的には確認されていません。
- 実験的な設定ツールです。読戻し成功だけではキー操作や電源断後の保持を保証できません。通信断によって自動復元も失敗することがあります。

## 導入・設定（Windows PowerShell）

ZIPを展開またはリポジトリをcloneし、`fun60_layer_tool.py`と`requirements.txt`があるフォルダでターミナルを開きます。

USB有線モードで接続し、公式ドライバ、Webドライバのタブ、キーボード設定・RGB制御アプリを終了してください。書込み中はキーを操作せず、USBを抜かないでください。

```powershell
python -m pip install -r requirements.txt
python fun60_layer_tool.py --version
python fun60_layer_tool.py list
python fun60_layer_tool.py diagnose
python fun60_layer_tool.py backup backup.json
python fun60_layer_tool.py install-ghjk
```

最後のコマンドは変更予定を表示するだけです。この段階では設定変更を行いません。読取りでもHID照会リクエストは送信します。

表示を確認して書き込む場合：

```powershell
python fun60_layer_tool.py install-ghjk --apply
```

変更直前のバックアップを自動保存し、既存のFnテーブルのG/H/J/Kだけを変更して一括送信します。各プロファイルへの書込み後に、4プロファイルすべてを読み返して検証します。数十秒かかります。不一致やエラー時は変更前への復元を試み、成否を表示します。

成功時は最後に次が表示されます。

```text
Write and full Fn-table readback verified. Test Fn+G/H/J/K and reconnect persistence.
```

Fn+G/H/J/Kで実際に切り替わること、USBを再接続しても動作することを確認してください。設定の再確認は次で行えます。

```powershell
python fun60_layer_tool.py install-ghjk
```

`Already matches. No writes.`なら、現在のFn割当が目的の値と一致しています。**元の`backup.json`は保管してください。**

## コマンド

| コマンド | 内容 |
| --- | --- |
| `list` | 候補のUSB設定インターフェースを列挙 |
| `diagnose` | 内部機種IDを照会 |
| `backup FILE` | 4プロファイルのWindows用Fnテーブルを保存。既存ファイルは上書きしない |
| `install-ghjk` | 変更予定を表示 |
| `install-ghjk --apply` | 自動バックアップ・書込み・検証 |
| `restore FILE` | バックアップからG/H/J/Kだけを戻す予定を表示 |
| `restore FILE --apply` | 他の現在のFn割当を保持してG/H/J/Kを復元 |

`list`以外の機器コマンドでは`--serial SERIAL`を指定できます。シリアルが空の個体を複数接続している場合は1台にしてください。install/restoreの`--backup-dir DIRECTORY`で自動バックアップ・ログの保存先を指定できます。既定は`backups/`です。

## 元に戻す

```powershell
python fun60_layer_tool.py restore backup.json
python fun60_layer_tool.py restore backup.json --apply
```

手動restoreで過去の値へ戻すのは**Fn+G/H/J/Kだけ**です。他の現在のFn設定は保持し、テーブル全体を送信します。一方、書込み失敗時の自動復元は、実行直前のFnテーブル全体を戻します。

バックアップはFnテーブル限定で、照明、磁気スイッチ設定、マクロ、本体全設定を含みません。シリアルが空の場合は同型番の別個体を区別できないため、必ず同じ個体のバックアップを使ってください。

## トラブル対応

| 症状 | 確認事項 |
| --- | --- |
| `requirements.txt`がない | ZIP展開でフォルダが二重になっていないか確認し、ファイルのある階層へ移動 |
| `list`が`[]` | USB有線モード、ケーブル、他アプリの終了を確認 |
| 未対応PID/機種ID | 判定を削除せず、`list`と個人情報を除いた`diagnose`をIssueへ記載 |
| `base mapping differs` | Profile 0のG/H/J/Kが想定のベース割当と異なる。カスタム割当や別レイアウトを確認 |
| フレーミング不一致・読取りが不安定 | 他の設定アプリを終了し、再接続後に読取りを確認 |
| 末尾8バイトが非ゼロ | 想定外のデータを保護するため、一括書込み前に停止 |
| 読戻し不一致 | 差分と復元結果を確認。原因を調べず書込みを繰り返さない |
| `Rollback verified.` | 4つのFnテーブルが実行前の値に戻ったことを読戻しで確認 |
| `Rollback FAILED` | インストールを中止し、バックアップとログを保持して調査。手動restoreは4キーだけを復元する点に注意 |

公式ドライバとの同時アクセスは非対応です。公式ドライバで設定を保存・読み込みすると今回の割当が上書きされる可能性があります。消えた場合は公式ドライバを終了し、変更予定を確認して再適用してください。

## テスト・開発

```powershell
python -m unittest -v
```

オフラインテスト14件を収録しています。実機やhidapiのインストールは不要です。GitHub Actionsの設定も同梱していますが、CI成功と実機成功は別の確認です。

[CONTRIBUTING.md](CONTRIBUTING.md)と[公開手順](docs/PUBLISHING_ja.md)を参照してください。診断ログには割当・機器情報・パス・シリアルが含まれ得ます。投稿前に確認し、個人のバックアップをリポジトリに含めないでください。

## 参考・ライセンス

[echtzeit-solutions/monsgeek-akko-linux](https://github.com/echtzeit-solutions/monsgeek-akko-linux)の解析・機器情報と、[Automata02/fun60-keymap](https://github.com/Automata02/fun60-keymap)の先行事例を参考にしています。参照箇所は[ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)に記載しています。

本リポジトリの独自ファイルは[GNU GPL v3.0](LICENSE)です。参照プロジェクトと依存ライブラリには、それぞれのライセンスが適用されます。
