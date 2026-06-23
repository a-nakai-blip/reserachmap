"""
業績.md パーサー

対応セクション:
  * 著書             → books
  * 学位論文          → skip
  * 学術論文・作品など  → papers
  * 国際会議、国内会議  → presentations
  * 報告書，その他     → misc
  * 外部資金の獲得     → projects
  * 地域社会への貢献   → skip
  * 委員・役員など     → skip
  * 学会等の組織運営   → skip
"""

import re
from dataclasses import dataclass, field as dc_field
from typing import Optional

# ── 和暦→西暦 ─────────────────────────────────────────────────

_WAREKI_BASE = {'令和': 2018, '平成': 1988, '昭和': 1925, '大正': 1911}
_WAREKI_RE = re.compile(r'(令和|平成|昭和|大正)(\d+)')


def _wareki(text: str) -> str:
    return _WAREKI_RE.sub(lambda m: str(_WAREKI_BASE[m.group(1)] + int(m.group(2))), text)


def _parse_ym(text: str) -> tuple[Optional[int], Optional[int]]:
    t = _wareki(text)
    m = re.search(r'(\d{4})年(\d{1,2})月', t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d{4})年', t)
    return (int(m.group(1)), None) if m else (None, None)


def _parse_year_range(text: str) -> tuple[Optional[int], Optional[int]]:
    """「令和8～11年度」→ (2026, 2029)"""
    t = _wareki(text)
    m = re.search(r'(\d{4})[～〜~](\d{4})', t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d{4})', t)
    return (int(m.group(1)), int(m.group(1))) if m else (None, None)


# ── ユーティリティ ────────────────────────────────────────────

def _strip_num(line: str) -> str:
    return re.sub(r'^\d+\.\s*', '', line)


def _detect_lang(text: str) -> str:
    return 'ja' if re.search(r'[ぁ-ん一-鿿]', text) else 'en'


def _split_first_colon(line: str) -> tuple[str, str]:
    """「著者: 残り」を分割。ただし '：' も対象。"""
    for sep in (': ', '：'):
        idx = line.find(sep)
        if idx != -1:
            return line[:idx], line[idx + len(sep):]
    return '', line


def _parse_authors(text: str) -> tuple[list[str], Optional[str]]:
    """
    著者文字列を解析して (著者リスト, 太字著者名) を返す。
    太字（**name**）は筆頭/最終著者判定に使う。
    """
    parts = re.split(r'[，、,]\s*', text)
    authors = []
    bold = None
    for p in parts:
        p = p.strip()
        bm = re.fullmatch(r'\*\*(.+?)\*\*', p)
        if bm:
            name = bm.group(1)
            authors.append(name)
            bold = name
        else:
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', p).strip()
            if clean:
                authors.append(clean)
    return authors, bold


def _split_csv(text: str) -> list[str]:
    """全角・半角カンマで分割。"""
    return [p.strip() for p in re.split(r'[，,]\s*', text) if p.strip()]


def _split_half(text: str) -> list[str]:
    """半角カンマ+スペースのみで分割（タイトル内の全角カンマを保持）。"""
    return [p.strip() for p in text.split(', ') if p.strip()]


# ── データクラス ─────────────────────────────────────────────

@dataclass
class Paper:
    title: str
    lang: str
    authors: list[str]
    bold_author: Optional[str] = None
    journal: str = ''
    year: Optional[int] = None
    month: Optional[int] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    start_page: Optional[str] = None
    end_page: Optional[str] = None
    doi: Optional[str] = None


@dataclass
class BookEtc:
    title: str
    lang: str
    author_text: str       # 著者欄の生テキスト（複雑な表記のためそのまま保持）
    publisher: str = ''
    year: Optional[int] = None
    month: Optional[int] = None
    note: str = ''         # 「分担執筆」など括弧内の注記


@dataclass
class Presentation:
    title: str
    lang: str
    authors: list[str]
    bold_author: Optional[str] = None
    event: str = ''
    year: Optional[int] = None
    month: Optional[int] = None


@dataclass
class MiscItem:
    title: str
    lang: str
    authors: list[str]
    publication: str = ''
    year: Optional[int] = None
    month: Optional[int] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    start_page: Optional[str] = None
    end_page: Optional[str] = None


@dataclass
class ResearchProject:
    title: str
    offer_org: str = ''
    system_name: str = ''
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    grant_number: Optional[str] = None
    investigators: str = ''


@dataclass
class ParsedData:
    papers: list[Paper] = dc_field(default_factory=list)
    books: list[BookEtc] = dc_field(default_factory=list)
    presentations: list[Presentation] = dc_field(default_factory=list)
    misc: list[MiscItem] = dc_field(default_factory=list)
    projects: list[ResearchProject] = dc_field(default_factory=list)


