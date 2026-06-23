#!/usr/bin/env python3
"""
大学研究業績サイト → researchmap 同期スクリプト

使い方:
  1. config.yaml を作成 (config.yaml.example を参考に)
  2. テキストファイルに研究業績を記述 (input_example.txt を参考に)
  3. 実行:
       python sync.py --input input.txt
     ドライラン（書き込みなし）:
       python sync.py --input input.txt --dry-run
     カテゴリを指定:
       python sync.py --input input.txt --category paper
"""

import argparse
import sys
from pathlib import Path

import yaml

import parser as p
import researchmap_api as api


CATEGORIES = ["paper", "book", "presentation", "project", "other"]

PAYLOAD_FUNCS = {
    "paper": api.paper_to_payload,
    "book": api.book_to_payload,
    "presentation": api.presentation_to_payload,
    "project": api.project_to_payload,
    "other": api.other_to_payload,
}

MATCH_KEYS = {
    "paper": {
        "doi": lambda item: item.get("doi"),
        "title": lambda item: (item.get("paper_title") or [{}])[0].get("@value", "").lower(),
    },
    "book": {
        "isbn": lambda item: item.get("isbn"),
        "title": lambda item: (item.get("book_title") or [{}])[0].get("@value", "").lower(),
    },
    "presentation": {
        "title": lambda item: (item.get("presentation_title") or [{}])[0].get("@value", "").lower(),
    },
    "project": {
        "title": lambda item: (item.get("research_project_title") or [{}])[0].get("@value", "").lower(),
    },
    "other": {
        "title": lambda item: (item.get("misc_title") or [{}])[0].get("@value", "").lower(),
    },
}

LOCAL_KEY_FUNCS = {
    "paper": {
        "doi": lambda obj: obj.doi,
        "title": lambda obj: obj.title.lower(),
    },
    "book": {
        "isbn": lambda obj: obj.isbn,
        "title": lambda obj: obj.title.lower(),
    },
    "presentation": {
        "title": lambda obj: obj.title.lower(),
    },
    "project": {
        "title": lambda obj: obj.title.lower(),
    },
    "other": {
        "title": lambda obj: obj.title.lower(),
    },
}


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_local_items(parsed: p.ParsedData, category: str) -> list:
    return {
        "paper": parsed.papers,
        "book": parsed.books,
        "presentation": parsed.presentations,
        "project": parsed.projects,
        "other": parsed.others,
    }[category]


def build_remote_index(remote_items: list, category: str, match_key: str) -> dict:
    """リモートのレコードを match_key でインデックス化する。"""
    key_func = MATCH_KEYS.get(category, {}).get(match_key)
    if not key_func:
        return {}
    index = {}
    for item in remote_items:
        k = key_func(item)
        if k:
            index[k] = item
    return index


def sync_category(
    client: api.ResearchmapClient,
    category: str,
    local_items: list,
    match_key: str,
    dry_run: bool,
) -> dict:
    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    if not local_items:
        return stats

    print(f"\n=== {category} ({len(local_items)} 件) ===")

    # リモートの既存データを取得
    try:
        remote_items = client.get_all(category)
    except api.ResearchmapAPIError as e:
        print(f"  [ERROR] リモートデータ取得失敗: {e}")
        stats["errors"] += len(local_items)
        return stats

    remote_index = build_remote_index(remote_items, category, match_key)
    local_key_func = LOCAL_KEY_FUNCS.get(category, {}).get(match_key)
    payload_func = PAYLOAD_FUNCS[category]

    for obj in local_items:
        try:
            payload = payload_func(obj)
            local_key = local_key_func(obj) if local_key_func else None

            existing = remote_index.get(local_key) if local_key else None

            if existing:
                record_id = existing.get("id") or existing.get("rm_id", "")
                print(f"  [UPDATE] {obj.title[:60]}")
                if not dry_run:
                    client.update(category, str(record_id), payload)
                stats["updated"] += 1
            else:
                print(f"  [ADD]    {obj.title[:60]}")
                if not dry_run:
                    client.create(category, payload)
                stats["added"] += 1

        except api.ResearchmapAPIError as e:
            print(f"  [ERROR]  {getattr(obj, 'title', str(obj))[:60]} -> {e}")
            stats["errors"] += 1

    return stats


def main():
    ap = argparse.ArgumentParser(description="大学研究業績 → researchmap 同期")
    ap.add_argument("--input", "-i", required=True, help="業績テキストファイル")
    ap.add_argument("--config", "-c", default="config.yaml", help="設定ファイル (デフォルト: config.yaml)")
    ap.add_argument("--dry-run", "-n", action="store_true", help="ドライラン（書き込みなし）")
    ap.add_argument("--category", choices=CATEGORIES, help="同期するカテゴリを指定 (省略時は全カテゴリ)")
    args = ap.parse_args()

    # 設定読み込み
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"設定ファイルが見つかりません: {config_path}")
        print("config.yaml.example をコピーして config.yaml を作成してください。")
        sys.exit(1)

    config = load_config(str(config_path))
    rm_cfg = config.get("researchmap", {})
    sync_cfg = config.get("sync", {})

    dry_run = args.dry_run or sync_cfg.get("dry_run", False)
    match_key = sync_cfg.get("match_key", "doi")

    if dry_run:
        print("*** ドライランモード: researchmap への書き込みは行いません ***")

    # テキストファイル読み込みとパース
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"入力ファイルが見つかりません: {input_path}")
        sys.exit(1)

    text = input_path.read_text(encoding="utf-8")
    parsed = p.parse_text(text)

    print(f"パース結果: 論文={len(parsed.papers)}, 著書={len(parsed.books)}, "
          f"講演={len(parsed.presentations)}, プロジェクト={len(parsed.projects)}, "
          f"その他={len(parsed.others)}")

    # API クライアント初期化
    client = api.ResearchmapClient(
        client_id=rm_cfg["client_id"],
        client_secret=rm_cfg["client_secret"],
        researcher_id=rm_cfg["researcher_id"],
    )

    # 同期実行
    target_categories = [args.category] if args.category else CATEGORIES
    total = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    for cat in target_categories:
        local_items = get_local_items(parsed, cat)
        stats = sync_category(client, cat, local_items, match_key, dry_run)
        for k in total:
            total[k] += stats[k]

    print(f"\n=== 完了 ===")
    print(f"  追加: {total['added']}, 更新: {total['updated']}, "
          f"スキップ: {total['skipped']}, エラー: {total['errors']}")
    if dry_run:
        print("  (ドライランのため実際の変更はありません)")


if __name__ == "__main__":
    main()
