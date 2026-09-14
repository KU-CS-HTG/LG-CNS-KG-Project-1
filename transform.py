"""
LG Careers 원본 JSON → 목표 스키마(JobData) 변환 파이프라인

    raw ──①normalize──> staged ──②extract(LLM)──> ③canonicalize ──> ④validate ──> curated

핵심 원칙:
    "LLM은 '문장을 이해해야만 하는 곳'에만 쓴다."
    HTML <li> 분할처럼 규칙으로 되는 일에 LLM을 쓰면 돈·시간·정확도를 모두 잃는다.

필요 패키지: pip install beautifulsoup4 pydantic langchain-openai python-dotenv
"""

from __future__ import annotations
from dotenv import load_dotenv
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Literal

from bs4 import BeautifulSoup, NavigableString
from pydantic import BaseModel, Field, field_validator

# ═════════════════════════════════════════════════════════════
# 0) 목표 스키마 — 여기부터 고정하고 시작한다
# ═════════════════════════════════════════════════════════════

# Literal: "이 필드는 이 값들 중 하나만 허용" 이라는 뜻.
# job_family 를 자유 문자열로 두면 "AI/Data", "AI·데이터", "인공지능" 이 전부
# 다른 노드가 되어 그래프가 터진다. 통제 어휘(controlled vocabulary)로 묶는다.
load_dotenv()
JobFamily = Literal[
    "AI/Data", "Software", "Cloud/Infra", "Security",
    "Consulting/PM", "Sales", "Manufacturing", "Corporate", "Other",
]


class JobData(BaseModel):
    """최종 산출물 1건 = 공고 1개 안의 직무 1개."""

    job_id: str = Field(description="공고ID-직무슬러그. 그래프 노드의 기본키")
    company: str
    job_family: JobFamily
    role: str = Field(description="직무명 (원문 그대로)")
    career_type: Literal["신입", "경력", "인턴", "기타"]
    ncs_code: str | None = Field(default=None, description="NCS 세분류 코드 (별도 매핑 단계)")

    duties: list[str] = Field(default_factory=list, description="주요 업무")
    required: list[str] = Field(default_factory=list, description="필수 역량·기술")
    preferred: list[str] = Field(default_factory=list, description="우대 역량·기술")

    source_url: str
    collected_at: str

    # 품질 메타데이터 — 나중에 "이 데이터 믿어도 되나" 를 판단하는 근거
    duties_source: Literal["mainTask", "detailContext", "none"]
    unmapped_terms: list[str] = Field(default_factory=list)

    @field_validator("duties", "required", "preferred")
    @classmethod
    def drop_empty(cls, v: list[str]) -> list[str]:
        """빈 문자열·공백만 있는 항목 제거. 중복도 제거하되 순서는 유지."""
        seen: set[str] = set()          # set: 중복 검사용 자료구조 (JS의 Set과 동일)
        out = []
        for item in v:
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                out.append(item)
        return out


# ═════════════════════════════════════════════════════════════
# ① NORMALIZE — HTML을 "의미 단위 리스트"로. LLM 안 씀.
# ═════════════════════════════════════════════════════════════

