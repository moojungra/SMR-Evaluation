"""Wikipedia 커넥터 — REST summary API로 노형 설계의 요약·최종수정일을 수집.

공개 엔드포인트: https://en.wikipedia.org/api/rest_v1/page/summary/<title>
반환: 짧은 설명, 발췌문(extract), 최종수정 타임스탬프, 문서 URL.
사실 교차검증과 '자료 신선도' 표시에 사용한다(설계 스펙은 자주 바뀌지 않음).
"""
from __future__ import annotations

import urllib.parse
from typing import Any

from .base import SourceConnector

try:
    import requests
    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    _HAS_REQUESTS = False

UA = "SMR-Evaluation-Agent/0.3 (https://github.com/moojungra/SMR-Evaluation; public research)"
REST = "https://en.wikipedia.org/api/rest_v1/page/summary/"


class WikipediaConnector(SourceConnector):
    name = "Wikipedia"
    homepage = "https://en.wikipedia.org/"
    provides = ["summary", "last_modified", "cross-check"]
    note = "REST summary API — 노형 요약·최종수정일 교차검증."

    def available(self) -> bool:
        return _HAS_REQUESTS

    def summary(self, title: str, timeout: int = 15) -> dict[str, Any] | None:
        """문서 요약을 가져온다. 404/오류면 None."""
        if not _HAS_REQUESTS or not title:
            return None
        url = REST + urllib.parse.quote(title.replace(" ", "_"), safe="")
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=timeout)
            if r.status_code != 200:
                return None
            d = r.json()
            if d.get("type", "").endswith("not_found"):
                return None
            return {
                "title": d.get("title"),
                "description": d.get("description"),
                "extract": d.get("extract"),
                "modified": d.get("timestamp"),
                "url": (d.get("content_urls", {}).get("desktop", {}) or {}).get("page"),
            }
        except Exception:
            return None
