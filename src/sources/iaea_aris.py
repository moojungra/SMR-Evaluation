"""IAEA ARIS 커넥터 — 공식 설계 스펙을 JSON API로 수집.

ARIS(Advanced Reactors Information System)는 Next.js 앱으로, 뒤에 공개 JSON API가 있다:
  POST https://aris.iaea.org/api/DSR/TechnicalData   (body {} → 전체 설계)
한 번 호출로 ~120개 설계(SMR ~62개)의 구조화된 기술데이터를 반환한다:
  설계기관·국가·design_status(설계성숙도)·정격출력(MWe)·노형·냉각재·중성자스펙트럼·
  연료물질·농축도·열출력·dsrId 등. 권위 있는 '사실 필드' 교차검증에 사용한다.

주의: design_status 는 IAEA의 '설계 성숙도' 라벨이며 실시간 프로젝트 상태가 아니다
(예: BWRX-300 = "Detailed Design"이지만 실제로는 건설 중). 참고용으로만 표시한다.
"""
from __future__ import annotations

import re
from typing import Any

from .base import SourceConnector

try:
    import requests
    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    _HAS_REQUESTS = False

UA = "SMR-Evaluation-Agent/0.4 (https://github.com/moojungra/SMR-Evaluation; public research)"
API = "https://aris.iaea.org/api/DSR/TechnicalData"


def _clean(v: Any) -> str | None:
    """ARIS의 빈값('-','N/A','') → None."""
    if v is None:
        return None
    s = str(v).strip()
    return None if s in ("", "-", "N/A", "n/a") else s


def _num(v: Any) -> float | None:
    s = _clean(v)
    if s is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    return float(m.group()) if m else None


def norm_name(s: str) -> str:
    """매칭용 정규화: 소문자 + 영숫자만."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


class IaeaArisConnector(SourceConnector):
    name = "IAEA ARIS"
    homepage = "https://aris.iaea.org/"
    provides = ["design_org", "design_status", "net_mwe", "type", "coolant",
                "spectrum", "fuel", "enrichment"]
    note = "Advanced Reactors Information System — 공식 설계 스펙(JSON API)."

    def available(self) -> bool:
        return _HAS_REQUESTS

    def fetch_all(self, timeout: int = 30) -> list[dict[str, Any]]:
        """전체 설계를 정규화해 반환. 실패 시 빈 리스트."""
        if not _HAS_REQUESTS:
            return []
        try:
            r = requests.post(API, json={}, headers={"User-Agent": UA,
                              "Content-Type": "application/json"}, timeout=timeout)
            if r.status_code != 200:
                return []
            results = (r.json().get("data") or {}).get("results") or []
        except Exception:
            return []

        out = []
        for x in results:
            out.append({
                "name": x.get("short_reactor_name"),
                "full_name": _clean(x.get("full_name")),
                "org": _clean(x.get("design_org")),
                "country": _clean(x.get("country_of_origin")),
                "design_status": _clean(x.get("design_status")),
                "net_mwe": _num(x.get("reference_plant_net_power_output")),
                "size": (x.get("category_reactor_size") or [None])[0],
                "type": _clean(x.get("category_reactor_type")),
                "coolant": _clean(x.get("category_core_coolant_for_display")),
                "spectrum": _clean(x.get("category_neutron_spectrum")),
                "fuel": _clean(x.get("param_fuel_core_fuel_material")),
                "enrichment": _clean(x.get("param_fuel_core_enrichment")),
                "thermal_mwt": _num(x.get("param_fuel_core_single_core_thermal_power")),
                "dsr_id": x.get("dsrId"),
            })
        return out

    def index_smr(self, timeout: int = 30) -> dict[str, dict]:
        """정규화 이름 → SMR 설계 레코드 딕셔너리."""
        idx = {}
        for d in self.fetch_all(timeout=timeout):
            if d.get("size") == "SMR" and d.get("name"):
                idx[norm_name(d["name"])] = d
        return idx
