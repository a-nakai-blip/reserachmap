# researchmap インポートファイル生成ツール

大学研究業績サイトのテキスト（業績.md）を読み込み、researchmap にインポート可能な JSONL ファイルを生成します。researchmap に既に登録されているデータとの重複を自動的に除外します。

## ファイル構成

| ファイル | 説明 |
|---|---|
| `generate_import.py` | メインスクリプト |
| `parser.py` | 業績.md パーサー |
| `converter.py` | researchmap JSONL 形式への変換 |

## 使い方

### ステップ 1: researchmap からデータをエクスポート

1. [researchmap](https://researchmap.jp) にログイン
2. 右上メニュー →「業績のエクスポート/インポート」→「エクスポート」
3. 形式「JSON Lines」を選択してダウンロード
4. ダウンロードしたファイルを `rm_researchers_YYYYMMDD.jsonl` などの名前で保存

### ステップ 2: インポートファイルを生成

```bash
python generate_import.py --gyoseki 業績.md --jsonl rm_researchers20260623.jsonl
```

#### オプション

| オプション | 短縮形 | 説明 |
|---|---|---|
| `--gyoseki` | `-g` | 業績テキストファイル（必須） |
| `--jsonl` | `-j` | researchmap エクスポート JSONL ファイル（必須） |
| `--output` | `-o` | 出力ファイル名（デフォルト: `import.jsonl`） |
| `--dry-run` | `-n` | 件数確認のみ。ファイルを出力しない |
| `--verbose` | `-v` | 各件の処理状況（新規/スキップ）を表示 |

#### 使用例

```bash
# 件数確認のみ（ファイルを出力しない）
python generate_import.py -g 業績.md -j rm_researchers20260623.jsonl --dry-run

# 詳細表示（各件の処理状況を確認）
python generate_import.py -g 業績.md -j rm_researchers20260623.jsonl --verbose

# 出力ファイル名を指定
python generate_import.py -g 業績.md -j rm_researchers20260623.jsonl --output 2026_import.jsonl
```

### ステップ 3: researchmap にインポート

1. researchmap にログイン
2. 右上メニュー →「業績のエクスポート/インポート」→「インポート」
3. 生成された `import.jsonl` を選択してインポート実行

## 対応セクション

業績.md の以下のセクション（`* セクション名` で始まる行）を処理します。

| 業績.md セクション | researchmap カテゴリ |
|---|---|
| 著書 | books_etc |
| 学術論文・作品など | published_papers |
| 国際会議・国内会議・学会発表・講演 | presentations |
| 報告書，その他 | misc |
| 外部資金の獲得 | research_projects |
| 学位論文・地域社会・委員・役員・組織運営 | スキップ |

## 業績.md の書式

各セクション内のエントリは `数字.` で始まる行として記述します。

```
* 学術論文・作品など
1. **中井聖**, 田中真紀: タイトル, 雑誌名, 26(5): 927-934, 2026年5月, DOI:10.xxxx/xxx

* 著書
1. 中井聖（分担執筆）: 書名, 出版社, 2025年4月

* 国際会議、国内会議
1. **中井聖**, 田中真紀: 発表タイトル, 学会名, 2026年3月

* 外部資金の獲得
1. 令和8年度 科研費基盤研究(C), 研究課題タイトル, 令和8～11年度, 課題番号：26K14474, 中井聖（代表者）, 佐近慎平

* 報告書，その他
1. 中井聖: タイトル, 掲載誌名, 2025年3月
```

**著者の太字表記（`**氏名**`）について:**
- 筆頭著者（1番目）の場合 → `published_paper_owner_roles: lead`
- 最終著者（最後）の場合 → `published_paper_owner_roles: last`
- 中間著者の場合 → ロール設定なし

## 重複判定のロジック

| カテゴリ | 判定キー |
|---|---|
| 論文 | DOI（一致すれば重複）またはタイトル |
| 著書 | タイトル |
| 発表 | タイトル + 年 |
| 報告書等 | タイトル |
| 外部資金 | 課題番号（あれば）またはタイトル |