def html_to_lines(html: str | None) -> list[str]:
    """HTML 조각 → 항목 리스트.

    LG Careers 의 requiredItem/preferredItem 은 실제로 이렇게 생겼다:
        <ul><li>고객 문제를 AI 기술로...</li><li>AI 기술을 직접...</li></ul>

    즉 원문이 **이미 리스트**다. 이걸 통째로 LLM에 던져서 "항목으로 쪼개줘" 하는 건
    낭비다. <li>·<p>·<br> 경계를 그대로 살리면 끝난다.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    # <br> 은 태그라서 get_text 로는 사라진다. 줄바꿈 문자로 바꿔 끼운다.
    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))

    lines: list[str] = []

    # <li> 가 있으면 그것이 가장 정확한 항목 경계다.
    items = soup.find_all("li")
    if not items:
        items = soup.find_all(["p", "div"])

    if items:
        for el in items:
            lines.extend(el.get_text(separator="\n").split("\n"))
    else:
        lines.extend(soup.get_text(separator="\n").split("\n"))

    return [clean_text(line) for line in lines if clean_text(line)]


def clean_text(s: str) -> str:
    """&nbsp;, 연속 공백, 앞머리 불릿기호 정리."""
    s = s.replace("\xa0", " ")               # &nbsp; → 일반 공백
    s = re.sub(r"\s+", " ", s)               # 연속 공백/개행 → 공백 하나
    s = re.sub(r"^[-•*·●■]\s*", "", s)   # 맨 앞 불릿 문자 제거
    s = re.sub(r"^\d+[.)]\s*", "", s)        # "1. " "2) " 같은 번호 제거
    return s.strip()


def flatten_notice(detail: dict[str, Any]) -> list[dict[str, Any]]:
    """공고 1건(API 응답) → 직무 N건으로 펼치기 (1:N 언네스팅).

    그래프에서 다루려면 '직무'가 레코드의 단위여야 한다.
    공고 단위로 두면 한 노드 안에 9개 직무가 뭉쳐서 관계를 못 만든다.
    """
    notice = detail["jobNoticesDetail"]
    notice_id = str(notice["jobNoticeId"])
    rows = []

    for rec in detail.get("recList", []):
        # ★ 실제 데이터 확인 결과: LG CNS 공고는 mainTask 가 전부 비어 있고
        #   업무 서술이 detailContext(=조직 소개) 안에 들어 있다.
        #   LG유플러스 공고는 반대로 mainTask 에 들어 있다.
        #   → 어디서 가져왔는지를 반드시 기록해 둔다.
        main_lines = html_to_lines(rec.get("mainTask"))
        ctx_lines = html_to_lines(rec.get("detailContext"))

        if main_lines:
            duty_lines, duties_source = main_lines, "mainTask"
        elif ctx_lines:
            duty_lines, duties_source = ctx_lines, "detailContext"
        else:
            duty_lines, duties_source = [], "none"

        rows.append({
            "job_id": f"{notice_id}-{slugify(rec.get('jobGroupName'))}",
            "company": notice.get("companyName"),
            "role": clean_text(rec.get("jobGroupName") or ""),
            "org": clean_text(rec.get("orgName") or ""),
            "career_type": notice.get("careerTypeName") or "기타",
            "location": rec.get("locationName"),
            "duty_lines": duty_lines,
            "duties_source": duties_source,
            "required_lines": html_to_lines(rec.get("requiredItem")),
            "preferred_lines": html_to_lines(rec.get("preferredItem")),
            "major": " ".join(html_to_lines(rec.get("majorCodeName"))),
            "source_url": f"https://careers.lg.com/apply/detail?id={notice_id}",
            "collected_at": date.today().isoformat(),
        })

    return rows


def slugify(name: str | None) -> str:
    """직무명 → 안전한 ID 조각. 'Cloud Application Modernization' → 'cloud-application-modernization'"""
    s = (name or "unknown").lower()
    s = re.sub(r"[^\w가-힣]+", "-", s)
    return s.strip("-")[:40]


# ═════════════════════════════════════════════════════════════
# ② EXTRACT — 여기서만 LLM. 문장 → 기술·역량 명사
# ═════════════════════════════════════════════════════════════
#
# ①에서 얻은 required_lines 는 이런 모양이다:
#   "생성형 AI(LLM)를 활용한 프로젝트 경험이 있으며 Prompt Engineering, RAG 등 ... 관심이 있는 분"
#
# 사람이 읽으면 기술명이 보이지만, 정규식으로는 못 뽑는다. 이 구간이 LLM의 자리다.

class JobExtraction(BaseModel):
    """LLM이 채울 스키마. 최종 JobData 와 분리해 두는 게 중요하다.
    LLM이 못 채우는 필드(job_id, source_url 등)를 LLM에 맡기면 환각이 섞인다."""

    job_family: JobFamily = Field(description="직무 대분류. 주어진 값 중에서만 선택")
    duties: list[str] = Field(description="주요 업무. 원문 문장을 40자 이내 동사구로 압축")
    required: list[str] = Field(description="필수 역량·기술. 가능한 한 명사 단위 (예: Python, RAG, 데이터 모델링)")
    preferred: list[str] = Field(description="우대 역량·기술. 명사 단위")


EXTRACT_SYSTEM = """너는 채용공고 정제 전문가다.
규칙:
1. 원문에 없는 기술·역량을 절대 추가하지 않는다. 추론·일반화 금지.
2. "~에 관심이 있는 분" 같은 서술은 핵심 명사만 남긴다.
   예: "Git, Docker·Kubernetes 등 형상관리 지식이 있는 분" → ["Git", "Docker", "Kubernetes", "형상관리"]
