"""
LG Careers 변환 파이프라인 v2

v1에서 바뀐 것:
  1. 단계를 파일로 끊었다 — raw / staged / extracted / curated 4개 산출물.
     LLM 호출 결과(extracted)를 파일로 남기므로, ALIASES를 고쳐도 LLM을 다시 부르지 않는다.
  2. required 를 4갈래로 쪼갰다 — skills / soft_skills / qualifications.
     v1 결과에서 "비자 발급 결격 사유 없음"이 최다 빈출 스킬이 되는 사고가 났다.
  3. canonicalize 가 문장을 통과시키지 않는다 (신고 후 제외).
  4. 대소문자 통일 — 'Java'와 'JAVA'가 별도 노드가 되던 문제.
  5. role_key 추가 — 같은 직무가 여러 공고에 나오므로 (:Role) 노드를 따로 세울 준비.

실행:
    python transform_v2.py normalize    # raw_notices.json  → staged_jobs.json      (LLM 안 씀)
    python transform_v2.py extract      # staged_jobs.json  → extracted_raw.json    (LLM, 캐시됨)
    python transform_v2.py curate       # extracted_raw.json→ curated_jobs.jsonl    (LLM 안 씀)
    python transform_v2.py all          # 위 셋을 순서대로
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Literal

from bs4 import BeautifulSoup, NavigableString
from pydantic import BaseModel, Field, field_validator

DATA = Path(__file__).resolve().parent / "data"   # 이 파일이 있는 폴더 기준 → 어디서 실행해도 같은 경로
RAW_DIR = DATA / "raw"                     # 계열사별·날짜별 스냅샷 {CODE}_{YYYYMMDD}.json — lg_careers.py 가 만든다
STAGED = DATA / "staged_jobs.json"
EXTRACTED = DATA / "extracted_raw.json"
CURATED = DATA / "curated_jobs.jsonl"

# ═════════════════════════════════════════════════════════════
# 0) 스키마
# ═════════════════════════════════════════════════════════════

JobFamily = Literal[
    "AI/Data", "Software", "Cloud/Infra", "Security", "Robotics/Automation",
    "ERP/Package", "Consulting/PM", "Sales/Marketing", "Manufacturing/Logistics",
    "Facility/Engineering", "Corporate", "Other",
]


class JobExtraction(BaseModel):
    """LLM이 채우는 스키마.

    ★ v1의 가장 큰 실수: required 하나에 기술·역량·자격요건을 다 넣었다.
      그 결과 "비자 발급 결격 사유 없음"이 가장 자주 등장하는 '스킬'이 되었다.
      성격이 다른 것은 필드를 나눈다 — 스키마 설계의 기본이다.
    """

    job_family: JobFamily = Field(description="직무 대분류. 주어진 값 중에서만 선택")
    duties: list[str] = Field(description="주요 업무. 최대 8개. 각 40자 이내 동사구. 기술명 나열 금지")

    required_skills: list[str] = Field(description="필수 기술·도구·방법론. 명사만 (예: Python, Kubernetes, MSA)")
    preferred_skills: list[str] = Field(description="우대 기술·도구·방법론. 명사만")
    soft_skills: list[str] = Field(description="비기술 역량 (예: 커뮤니케이션, 문제해결, 리더십)")
    qualifications: list[str] = Field(description="자격요건: 경력연수·학력·자격증·비자 등. 기술명은 여기 넣지 않는다")
    domains: list[str] = Field(description="업무 도메인 (예: 금융, 공공, 제조, 물류)")


class JobData(BaseModel):
    """최종 산출물 1건 = 공고 1개 안의 직무 1개."""

    job_id: str = Field(description="공고ID-직무슬러그. (:JobPosting)-[:OFFERS]->(:Role) 의 간선 키")
    role_key: str = Field(description="회사+직무명 기준 키. 여러 공고에 같은 직무가 나오므로 (:Role) 노드의 기본키")
    company: str
    job_family: JobFamily
    role: str
    career_type: Literal["신입", "경력", "인턴", "기타"]
    ncs_code: str | None = None

    duties: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)

    source_url: str
    collected_at: str

    duties_source: Literal["mainTask", "detailContext", "none"]
    dropped_terms: list[str] = Field(default_factory=list, description="문장이라 제외된 항목")
    suspect_terms: list[str] = Field(default_factory=list, description="원문에 없어 환각 의심")

    @field_validator("duties", "required_skills", "preferred_skills",
                     "soft_skills", "qualifications", "domains")
    @classmethod
    def dedup(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out = []
        for item in v:
            item = item.strip()
            k = item.lower()
            if item and k not in seen:
                seen.add(k)
                out.append(item)
        return out


# ═════════════════════════════════════════════════════════════
# ① NORMALIZE
# ═════════════════════════════════════════════════════════════

def html_to_lines(html: str | None) -> list[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))

    items = soup.find_all("li") or soup.find_all(["p", "div"])
    lines: list[str] = []
    if items:
        for el in items:
            lines.extend(el.get_text(separator="\n").split("\n"))
    else:
        lines.extend(soup.get_text(separator="\n").split("\n"))
    return [c for c in (clean_text(x) for x in lines) if c]


def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^[-•*·●■]\s*", "", s)
    s = re.sub(r"^\d+[.)]\s*", "", s)
    return s.strip()


def slugify(name: str | None) -> str:
    s = (name or "unknown").lower()
    s = re.sub(r"[^\w가-힣]+", "-", s)
    return s.strip("-")[:40]


def flatten_notice(detail: dict[str, Any]) -> list[dict[str, Any]]:
    notice = detail["jobNoticesDetail"]
    notice_id = str(notice["jobNoticeId"])
    company = notice.get("companyName") or ""
    rows = []

    for rec in detail.get("recList", []):
        main_lines = html_to_lines(rec.get("mainTask"))
        ctx_lines = html_to_lines(rec.get("detailContext"))
        if main_lines:
            duty_lines, src = main_lines, "mainTask"
        elif ctx_lines:
            duty_lines, src = ctx_lines, "detailContext"
        else:
            duty_lines, src = [], "none"

        role = clean_text(rec.get("jobGroupName") or "")
        rows.append({
            "job_id": f"{notice_id}-{slugify(role)}",
            # ★ role_key: 공고가 달라도 같은 직무면 같은 키.
            #   실측 결과 'Robotics (RX)', 'DX Engineer', 'ERP' 등 5개 직무가
            #   서로 다른 공고에 중복 등장했다. 이걸 구분하지 않으면
            #   그래프에서 같은 직무가 여러 노드로 쪼개진다.
            "role_key": f"{slugify(company)}--{slugify(role)}",
            "company": company,
            "role": role,
            "org": clean_text(rec.get("orgName") or ""),
            "career_type": notice.get("careerTypeName") or "기타",
            "duty_lines": duty_lines,
            "duties_source": src,
            "required_lines": html_to_lines(rec.get("requiredItem")),
            "preferred_lines": html_to_lines(rec.get("preferredItem")),
            "source_url": f"https://careers.lg.com/apply/detail?id={notice_id}",
            "collected_at": date.today().isoformat(),
        })
    return rows


def load_raw() -> list[dict[str, Any]]:
    """data/raw/*.json 을 전부 읽어 공고 목록으로 합친다. 같은 jobNoticeId 는 파일명 날짜가 늦은 쪽을 쓴다.

    파일명 규칙 {CODE}_{YYYYMMDD}.json 덕에 정렬만으로 '최신 우선' 이 된다.
    닫힌 공고(예: CNS 9/11 신입)는 옛 스냅샷에만 있으므로 그대로 살아남는다 — 스냅샷을 지우지 않는 이유.
    """
    files = sorted(RAW_DIR.glob("*.json"))          # 이름순 = 날짜순 (같은 계열사 안에서)
    if not files:
        raise FileNotFoundError(f"{RAW_DIR} 에 raw 스냅샷이 없다. 먼저 lg_careers.py 를 실행")
    by_id: dict[str, dict[str, Any]] = {}
    for f in files:
        for d in json.loads(f.read_text(encoding="utf-8")):
            by_id[str(d["jobNoticesDetail"]["jobNoticeId"])] = d     # 뒤(=최신)가 덮어쓴다
        print(f"   raw: {f.name}")
    return list(by_id.values())


def run_normalize() -> None:
    raw = load_raw()
    rows = [r for d in raw for r in flatten_notice(d)]
    STAGED.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    by_company = Counter(r["company"] for r in rows)
    print(f"① normalize: 공고 {len(raw)}건 → 직무 {len(rows)}건 → {STAGED}")
    print("   회사별 직무:", dict(by_company))


# ═════════════════════════════════════════════════════════════
# ② EXTRACT (LLM) — 캐시 있음
# ═════════════════════════════════════════════════════════════

EXTRACT_SYSTEM = """너는 채용공고 정제 전문가다. 아래 규칙을 엄격히 지켜라.

[필드 구분 — 가장 중요]
- required_skills / preferred_skills: **기술·도구·방법론의 이름만.** 명사구.
  예: Python, Kubernetes, MSA, Spring Boot, Data Modeling
- soft_skills: 비기술 역량. 예: 커뮤니케이션, 문제해결, 리더십
- qualifications: 경력 연수·학력·자격증·비자·거주요건.
  예: "경력 5년 이상", "정보처리기사", "비자 발급 결격 사유 없음"
- domains: 산업/업무 도메인. 예: 금융, 공공, 제조, 물류, 보험

"경력 3년 이상" 을 skills 에 넣지 마라. "커뮤니케이션 역량" 을 skills 에 넣지 마라.

[일반 규칙]
1. 원문에 없는 내용을 추가하지 않는다. 추론·일반화 금지.
2. 문장을 그대로 옮기지 말고 핵심 명사만 남긴다.
   "Git, Docker·Kubernetes 등 형상관리 지식이 있는 분"
   → required_skills: ["Git", "Docker", "Kubernetes"], soft_skills: []
3. 영문 기술명은 원문 표기를 유지한다. 한국어로 번역하지 않는다.
4. duties 는 최대 8개. 원문이 "설계/구축/운영/컨설팅" 처럼 나열되어 있으면
   조합을 다 펼치지 말고 대표 동사구로 묶는다.
5. 해당 항목이 원문에 없으면 빈 리스트. 지어내지 않는다."""


def build_chain():
    from dotenv import load_dotenv
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    load_dotenv()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACT_SYSTEM),
        ("human",
         "직무명: {role}\n소속: {org}\n채용구분: {career_type}\n\n"
         "[업무 서술]\n{duties}\n\n[필수 사항]\n{required}\n\n[우대 사항]\n{preferred}"),
    ])
    return prompt | llm.with_structured_output(JobExtraction)


def run_extract() -> None:
    rows = json.loads(STAGED.read_text(encoding="utf-8"))

    # 캐시: 이미 뽑은 job_id 는 건너뛴다.
    # LLM 호출이 이 파이프라인의 유일한 유료 구간이다. 중간에 끊겨도 이어서 돌 수 있게.
    cache: dict[str, dict] = {}
    if EXTRACTED.exists():
        cache = json.loads(EXTRACTED.read_text(encoding="utf-8"))
        print(f"② 캐시 {len(cache)}건 발견 — 건너뜀")

    chain = build_chain()
    for i, row in enumerate(rows, 1):
        jid = row["job_id"]
        if jid in cache:
            continue
        payload = {
            "role": row["role"], "org": row["org"], "career_type": row["career_type"],
            "duties": "\n".join(f"- {x}" for x in row["duty_lines"]) or "(없음)",
            "required": "\n".join(f"- {x}" for x in row["required_lines"]) or "(없음)",
            "preferred": "\n".join(f"- {x}" for x in row["preferred_lines"]) or "(없음)",
        }
        try:
            cache[jid] = chain.invoke(payload).model_dump()
            print(f"  [{i}/{len(rows)}] {row['role']}")
        except Exception as e:
            print(f"  ! 실패 {jid}: {e}")
            cache[jid] = JobExtraction(
                job_family="Other", duties=[], required_skills=[], preferred_skills=[],
                soft_skills=[], qualifications=[], domains=[],
            ).model_dump()
        # 한 건 끝날 때마다 저장 — 중간에 죽어도 여기까지는 남는다
        EXTRACTED.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"② extract: {len(cache)}건 → {EXTRACTED}")


# ═════════════════════════════════════════════════════════════
# ③ CANONICALIZE + ④ VALIDATE
# ═════════════════════════════════════════════════════════════

ALIASES: dict[str, str] = {
    "파이썬": "Python", "python3": "Python", "py": "Python",
    "자바": "Java", "java": "Java",                      # ← 'JAVA' 표기 통일
    "자바스크립트": "JavaScript", "javascript": "JavaScript", "js": "JavaScript",
    "node.js": "Node.js", "nodejs": "Node.js",
    "쿠버네티스": "Kubernetes", "k8s": "Kubernetes", "kubernetes": "Kubernetes",
    "도커": "Docker", "docker": "Docker",
    "에스큐엘": "SQL", "sql": "SQL", "oracle": "Oracle",
    "llm": "LLM", "거대언어모델": "LLM", "초거대언어모델": "LLM", "생성형 ai": "LLM",
    "rag": "RAG", "프롬프트 엔지니어링": "Prompt Engineering", "prompt engineering": "Prompt Engineering",
    "랭체인": "LangChain", "langchain": "LangChain", "langgraph": "LangGraph",
    "벡터db": "Vector DB", "vector db": "Vector DB",
    "지식그래프": "Knowledge Graph", "knowledge graph": "Knowledge Graph",
    "그래프db": "Graph DB", "neo4j": "Neo4j",
    "머신러닝": "Machine Learning", "ml": "Machine Learning",
    "딥러닝": "Deep Learning", "dl": "Deep Learning",
    "git": "Git", "svn": "SVN", "형상관리": "Version Control",
    "클라우드": "Cloud", "cloud": "Cloud", "aws": "AWS", "azure": "Azure", "gcp": "GCP",
    "데이터 모델링": "Data Modeling", "data modeling": "Data Modeling",
    "etl": "ETL", "airflow": "Airflow", "kafka": "Kafka",
    "msa": "MSA", "devops": "DevOps", "cicd": "CI/CD", "ci/cd": "CI/CD",
    "react": "React", "vue.js": "Vue.js", "vue": "Vue.js", "angularjs": "AngularJS",
    "spring boot": "Spring Boot", "springboot": "Spring Boot", "spring": "Spring",
    "terraform": "Terraform", "jenkins": "Jenkins", "argocd": "ArgoCD",
    "sap": "SAP", "abap": "ABAP", "fiori": "Fiori", "salesforce": "Salesforce",
}

# 기술명이 아닌 것을 걸러내는 신호어.
# "역량/경험자/년 이상" 같은 말이 붙어 있으면 그건 이름이 아니라 문장이다.
NOT_A_SKILL = re.compile(
    r"(경험자|경력|년 이상|결격|졸업|우대|의지|희망|관심|가능자|보유자|필요|이해도|"
    r"역량|능력|태도|마인드|열정|분$|자$|"
    r"경험$|이해$|지식$|수행$|활용$|적용$|해결$|관리$|개선$)"      # 서술형 꼬리
)


def canonicalize(terms: list[str]) -> tuple[list[str], list[str]]:
    """(정규화된 기술명, 제외된 항목)

    ★ 연습문제의 답: 사전에 없다고 무조건 버리면 안 된다.
      Spring Boot, Terraform, MSA 처럼 사전에 없지만 살려야 할 이름이 훨씬 많다.
      '문장인가'를 따져서 분기한다.
    """
    mapped: list[str] = []
    dropped: list[str] = []

    for t in terms:
        original = clean_text(t)
        if not original:
            continue
        key = original.lower()

        if key in ALIASES:
            mapped.append(ALIASES[key])          # 사전에 있으면 대표 표기로
        elif len(original) > 25 or NOT_A_SKILL.search(original):
            dropped.append(original)             # 문장이면 제외 + 신고
        else:
            mapped.append(original)              # 사전에 없는 짧은 이름은 그대로 채택

    return list(dict.fromkeys(mapped)), list(dict.fromkeys(dropped))


def check_hallucination(terms: list[str], source_lines: list[str]) -> list[str]:
    """LLM 원출력이 원문에 실제로 있는지. ③ 정규화 전에 돌려야 오탐이 없다."""
    haystack = " ".join(source_lines).lower()
    out = []
    for t in terms:
        key = clean_text(t).lower()
        candidates = {key, ALIASES.get(key, "").lower()} - {""}
        if not any(c in haystack for c in candidates):
            out.append(t)
    return out


def run_curate() -> None:
    rows = json.loads(STAGED.read_text(encoding="utf-8"))
    extracted = json.loads(EXTRACTED.read_text(encoding="utf-8"))

    jobs: list[JobData] = []
    for row in rows:
        ext = JobExtraction(**extracted[row["job_id"]])
        source_all = row["duty_lines"] + row["required_lines"] + row["preferred_lines"]

        # ④ 먼저 (LLM 원출력 기준)
        suspect = (check_hallucination(ext.required_skills, source_all)
                   + check_hallucination(ext.preferred_skills, source_all))

        # ③ 그 다음
        req, drop_r = canonicalize(ext.required_skills)
        pref, drop_p = canonicalize(ext.preferred_skills)

        jobs.append(JobData(
            job_id=row["job_id"], role_key=row["role_key"], company=row["company"],
            job_family=ext.job_family, role=row["role"],
            career_type=row["career_type"] if row["career_type"] in ("신입", "경력", "인턴") else "기타",
            duties=ext.duties, required_skills=req, preferred_skills=pref,
            soft_skills=ext.soft_skills, qualifications=ext.qualifications, domains=ext.domains,
            source_url=row["source_url"], collected_at=row["collected_at"],
            duties_source=row["duties_source"],
            dropped_terms=drop_r + drop_p, suspect_terms=suspect,
        ))

    with CURATED.open("w", encoding="utf-8") as f:
        for j in jobs:
            f.write(j.model_dump_json() + "\n")

    report(jobs)
    print(f"\n③④ curate: {len(jobs)}건 → {CURATED}")


def report(jobs: list[JobData]) -> None:
    """품질 리포트 — 다음 단계로 갈지 판단하는 근거."""
    from collections import Counter, defaultdict

    skills = Counter(s for j in jobs for s in j.required_skills + j.preferred_skills)
    once = sum(1 for v in skills.values() if v == 1)

    fam_by_role = defaultdict(set)
    for j in jobs:
        fam_by_role[j.role_key].add(j.job_family)
    inconsistent = {k: v for k, v in fam_by_role.items() if len(v) > 1}

    print("\n── 품질 리포트 ──")
    print(f"  skill 고유 {len(skills)}개 / 1회만 등장 {once}개 ({once / max(len(skills), 1) * 100:.0f}%)")
    print(f"    ↑ 이 비율이 70%를 넘으면 그래프가 거의 연결되지 않는다. 60% 이하를 목표로.")
    print(f"  상위 10: {[s for s, _ in skills.most_common(10)]}")
    print(f"  같은 role_key인데 job_family 불일치: {len(inconsistent)}건 {list(inconsistent)[:3]}")
    print(f"  환각 의심: {sum(1 for j in jobs if j.suspect_terms)}건")
    print(f"  duties 0개: {[j.job_id for j in jobs if not j.duties]}")
    dropped = sorted({t for j in jobs for t in j.dropped_terms})
    print(f"  문장이라 제외됨: {len(dropped)}개 (예: {dropped[:3]})")


# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("normalize", "all"):
        run_normalize()
    if cmd in ("extract", "all"):
        run_extract()
    if cmd in ("curate", "all"):
        run_curate()
