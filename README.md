# researchmap インポートファイル生成ツール

大学研究業績サイトのテキストデータを読み込み、researchmap にインポート可能な JSON ファイルを生成します。researchmap に既に登録されているデータとの重複を自動的に除外します。

## 使い方

### 1. セットアップ

```bash
pip install -r requirements.txt
```

### 2. researchmap からエクスポート

1. [researchmap](https://researchmap.jp) にログイン
2. 業績管理 → 各カテゴリ（論文・著書・講演など）→「エクスポート」→ JSON を選択
3. ダウンロードしたファイルを `researchmap_export.json` という名前で保存

複数カテゴリのエクスポートファイルを結合するか、カテゴリを個別に処理することもできます。

### 3. 業績テキストファイルを作成

`input_example.txt` を参考に、大学研究業績サイトからコピーしたテキストを用意します。

```
[論文]
著者1, 著者2: タイトル, 雑誌名, 巻(号): ページ, 年月, DOI:xxx
中井聖, 田中真紀: ラダーゲッターの投げ方..., 自由時間研究, 50, 8-15, 2025年3月

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

### 4. インポートファイルを生成

```bash
# 基本的な使い方
python generate_import.py --input 業績.txt --export researchmap_export.json

# 詳細表示（各件の処理状況を確認）
python generate_import.py --input 業績.txt --export researchmap_export.json --verbose

# 出力ファイル名を指定
python generate_import.py --input 業績.txt --export researchmap_export.json --output 2025_import.json

# 件数確認のみ（ファイルを出力しない）
python generate_import.py --input 業績.txt --export researchmap_export.json --dry-run

# 特定カテゴリのみ処理
python generate_import.py --input 業績.txt --export researchmap_export.json --category paper

# エクスポートなし（全件を出力）
python generate_import.py --input 業績.txt
```

### 5. researchmap にインポート

1. researchmap にログイン
2. 業績管理 → 各カテゴリ → 「インポート」
3. 生成された `import.json` を選択してインポート

## 重複判定のロジック

| カテゴリ | 優先キー | 代替キー |
|---|---|---|
| 論文 | DOI | タイトル（DOIなしの場合） |
| 著書 | ISBN | タイトル（ISBNなしの場合） |
| 講演 | タイトル | - |
| 研究プロジェクト | タイトル | - |
| その他 | タイトル | - |

## ファイル構成

| ファイル | 説明 |
|---|---|
| `generate_import.py` | メインスクリプト |
| `parser.py` | 大学業績テキストのパーサー |
| `converter.py` | researchmap JSON 形式への変換 |
| `input_example.txt` | 入力テキストのサンプル |
| `researchmap_export_example.json` | エクスポート JSON のサンプル |
