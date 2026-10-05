"""공개기관 데이터 소스 레지스트리.

노형 평가가 '참조해 연결'할 공개 DB 목록을 한 곳에 정의한다.
각 소스는 제공 필드/홈페이지/수집 상태를 선언하며, 실제 수집 로직은
해당 커넥터 모듈에서 단계적으로 구현한다(현재는 provenance 메타데이터 중심).
"""
from __future__ import annotations

from .base import SourceConnector
from .googlenews import GoogleNewsConnector
from .iaea_aris import IaeaArisConnector
from .wikipedia import WikipediaConnector


class IAEA_ARIS(SourceConnector):
    name = "IAEA ARIS"
    homepage = "https://aris.iaea.org/"
    provides = ["type", "coolant", "spectrum", "capacity_mwe_total",
                "capacity_mwe_module", "modules", "fuel", "vendor", "country", "summary"]
    note = "Advanced Reactors Information System. SMR Booklet 포함 설계 서술 표준 출처."


class IAEA_PRIS(SourceConnector):
    name = "IAEA PRIS"
    homepage = "https://pris.iaea.org/"
    provides = ["status", "construction_start", "grid_connection", "operation"]
    note = "Power Reactor Information System. 건설/운전 중 노형의 공정 상태."


class NEA_SMR_Dashboard(SourceConnector):
    name = "NEA SMR Dashboard"
    homepage = "https://www.oecd-nea.org/smrdashboard"
    provides = ["licensing", "deployment", "economics", "supply_fuel"]
    note = "OECD/NEA SMR Digital Dashboard(4판, 95개). Power BI 임베드라 자동수집 불가 — 링크/참조용."


class WNA(SourceConnector):
    name = "World Nuclear Association"
    homepage = "https://world-nuclear.org/information-library/"
    provides = ["summary", "status", "vendor", "country"]
    note = "SMR 정보 라이브러리. 노형 개요·현황 교차검증용."


class US_NRC(SourceConnector):
    name = "US NRC"
    homepage = "https://www.nrc.gov/reactors/new-reactors/smr.html"
    provides = ["licensing"]
    note = "미국 규제기관. 설계인증/표준설계승인/건설허가 단계."


class CNSC(SourceConnector):
    name = "CNSC"
    homepage = "https://www.cnsc-ccsn.gc.ca/"
    provides = ["licensing"]
    note = "캐나다 규제기관. 벤더 설계사전심사(VDR)·건설허가."


class KINS(SourceConnector):
    name = "KINS/NSSC (한국)"
    homepage = "https://www.kins.re.kr/"
    provides = ["licensing"]
    note = "한국 원자력안전위원회/안전기술원. 표준설계인가(SDA) 등 국내 인허가."


# 평가가 참조하는 공개 소스 목록.
# Wikipedia·Google News 는 실수집 구현 완료(available), 나머지는 메타데이터 단계.
REGISTRY: list[SourceConnector] = [
    IaeaArisConnector(),
    WikipediaConnector(),
    GoogleNewsConnector(),
    IAEA_PRIS(),
    NEA_SMR_Dashboard(),
    WNA(),
    US_NRC(),
    CNSC(),
    KINS(),
]


def describe_sources() -> list[dict]:
    """등록된 공개 소스의 메타데이터를 반환(대시보드 '출처' 패널용)."""
    return [
        {
            "name": s.name,
            "homepage": s.homepage,
            "provides": s.provides,
            "note": getattr(s, "note", ""),
            "connected": s.available(),
        }
        for s in REGISTRY
    ]


if __name__ == "__main__":
    for s in describe_sources():
        flag = "✓연결" if s["connected"] else "·대기"
        print(f"[{flag}] {s['name']:<26} {s['homepage']}")
        print(f"        제공: {', '.join(s['provides'])}")
