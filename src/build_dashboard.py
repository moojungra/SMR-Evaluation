"""평가 결과 + 소스 메타데이터를 대시보드가 읽는 data.js 로 내보낸다.

산출물: dashboard/data.js  ->  `window.SMR_DATA = {...}`
dashboard/index.html 이 이 파일을 로드해 렌더링한다(로컬 file:// 에서도 동작).
"""
from __future__ import annotations

import json
from pathlib import Path

from scoring import evaluate_all
from sources import describe_sources

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard" / "data.js"


def build() -> dict:
    data = evaluate_all()
    data["sources"] = describe_sources()
    # 분류 체계(세대·분류·기술계열)를 대시보드 필터용으로 전달
    import json
    with open(ROOT / "data" / "reactors.json", encoding="utf-8") as f:
        data["taxonomy"] = json.load(f).get("taxonomy", {})
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    OUT.write_text(f"window.SMR_DATA = {payload};\n", encoding="utf-8")
    print(f"대시보드 데이터 생성: {OUT}")
    print(f"  노형 {data['meta']['count']}개, 공개 소스 {len(data['sources'])}개")


if __name__ == "__main__":
    main()
