> 📘 **프로젝트가 처음이면 먼저 [docs/프로젝트-설명서.md](docs/프로젝트-설명서.md) 를 읽어 주세요.**
> 구조 · 데이터 흐름 · 파일별 역할 · 함수 연결 · 점수 계산 · 실행 방법 · Python 문법까지 한 문서에 정리되어 있습니다.

---

*기본 세팅(새로운 기기에서 git 시작하기)

1: git을 설치한다 (pull할때 기본을 merge로 할지, rebase로 할지 고르는 거 있는데 협업 염두하면 merge로 하는 게 좋을듯

2: github에 올리고 싶은 폴더에 우클릭해서 bash 창을 연다 - git init

3: 
git config --global user.email "yyggh337@gmail.com"

git config --global user.name "KU_CS_HTG" 이름과 이메일을 등록

4: github repository를 만들고 주소를 복사해둔다

5: git remote add origin https://github.com/KU-CS-HTG/LG-CNS-KG-Project-1.git
이런 식으로 repository와 연결

6: git remote -v로 잘 연결되었는지 확인

*깃허브 저장소 내용 pull하기(다른 사람이 올려놓은 최신 코드를 먼저 받아오고, 그걸 업데이트해야 각자 사용하는 코드의 버전이 달라지는 것을 막을 수 있음)
git pull origin main

*업데이트한 내용 push하기(자신이 업데이트한 내용을 github에 올려서 이게 최신 버전이라고 다른 팀원들에게 알리기)

1: git에 있는 거(다른 기기에서 repository 업데이트 해놓은 경우) 먼저 pull하고 업데이트해야 함
까먹었다면 일일이 대조하면서 추가된 파일 다 빼놓고 pull할 수밖에 없음

2: git add . 

git commit -m “20260909-2” 이런 식으로 commit message 작성

3: git branch로 현재 branch 확인

main이 아니라면 git branch -M main 

4: git push -u origin main

※환경변수 .env 는 본인 파일을 복사해서 사용하세요.
---

## 폴더 구조 (2026-09-15 정리)

```
LG-CNS-KG-Project-1/
├── data/                       ← 데이터는 전부 여기. 코드에서 DATA / "파일명" 으로 참조
│   ├── subject_cleaned.csv     서울대 교육과정 (학교명·전공명·과목명, UTF-8, 105개 전공)
│   ├── raw_notices.json        LG careers API 응답 원본 (raw 층)      ← lg_careers.py
│   ├── staged_jobs.json        공고 → 직무 단위로 펼친 것 (LLM 없음)   ← transform_v2.py normalize
│   ├── extracted_raw.json      직무별 LLM 원출력 캐시                 ← transform_v2.py extract
│   ├── curated_jobs.jsonl      정규화·검증 결과                       ← transform_v2.py curate
│   ├── majors_extracted.json   전공별 LLM 원출력 캐시                 ← build_graph_majors.py
│   └── graph.json              최종 그래프 (skills / majors / jobs)   ← build_graph_*.py
├── vocab.py                A  통제 어휘 (CANON, canonicalize)
├── build_graph_jobs.py     C  직무 절반 → graph.json
├── build_graph_majors.py   C  전공 절반 → graph.json   (LLM 호출: 전공당 1회)
├── graph_store.py          B  graph.json 조회 함수 (LLM 없음)
├── app.py                  D  온라인 파이프라인 (질문 3개 → 전공·과목·직무)
├── webapp.py               D  위 파이프라인을 감싼 웹 페이지 (Flask)
├── templates/index.html    D  웹 페이지 화면
├── check.py                D  확인 3건
├── lg_careers.py              수집 (완료. 다시 돌릴 일 거의 없음)
├── transform_v2.py            직무 데이터 가공 파이프라인
├── requirements.txt            의존성 목록
└── skeleton.py                walking skeleton (전부 가짜, 흐름 확인용)
```

- 경로는 각 스크립트 위치 기준(`Path(__file__).parent / "data"`)이라 **어느 폴더에서 실행해도 동일**하게 동작합니다.
- LLM 캐시(`extracted_raw.json`, `majors_extracted.json`)는 **커밋 대상**입니다. 공유하면 다른 사람은 LLM을 다시 부르지 않아도 됩니다. 재추출이 필요할 때만 지웁니다.
- 실행 순서: `lg_careers.py` → `transform_v2.py normalize / extract / curate` → `build_graph_jobs.py` → `build_graph_majors.py sample` (눈으로 확인) → `build_graph_majors.py` → `app.py` / `check.py`

## 웹 페이지로 실행하기

```
pip install -r requirements.txt
python webapp.py
```

`http://localhost:5000` 접속. `app.py`(CLI)와 완전히 같은 로직(`run` / `render` / `explain_stream`)을 그대로 불러 쓰므로, 질문 흐름·전공/직무 판정·[진로 추천] 문단이 동일합니다. `.env`에 `OPENAI_API_KEY`가 있어야 합니다.
