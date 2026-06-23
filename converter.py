"""
ParsedData → researchmap JSONL インポート形式への変換。

実際の researchmap JSONL エクスポート形式に準拠:
  paper_title: {"ja": "...", "en": "..."}
  authors:     {"ja": [{"name": "..."}, ...]}
  event:       {"ja": "..."}   (presentations)
  paper_title: {"ja": "..."}   (misc)
"""

from typing import Any, Optional


def _lv(value: str, lang: str) -> dict:
    return {lang: value}


def _authors(names: list[str], lang: str) -> dict:
    return {lang: [{'name': n} for n in names]}


def _date(year: Optional[int], month: Optional[int]) -> str:
    if year and month:
        return f'{year}-{month:02d}'
    return str(year) if year else ''


def paper_to_merge(paper) -> dict:
    lang = paper.lang
    m: dict[str, Any] = {
        'paper_title': _lv(paper.title, lang),
        'authors': _authors(paper.authors, lang),
    }
    # 筆頭/最終著者ロール（太字著者の位置から判定）
    if paper.bold_author and paper.authors:
        if paper.bold_author == paper.authors[0]:
            m['published_paper_owner_roles'] = ['lead']
        elif paper.bold_author == paper.authors[-1]:
            m['published_paper_owner_roles'] = ['last']

    d = _date(paper.year, paper.month)
    if d:
        m['publication_date'] = d
    if paper.journal:
        m['publication_name'] = _lv(paper.journal, lang)
    if paper.volume:
        m['volume'] = paper.volume
    if paper.number:
        m['number'] = paper.number
    if paper.start_page:
        m['starting_page'] = paper.start_page
    if paper.end_page:
        m['ending_page'] = paper.end_page
    if paper.doi:
        m['identifiers'] = {'doi': [paper.doi]}
    return m


def book_to_merge(book) -> dict:
    lang = book.lang
    m: dict[str, Any] = {
        'book_title': _lv(book.title, lang),
    }
    if book.author_text:
        m['authors'] = {lang: [{'name': book.author_text}]}
    if book.publisher:
        m['publisher'] = _lv(book.publisher, lang)
    d = _date(book.year, book.month)
    if d:
        m['publication_date'] = d
    # 分担執筆 → contributor
    if '分担' in book.note:
        m['book_owner_role'] = 'contributor'
    elif '編' in book.note:
        m['book_owner_role'] = 'editor'
    return m


def presentation_to_merge(pres) -> dict:
    lang = pres.lang
    m: dict[str, Any] = {
        'presentation_title': _lv(pres.title, lang),
        'presenters': _authors(pres.authors, lang),
        'presentation_type': 'oral_presentation',
        'invited': False,
    }
    if pres.event:
        m['event'] = _lv(pres.event, lang)
    d = _date(pres.year, pres.month)
    if d:
        m['publication_date'] = d
    return m


def misc_to_merge(item) -> dict:
    lang = item.lang
    m: dict[str, Any] = {
        'paper_title': _lv(item.title, lang),
    }
    if item.authors:
        m['authors'] = _authors(item.authors, lang)
    d = _date(item.year, item.month)
    if d:
        m['publication_date'] = d
    if item.publication:
        m['publication_name'] = _lv(item.publication, lang)
    if item.volume:
        m['volume'] = item.volume
    if item.number:
        m['number'] = item.number
    if item.start_page:
        m['starting_page'] = item.start_page
    if item.end_page:
        m['ending_page'] = item.end_page
    return m


def project_to_merge(proj) -> dict:
    m: dict[str, Any] = {
        'research_project_title': _lv(proj.title, 'ja'),
    }
    if proj.offer_org:
        m['offer_organization'] = _lv(proj.offer_org, 'ja')
    if proj.system_name:
        m['system_name'] = _lv(proj.system_name, 'ja')
    if proj.year_start:
        m['from_date'] = f'{proj.year_start}-04'
    if proj.year_end:
        # 年度末は翌年3月
        m['to_date'] = f'{proj.year_end + 1}-03'
    if proj.grant_number:
        m['identifiers'] = {'grant_number': [proj.grant_number]}
    if proj.investigators:
        m['investigators'] = {'ja': [{'name': proj.investigators}]}
    return m
