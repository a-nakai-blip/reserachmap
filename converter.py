"""
パースされたデータを researchmap インポート用 JSON 形式に変換するモジュール。

researchmap の一括インポート形式:
  https://researchmap.jp の「業績管理」→「インポート」で使用する JSON 形式。

各カテゴリの payload 構造は researchmap API v2 に準拠。
"""

import re
from typing import Any


def _lang_value(text: str, lang: str) -> list[dict]:
    return [{"@value": text, "@language": lang}]


def _names(authors: list[str], lang: str) -> list[dict]:
    result = []
    for a in authors:
        parts = a.strip().split()
        if len(parts) >= 2:
            if lang == "en":
                family = parts[-1]
                given = " ".join(parts[:-1])
            else:
                family = parts[0]
                given = " ".join(parts[1:])
        else:
            family = a.strip()
            given = ""
        entry: dict[str, Any] = {
            "name": _lang_value(a.strip(), lang),
        }
        if family:
            entry["family"] = _lang_value(family, lang)
        if given:
            entry["given"] = _lang_value(given, lang)
        result.append(entry)
    return result


def _split_pages(pages: str) -> tuple[str, str]:
    m = re.split(r'[-–]', pages, maxsplit=1)
    if len(m) == 2:
        return m[0].strip(), m[1].strip()
    return pages.strip(), ""


def _date_str(year, month) -> str:
    if year and month:
        return f"{year}-{month:02d}"
    if year:
        return str(year)
    return ""


def paper_to_payload(paper) -> dict:
    lang = paper.language
    payload: dict[str, Any] = {
        "paper_title": _lang_value(paper.title, lang),
        "authors": {"@list": _names(paper.authors, lang)},
    }
    if paper.journal:
        payload["publication_name"] = _lang_value(paper.journal, lang)
    d = _date_str(paper.year, paper.month)
    if d:
        payload["published_date"] = d
    if paper.volume:
        payload["volume"] = paper.volume
    if paper.number:
        payload["number"] = paper.number
    if paper.pages:
        start, end = _split_pages(paper.pages)
        payload["starting_page"] = start
        if end:
            payload["ending_page"] = end
    if paper.doi:
        payload["doi"] = paper.doi
    return payload


def book_to_payload(book) -> dict:
    lang = book.language
    payload: dict[str, Any] = {
        "book_title": _lang_value(book.title, lang),
        "authors": {"@list": _names(book.authors, lang)},
    }
    if book.publisher:
        payload["publisher"] = _lang_value(book.publisher, lang)
    d = _date_str(book.year, book.month)
    if d:
        payload["publication_date"] = d
    if book.isbn:
        payload["isbn"] = book.isbn
    return payload


def presentation_to_payload(pres) -> dict:
    lang = pres.language
    payload: dict[str, Any] = {
        "presentation_title": _lang_value(pres.title, lang),
        "presenters": {"@list": _names(pres.authors, lang)},
    }
    if pres.event:
        payload["event_name"] = _lang_value(pres.event, lang)
    d = _date_str(pres.year, pres.month)
    if d:
        payload["announced_date"] = d
    if pres.location:
        payload["event_location"] = _lang_value(pres.location, lang)
    return payload


def project_to_payload(proj) -> dict:
    payload: dict[str, Any] = {
        "research_project_title": _lang_value(proj.title, "ja"),
    }
    if proj.funding_agency:
        payload["funding_agency"] = _lang_value(proj.funding_agency, "ja")
    if proj.year_start:
        payload["start_year"] = str(proj.year_start)
    if proj.year_end:
        payload["end_year"] = str(proj.year_end)
    if proj.pi:
        payload["principal_investigator"] = _lang_value(proj.pi, "ja")
    if proj.project_number:
        payload["project_number"] = proj.project_number
    return payload


def other_to_payload(other) -> dict:
    lang = other.language
    payload: dict[str, Any] = {
        "misc_title": _lang_value(other.title, lang),
        "authors": {"@list": _names(other.authors, lang)},
    }
    if other.publisher:
        payload["publication_name"] = _lang_value(other.publisher, lang)
    d = _date_str(other.year, other.month)
    if d:
        payload["published_date"] = d
    return payload


PAYLOAD_FUNCS = {
    "paper": paper_to_payload,
    "book": book_to_payload,
    "presentation": presentation_to_payload,
    "project": project_to_payload,
    "other": other_to_payload,
}

# researchmap エクスポート JSON のカテゴリキー名
EXPORT_KEYS = {
    "paper": "published_papers",
    "book": "books",
    "presentation": "presentations",
    "project": "research_projects",
    "other": "misc",
}
