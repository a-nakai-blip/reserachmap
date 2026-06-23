#!/usr/bin/env python3
"""
業績.md + researchmap エクスポート JSONL → インポート用 JSONL 生成

使い方:
  python generate_import.py --gyoseki 業績.md --jsonl rm_researchers20260623.jsonl
  python generate_import.py --gyoseki 業績.md --jsonl rm_researchers20260623.jsonl --output import.jsonl --verbose
"""

import argparse
import json
import sys
from pathlib import Path

import parser as p
import converter as c


# ── JSONL から既存データのインデックスを構築 ─────────────────────

class DedupIndex:
    def __init__(self, jsonl_path: str):
        self.papers_doi: set[str] = set()
        self.papers_title: set[str] = set()
        self.books_title: set[str] = set()
        self.pres_key: set[tuple] = set()   # (title_lower, year_str)
        self.misc_title: set[str] = set()   # misc + books_etc のタイトル両方
        self.proj_grant: set[str] = set()
        self.proj_title: set[str] = set()
        self.user_id: str = ''

        with open(jsonl_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                ins = data.get('insert', {})
                m = data.get('merge', {})
                t = ins.get('type', '')

                if t == 'researchers' and not self.user_id:
                    self.user_id = ins.get('id', '')

                elif t == 'published_papers':
                    for doi in m.get('identifiers', {}).get('doi', []):
                        self.papers_doi.add(doi.lower())
                    for v in m.get('paper_title', {}).values():
                        self.papers_title.add(_norm(v))

                elif t == 'books_etc':
                    for v in m.get('book_title', {}).values():
                        k = _norm(v)
                        self.books_title.add(k)
                        self.misc_title.add(k)   # misc との重複も防ぐ

                elif t == 'presentations':
                    year = str(m.get('publication_date', ''))[:4]
                    for v in m.get('presentation_title', {}).values():
                        self.pres_key.add((_norm(v), year))

                elif t == 'misc':
                    for v in m.get('paper_title', {}).values():
                        self.misc_title.add(_norm(v))

                elif t == 'research_projects':
                    for gn in m.get('identifiers', {}).get('grant_number', []):
                        self.proj_grant.add(gn)
                    for v in m.get('research_project_title', {}).values():
                        self.proj_title.add(_norm(v))

    # ── 重複判定メソッド ──────────────────────────────────────

    def is_paper_dup(self, paper) -> bool:
        if paper.doi and paper.doi.lower() in self.papers_doi:
            return True
        return _norm(paper.title) in self.papers_title

    def is_book_dup(self, book) -> bool:
        return _norm(book.title) in self.books_title

    def is_pres_dup(self, pres) -> bool:
        year = str(pres.year) if pres.year else ''
        return (_norm(pres.title), year) in self.pres_key

    def is_misc_dup(self, item) -> bool:
        return _norm(item.title) in self.misc_title

    def is_proj_dup(self, proj) -> bool:
        if proj.grant_number:
            return proj.grant_number in self.proj_grant
        return _norm(proj.title) in self.proj_title


def _norm(text: str) -> str:
    return text.lower().strip()


# ── カテゴリ処理 ─────────────────────────────────────────────

def _process(parsed: p.ParsedData, idx: DedupIndex, verbose: bool) -> list[tuple[str, dict]]:
    """(type, merge_dict) のリストを返す"""
    results = []

    def _add(type_name, obj, merge_fn, is_dup_fn, label_fn):
        dup = is_dup_fn(obj)
        label = label_fn(obj)
        if dup:
            if verbose:
                print(f'  [SKIP] {label[:70]}')
        else:
            if verbose:
                print(f'  [NEW]  {label[:70]}')
            results.append((type_name, merge_fn(obj)))

    # 論文
    if verbose:
        print(f'\n=== 学術論文 ({len(parsed.papers)} 件) ===')
    for obj in parsed.papers:
        _add('published_papers', obj, c.paper_to_merge, idx.is_paper_dup,
             lambda o: o.title)

    # 著書等
    if verbose:
        print(f'\n=== 著書等 ({len(parsed.books)} 件) ===')
    for obj in parsed.books:
        _add('books_etc', obj, c.book_to_merge, idx.is_book_dup,
             lambda o: o.title)

    # 発表
    if verbose:
        print(f'\n=== 発表 ({len(parsed.presentations)} 件) ===')
    for obj in parsed.presentations:
        _add('presentations', obj, c.presentation_to_merge, idx.is_pres_dup,
             lambda o: o.title)

    # 報告書・その他
    if verbose:
        print(f'\n=== 報告書・その他 ({len(parsed.misc)} 件) ===')
    for obj in parsed.misc:
        _add('misc', obj, c.misc_to_merge, idx.is_misc_dup,
             lambda o: o.title)

    # 外部資金
    if verbose:
        print(f'\n=== 外部資金 ({len(parsed.projects)} 件) ===')
    for obj in parsed.projects:
        _add('research_projects', obj, c.project_to_merge, idx.is_proj_dup,
             lambda o: o.title)

    return results


# ── メイン ──────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='業績.md + researchmap JSONL → インポート用 JSONL 生成'
    )
    ap.add_argument('--gyoseki', '-g', required=True,
                    help='業績テキストファイル（.md など）')
    ap.add_argument('--jsonl', '-j', required=True,
                    help='researchmap エクスポート JSONL ファイル')
    ap.add_argument('--output', '-o', default='import.jsonl',
                    help='出力ファイル名（デフォルト: import.jsonl）')
    ap.add_argument('--dry-run', '-n', action='store_true',
                    help='件数確認のみ。ファイルは出力しない')
    ap.add_argument('--verbose', '-v', action='store_true',
                    help='各件の処理状況を表示')
    args = ap.parse_args()

    # 入力ファイル確認
    for path, name in [(args.gyoseki, '業績ファイル'), (args.jsonl, 'JSONL ファイル')]:
        if not Path(path).exists():
            print(f'[ERROR] {name}が見つかりません: {path}', file=sys.stderr)
            sys.exit(1)

    # 業績テキストをパース
    text = Path(args.gyoseki).read_text(encoding='utf-8')
    parsed = p.parse_text(text)
    print(
        f'業績パース結果: 論文={len(parsed.papers)}, 著書={len(parsed.books)}, '
        f'発表={len(parsed.presentations)}, 報告書等={len(parsed.misc)}, '
        f'外部資金={len(parsed.projects)}'
    )

    # JSONL から既存データを読み込み
    idx = DedupIndex(args.jsonl)
    print(f'既存データ読み込み完了 (user_id: {idx.user_id})')

    # 重複チェック・変換
    new_items = _process(parsed, idx, args.verbose)

    total_new = len(new_items)
    total_dup = (len(parsed.papers) + len(parsed.books) +
                 len(parsed.presentations) + len(parsed.misc) +
                 len(parsed.projects)) - total_new

    print(f'\n新規: {total_new} 件 / スキップ（重複）: {total_dup} 件')

    if args.dry_run:
        print('（ドライラン: ファイルを出力しません）')
        return

    if not new_items:
        print('新規データがないため、ファイルを出力しません。')
        return

    # JSONL 出力
    out_path = Path(args.output)
    with out_path.open('w', encoding='utf-8') as f:
        for type_name, merge in new_items:
            record = {
                'insert': {'type': type_name, 'user_id': idx.user_id},
                'merge': merge,
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(f'\nインポートファイルを出力しました: {out_path}  ({total_new} 件)')
    print()
    print('次のステップ:')
    print('  1. researchmap にログイン')
    print('  2. 右上メニュー → 「業績のエクスポート/インポート」')
    print(f'  3. {out_path} を選択してインポート実行')


if __name__ == '__main__':
    main()
