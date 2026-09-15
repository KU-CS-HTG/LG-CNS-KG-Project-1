"""
vocab.py — 통제 어휘집 (담당: A)

transform_v2.py 의 ALIASES + NOT_A_SKILL 을 계약 시그니처에 맞춰 옮긴 것.
설계서 4절 계약:  CANON: dict[str, str]  /  canonicalize(term: str) -> str | None

★ 이 파일이 프로젝트에서 가장 중요한 파일이다.
  전공 쪽과 직무 쪽이 같은 어휘를 쓸 때만 그래프가 이어진다.
  A 혼자 관리하고, 다른 사람은 PR로만 건드린다.

목표 규모: 40~60개 태그 (설계서 6절 월요일 과제)
  - 너무 많으면 겹치는 역량이 없어서 추천 결과가 0개가 된다
  - 너무 적으면 모든 전공이 같은 태그를 받아 변별력이 없다
"""

from __future__ import annotations

import re

# ═════════════════════════════════════════════════════════════
# CANON — 표기 변형(소문자) → 대표 표기
# ═════════════════════════════════════════════════════════════
# 키는 반드시 소문자. canonicalize() 가 .lower() 로 조회한다.
# 'Java' 와 'JAVA' 가 별도 노드가 되던 문제를 이걸로 막는다.

