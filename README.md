# researchmap 同期ツール

大学研究業績サイトのテキストデータを researchmap に同期するツールです。

## セットアップ

```bash
pip install -r requirements.txt
cp config.yaml.example config.yaml
```

`config.yaml` を編集して researchmap の認証情報を設定します。

### researchmap API キーの取得

1. [researchmap](https://researchmap.jp) にログイン
2. 右上のユーザー名 → 「外部サービス連携」→「API」を開く
3. 「クライアント登録」でアプリ名を入力し、**クライアントID** と **クライアントシークレット** を取得
4. **研究者ID** は researchmap の自分のページURL (`https://researchmap.jp/【この部分】`) を確認

## 入力データ形式

`input_example.txt` を参考に、以下のカテゴリで業績を記述します。

```
[論文]
著者1, 著者2: タイトル, 雑誌名, 巻(号): ページ, 年月, DOI:xxx

[著書・編著]
著者1: 書名, 出版社, 年月, ISBN:xxx

[講演・口頭発表]
著者1, 著者2: 発表タイトル, 学会名, 年月, 開催地

[研究プロジェクト]
科研費基盤研究(C): 研究課題名, 開始年-終了年, 代表者: 氏名, 課題番号: 番号

[報告書・その他]
著者1: タイトル, 掲載誌・機関名, 年月
```

カテゴリヘッダーは `[論文]`、`【著書】`、`# 講演` など柔軟に書けます。

## 実行

```bash
# ドライラン（確認のみ、researchmap への書き込みなし）
python sync.py --input input.txt --dry-run

# 実際に同期
python sync.py --input input.txt

# 特定カテゴリのみ同期
python sync.py --input input.txt --category paper
```

## 同期の仕組み

- DOI（論文）または ISBN（著書）が一致する場合は **更新**
- 一致するものがない場合は **新規追加**
- `config.yaml` の `match_key` で照合キーを変更可能

## ファイル構成

| ファイル | 説明 |
|---|---|
| `sync.py` | メインスクリプト |
| `parser.py` | 大学業績テキストのパーサー |
| `researchmap_api.py` | researchmap API クライアント |
| `config.yaml` | 設定ファイル（要作成） |
| `input_example.txt` | 入力テキストのサンプル |
