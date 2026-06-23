#!/usr/bin/env python3
"""
大学研究業績テキスト → researchmap インポート JSON 生成スクリプト

使い方:
  python generate_import.py --input 業績.txt --export researchmap_export.json --output import.json

  --export を省略すると重複チェックなしで全件をインポートファイルに出力する。
  --dry-run を付けると件数確認のみ行い、ファイルを出力しない。
  --category で特定カテゴリのみ処理 (paper / book / presentation / project / other)

researchmap のエクスポート/インポート:
  エクスポート: researchmap にログイン → 業績管理 → 各カテゴリ → 「エクスポート」→ JSON
  インポート:   researchmap にログイン → 業績管理 → 各カテゴリ → 「インポート」→ JSON を選択
"""

import argparse
import json
import sys
from pathlib import Path

import parser as p
import converter as c


CATEGORIES = ["paper", "book", "presentation", "project", "other"]

# ---- エクスポート JSON から既存データをインデックス化するキー抽出関数 ----

def _text_val(field) -> str:
    """[{"@value": "...", "@language": "..."}] 形式から値を取り出す。"""
    if isinstance(field, list) and field:
        return field[0].get("@value", "").strip().lower()
    if isinstance(field, str):
        return field.strip().lower()
    return ""


REMOTE_KEY_FUNCS: dict[str, dict[str, callable]] = {
    "paper": {
        "doi": lambda item: (item.get("doi") or "").strip().lower(),
        "title": lambda item: _text_val(item.get("paper_title")),
    },
    "book": {
        "isbn": lambda item: re.sub(r'[-\s]', '', item.get("isbn") or "").lower(),
        "title": lambda item: _text_val(item.get("book_title")),
    },
    "presentation": {
        "title": lambda item: _text_val(item.get("presentation_title")),
    },
    "project": {
        "title": lambda item: _text_val(item.get("research_project_title")),
    },
    "other": {
        "title": lambda item: _text_val(item.get("misc_title")),
    },
}

LOCAL_KEY_FUNCS: dict[str, dict[str, callable]] = {
    "paper": {
        "doi": lambda obj: (obj.doi or "").strip().lower(),
        "title": lambda obj: obj.title.strip().lower(),
    },
    "book": {
        "isbn": lambda obj: re.sub(r'[-\s]', '', obj.isbn or "").lower(),
        "title": lambda obj: obj.title.strip().lower(),
    },
    "presentation": {
        "title": lambda obj: obj.title.strip().lower(),
    },
    "project": {
        "title": lambda obj: obj.title.strip().lower(),
    },
    "other": {
        "title": lambda obj: obj.title.strip().lower(),
    },
}

PRIMARY_KEYS = {
    "paper": "doi",
    "book": "isbn",
    "presentation": "title",
    "project": "title",
    "other": "title",
}


def build_remote_index(export_data: dict, category: str) -> dict[str, set]:
    """
    エクスポートデータからカテゴリごとの既存キーセットを返す。
    {key_type: {value, ...}} の形式。
    """
    export_key = c.EXPORT_KEYS[category]
    items = export_data.get(export_key, [])
    index: dict[str, set] = {k: set() for k in REMOTE_KEY_FUNCS[category]}
    for item in items:
        for key_type, extractor in REMOTE_KEY_FUNCS[category].items():
            val = extractor(item)
            if val:
                index[key_type].add(val)
    return index


def is_duplicate(obj, category: str, remote_index: dict[str, set]) -> bool:
    """ローカルオブジェクトが既存データに含まれるか判定する。"""
    prim = PRIMARY_KEYS[category]
    local_funcs = LOCAL_KEY_FUNCS[category]

    # プライマリキー（DOI / ISBN）が両方に存在する場合はそれで判定
    primary_func = local_funcs.get(prim)
    if primary_func:
        local_val = primary_func(obj)
        if local_val and local_val in remote_index.get(prim, set()):
            return True
        # プライマリキーが取れたがリモートに無い → 重複なし（タイトル照合しない）
        if local_val:
            return False

    # プライマリキーが無い場合はタイトルで照合
    title_func = local_funcs.get("title")
    if title_func:
        local_title = title_func(obj)
        if local_title and local_title in remote_index.get("title", set()):
            return True

    return False