# ── セクション判定 ────────────────────────────────────────────

_SECTIONS = [
    (re.compile(r'著書'), 'books'),
    (re.compile(r'学位論文'), 'skip'),
    (re.compile(r'学術論文|作品'), 'papers'),
    (re.compile(r'国際会議|国内会議|学会発表|講演'), 'presentations'),
    (re.compile(r'報告書|その他'), 'misc'),
    (re.compile(r'外部資金|特許|知財'), 'projects'),
    (re.compile(r'地域社会|委員|役員|組織運営|財団法人|社団法人'), 'skip'),
]


def _detect_section(line: str) -> Optional[str]:
    stripped = re.sub(r'^[*＊#\s]+', '', line).strip()
    for pat, cat in _SECTIONS:
        if pat.search(stripped):
            return cat
    return None


# ── 行パーサー ──────────────────────────────────────────────

def _parse_paper(line: str) -> Optional[Paper]:
    author_str, rest = _split_first_colon(line)
    if not rest:
        return None
    authors, bold = _parse_authors(author_str)
    parts = _split_half(rest)
    if not parts:
        return None
    title = parts[0]
    journal = parts[1] if len(parts) > 1 else ''

    doi = None
    doi_m = re.search(r'DOI:\s*([\w./\-]+)', rest, re.IGNORECASE)
    if doi_m:
        doi = doi_m.group(1)

    year, month = _parse_ym(rest)
    volume = number = start_page = end_page = None

    # 26(5): 927-934 形式
    rest_csv = _split_csv(rest)
    vm = re.search(r'(\d+)\(([^)]+)\)[：:]\s*(\d+)[-–](\d+)', rest)
    if vm:
        volume, number = vm.group(1), vm.group(2)
        start_page, end_page = vm.group(3), vm.group(4)
    else:
        for p in rest_csv[2:]:
            if re.match(r'^\d+$', p) and volume is None and not re.search(r'年|月', p):
                volume = p
            elif re.match(r'^(\d+)[-–](\d+)$', p) and start_page is None:
                pm = re.match(r'^(\d+)[-–](\d+)$', p)
                start_page, end_page = pm.group(1), pm.group(2)

    return Paper(
        title=title, lang=_detect_lang(title),
        authors=authors, bold_author=bold,
        journal=journal, year=year, month=month,
        volume=volume, number=number,
        start_page=start_page, end_page=end_page, doi=doi,
    )


def _parse_book(line: str) -> Optional[BookEtc]:
    author_str, rest = _split_first_colon(line)
    if not rest:
        return None
    parts = _split_csv(rest)
    title = parts[0] if parts else rest
    publisher = parts[1] if len(parts) > 1 else ''
    year, month = _parse_ym(rest)
    note_m = re.search(r'[（(]([^）)]+)[）)]', rest)
    note = note_m.group(1) if note_m else ''
    return BookEtc(
        title=title, lang=_detect_lang(title),
        author_text=re.sub(r'\*\*(.+?)\*\*', r'\1', author_str).strip(),
        publisher=publisher, year=year, month=month, note=note,
    )


def _parse_presentation(line: str) -> Optional[Presentation]:
    author_str, rest = _split_first_colon(line)
    if not rest:
        return None
    authors, bold = _parse_authors(author_str)
    parts = _split_csv(rest)
    title = parts[0] if parts else rest
    event = parts[1] if len(parts) > 1 else ''
    year, month = _parse_ym(rest)
    return Presentation(
        title=title, lang=_detect_lang(title),
        authors=authors, bold_author=bold,
        event=event, year=year, month=month,
    )


def _parse_misc(line: str) -> Optional[MiscItem]:
    author_str, rest = _split_first_colon(line)
    if not rest:
        return None
    authors, _ = _parse_authors(author_str)
    parts = _split_half(rest)
    rest_csv = _split_csv(rest)
    title = parts[0] if parts else rest
    publication = parts[1] if len(parts) > 1 else ''
    year, month = _parse_ym(rest)
    volume = number = start_page = end_page = None

    vm = re.search(r'(\d+)\((\d+)\)[,，：:]\s*(\d+)[-–](\d+)', rest)
    if vm:
        volume, number = vm.group(1), vm.group(2)
        start_page, end_page = vm.group(3), vm.group(4)
    else:
        for p in rest_csv[2:]:
            if re.match(r'^\d+$', p) and volume is None and not re.search(r'年|月', p):
                volume = p
            elif re.match(r'^(\d+)[-–](\d+)$', p) and start_page is None:
                pm = re.match(r'^(\d+)[-–](\d+)$', p)
                start_page, end_page = pm.group(1), pm.group(2)

    return MiscItem(
        title=title, lang=_detect_lang(title),
        authors=authors, publication=publication,
        year=year, month=month,
        volume=volume, number=number,
        start_page=start_page, end_page=end_page,
    )


