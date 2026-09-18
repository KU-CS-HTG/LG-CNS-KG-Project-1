# docs/발표 — 미니 프로젝트 발표 자료 (2026-09-18 금)

| 파일 | 무엇 |
|---|---|
| **`발표_최종_20260918.pptx`** | **실제로 발표한 덱** (11장, 팀 공동 편집 · Google Slides 경유). 타깃 → 아키텍처 → 데이터 → 서비스 구조 → AI & Agent → 챗봇 비교 → 구현 결과 → 한계 → 확장 |
| `20260918_발표_대본_참고.md` | 발표 직전 정리한 대본 보강 · 질의응답 12건 · 숫자 카드 · "쓰지 말 말". 발표 후 질의응답 대비 자료로도 유효 |
| `presentation_version2.pptx` | 팀원 초안 8장 (9/17). 우상단 모티프를 실제 스키마 모양(전공 → 역량 ← 직무, 하위 역량 ↑)으로 교체한 판 |
| `발표_초안_v1_{GraphInk,DarkBoard,SignalRed}.pptx` · `테마_비교.png` | 9/17 낮 초안 v1 (시행착오 6건 중심, 20~23장) — 테마 3종. `build_deck.py` 로 생성 |
| `발표_초안_v2_GraphInk.pptx` | v1 을 쉬운 말로 고치고 이미지·도형을 넣은 v2 (22장). `build_deck_v2.py` + `deck_lib.py` + `make_images.py`(`img/`) 로 생성 |
| `보조자료/` | 최종 덱에 넣지 않은 대체 슬라이드와 생성 스크립트 (아래) |

## 보조자료/

| 파일 | 무엇 |
|---|---|
| `지식그래프_집계_비교_2장.pptx` (`kg_slides.py`) | "웹 검색 LLM이면 되지 않나?" 방어용 — 집계 차트 2개(신입 직무가 요구하는 역량 Top 5 · LG 신입 직무와 이어지는 전공 Top 5) + 수치 타일(58/61 · 115k vs 1.4k 토큰 · 챗봇 과목 9개 중 실재 2개), 비교표 7행. `img/집계_차트.png`, `img/검색LLM_비교표.png` 는 렌더 |
| `3장_대체안_아키텍처.pptx` (`slide3.py`) | 최종 덱 3장(Overall Architecture)과 5장(서비스 구조)을 한 장으로 합친 안 — 지도 만들기/읽기 두 띠 + 파일명 + AI/코드 배지 |
| `6장_대체안_AI와_코드.pptx` (`slide6.py`) | 최종 덱 6장(AI & Agent 워크플로우)의 대체안 — 글머리 12줄 대신 "AI 2곳 · 코드 3곳 · 사전이 잇는다" |
| `motif_patch.py` | pptx 의 우상단 모티프를 스키마 모양으로 바꾸는 패치 (`presentation_version2.pptx` 에 적용한 것) |

스크립트는 전부 `python-pptx` 로 도형·차트를 그리므로 PowerPoint 에서 편집 가능. `slide3.py`·`slide6.py` 는 같은 폴더의 `kg_slides.py` 헬퍼를 읽는다.
렌더 확인은 PowerPoint COM(`win32com`) → PDF → PyMuPDF 로 했다 (LibreOffice 없음).
