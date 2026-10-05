"""SMR 노형 평가 점수 엔진.

수집·정규화된 reactors.json 을 rubric.json 의 가중치에 따라 차원별/종합 점수로 변환한다.
'에이전트'는 직접 분석하지 않고 공개 자료에서 매핑된 level(1~5)과 confidence 를
입력으로 받아, 결정론적이고 재현 가능한 방식으로 점수를 계산한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# level(1~5) -> 0~100 선형 매핑
LEVEL_TO_SCORE = {1: 10.0, 2: 32.5, 3: 55.0, 4: 77.5, 5: 100.0}

# confidence -> 가중치 보정 계수 (신뢰도 낮으면 기여도 할인)
CONFIDENCE_FACTOR = {"high": 1.0, "medium": 0.85, "low": 0.7}


def load_json(name: str) -> dict[str, Any]:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def score_reactor(reactor: dict, rubric: dict) -> dict:
    """하나의 노형에 대해 차원별 점수와 종합 점수를 계산해 반환."""
    dims = {d["key"]: d for d in rubric["dimensions"]}
    total_weight = sum(d["weight"] for d in rubric["dimensions"])

    dim_results: dict[str, dict] = {}
    weighted_sum = 0.0
    conf_weighted_sum = 0.0
    conf_tally = {"high": 0, "medium": 0, "low": 0}

    for key, spec in dims.items():
        entry = reactor["dimensions"].get(key)
        if entry is None:
            continue
        level = int(entry["level"])
        confidence = entry.get("confidence", "low")
        base = LEVEL_TO_SCORE[level]
        weight = spec["weight"]

        weighted_sum += base * weight
        conf_weighted_sum += base * weight * CONFIDENCE_FACTOR[confidence]
        conf_tally[confidence] += 1

        dim_results[key] = {
            "label": spec["label"],
            "label_en": spec["label_en"],
            "weight": weight,
            "level": level,
            "confidence": confidence,
            "score": round(base, 1),
            "rationale": entry.get("rationale", ""),
        }

    overall = round(weighted_sum / total_weight, 1)
    overall_conf_adj = round(conf_weighted_sum / total_weight, 1)

    # 데이터 신뢰도 등급: low 비중이 높으면 전체 신뢰도 하향
    n = sum(conf_tally.values()) or 1
    if conf_tally["low"] / n >= 0.4:
        data_confidence = "low"
    elif conf_tally["high"] / n >= 0.5:
        data_confidence = "high"
    else:
        data_confidence = "medium"

    return {
        "overall_score": overall,
        "overall_score_confidence_adjusted": overall_conf_adj,
        "data_confidence": data_confidence,
        "dimensions": dim_results,
    }


def evaluate_all() -> dict:
    """전체 노형을 평가해 대시보드/리포트용 구조로 반환."""
    rubric = load_json("rubric.json")
    db = load_json("reactors.json")

    evaluated = []
    for r in db["reactors"]:
        result = score_reactor(r, rubric)
        evaluated.append({**r, "evaluation": result})

    evaluated.sort(key=lambda x: x["evaluation"]["overall_score"], reverse=True)
    for rank, r in enumerate(evaluated, 1):
        r["evaluation"]["rank"] = rank

    return {
        "meta": {
            "rubric_version": rubric["version"],
            "data_version": db["version"],
            "updated": db["updated"],
            "disclaimer": db["disclaimer"],
            "count": len(evaluated),
        },
        "rubric": rubric,
        "reactors": evaluated,
    }


if __name__ == "__main__":
    out = evaluate_all()
    print(f"평가 완료: {out['meta']['count']}개 노형 (rubric v{out['meta']['rubric_version']})\n")
    for r in out["reactors"]:
        ev = r["evaluation"]
        print(
            f"{ev['rank']:>2}. {r['name']:<28} "
            f"종합 {ev['overall_score']:>5} "
            f"(신뢰도보정 {ev['overall_score_confidence_adjusted']:>5}) "
            f"[{ev['data_confidence']}]  {r['country']} · {r['type']}"
        )