CANON: dict[str, str] = {
    # ── 프로그래밍 언어
    "파이썬": "Python", "python": "Python", "python3": "Python",
    "자바": "Java", "java": "Java",
    "자바스크립트": "JavaScript", "javascript": "JavaScript", "js": "JavaScript",
    "타입스크립트": "TypeScript", "typescript": "TypeScript",
    "c": "C", "c++": "C++", "c#": "C#",

    # ── 데이터 · DB
    "sql": "SQL", "에스큐엘": "SQL",
    "오라클": "Oracle", "oracle": "Oracle",
    "데이터 모델링": "Data Modeling", "data modeling": "Data Modeling", "데이터모델링": "Data Modeling",
    "데이터베이스": "Database", "database": "Database", "db": "Database",
    "etl": "ETL", "airflow": "Airflow", "kafka": "Kafka",
    "데이터 분석": "Data Analysis", "데이터분석": "Data Analysis", "통계": "Statistics",

    # ── AI
    "머신러닝": "Machine Learning", "ml": "Machine Learning", "기계학습": "Machine Learning",
    "딥러닝": "Deep Learning", "dl": "Deep Learning",
    "llm": "LLM", "생성형 ai": "LLM", "거대언어모델": "LLM", "초거대언어모델": "LLM",
    "rag": "RAG", "프롬프트 엔지니어링": "Prompt Engineering", "prompt engineering": "Prompt Engineering",
    "랭체인": "LangChain", "langchain": "LangChain", "langgraph": "LangGraph",
    "자연어처리": "NLP", "nlp": "NLP",
    "컴퓨터비전": "Computer Vision", "computer vision": "Computer Vision",

    # ── 그래프 · 지식
    "지식그래프": "Knowledge Graph", "knowledge graph": "Knowledge Graph",
    "그래프db": "Graph DB", "neo4j": "Neo4j",
    "온톨로지": "Ontology", "ontology": "Ontology",

    # ── 웹 · 백엔드
    "react": "React", "리액트": "React",
    "vue": "Vue.js", "vue.js": "Vue.js", "angularjs": "AngularJS",
    "spring": "Spring", "spring boot": "Spring Boot", "springboot": "Spring Boot",
    "node.js": "Node.js", "nodejs": "Node.js",
    "msa": "MSA", "마이크로서비스": "MSA",

    # ── 인프라 · 클라우드
    "클라우드": "Cloud", "cloud": "Cloud",
    "aws": "AWS", "azure": "Azure", "gcp": "GCP",
    "도커": "Docker", "docker": "Docker",
    "쿠버네티스": "Kubernetes", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "devops": "DevOps", "ci/cd": "CI/CD", "cicd": "CI/CD",
    "terraform": "Terraform", "jenkins": "Jenkins",
    "네트워크": "Network", "network": "Network",
    "보안": "Security", "정보보안": "Security", "security": "Security",

    # ── 협업 · 방법론
    "git": "Git", "형상관리": "Version Control", "svn": "SVN",
    "agile": "Agile", "애자일": "Agile", "scrum": "Agile",

    # ── 학문 역량 (전공 과목명에서 나온다 — 컴공·전기정보·수리과학 과목이 실제로 가리키는 것들.
    #    LG CNS 신입 공고에도 등장하는 말이라 직무 쪽과 이어질 수 있다)
    "프로그래밍": "Programming", "programming": "Programming", "코딩": "Programming",   # 언어 무관 상위 개념 (PARENT 참고)
    "알고리즘": "Algorithm", "algorithm": "Algorithm",
    "자료구조": "Data Structure", "data structure": "Data Structure",
    "운영체제": "Operating Systems", "os": "Operating Systems", "operating systems": "Operating Systems",
    "컴퓨터구조": "Computer Architecture", "컴퓨터조직론": "Computer Architecture", "computer architecture": "Computer Architecture",
    "소프트웨어공학": "Software Engineering", "software engineering": "Software Engineering",
    "최적화": "Optimization", "optimization": "Optimization",
    "신호처리": "Signal Processing", "디지털신호처리": "Signal Processing", "signal processing": "Signal Processing",
    "수치해석": "Numerical Analysis", "수리모델링": "Numerical Analysis", "numerical analysis": "Numerical Analysis",

    # ── 기존 대표 표기의 별칭 보강 (2단계, 2026-09-15 canon_candidates.txt 2회 이상 119개 검토)
    "data 분석": "Data Analysis", "big data": "Data Analysis", "빅데이터": "Data Analysis",
    "빅데이터 기반 예측 모델링": "Machine Learning", "ai": "Machine Learning", "인공지능": "Machine Learning",
    "public cloud": "Cloud", "hybrid cloud": "Cloud", "cloud infrastructure": "Cloud", "container": "Cloud",
    "iac": "Cloud", "serverless": "Cloud", "virtualization": "Cloud", "가상화": "Cloud",
    "최적화 방법론": "Optimization", "최적화 기법": "Optimization",
    "알고리즘 개발": "Algorithm",
    "실험계획법": "Statistics", "통계 분석": "Statistics",
    "postgresql": "PostgreSQL", "r": "R", "minitab": "minitab", "jmp": "JMP",
    "pytorch": "PyTorch", "tensorflow": "TensorFlow", "matlab": "MATLAB", "vba": "VBA",

    # ── 2단계 클러스터 ① 배터리·화학·재료 (LGES·LGC 직무 ↔ 화학부·화학생물공학부·재료공학부)
    "전기화학": "Electrochemistry", "전기 화학": "Electrochemistry", "배터리": "Electrochemistry",
    "bms": "BMS",
    "화학": "Chemical Engineering", "화학공학": "Chemical Engineering", "화학 공학": "Chemical Engineering",
    "재료공학": "Materials Engineering", "소재": "Materials Engineering", "고분자 소재": "Materials Engineering",
    "원소재 개발": "Materials Engineering", "재료": "Materials Engineering",
    "유변학": "Rheology", "sem": "SEM",

    # ── 2단계 클러스터 ② 기계·설계·시뮬레이션·전기 HW (LGES·LGD·LGE 직무 ↔ 기계·전기정보·조선해양)
    "기계공학": "Mechanical Engineering", "기계 공학": "Mechanical Engineering", "기계": "Mechanical Engineering",
    "메카트로닉스": "Mechanical Engineering",
    "기구설계": "Mechanical Design", "3d 설계": "Mechanical Design", "3d cad": "Mechanical Design", "cad": "Mechanical Design",
    "3d 설계 tool": "Mechanical Design", "설계최적화": "Mechanical Design",
    "catia": "CATIA", "creo": "Creo", "solidworks": "SolidWorks", "autocad": "AutoCAD", "inventor": "Inventor",
    "시뮬레이션": "Simulation", "cae": "Simulation", "simulator": "Simulation",
    "simulink": "Simulink", "fdtd": "FDTD", "speos": "SPEOS", "lighttools": "LightTools", "setfos": "Setfos",
    "전기": "Electrical Engineering", "전기공학": "Electrical Engineering", "전기 공학": "Electrical Engineering",
    "전자공학": "Electrical Engineering", "전자 공학": "Electrical Engineering",
    "회로 설계": "Electrical Engineering", "회로설계": "Electrical Engineering", "display 제품 회로 설계": "Electrical Engineering",
    "회로 시뮬레이션 tool": "Electrical Engineering",
    "smartspice": "SmartSpice", "cadence spectre": "Cadence Spectre",

    # ── 2단계 클러스터 ③ 로봇·생산·ERP (LGES 공정/설비, CNS Robotics·ERP ↔ 산업공학·기계·경영)
    "로봇 제어": "Robotics", "robotics sw": "Robotics", "로봇팔": "Robotics", "robotics": "Robotics",
    "ros": "ROS", "ros2": "ROS2", "자율주행": "Autonomous Driving", "plc 제어": "PLC", "amr": "AMR",
    "공정기술": "Manufacturing", "생산운영": "Manufacturing", "설비": "Manufacturing", "smart factory": "Manufacturing",
    "생산기술": "Manufacturing", "제조": "Manufacturing", "manufacturing": "Manufacturing",
    "디지털 트윈": "Digital Twin", "digital twin": "Digital Twin",
    "erp": "ERP", "sap": "SAP", "s/4hana": "S/4HANA", "s/4hana public cloud": "S/4HANA", "s/4hana cloud private": "S/4HANA",
    "fiori": "Fiori", "abap": "ABAP",

    # ── 비기술 역량 (전공 쪽에서 자주 나온다)
    "커뮤니케이션": "Communication", "의사소통": "Communication",
    "문제해결": "Problem Solving", "문제 해결": "Problem Solving",
    "프로젝트관리": "Project Management", "프로젝트 관리": "Project Management", "pm": "Project Management",
}

