"""공개 소스 실수집 오케스트레이터.

각 노형에 대해 Wikipedia 요약 + Google News 최신 기사(상태 신호)를 수집해
  - data/collected.json      : 대시보드가 라이브로 표시할 신호
  - data/collection_report.md: 상태 변화 제안 + 큐레이션 불일치 리포트
를 생성한다. 큐레이션된 평가(dimension level/confidence)는 덮어쓰지 않는다
('에이전트가 직접 분석'이 아니라 '공개 자료 신호를 수집·제시').

로컬 Python이 없어도 GitHub Actions(러너)가 주기적으로 실행한다.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sources.googlenews import GoogleNewsConnector, status_hint
from sources.wikipedia import WikipediaConnector

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 노형 id -> (Wikipedia 제목 | None, Google News 질의)
# 질의 레시피: 프로젝트 고유 토큰(VOYGR·Seadrift·Shidaowan 등)으로 특정성↑,
# 사명이 주식 티커인 경우(-stock -shares -NASDAQ)로 금융 노이즈 제외.
QUERIES: dict[str, tuple[str | None, str]] = {
    "htr-pm":            ("HTR-PM", '"HTR-PM" OR "Shidaowan" OR "Shidao Bay" nuclear -Hualong -steal'),
    "klt-40s":           ("Akademik Lomonosov", '"Akademik Lomonosov" OR "KLT-40S"'),
    "bwrx-300":          ("BWRX-300", '"BWRX-300"'),
    "linglong-one":      ("ACP100", '"Linglong One" OR "ACP100" reactor'),
    "nuscale-voygr":     ("NuScale Power", '(VOYGR OR RoPower OR Doicesti) NuScale -stock -stocks -NYSE -valuation'),
    "natrium":           ("TerraPower", '"Natrium" (TerraPower OR Kemmerer) reactor -stock -shares'),
    "rolls-royce-smr":   ("Rolls-Royce SMR", '"Rolls-Royce SMR" -shares -stock'),
    "smart100":          ("SMART (nuclear reactor)", '"SMART100" OR "SMART-100" reactor Korea'),
    "i-smr":             (None, '"i-SMR" Korea (reactor OR SMR)'),
    "holtec-smr-300":    ("Holtec International", '"SMR-300" Holtec'),
    "ritm-200":          ("RITM-200", '"RITM-200"'),
    "kairos-kp-fhr":     ("Kairos Power", '"Kairos" (Hermes OR "KP-FHR") reactor'),
    "xe-100":            ("Xe-100", '"Xe-100" OR (X-energy Seadrift) reactor -stock -NASDAQ'),
    "brest-od-300":      ("BREST (reactor)", '"BREST-OD-300"'),
    "carem-25":          ("CAREM", '"CAREM-25" OR ("CAREM" reactor Argentina)'),
    "ap300":             ("AP300", '"AP300" reactor -stock -stocks'),
    "terrestrial-imsr":  ("Terrestrial Energy", '"Terrestrial Energy" IMSR (molten OR reactor) -stock -TradingView'),
    "arc-100":           ("ARC Clean Technology", '"ARC-100" reactor'),
    "nuward":            ("Nuward", '"Nuward" (EDF OR SMR OR reactor)'),
    "newcleo-lfr":       ("Newcleo", '"newcleo" reactor -stock'),
    "seaborg-cmsr":      ("Seaborg Technologies", '"Seaborg" (CMSR OR reactor) -stock'),
    "tmsr-lf1":          ("TMSR-LF1", '"TMSR-LF1" OR ("thorium molten salt" reactor China Gobi) -Hualong -Seaborg -Danish'),
    "evinci":            ("EVinci", '"eVinci" microreactor'),
    "bwxt-pele":         ("Project Pele", '"Project Pele" microreactor'),
    "oklo-aurora":       ("Oklo", 'Oklo Aurora reactor Idaho -stock -shares -"price target"'),
    "usnc-mmr":          ("Ultra Safe Nuclear Corporation", '("USNC" OR "Kronos MMR") microreactor'),
    "last-energy-pws20": ("Last Energy", '"Last Energy" reactor'),
    "radiant-kaleidos":  (None, '"Radiant" (Kaleidos OR microreactor) nuclear -stock'),
    "bharat-smr":        ("Bharat Small Modular Reactor", '"Bharat Small Modular Reactor" OR "BSMR-200" India'),
    "httr":              ("High-temperature engineering test reactor", '"HTTR" (JAEA OR hydrogen OR reactor) Japan'),
    "marvel":            (None, '"MARVEL" microreactor INL Idaho'),
    "acpr50s":           ("ACPR50S", '"ACPR50S" OR "ACPR50" CGN floating reactor'),
    "svbr-100":          ("SVBR-100", '"SVBR-100" reactor'),
    "moltex-ssr":        ("Moltex Energy", '"Moltex" (SSR OR reactor) -stock'),
    "ga-em2":            ("Energy Multiplier Module", '"General Atomics" (EM2 OR "fast modular reactor") nuclear -stock'),
    "nano-zeus":         (None, '"NANO Nuclear" (ZEUS OR microreactor) -stock'),
    "dhr-400":           (None, '"DHR-400" OR "Yanlong" OR "district heating reactor" China nuclear'),
    "copenhagen-atomics":(None, '"Copenhagen Atomics" (reactor OR thorium)'),
    "blykalla-sealer":   ("Blykalla", '"Blykalla" OR "SEALER" reactor Sweden -stock'),
    "thorcon":           ("ThorCon nuclear reactor", '"ThorCon" Indonesia reactor'),
}


def curated_levels(reactor: dict) -> dict[str, int]:
    return {k: v["level"] for k, v in reactor.get("dimensions", {}).items()}


def main(delay: float = 0.8) -> None:
    with open(DATA / "reactors.json", encoding="utf-8") as f:
        db = json.load(f)

    wiki = WikipediaConnector()
    news = GoogleNewsConnector()
    print(f"수집 시작: {len(db['reactors'])}개 노형 · Wikipedia={wiki.available()} · GoogleNews={news.available()}")

    collected: dict[str, dict] = {}
    report_lines: list[str] = []
    flags: list[str] = []

    for r in db["reactors"]:
        rid = r["id"]
        wtitle, nquery = QUERIES.get(rid, (None, f'"{r["name"]}" reactor'))

        w = wiki.summary(wtitle) if wtitle else None
        time.sleep(delay)
        items = news.search(nquery, limit=6)
        time.sleep(delay)

        hint = status_hint(items)
        collected[rid] = {
            "news": [{k: it[k] for k in ("title", "source", "date", "url")} for it in items[:3]],
            "wiki": w,
            "status_hint": hint,
        }

        top = items[0]["title"] if items else "(뉴스 없음)"
        top_date = items[0]["date"] if items else "—"
        report_lines.append(f"### {r['name']}  \n- 최신: {top_date} · {top}")
        if hint:
            report_lines.append(f"- 신호: **{hint['label']}** → {hint['dimension']} 제안 Lv{hint['suggested_level']} "
                                f"(근거: {hint['evidence']})")
            cur = curated_levels(r).get(hint["dimension"])
            if cur is not None and hint["suggested_level"] > cur:
                msg = (f"⚠ {r['name']}: {hint['dimension']} 큐레이션 Lv{cur} < 수집신호 Lv{hint['suggested_level']} "
                       f"— 검토 필요 ({hint['label']})")
                flags.append(msg)
                report_lines.append(f"- {msg}")
        report_lines.append("")
        print(f"  · {rid:<20} 뉴스 {len(items)}건" + (f" · 힌트 {hint['label']}" if hint else ""))

    out = {"collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "count": len(collected), "reactors": collected}
    (DATA / "collected.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    header = [f"# SMR 수집 리포트", f"수집 시각: {out['collected_at']}", "",
              f"## 검토 필요 ({len(flags)}건)", ""]
    header += [f"- {m}" for m in flags] if flags else ["- (없음) 큐레이션 상태와 수집 신호 일치", ""]
    header += ["", "## 노형별 최신 신호", ""]
    (DATA / "collection_report.md").write_text("\n".join(header + report_lines), encoding="utf-8")

    print(f"\n완료 → data/collected.json, data/collection_report.md")
    print(f"검토 필요 {len(flags)}건")
    for m in flags:
        print("  " + m)


if __name__ == "__main__":
    main()
