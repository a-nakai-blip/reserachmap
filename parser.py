"""
大学研究業績サイトのテキストデータをパースするモジュール。

対応フォーマット例:
  [論文]
  Akira Nakai, Maki Tanaka: Development and validation ..., Journal Name, 26(5): 927-934, 2026年5月, DOI:10.7752/jpes.2026.05093
  中井聖，田中真紀: タイトル, 雑誌名, 50, 8-15, 2025年3月

  [著書]
  中井聖: 書名, 出版社, 2024年4月

  [講演]
  中井聖: 発表タイトル, 学会名, 2025年9月, 大阪

  [研究プロジェクト]
  科研費基盤研究(C): 研究課題名, 2022-2024, 代表者: 中井聖

  [報告書・その他]
  中井聖: タイトル, 掲載誌・機関名, 2025年3月
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Paper:
    authors: list[str]
    title: str
    journal: str
    year: Optional[int] = None
    month: Optional[int] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    language: str = "ja"


@dataclass
class Book:
    authors: list[str]
    title: str
    publisher: str
    year: Optional[int] = None
    month: Optional[int] = None
    isbn: Optional[str] = None
    language: str = "ja"


@dataclass
class Presentation:
    authors: list[str]
    title: str
    event: str
    year: Optional[int] = None
    month: Optional[int] = None
    location: Optional[str] = None
    language: str = "ja"


@dataclass
class ResearchProject:
    title: str
    funding_agency: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    pi: Optional[str] = None
    project_number: Optional[str] = None


@dataclass
class OtherAchievement:
    authors: list[str]
    title: str
    publisher: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    language: str = "ja"


@dataclass
class ParsedData:
    papers: list[Paper] = field(default_factory=list)
    books: list[Book] = field(default_factory=list)
    presentations: list[Presentation] = field(default_factory=list)
    projects: list[ResearchProject] = field(default_factory=list)
    others: list[OtherAchievement] = field(default_factory=list)


# 年月のパターン (例: 2025年3月, 2025年, 2025/03)
_YEAR_MONTH_RE = re.compile(r'(\d{4})年(?:(\d{1,2})月)?')
_YEAR_ONLY_RE = re.compile(r'(\d{4})年')
_YEAR_SLASH_RE = re.compile(r'(\d{4})/(\d{1,2})')
_DOI_RE = re.compile(r'DOI:\s*([\w./\-]+)', re.IGNORECASE)
_VOL_NUM_PAGES_RE = re.compile(r'(\d+)\((\d+)\):\s*([\d\-–]+)')
_VOL_PAGES_RE = re.compile(r'(\d+),\s*([\d\-–]+)')
_ISBN_RE = re.compile(r'ISBN[:\-]?\s*([\d\-X]+)', re.IGNORECASE)


def _detect_language(text: str) -> str:
    # 日本語文字が含まれていれば ja
    if re.search(r'[぀-ヿ一-鿿]', text):
        return "ja"
    return "en"


def _parse_year_month(text: str) -> tuple[Optional[int], Optional[int]]:
    m = _YEAR_MONTH_RE.search(text)
    if m:
        year = int(m.group(1))
        month = int(m.group(2)) if m.group(2) else None
        return year, month
    m = _YEAR_SLASH_RE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _YEAR_ONLY_RE.search(text)
    if m:
        return int(m.group(1)), None
    return None, None


def _split_authors(authors_str: str) -> list[str]:
    # 読点（，、,）やセミコロンで著者を分割
    parts = re.split(r'[，、,;；]\s*', authors_str.strip())
    return [p.strip() for p in parts if p.strip()]


def _parse_paper_line(line: str) -> Optional[Paper]:
    """
    例: 著者1, 著者2: タイトル, 雑誌名, 26(5): 927-934, 2025年3月, DOI:xxx
    """
    if ':' not in line:
        return None
    # 著者部分とそれ以降に分割（最初の ':' で分割）
    author_part, rest = line.split(':', 1)
    authors = _split_authors(author_part)

    # 残りをカンマで分割
    parts = [p.strip() for p in rest.split(',')]
    if not parts:
        return None

    title = parts[0].strip()
    journal = parts[1].strip() if len(parts) > 1 else ""

    doi = None
    doi_m = _DOI_RE.search(line)
    if doi_m:
        doi = doi_m.group(1)

    year, month = _parse_year_month(line)
    volume = number = pages = None

    # 巻号ページのパース
    vol_num_m = _VOL_NUM_PAGES_RE.search(line)
    if vol_num_m:
        volume = vol_num_m.group(1)
        number = vol_num_m.group(2)
        pages = vol_num_m.group(3)
    else:
        # 巻, ページ形式 (例: 50, 8-15)
        for p in parts[2:]:
            p = p.strip()
            if re.match(r'^\d+$', p):
                if volume is None:
                    volume = p
            elif re.match(r'^\d+[\-–]\d+$', p):
                pages = p

    lang = _detect_language(title + author_part)

    return Paper(
        authors=authors,
        title=title,
        journal=journal,
        year=year,
        month=month,
        volume=volume,
        number=number,
        pages=pages,
        doi=doi,
        language=lang,
    )


def _parse_book_line(line: str) -> Optional[Book]:
    """
    例: 著者1, 著者2: 書名, 出版社, 2024年4月, ISBN:xxx
    """
    if ':' not in line:
        return None
    author_part, rest = line.split(':', 1)
    authors = _split_authors(author_part)
    parts = [p.strip() for p in rest.split(',')]
    if not parts:
        return None
    title = parts[0].strip()
    publisher = parts[1].strip() if len(parts) > 1 else ""
    year, month = _parse_year_month(line)
    isbn = None
    isbn_m = _ISBN_RE.search(line)
    if isbn_m:
        isbn = isbn_m.group(1)
    lang = _detect_language(title + author_part)
    return Book(authors=authors, title=title, publisher=publisher,
                year=year, month=month, isbn=isbn, language=lang)


def _parse_presentation_line(line: str) -> Optional[Presentation]:
    """
    例: 著者1, 著者2: 発表タイトル, 学会名, 2025年9月, 東京
    """
    if ':' not in line:
        return None
    author_part, rest = line.split(':', 1)
    authors = _split_authors(author_part)
    parts = [p.strip() for p in rest.split(',')]
    if not parts:
        return None
    title = parts[0].strip()
    event = parts[1].strip() if len(parts) > 1 else ""
    year, month = _parse_year_month(line)
    # 最後の部分で年月に該当しないものを場所とみなす
    location = None
    for p in reversed(parts[2:]):
        p = p.strip()
        if not _YEAR_MONTH_RE.search(p) and not _YEAR_ONLY_RE.search(p):
            location = p
            break
    lang = _detect_language(title + author_part)
    return Presentation(authors=authors, title=title, event=event,
                        year=year, month=month, location=location, language=lang)


def _parse_project_line(line: str) -> Optional[ResearchProject]:
    """
    例: 科研費基盤研究(C): 研究課題名, 2022-2024, 代表者: 中井聖
    例: 研究課題名, 機関名, 2023-2025, 課題番号: 12345
    """
    year_start = year_end = None
    year_range_m = re.search(r'(\d{4})\s*[-–]\s*(\d{4})', line)
    if year_range_m:
        year_start = int(year_range_m.group(1))
        year_end = int(year_range_m.group(2))

    pi = None
    pi_m = re.search(r'代表者[:：]\s*(.+?)(?:,|$)', line)
    if pi_m:
        pi = pi_m.group(1).strip()

    proj_num = None
    num_m = re.search(r'課題番号[:：]\s*([\w\d]+)', line)
    if num_m:
        proj_num = num_m.group(1)

    funding = None
    title = line
    if ':' in line or '：' in line:
        sep_idx = min(
            (line.index(':') if ':' in line else len(line)),
            (line.index('：') if '：' in line else len(line))
        )
        funding = line[:sep_idx].strip()
        rest = line[sep_idx + 1:].strip()
        parts = [p.strip() for p in rest.split(',')]
        title = parts[0] if parts else rest
    else:
        parts = [p.strip() for p in line.split(',')]
        title = parts[0]

    return ResearchProject(
        title=title.strip(),
        funding_agency=funding,
        year_start=year_start,
        year_end=year_end,
        pi=pi,
        project_number=proj_num,
    )


def _parse_other_line(line: str) -> Optional[OtherAchievement]:
    """
    例: 著者1, 著者2: タイトル, 掲載誌・機関名, 2025年3月
    """
    if ':' not in line:
        return None
    author_part, rest = line.split(':', 1)
    authors = _split_authors(author_part)
    parts = [p.strip() for p in rest.split(',')]
    if not parts:
        return None
    title = parts[0].strip()
    publisher = parts[1].strip() if len(parts) > 1 else None
    year, month = _parse_year_month(line)
    lang = _detect_language(title + author_part)
    return OtherAchievement(authors=authors, title=title, publisher=publisher,
                            year=year, month=month, language=lang)


# カテゴリを示すヘッダー行のパターン
_CATEGORY_HEADERS = {
    re.compile(r'論文|paper|article', re.IGNORECASE): 'paper',
    re.compile(r'著書|book|編著', re.IGNORECASE): 'book',
    re.compile(r'講演|口頭発表|presentation|conference', re.IGNORECASE): 'presentation',
    re.compile(r'研究プロジェクト|project|科研費|競争的資金|grants', re.IGNORECASE): 'project',
    re.compile(r'報告書|その他|other|misc', re.IGNORECASE): 'other',
}


def _detect_category(line: str) -> Optional[str]:
    stripped = line.strip()
    # ヘッダー行は括弧で囲まれているか、短い（30文字以下）かつデータ行でない行
    is_header = (
        re.match(r'^[\[【〔#]', stripped)  # [ 【 〔 # で始まる
        or (len(stripped) <= 30 and ':' not in stripped and '，' not in stripped)
    )
    if not is_header:
        return None
    stripped = stripped.strip('[]【】〔〕#')
    for pattern, cat in _CATEGORY_HEADERS.items():
        if pattern.search(stripped):
            return cat
    return None


def parse_text(text: str) -> ParsedData:
    """テキストをパースして ParsedData を返す。"""
    result = ParsedData()
    current_category = 'paper'  # デフォルトは論文

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue

        # カテゴリヘッダーの検出
        cat = _detect_category(line)
        if cat:
            current_category = cat
            continue

        try:
            if current_category == 'paper':
                obj = _parse_paper_line(line)
                if obj:
                    result.papers.append(obj)
            elif current_category == 'book':
                obj = _parse_book_line(line)
                if obj:
                    result.books.append(obj)
            elif current_category == 'presentation':
                obj = _parse_presentation_line(line)
                if obj:
                    result.presentations.append(obj)
            elif current_category == 'project':
                obj = _parse_project_line(line)
                if obj:
                    result.projects.append(obj)
            elif current_category == 'other':
                obj = _parse_other_line(line)
                if obj:
                    result.others.append(obj)
        except Exception as e:
            print(f"[WARN] パース失敗: {line!r} -> {e}")

    return result
