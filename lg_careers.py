"""
LG Careers 채용공고 수집기 (내부 JSON API 사용)

기존 start.py가 실패한 이유:
    careers.lg.com 은 SPA(Single Page Application)라서
    requests.get() 이 받아오는 HTML 에는 <div id="root"></div> 뿐이고
    실제 공고 내용은 브라우저가 JS 를 실행한 뒤 API 를 호출해 채운다.
    → BeautifulSoup 이 파싱할 텍스트 자체가 없음.

해결:
    화면을 그리는 데 쓰이는 그 API 를 파이썬에서 직접 호출한다.
    HTML 파싱 없이 구조화된 JSON 을 바로 받으므로 더 빠르고 안정적이다.

필요 패키지: pip install requests beautifulsoup4
"""

from __future__ import annotations   # 타입 힌트에서 list[str] 같은 표기를 구버전에서도 허용

import json
from pathlib import Path
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

DATA = Path(__file__).resolve().parent / "data"   # 이 파일이 있는 폴더 기준 → 어디서 실행해도 같은 경로
RAW_DIR = DATA / "raw"                              # 계열사별·날짜별 API 응답 원본. 예: raw/LGES_20260915.json

# 공고는 닫히면 API 에서 사라진다 (실측: CNS 신입 공고가 9/11 → 9/15 사이에 닫혀 13공고 → 12공고).
# 그래서 raw 는 "덮어쓰기" 가 아니라 "날짜별 스냅샷 추가" 다. 같은 계열사를 다시 받으면 새 날짜 파일이 하나 더 생기고,
# transform_v2 가 전부 읽어서 jobNoticeId 로 중복을 없앤다 (같은 공고면 최신 파일 우선).

# ─────────────────────────────────────────────────────────────
# 1) API 기본 설정
# ─────────────────────────────────────────────────────────────

API_BASE = "https://api.careers.lg.com/rmk"

# Origin / Referer 는 브라우저가 자동으로 붙여주는 헤더.
# 서버가 "우리 사이트에서 온 요청인가"를 확인할 수 있으므로 함께 보내준다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Origin": "https://careers.lg.com",
    "Referer": "https://careers.lg.com/",
    "Accept": "application/json",
}


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """API 공통 호출 함수.

    이 사이트의 API 는 전부 POST + JSON body 이고,
    응답은 {"status": "S", "data": {...}} 형태로 한 겹 감싸져 있다.
    status 가 "S"(Success) 가 아니면 data 를 믿으면 안 된다.
    """
    url = f"{API_BASE}{path}"          # f-string: 문자열 안에서 {변수} 를 그대로 치환
    response = requests.post(
        url,
        json=payload,                  # json= 로 주면 requests 가 알아서 직렬화 + 헤더 처리
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()        # 4xx/5xx 면 여기서 예외 발생
    body = response.json()

    if body.get("status") != "S":
        raise RuntimeError(f"API 실패: {body.get('msg')} (payload={payload})")

    return body["data"]


# ─────────────────────────────────────────────────────────────
# 2) 공고 목록 / 상세 조회
# ─────────────────────────────────────────────────────────────

def list_job_notices(company_codes: list[str] | None = None) -> list[dict]:
    """채용공고 목록. company_codes 예: ["CNS"], ["LGE", "LGU"]

    계열사 코드: LGE(전자) LGD(디스플레이) LGIT(이노텍) LGC(화학) LGES(에너지솔루션)
                 LGHH(생활건강) LGU(유플러스) HELLOVISION CNS SVO(스포츠) GIIR
    """
    payload = {
        "lnbSearch": "",               # 검색어
        "hashTagText": "",
        "recDate": "CREATION_DATE",    # 정렬 기준
        "order": "DESC",
        "careerList": [],              # 신입/경력 필터
        "companyCodeList": company_codes or [],
        "desireLocList": [],
        "jobGroupList": [],
    }
    data = api_post("/job/retrieveJobNoticesList", payload)
    return data["jobNoticeList"]


def fetch_job_detail(job_notice_id: str | int) -> dict:
    """공고 상세. job_notice_id 는 상세 URL 의 ?id= 값과 동일하다."""
    data = api_post(
        "/job/retrieveJobNoticesDetail",
        {"jobNoticeId": str(job_notice_id)},   # ← 키 이름이 'id' 가 아니라 'jobNoticeId'
    )
    return data["jobNoticesDetail"]


# ─────────────────────────────────────────────────────────────
# 3) HTML 조각 → 평문 텍스트
# ─────────────────────────────────────────────────────────────

def html_to_text(html: str | None) -> str:
    """API 가 주는 mainTask / requiredItem 등은 에디터가 만든 HTML 조각이다.
    여기서만 BeautifulSoup 을 쓴다 (페이지 전체가 아니라 필드 단위로).
    """
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    text = text.replace("\xa0", " ")             # &nbsp; 제거
    text = re.sub(r"\n{3,}", "\n\n", text)       # 빈 줄 3개 이상 → 2개로 정리
    return text.strip()


def parse_notice(detail: dict) -> list[dict]:
    """상세 응답에서 직무별 추천에 필요한 정보만 추출."""
    notice = detail["jobNoticesDetail"]
    company = notice.get("companyName")
    career_type = notice.get("careerTypeName")
    jobs = [
        {
            "company": company,
            "job_name": rec.get("jobGroupName"),
            "org_intro": html_to_text(rec.get("detailContext")),
            "main_tasks": html_to_text(rec.get("mainTask")),
            "required": html_to_text(rec.get("requiredItem")),
            "preferred": html_to_text(rec.get("preferredItem")),
        }
        for rec in detail.get("recList", [])
    ]
    return jobs


# ─────────────────────────────────────────────────────────────
# 4) 실행 예시
# ─────────────────────────────────────────────────────────────

def collect(company_codes: list[str], stamp: str | None = None) -> list[Path]:
    """계열사별로 공고 상세를 전부 받아 data/raw/{CODE}_{YYYYMMDD}.json 에 저장한다. 저장한 파일 경로 목록을 돌려준다."""
    from datetime import date
    stamp = stamp or date.today().strftime("%Y%m%d")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for code in company_codes:
        raw = []
        for item in list_job_notices(company_codes=[code]):
            raw.append(fetch_job_detail(item["jobNoticeId"]))
            time.sleep(0.5)                   # 요청 간격 (robots 예의)
        out = RAW_DIR / f"{code}_{stamp}.json"
        out.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {code:12} 공고 {len(raw):3}건 → {out.name}")
        saved.append(out)
    return saved


if __name__ == "__main__":
    import sys
    # 사용법:  python lg_careers.py LGES LGU LGD        (계열사 코드를 나열. 생략하면 CNS 를 제외한 전부)
    # 계열사 코드: LGE LGD LGIT LGC LGES LGHH LGU HELLOVISION CNS SVO GIIR
    # ★ CNS 는 기본에서 뺐다 — 9/11 스냅샷(raw/CNS_20260911.json)에 신입 공고 9건이 있고 그 공고는 이미 닫혔다.
    #   CNS 를 다시 받고 싶으면 명시적으로 적는다. 스냅샷은 지우지 않는다.
    codes = sys.argv[1:] or ["LGE", "LGD", "LGIT", "LGC", "LGES", "LGHH", "LGU", "HELLOVISION", "SVO", "GIIR"]
    print(f"수집: {codes}")
    collect(codes)