_KAKENHI_TYPE_RE = re.compile(
    r'基盤研究\([A-Z]\)|挑戦的萌芽研究|挑戦的研究\([^)]+\)|若手研究|研究活動スタート支援|特別研究員奨励費|萌芽研究'
)


def _parse_project(line: str) -> Optional[ResearchProject]:
    grant_m = re.search(r'課題番号[：:]\s*([\w\d]+)', line)
    grant_no = grant_m.group(1) if grant_m else None

    parts = re.split(r'[，,]\s*', line)
    funding_raw = parts[0].strip() if parts else ''

    year_start = year_end = None
    title_parts: list[str] = []
    inv_parts: list[str] = []

    found_inv = False
    for raw in parts[1:]:
        raw = raw.strip()

        # 同一元号の年度範囲（例: 令和8～11年度）を先に処理
        era_range_m = re.search(r'(令和|平成|昭和|大正)(\d+)[～〜~](\d+)年度?', raw)
        if era_range_m:
            base = _WAREKI_BASE[era_range_m.group(1)]
            year_start = base + int(era_range_m.group(2))
            year_end = base + int(era_range_m.group(3))
            continue

        conv = _wareki(raw)

        # 年度範囲
        yrm = re.search(r'(\d{4})[～〜~](\d{4})年度', conv)
        if yrm:
            year_start, year_end = int(yrm.group(1)), int(yrm.group(2))
            continue
        # 単年度（短い文字列）
        yrm2 = re.search(r'^(\d{4})年度$', conv)
        if yrm2:
            if not year_start:
                year_start = year_end = int(yrm2.group(1))
            continue
        # 課題番号
        if re.search(r'課題番号[：:]', raw):
            continue
        # 研究者（（代表者）・（分担者）・太字）
        if re.search(r'（代表者）|（分担者）|\*\*', raw):
            inv_parts.append(re.sub(r'\*\*(.+?)\*\*', r'\1', raw))
            found_inv = True
            continue
        # 最初の研究者が見つかった後は残りも研究者とみなす
        if found_inv:
            inv_parts.append(raw)
            continue
        # タイトル候補（それ以外の意味のある文字列）
        if len(raw) >= 5:
            title_parts.append(raw)

    if not title_parts:
        return None
    title = '，'.join(title_parts)

    # funding_raw から年度プレフィックスを除去して機関名・事業名を分離
    funding_conv = _wareki(funding_raw)
    funding_clean = re.sub(r'^\d{4}年度\s*', '', funding_conv).strip()

    kakenhi_m = _KAKENHI_TYPE_RE.search(funding_raw)
    if kakenhi_m or '科学研究費' in funding_raw:
        offer_org = '日本学術振興会'
        system_name = '科学研究費助成事業'
        if kakenhi_m:
            system_name += ' ' + kakenhi_m.group(0)
    else:
        # スペースで機関名と事業名を分離
        sp = funding_clean.find(' ')
        if sp != -1:
            offer_org = funding_clean[:sp]
            system_name = funding_clean[sp:].strip()
        else:
            offer_org = funding_clean
            system_name = ''

    # 年度が未取得の場合は funding_raw から探す
    if not year_start:
        year_start, year_end = _parse_year_range(funding_raw)

    return ResearchProject(
        title=title,
        offer_org=offer_org,
        system_name=system_name,
        year_start=year_start,
        year_end=year_end,
        grant_number=grant_no,
        investigators='，'.join(inv_parts),
    )


# ── メインパース関数 ─────────────────────────────────────────

def parse_text(text: str) -> ParsedData:
    result = ParsedData()
    current = 'skip'

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # セクションヘッダー
        if raw.lstrip().startswith('*'):
            sec = _detect_section(line)
            if sec is not None:
                current = sec
            continue

        if current == 'skip':
            continue
        if not re.match(r'^\d+\.', line):
            continue

        line = _strip_num(line)
        try:
            if current == 'papers':
                obj = _parse_paper(line)
                if obj:
                    result.papers.append(obj)
            elif current == 'books':
                obj = _parse_book(line)
                if obj:
                    result.books.append(obj)
            elif current == 'presentations':
                obj = _parse_presentation(line)
                if obj:
                    result.presentations.append(obj)
            elif current == 'misc':
                obj = _parse_misc(line)
                if obj:
                    result.misc.append(obj)
            elif current == 'projects':
                obj = _parse_project(line)
                if obj:
                    result.projects.append(obj)
        except Exception as e:
            print(f'[WARN] パース失敗: {line[:70]!r} -> {e}')

    return result