3. 영문 기술명은 원문 표기를 유지한다. 한국어로 번역하지 않는다.
4. 해당 항목이 원문에 없으면 빈 리스트를 반환한다. 지어내지 않는다."""


def build_extract_chain():
    """LLM 체인 생성. import 를 함수 안에 둬서 LLM 없이도 ①③④ 테스트가 가능하게 한다."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(JobExtraction)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACT_SYSTEM),
        ("human",
         "직무명: {role}\n소속: {org}\n\n"
         "[주요 업무]\n{duties}\n\n"
         "[필수 사항]\n{required}\n\n"
         "[우대 사항]\n{preferred}"),
    ])
    return prompt | structured_llm


def extract_one(chain, row: dict[str, Any]) -> JobExtraction:
    """직무 1건 추출. 실패 시 빈 결과로 폴백해서 파이프라인 전체가 멈추지 않게 한다."""
    payload = {
        "role": row["role"],
        "org": row["org"],
        # 리스트를 번호 붙인 줄글로. LLM이 항목 경계를 헷갈리지 않게 하는 작은 장치.
        "duties": "\n".join(f"- {x}" for x in row["duty_lines"]) or "(없음)",
        "required": "\n".join(f"- {x}" for x in row["required_lines"]) or "(없음)",
        "preferred": "\n".join(f"- {x}" for x in row["preferred_lines"]) or "(없음)",
    }
    try:
        return chain.invoke(payload)
    except Exception as e:
        print(f"  ! 추출 실패 {row['job_id']}: {e}")
        return JobExtraction(job_family="Other", duties=[], required=[], preferred=[])


# ═════════════════════════════════════════════════════════════
# ③ CANONICALIZE — 표기 통일. 이 단계가 없으면 그래프가 쓸모없어진다.
# ═════════════════════════════════════════════════════════════
#
# "파이썬" / "Python" / "python3" 가 서로 다른 노드가 되면
# "Python 쓰는 직무 찾아줘" 쿼리가 3분의 1만 맞힌다.

ALIASES: dict[str, str] = {
    # 표기 변형 → 대표 표기
    "파이썬": "Python", "python3": "Python", "py": "Python",
    "자바": "Java", "자바스크립트": "JavaScript", "js": "JavaScript",
    "쿠버네티스": "Kubernetes", "k8s": "Kubernetes", "도커": "Docker",
    "에스큐엘": "SQL", "sql 쿼리": "SQL",
    "llm": "LLM", "거대언어모델": "LLM", "초거대언어모델": "LLM", "생성형 ai": "LLM",
    "rag": "RAG", "retrieval augmented generation": "RAG",
    "프롬프트 엔지니어링": "Prompt Engineering", "prompt engineering": "Prompt Engineering",
    "랭체인": "LangChain", "langchain": "LangChain", "langgraph": "LangGraph",
    "벡터db": "Vector DB", "vector db": "Vector DB", "벡터 디비": "Vector DB",
    "지식그래프": "Knowledge Graph", "knowledge graph": "Knowledge Graph",
    "그래프db": "Graph DB", "graph db": "Graph DB", "neo4j": "Neo4j",
    "머신러닝": "Machine Learning", "ml": "Machine Learning",
    "딥러닝": "Deep Learning", "dl": "Deep Learning",
    "형상관리": "Version Control", "git": "Git",
    "클라우드": "Cloud", "aws": "AWS", "azure": "Azure", "gcp": "GCP",
    "데이터 모델링": "Data Modeling", "etl": "ETL", "airflow": "Airflow",
}


def canonicalize(terms: list[str]) -> tuple[list[str], list[str]]:
    """(정규화된 용어, 사전에 없던 용어) 를 함께 반환.

    사전에 없는 건 버리지 말고 **모아서 보고**한다.
    그걸 보고 사람이 ALIASES 를 키우는 게 실제 운영 방식이다.
    """
    mapped: list[str] = []
    unknown: list[str] = []

    for t in terms:
        key = clean_text(t).lower()
        if key in ALIASES:
            mapped.append(ALIASES[key])
        else:
            # 사전에 없어도 '짧은 명사'면 그대로 채택, 긴 문장이면 미매핑으로 신고
            original = clean_text(t)
            mapped.append(original)
            if len(original) > 25 or original.endswith("분"):
                unknown.append(original)

    # dict.fromkeys: 순서를 유지하면서 중복 제거하는 관용구
    return list(dict.fromkeys(mapped)), list(dict.fromkeys(unknown))


# ═════════════════════════════════════════════════════════════
# ④ VALIDATE — 환각 검사. LLM을 썼다면 반드시 있어야 하는 단계.
# ═════════════════════════════════════════════════════════════

