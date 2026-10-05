"""Google News 커넥터 — 노형별 최신 뉴스(상태 신호)를 RSS로 수집.

공개 엔드포인트: https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en
반환: 최신 기사 title/source/pubDate/link 목록.
인허가·건설 '상태 변화'는 시간에 따라 바뀌므로 자동 수집의 핵심 대상이다.
feedparser 없이 표준 xml 파서만 사용.
"""
from __future__ import annotations

import html
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .base import SourceConnector

try:
    import requests
    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    _HAS_REQUESTS = False

UA = "SMR-Evaluation-Agent/0.3 (https://github.com/moojungra/SMR-Evaluation; public research)"
RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# 뉴스 제목에서 상태 변화를 시사하는 키워드 -> (차원, 제안 성숙도, 라벨)
STATUS_KEYWORDS: list[tuple[tuple[str, ...], str, int, str]] = [
    (("commercial operation", "grid connection", "grid-connected", "begins operation",
      "enters operation", "first power", "connected to the grid"), "deployment", 5, "운전/계통연계"),
    (("first criticality", "achieved criticality", "goes critical", "fuel load", "fuel loading"),
     "deployment", 4, "임계/연료장전"),
    (("begins construction", "starts construction", "construction begins", "construction start",
      "first concrete", "breaks ground", "groundbreaking", "under construction", "pour"),
     "deployment", 4, "착공/건설"),
    (("construction permit", "licence to construct", "license to construct", "construction licence",
      "approved for construction", "build approval"), "licensing", 4, "건설허가"),
    (("design approval", "design certification", "standard design", "certified", "gda",
      "generic design assessment", "design acceptance"), "licensing", 4, "설계승인/인증"),
    (("construction permit application", "docketed", "licensing application", "safety review",
      "pre-application"), "licensing", 3, "인허가 심사"),
    (("final investment decision", " fid ", "signs contract", "order for", "selected",
      "power purchase"), "deployment", 3, "투자결정/발주"),
]


class GoogleNewsConnector(SourceConnector):
    name = "Google News"
    homepage = "https://news.google.com/"
    provides = ["latest_status", "milestones"]
    note = "RSS 검색 — 노형별 인허가·건설 최신 신호."

    def available(self) -> bool:
        return _HAS_REQUESTS

    def search(self, query: str, limit: int = 6, timeout: int = 15) -> list[dict[str, Any]]:
        """질의에 대한 최신 기사 목록(최신순)."""
        if not _HAS_REQUESTS or not query:
            return []
        url = RSS.format(q=urllib.parse.quote(query))
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if r.status_code != 200:
                return []
            root = ET.fromstring(r.content)
        except Exception:
            return []

        items: list[dict[str, Any]] = []
        for it in root.iterfind(".//item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = it.findtext("pubDate")
            src_el = it.find("source")
            source = (src_el.text if src_el is not None else "") or ""
            iso, ts = None, 0.0
            if pub:
                try:
                    dt = parsedate_to_datetime(pub)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
                    ts = dt.timestamp()
                except Exception:
                    pass
            items.append({"title": html.unescape(title), "source": html.unescape(source),
                          "date": iso, "_ts": ts, "url": link})

        items.sort(key=lambda x: x["_ts"], reverse=True)
        return items[:limit]


def status_hint(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """최신 기사들에서 가장 진전된 상태 신호를 추출(제안용, 자동 반영 아님)."""
    best = None
    for it in items:
        t = f" {it['title'].lower()} "
        for keys, dim, level, label in STATUS_KEYWORDS:
            if any(k in t for k in keys):
                cand = {"dimension": dim, "suggested_level": level, "label": label,
                        "evidence": it["title"], "date": it.get("date"), "url": it["url"]}
                if best is None or level > best["suggested_level"]:
                    best = cand
                break
    return best
