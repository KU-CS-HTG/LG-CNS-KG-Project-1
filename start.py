#pip install requests beautifulsoup4 필요


#url 입력하면 그 웹페이지에 있는 단어들 전부 크롤링하는 코드
import requests
from bs4 import BeautifulSoup

#Python으로 웹페이지 가져오기
def fetch_page(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )
    response.raise_for_status()
    return response.text

#HTML에서 텍스트만 추출
def extract_text(html: str) -> str:
    soup = BeautifulSoup(
        html,
        "html.parser"
    )
    # 필요 없는 태그 제거
    for tag in soup([
        "script",
        "style",
        "noscript"
    ]):
        tag.decompose()
    text = soup.get_text(
        separator="\n",
        strip=True
    )
    return text

url = "https://www.lgcns.com/kr/careers/jobs/AI"
html = fetch_page(url)
text = extract_text(html)
# print(text[:5000])



#LLM을 활용하여 그 텍스트들 중에서 쓸만한 것들만 JobData class 형태로 추리기
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

load_dotenv()

class JobData(BaseModel):
    job_name: str = Field(
        description="직무명"
    )
    summary: str = Field(
        description="직무를 한 문장으로 요약"
    )
    main_tasks: List[str] = Field(
        description="주요 업무"
    )
    technology: List[str] = Field(
        description="사용하거나 다루는 기술"
    )
    sub_roles: List[str] = Field(
        description="직무 안에서 수행할 수 있는 세부 역할"
    )
    work_domains: List[str] = Field(
        description="업무 영역"
    )
    related_skills: List[str] = Field(
        description="직무 수행에 필요한 역량"
    )
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)
structured_llm = llm.with_structured_output(
    JobData
)

prompt = f"""
너는 기업 채용 데이터 정제 전문가다.

다음은 LG CNS 공식 직무소개 페이지에서
추출한 텍스트다.

이 텍스트를 JobData Schema에 맞춰 구조화하라.

규칙:
1. 원문에 없는 정보를 추가하지 않는다.
2. 기술명은 가능한 한 명확한 명사로 작성한다.
3. 주요 업무와 기술을 구분한다.
4. 직무와 직접 관련된 정보만 추출한다.
5. 불확실한 정보는 추측하지 않는다.

[원문] {text}
"""
job = structured_llm.invoke(prompt)

print(job)