# ═════════════════════════════════════════════════════════════
# PARENT — IS_A 계층 (한 단계). 직무 쪽 도구·제품명 → 전공 쪽 학문·개념명
# ═════════════════════════════════════════════════════════════
# 왜 필요한가 (2026-09-15 실측): 직무 쪽 상위 역량은 Java·React·Cloud·MSA·Kubernetes(도구 이름),
#   전공 쪽 상위 역량은 Data Analysis·Statistics·Algorithm·Database(학문 이름). 글자가 같아야 이어지는
#   flat 어휘집으로는 공통 Skill 이 8개에서 멈춘다. "Oracle 은 Database 의 한 종류" 를 데이터로 적어 두면
#   전공의 Database 가 직무의 Oracle 과 이어진다. 이게 온톨로지의 가장 기본 관계 IS_A (rdfs:subClassOf, skos:broader).
#
# 규칙 세 가지
#   ① 한 단계만. Programming → Computer Science → IT 처럼 두 단계 올리면 모든 전공이 모든 직무와 이어져 변별력 0.
#   ② 상위 개념도 과목명에서 근거를 댈 수 있는 단어여야 한다 (Database 는 '데이터베이스' 과목이 있고, IT 는 없다).
#   ③ 추론은 위로만 흐른다. 직무가 Oracle 을 요구하면 "Database 계열을 요구" 로 일반화(참).
#      전공이 Database 를 가르친다고 "Oracle 을 가르친다" 로 구체화하면 환각. graph_store 가 이 방향을 지킨다.
#
# 키·값 모두 CANON 의 대표 표기여야 한다 (아래 assert 가 오타를 잡는다 — 오타 나면 엣지가 조용히 사라지므로).