def check_hallucination(extracted: list[str], source_lines: list[str]) -> list[str]:
    """추출된 용어가 원문에 실제로 등장하는지 확인. 없으면 의심 목록으로 반환.

    ★ 순서가 중요하다: 반드시 **③ 정규화 이전, LLM 원출력**에 대해 검사해야 한다.
      정규화 후에 검사하면 '딥러닝'→'Deep Learning' 변환까지 환각으로 잡혀
      오탐(false positive)이 쏟아진다. (실제로 처음 짰을 때 그렇게 됐다.)
    """
    haystack = " ".join(source_lines).lower()
    suspects = []
    for t in extracted:
        key = clean_text(t).lower()
        # 원문에 그대로 있거나, 동의어(예: '도커'↔'Docker')로 있으면 통과
        candidates = {key, ALIASES.get(key, "").lower()} - {""}
        if not any(c in haystack for c in candidates):
            suspects.append(t)
    return suspects


def to_job_data(row: dict[str, Any], ext: JobExtraction) -> tuple[JobData, dict]:
    """①의 결정론적 결과 + ②의 LLM 결과 → 최종 스키마 조립 및 검증."""
    source_all = row["duty_lines"] + row["required_lines"] + row["preferred_lines"]

    # ④ 먼저 (LLM 원출력 기준) → ③ 나중에
    report = {
        "job_id": row["job_id"],
        "suspect_required": check_hallucination(ext.required, source_all),
        "suspect_preferred": check_hallucination(ext.preferred, source_all),
        "duties_source": row["duties_source"],
    }

    required, unk_r = canonicalize(ext.required)
    preferred, unk_p = canonicalize(ext.preferred)

    job = JobData(
        job_id=row["job_id"],
        company=row["company"],
        job_family=ext.job_family,
        role=row["role"],
        career_type=row["career_type"] if row["career_type"] in ("신입", "경력", "인턴") else "기타",
        ncs_code=None,                        # 별도 매핑 단계에서 채움 (워크넷 표준직무기술서 API)
        duties=ext.duties,
        required=required,
        preferred=preferred,
        source_url=row["source_url"],
        collected_at=row["collected_at"],
        duties_source=row["duties_source"],
        unmapped_terms=unk_r + unk_p,
    )
    return job, report


# ═════════════════════════════════════════════════════════════
# ⑤ RUN — 오케스트레이션
# ═════════════════════════════════════════════════════════════

def run(raw_path: str = "raw_notices.json", out_path: str = "curated_jobs.jsonl") -> None:
    """raw_notices.json = retrieveJobNoticesDetail 응답(data.jobNoticesDetail)의 리스트"""
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))

    # ① 전 공고를 직무 단위로 펼치기
    rows = [row for detail in raw for row in flatten_notice(detail)]
    print(f"① normalize: 공고 {len(raw)}건 → 직무 {len(rows)}건")

    # ② + ③ + ④
    chain = build_extract_chain()
    jobs, reports = [], []
    for i, row in enumerate(rows, 1):
        ext = extract_one(chain, row)
        job, report = to_job_data(row, ext)
        jobs.append(job)
        reports.append(report)
        print(f"  [{i}/{len(rows)}] {job.role} — required {len(job.required)}개")

    # ⑤ JSONL 로 저장 (한 줄에 한 레코드 = 스트리밍·증분 처리에 유리한 표준 포맷)
    with open(out_path, "w", encoding="utf-8") as f:
        for job in jobs:
            f.write(job.model_dump_json() + "\n")

    # 사람이 보기 편한 pretty-print 버전도 함께 저장
    pretty_path = Path(out_path).with_suffix(".pretty.json")
    pretty_path.write_text(
        json.dumps(
            [job.model_dump(mode="json") for job in jobs],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    
    # 품질 리포트 — 눈으로 확인할 것들
    no_duties = [r["job_id"] for r in reports if r["duties_source"] == "none"]
    suspects = [r for r in reports if r["suspect_required"] or r["suspect_preferred"]]
    unmapped = sorted({t for j in jobs for t in j.unmapped_terms})

    print(f"\n④ 품질 리포트")
    print(f"  업무 서술 없음: {len(no_duties)}건 {no_duties[:5]}")
    print(f"  환각 의심: {len(suspects)}건")
    for r in suspects[:5]:
        print(f"    - {r['job_id']}: {r['suspect_required'] + r['suspect_preferred']}")
    print(f"  미매핑 용어 {len(unmapped)}개 → ALIASES에 추가 검토: {unmapped[:10]}")
    print(f"\n저장 완료: {out_path} ({len(jobs)}건)")


if __name__ == "__main__":
    run()
