"""
researchmap API v2 クライアント。
OAuth 2.0 クライアントクレデンシャルフローでトークンを取得し、
研究業績の取得・登録・更新を行う。

API ドキュメント: https://api.researchmap.jp/
"""

import re
import time
from typing import Any, Optional

import requests


_TOKEN_URL = "https://api.researchmap.jp/oauth2/token"
_API_BASE = "https://api.researchmap.jp"

# researchmap API のエンドポイント名
_ENDPOINT = {
    "paper": "published_papers",
    "book": "books",
    "presentation": "presentations",
    "project": "research_projects",
    "other": "misc",
}


class ResearchmapAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class ResearchmapClient:
    def __init__(self, client_id: str, client_secret: str, researcher_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.researcher_id = researcher_id
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._session = requests.Session()

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = self._session.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if resp.status_code != 200:
            raise ResearchmapAPIError(resp.status_code, resp.text)

        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _url(self, category: str) -> str:
        endpoint = _ENDPOINT[category]
        return f"{_API_BASE}/researchers/{self.researcher_id}/{endpoint}"

    def get_all(self, category: str) -> list[dict]:
        """指定カテゴリの全件を取得する。"""
        url = self._url(category)
        results = []
        limit = 100
        offset = 0
        while True:
            resp = self._session.get(
                url,
                headers=self._headers(),
                params={"limit": limit, "offset": offset},
            )
            if resp.status_code != 200:
                raise ResearchmapAPIError(resp.status_code, resp.text)
            data = resp.json()
            items = data.get("items", [])
            results.extend(items)
            if len(results) >= data.get("total", 0) or not items:
                break
            offset += limit
        return results

    def create(self, category: str, payload: dict) -> dict:
        """新規登録する。"""
        resp = self._session.post(
            self._url(category),
            headers=self._headers(),
            json=payload,
        )
        if resp.status_code not in (200, 201):
            raise ResearchmapAPIError(resp.status_code, resp.text)
        return resp.json()

    def update(self, category: str, record_id: str, payload: dict) -> dict:
        """既存レコードを更新する。"""
        url = f"{self._url(category)}/{record_id}"
        resp = self._session.put(
            url,
            headers=self._headers(),
            json=payload,
        )
        if resp.status_code not in (200, 204):
            raise ResearchmapAPIError(resp.status_code, resp.text)
        return resp.json() if resp.content else {}


# ---- データ変換ヘルパー ----

def _names(authors: list[str], lang: str) -> list[dict]:
    """著者リストを researchmap 形式に変換する。"""
    result = []
    for a in authors:
        # 姓名の分割を試みる（スペース区切り）
        parts = a.strip().split()
        if len(parts) >= 2:
            if lang == "en":
                # 英語: First Last → family=Last, given=First
                family = parts[-1]
                given = " ".join(parts[:-1])
            else:
                # 日本語: 姓 名
                family = parts[0]
                given = " ".join(parts[1:])
        else:
            family = a.strip()
            given = ""
        entry: dict[str, Any] = {"name": [{"@value": a, "@language": lang}]}
        if family:
            entry["family"] = [{"@value": family, "@language": lang}]
        if given:
            entry["given"] = [{"@value": given, "@language": lang}]
        result.append(entry)
    return result


def paper_to_payload(paper) -> dict:
    lang = paper.language
    payload: dict[str, Any] = {
        "paper_title": [{"@value": paper.title, "@language": lang}],
        "authors": {"@list": _names(paper.authors, lang)},
        "publication_name": [{"@value": paper.journal, "@language": lang}],
    }
    if paper.year:
        date_str = f"{paper.year}"
        if paper.month:
            date_str += f"-{paper.month:02d}"
        payload["published_date"] = date_str
    if paper.volume:
        payload["volume"] = paper.volume
    if paper.number:
        payload["number"] = paper.number
    if paper.pages:
        start, *end = re.split(r'[-–]', paper.pages)
        payload["starting_page"] = start.strip()
        if end:
            payload["ending_page"] = end[0].strip()
    if paper.doi:
        payload["doi"] = paper.doi
    return payload


def book_to_payload(book) -> dict:
    lang = book.language
    payload: dict[str, Any] = {
        "book_title": [{"@value": book.title, "@language": lang}],
        "authors": {"@list": _names(book.authors, lang)},
        "publisher": [{"@value": book.publisher, "@language": lang}],
    }
    if book.year:
        date_str = f"{book.year}"
        if book.month:
            date_str += f"-{book.month:02d}"
        payload["publication_date"] = date_str
    if book.isbn:
        payload["isbn"] = book.isbn
    return payload


def presentation_to_payload(pres) -> dict:
    lang = pres.language
    payload: dict[str, Any] = {
        "presentation_title": [{"@value": pres.title, "@language": lang}],
        "presenters": {"@list": _names(pres.authors, lang)},
        "event_name": [{"@value": pres.event, "@language": lang}],
    }
    if pres.year:
        date_str = f"{pres.year}"
        if pres.month:
            date_str += f"-{pres.month:02d}"
        payload["announced_date"] = date_str
    if pres.location:
        payload["event_location"] = [{"@value": pres.location, "@language": lang}]
    return payload


def project_to_payload(proj) -> dict:
    payload: dict[str, Any] = {
        "research_project_title": [{"@value": proj.title, "@language": "ja"}],
    }
    if proj.funding_agency:
        payload["funding_agency"] = [{"@value": proj.funding_agency, "@language": "ja"}]
    if proj.year_start:
        payload["start_year"] = str(proj.year_start)
    if proj.year_end:
        payload["end_year"] = str(proj.year_end)
    if proj.pi:
        payload["principal_investigator"] = [{"@value": proj.pi, "@language": "ja"}]
    if proj.project_number:
        payload["project_number"] = proj.project_number
    return payload


def other_to_payload(other) -> dict:
    lang = other.language
    payload: dict[str, Any] = {
        "misc_title": [{"@value": other.title, "@language": lang}],
        "authors": {"@list": _names(other.authors, lang)},
    }
    if other.publisher:
        payload["publication_name"] = [{"@value": other.publisher, "@language": lang}]
    if other.year:
        date_str = f"{other.year}"
        if other.month:
            date_str += f"-{other.month:02d}"
        payload["published_date"] = date_str
    return payload