PARENT: dict[str, str] = {
    # 데이터베이스 계열
    "Oracle": "Database", "SQL": "Database", "Data Modeling": "Database",
    "Graph DB": "Database", "Neo4j": "Database",
    # 클라우드·인프라 계열
    "AWS": "Cloud", "Azure": "Cloud", "GCP": "Cloud", "Docker": "Cloud", "Kubernetes": "Cloud",
    "DevOps": "Cloud", "CI/CD": "Cloud", "Terraform": "Cloud", "Jenkins": "Cloud",
    # 프로그래밍 언어 → Programming
    "Java": "Programming", "Python": "Programming", "JavaScript": "Programming", "TypeScript": "Programming",
    "C": "Programming", "C++": "Programming", "C#": "Programming", "Node.js": "Programming",
    # 프레임워크·개발 방법 → Software Engineering
    "React": "Software Engineering", "Vue.js": "Software Engineering", "AngularJS": "Software Engineering",
    "Spring": "Software Engineering", "Spring Boot": "Software Engineering", "MSA": "Software Engineering",
    "Git": "Software Engineering", "SVN": "Software Engineering", "Version Control": "Software Engineering",
    # AI 세부 → Machine Learning
    "Deep Learning": "Machine Learning", "NLP": "Machine Learning", "Computer Vision": "Machine Learning",
    "LLM": "Machine Learning", "RAG": "Machine Learning", "LangChain": "Machine Learning",
    "LangGraph": "Machine Learning", "Prompt Engineering": "Machine Learning",
    # 방법론
    "Agile": "Project Management",

    # ── 2단계 (2026-09-15): 기존 부모에 붙는 도구
    "PyTorch": "Deep Learning", "TensorFlow": "Deep Learning",
    "PostgreSQL": "Database",
    "R": "Statistics", "minitab": "Statistics", "JMP": "Statistics",
    "MATLAB": "Numerical Analysis",
    "VBA": "Programming",
    # ── 2단계 클러스터 ① 배터리·화학·재료
    "BMS": "Electrochemistry",
    "Rheology": "Materials Engineering", "SEM": "Materials Engineering",
    # ── 2단계 클러스터 ② 기계·설계·시뮬레이션·전기 HW
    "CATIA": "Mechanical Design", "Creo": "Mechanical Design", "SolidWorks": "Mechanical Design",
    "AutoCAD": "Mechanical Design", "Inventor": "Mechanical Design",
    "Simulink": "Simulation", "FDTD": "Simulation", "SPEOS": "Simulation", "LightTools": "Simulation", "Setfos": "Simulation",
    "SmartSpice": "Electrical Engineering", "Cadence Spectre": "Electrical Engineering",
    # ── 2단계 클러스터 ③ 로봇·생산·ERP
    "ROS": "Robotics", "ROS2": "Robotics", "Autonomous Driving": "Robotics", "PLC": "Robotics", "AMR": "Robotics",
    "Digital Twin": "Manufacturing",
    "SAP": "ERP", "S/4HANA": "ERP", "Fiori": "ERP", "ABAP": "ERP",
}

_canon_values = set(CANON.values())
_bad = [k for k in PARENT if k not in _canon_values] + [v for v in PARENT.values() if v not in _canon_values]
assert not _bad, f"PARENT 에 CANON 대표 표기가 아닌 이름이 있다: {_bad}"


def parent_of(skill: str) -> str | None:
    """상위 개념. 없으면 None. (한 단계만 — 규칙 ①)"""
    return PARENT.get(skill)


# ═════════════════════════════════════════════════════════════
# NOT_A_SKILL — 이름이 아니라 문장인 것을 걸러내는 신호어
# ═════════════════════════════════════════════════════════════
# "생성형 AI를 활용한 프로젝트 경험이 있으신 분" 같은 서술은 역량 이름이 아니다.
# 이걸 안 거르면 skill 노드가 문장으로 가득 차고 아무것도 연결되지 않는다.
# (실측: v1에서 최다 빈출 '스킬'이 "비자 발급 결격 사유 없음" 이었다)

NOT_A_SKILL = re.compile(
    r"(경험자|경력|년 이상|결격|졸업|우대|의지|희망|관심|가능자|보유자|필요|이해도|"
    r"역량|능력|태도|마인드|열정|분$|자$|"
    r"경험$|이해$|지식$|수행$|활용$|적용$|해결$|관리$|개선$)"
)

MAX_LEN = 25   # 이보다 길면 이름이 아니라 문장으로 본다

# 대표 표기 자기 자신도 통과해야 한다.
# LLM 은 프롬프트의 통제 어휘 목록(= CANON 의 값)을 보고 "Machine Learning" 처럼 대표 표기를 그대로 적는데,
# CANON 키에 "machine learning" 이 없으면 canonicalize 가 None 을 돌려줘 그 역량이 조용히 버려진다.
# (실측: 대표 표기 63개 중 9개 — Machine Learning, Data Analysis, Statistics, Deep Learning 등 — 가 이 경로로 탈락했다)
# 별칭을 일일이 추가하는 대신, 값 쪽에서도 찾는다. 새 대표 표기를 넣어도 자동으로 보호된다.
_CANON_VALUES: dict[str, str] = {v.lower(): v for v in CANON.values()}