def get_local_items(parsed: p.ParsedData, category: str) -> list:
    return {
        "paper": parsed.papers,
        "book": parsed.books,
        "presentation": parsed.presentations,
        "project": parsed.projects,
        "other": parsed.others,
    }[category]


def process_category(
    parsed: p.ParsedData,
    category: str,
    export_data: dict,
    verbose: bool,
) -> tuple[list[dict], int, int]:
    """
    カテゴリを処理し、(新規ペイロードリスト, 新規件数, 重複件数) を返す。
    """
    local_items = get_local_items(parsed, category)
    if not local_items:
        return [], 0, 0

    remote_index = build_remote_index(export_data, category)
    payload_func = c.PAYLOAD_FUNCS[category]

    new_items = []
    dup_count = 0
    for obj in local_items:
        if is_duplicate(obj, category, remote_index):
            dup_count += 1
            if verbose:
                print(f"  [SKIP] {obj.title[:60]}")
        else:
            new_items.append(payload_func(obj))
            if verbose:
                print(f"  [NEW]  {obj.title[:60]}")

    return new_items, len(new_items), dup_count


import re  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        description="大学業績テキスト → researchmap インポート JSON 生成"
    )
    ap.add_argument("--input", "-i", required=True, help="業績テキストファイル")
    ap.add_argument(
        "--export", "-e",
        help="researchmap からエクスポートした JSON ファイル（省略時は全件出力）",
    )
    ap.add_argument(
        "--output", "-o", default="import.json",
        help="出力ファイル名 (デフォルト: import.json)",
    )
    ap.add_argument("--dry-run", "-n", action="store_true", help="件数確認のみ、ファイル出力しない")
    ap.add_argument("--category", choices=CATEGORIES, help="処理するカテゴリを指定")
    ap.add_argument("--verbose", "-v", action="store_true", help="各件の処理状況を表示")
    args = ap.parse_args()

    # 業績テキスト読み込み
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] 入力ファイルが見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    text = input_path.read_text(encoding="utf-8")
    parsed = p.parse_text(text)
    print(f"パース結果: 論文={len(parsed.papers)}, 著書={len(parsed.books)}, "
          f"講演={len(parsed.presentations)}, プロジェクト={len(parsed.projects)}, "
          f"その他={len(parsed.others)}")

    # researchmap エクスポート JSON 読み込み
    export_data: dict = {}
    if args.export:
        export_path = Path(args.export)
        if not export_path.exists():
            print(f"[ERROR] エクスポートファイルが見つかりません: {export_path}", file=sys.stderr)
            sys.exit(1)
        raw = json.loads(export_path.read_text(encoding="utf-8"))
        # エクスポートファイルがリストの場合（カテゴリ単体エクスポート）も対応
        if isinstance(raw, list):
            # カテゴリ名をファイル名から推定
            stem = export_path.stem.lower()
            for cat, key in c.EXPORT_KEYS.items():
                if cat in stem or key in stem:
                    export_data = {key: raw}
                    break
            else:
                # 推定できない場合は --category が必須
                if not args.category:
                    print("[ERROR] エクスポートがリスト形式の場合は --category を指定してください。",
                          file=sys.stderr)
                    sys.exit(1)
                export_data = {c.EXPORT_KEYS[args.category]: raw}
        else:
            export_data = raw
        print(f"エクスポート読み込み: {export_path.name}")
    else:
        print("エクスポートファイル未指定: 重複チェックなしで全件を出力します。")

    # カテゴリ処理
    target_categories = [args.category] if args.category else CATEGORIES
    result: dict[str, list] = {}
    total_new = total_dup = 0

    for cat in target_categories:
        if args.verbose:
            print(f"\n=== {cat} ===")
        new_items, new_count, dup_count = process_category(
            parsed, cat, export_data, args.verbose
        )
        total_new += new_count
        total_dup += dup_count
        if new_items:
            result[c.EXPORT_KEYS[cat]] = new_items

    # サマリ
    print(f"\n新規: {total_new} 件, スキップ(重複): {total_dup} 件")

    if args.dry_run:
        print("（ドライラン: ファイルを出力しません）")
        return

    if not result:
        print("出力する新規データがありません。")
        return

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"インポートファイルを出力しました: {output_path}")
    print()
    print("次のステップ:")
    print("  1. researchmap にログイン")
    print("  2. 業績管理 → 各カテゴリ → 「インポート」")
    print(f"  3. {output_path} を選択してインポート")


if __name__ == "__main__":
    main()
