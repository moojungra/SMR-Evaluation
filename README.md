# SMR 노형 평가 에이전트 & 대시보드

소형모듈원자로(SMR) 노형을 **직접 분석하는 대신, 공개 기관 자료를 참조·정규화해**
6개 차원으로 평가하고 NEA SMR Dashboard 스타일로 시각화하는 도구.

로컬에 Python을 설치할 필요가 없다. **GitHub Actions**(클라우드 러너)가 데이터를
수집·채점하고, **GitHub Pages**가 대시보드를 호스팅한다.

---

## 구조

```
smr-evaluation-agent/
├─ data/
│  ├─ rubric.json          # 평가 루브릭 (6개 차원 · 가중치 · 성숙도 기준)
│  └─ reactors.json        # 정규화된 노형 DB (모든 값에 출처·신뢰도 태그)
├─ src/
│  ├─ scoring.py           # 점수 엔진 (level 1~5 → 가중 0~100)
│  ├─ build_dashboard.py   # 평가결과 + 소스메타 → dashboard/data.js 생성
│  └─ sources/             # 공개기관 DB 커넥터 계층
│     ├─ base.py           #   커넥터 공통 인터페이스
│     └─ registry.py       #   참조 소스 목록(IAEA·NEA·WNA·규제기관…)
├─ dashboard/
│  └─ index.html           # 대시보드 (평가 로직 JS 내장, data.js 있으면 우선)
├─ .github/workflows/deploy.yml   # 수집→빌드→Pages 배포 (주간 자동)
└─ requirements.txt
```

### 데이터 흐름 (에이전트 → 데이터 → 대시보드)

1. `src/sources/*` 커넥터가 공개 DB에서 노형 정보를 가져와 `reactors.json` 스키마로 정규화
2. `scoring.py`가 루브릭 가중치로 차원별·종합 점수 산출
3. `build_dashboard.py`가 결과 + 소스 메타데이터를 `dashboard/data.js`로 내보냄
4. `dashboard/index.html`이 이를 읽어 랭킹·레이더·히트맵으로 표시
   (`data.js`가 없으면 HTML 내장 베이스라인 데이터로 단독 동작)

---

## 평가 차원 (rubric v0.1)

| 차원 | 가중 | 설명 |
|---|---|---|
| 기술 성숙도 | 22% | 설계 성숙도 + 기반 기술 운전 경험 |
| 인허가 진행도 | 20% | 규제 설계인증/건설허가 단계 |
| 경제성 | 18% | 목표 LCOE·건설단가·비용 신뢰도 |
| 안전성·설계 | 15% | 피동안전·EPZ 축소·핵확산저항성 |
| 공급망·연료 | 13% | LEU/HALEU 연료·기기 제작 공급망 |
| 배치 성숙도 | 12% | 확정 발주·착공·FOAK 시점 |

성숙도는 1(개념)~5(실증/운전)로 매핑하고 **데이터 신뢰도**(高/中/低)를 함께 기록한다.

---

## 분류 체계 (taxonomy)

54개 노형을 다음 축으로 분류해 한눈에 비교한다(대시보드 필터).

- **세대**: `Gen III+`(경수로 중심) · `Gen IV`(고속로·고온가스로·용융염·납냉각)
- **분류**: `경수로 SMR` · `비경수로 SMR` · `마이크로로(MMR)`
- **기술계열**: PWR · iPWR · PHWR · BWR · HTGR · SFR · LFR · MSR · FHR · GFR · 히트파이프 · Pool

운전 중(HTR-PM·HTTR·Akademik Lomonosov)부터 건설 중(BWRX-300·Natrium·BREST·Kairos Hermes·
Linglong One·Bharat SMR), 인허가·설계, 마이크로로(eVinci·Pele·Oklo·MARVEL 등)까지 포괄한다.
지역도 미·중·러·한·영·불·캐·인도·일본·스웨덴·덴마크·인도네시아·아르헨티나로 확대.

---

## 참조 공개 데이터 소스

| 소스 | 제공 | 링크 |
|---|---|---|
| IAEA ARIS | 설계 서술·용량·연료 | https://aris.iaea.org/ |
| IAEA PRIS | 건설/운전 상태 | https://pris.iaea.org/ |
| NEA SMR Dashboard | 인허가·금융·공급망·연료 | https://www.oecd-nea.org/smrdashboard |
| World Nuclear Association | 개요·현황 | https://world-nuclear.org/ |
| US NRC / CNSC / KINS·NSSC | 각국 인허가 | 각 규제기관 |

> 커넥터는 현재 **레지스트리·정규화 인터페이스**까지 구현되어 있으며, 각 소스의
> 실제 수집 로직은 `src/sources/`에서 단계적으로 추가한다. 그때까지 `reactors.json`은
> 공개 자료 기반의 수작업 검증 베이스라인으로 유지된다.

---

## 실수집 파이프라인 (live collection)

`src/collect.py`가 노형별로 공개 소스를 실제 수집한다(추가 의존성은 `requests`뿐).

- **IAEA ARIS JSON API** (`POST /api/DSR/TechnicalData`) — 공식 설계 스펙(설계기관·
  설계성숙도·정격MWe·노형·냉각재·연료·농축도). 54개 중 42개가 ARIS에 직접 매칭되어
  권위 있는 '사실 필드'로 교차검증되며, ARIS에만 있는 설계는 **추가 후보**로 리포트.
- **Wikipedia REST API** — 노형 요약·최종수정일(교차검증·신선도)
- **Google News RSS** — 노형별 최신 기사(인허가·건설 상태 신호)
- **상태 힌트** — 기사 제목의 마일스톤 키워드(건설허가·착공·계통연계 등)를 감지해
  해당 차원의 성숙도를 *제안*하고, 큐레이션 값과 불일치 시 `검토 필요`로 플래그

산출물: `data/collected.json`(대시보드가 노형 상세에 '자동수집 신호' + 'IAEA ARIS 공식
스펙'으로 표시) + `data/collection_report.md`(검토 필요 + ARIS 매칭/추가 후보 목록).
**큐레이션된 평가(level/confidence)는 덮어쓰지 않는다** — 에이전트는 공개 자료를
수집·제시하고, 승급 판단은 사람이 한다.

> **NEA SMR Dashboard**는 Power BI 임베드(app.powerbi.com)라 깨끗한 JSON API가 없어
> 자동수집이 비현실적 — 링크/참조용으로만 둔다. IAEA PRIS·규제기관은 단계적 추가 대상.

---

## GitHub로 배포하기 (로컬 Python 불필요)

1. 이 폴더를 GitHub 저장소로 push
2. 저장소 **Settings → Pages → Build and deployment → Source: GitHub Actions** 선택
3. `main`에 push하면 Actions가 자동으로 데이터 생성 + Pages 배포
4. 배포 URL: `https://<사용자명>.github.io/<저장소명>/`
5. 매주 월요일 자동 재빌드(또는 Actions 탭에서 수동 실행)

### 로컬에서 돌려보려면 (선택, Python 필요)

```bash
pip install -r requirements.txt
python src/scoring.py           # 콘솔 랭킹 출력
python src/build_dashboard.py   # dashboard/data.js 생성
```

---

## 주의

공개 자료 기반 **베이스라인**이며 수치는 근사·변동 가능하다. 각 항목의 신뢰도와
출처를 함께 확인할 것. 의사결정 보조용이며 1차 자료 검증을 대체하지 않는다.
보유 1차 자료를 추가하면 해당 노형의 값과 신뢰도를 갱신한다.