def canonicalize(term: str, strict: bool = True) -> str | None:
    """용어 하나를 대표 표기로. 역량 이름이 아니면 None.

    strict=True  (graph.json 만들 때) — CANON에 있는 것만 통과.
    strict=False (데이터 탐색할 때)   — 짧은 이름은 CANON에 없어도 통과.

    ★ 왜 두 모드가 필요한가
      Skill이 그래프의 유일한 허브다. 전공 쪽과 직무 쪽이 **같은 어휘**를 써야만
      교집합이 생긴다. 한쪽이 'Terraform'을 쓰고 다른 쪽이 안 쓰면 그 노드는 고립된다.
      실측: 관대 모드로 직무 40건을 돌리면 Skill이 166개가 되고,
           그중 대부분은 직무 하나에만 붙어 있다 → 추천에 아무 도움이 안 된다.
      그래서 그래프에는 A가 승인한 어휘만 올린다. 승인 안 된 건 버리는 게 아니라
      '추가 후보'로 보고해서 A가 CANON에 넣을지 결정한다.

    >>> canonicalize("파이썬")
    'Python'
    >>> canonicalize("JAVA")
    'Java'
    >>> canonicalize("Terraform")                  # CANON에 없으므로 strict에선 탈락
    >>> canonicalize("Terraform", strict=False)
    'Terraform'
    >>> canonicalize("생성형 AI를 활용한 프로젝트 경험이 있으신 분") is None
    True
    """
    if not term:
        return None

    cleaned = re.sub(r"\s+", " ", term.replace("\xa0", " ")).strip()
    cleaned = re.sub(r"^[-•*·●■]\s*", "", cleaned)
    if not cleaned:
        return None

    key = cleaned.lower()

    if key in CANON:
        return CANON[key]
    if key in _CANON_VALUES:           # 대표 표기 그대로 들어온 경우 (대소문자 무시)
        return _CANON_VALUES[key]
    if strict:
        return None
    if len(cleaned) > MAX_LEN or NOT_A_SKILL.search(cleaned):
        return None          # 문장이다. 버린다.
    return cleaned           # 사전에 없는 짧은 이름은 그대로 채택


def is_name_like(term: str) -> bool:
    """'짧은 이름' 인지 — CANON 추가 후보를 가려내는 데 쓴다."""
    cleaned = re.sub(r"\s+", " ", (term or "").replace("\xa0", " ")).strip()
    return bool(cleaned) and len(cleaned) <= MAX_LEN and not NOT_A_SKILL.search(cleaned)


def canonicalize_all(terms: list[str]) -> tuple[list[str], list[str], list[str]]:
    """리스트 통째로. (채택, CANON 추가 후보, 버림) 세 갈래로 돌려준다.

    - 채택       : CANON에 있는 용어 → 그래프에 올라감
    - 추가 후보  : CANON엔 없지만 이름처럼 생긴 것 → A가 보고 CANON에 넣을지 결정
    - 버림       : 문장. 그냥 버린다.

    조용히 버리면 어휘집이 자라지 않는다. 세 갈래로 나눠야 A의 작업이 가능하다.
    """
    kept: list[str] = []
    candidates: list[str] = []
    dropped: list[str] = []

    for t in terms:
        c = canonicalize(t, strict=True)
        if c:
            kept.append(c)
        elif is_name_like(t):
            candidates.append(t.strip())
        else:
            dropped.append(t.strip())

    # dict.fromkeys: 순서 유지하면서 중복 제거하는 관용구
    return list(dict.fromkeys(kept)), list(dict.fromkeys(candidates)), list(dict.fromkeys(dropped))


if __name__ == "__main__":
    for s in ["파이썬", "JAVA", "Terraform", "쿠버네티스",
              "생성형 AI를 활용한 프로젝트 경험이 있으신 분", "비자 발급 결격 사유 없음"]:
        print(f"{s!r:50} → {canonicalize(s)!r}")
    print(f"\nCANON 대표 표기 {len(set(CANON.values()))}개 / 별칭 {len(CANON)}개")
