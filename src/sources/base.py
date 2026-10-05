"""공개기관 데이터 소스 커넥터의 공통 인터페이스.

각 커넥터는 외부 공개 DB/페이지에서 SMR 노형 정보를 가져와
reactors.json 스키마의 '부분 레코드'로 정규화해 반환한다.
수집 로직(HTTP/파싱)은 기관별 모듈에서 구현하며, 여기서는 계약(인터페이스)만 정의.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class SourceRecord:
    """한 소스에서 가져온 노형 1건의 정규화 결과."""

    reactor_id: str
    source: str
    fetched: str = field(default_factory=lambda: date.today().isoformat())
    fields: dict[str, Any] = field(default_factory=dict)  # 예: capacity_mwe_total, status
    citations: list[str] = field(default_factory=list)     # 근거 URL/문서
    confidence: str = "medium"


class SourceConnector:
    """모든 공개기관 커넥터의 베이스 클래스."""

    name: str = "base"
    homepage: str = ""
    provides: list[str] = []  # 이 소스가 채워줄 수 있는 필드 목록

    def fetch(self, reactor_ids: list[str] | None = None) -> list[SourceRecord]:
        """노형 레코드를 수집해 반환. 하위 클래스에서 구현."""
        raise NotImplementedError

    def available(self) -> bool:
        """네트워크/자격증명 등 사용 가능 여부. 기본은 미구현(False)."""
        return False
