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
    "자연어처리": "NLP", "nlp": "NLP", "natural language processing": "NLP",
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
    "메카트로닉스": "Mechanical Engineering", "mechatronics": "Mechanical Engineering",
    # 전공 과목명에서 LLM 이 영문으로 적는 기계 세부 분야 → 부모로 (2026-09-15 재추출 탈락 목록에서)
    "fluid mechanics": "Mechanical Engineering", "thermodynamics": "Mechanical Engineering", "dynamics": "Mechanical Engineering",
    "structural analysis": "Mechanical Engineering", "유체역학": "Mechanical Engineering", "열역학": "Mechanical Engineering",
    "computer-aided design": "Mechanical Design", "machine design": "Mechanical Design", "기계설계": "Mechanical Design",
    "computer simulation": "Simulation",
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


    # ═══ 3단계 (2026-09-16 초안, A 검토 전) ═══
    # 근거: 신입 직무 85건 중 33건이 어휘 밖이라 그래프에 못 올랐다 (LGES 22 · LGD 4 · LGU 4 · HSAD 3).
    #       탈락 직무의 LLM 원출력(extracted_raw.json)과 canon_candidates.txt 2회 이상 41개를 대조해 만들었다.
    #       새 대표 표기는 모두 서울대 과목명에 근거가 있는 것만 (규칙 ②). 어학·오피스 도구·자격증 그 자체는 넣지 않았다.
    # ── 3단계 클러스터 ④ 배터리 공정·재료 분석 (LGES Cell개발·공정기술·생산운영 ↔ 화학생물공학부 '공정제어 및 설계'·재료공학부 '재료공정통계분석')
    "2차전지": "Electrochemistry", "이차전지": "Electrochemistry", "2차전지 부품 개발": "Electrochemistry",
    "cell 설계": "Electrochemistry", "cell design": "Electrochemistry", "cell 설계 이해": "Electrochemistry",
    "electrochemical modeling": "Electrochemistry", "전기화학적 기본 지식": "Electrochemistry",
    "공정": "Process Engineering", "process engineering": "Process Engineering", "공정 이해": "Process Engineering",
    "공정 관련 지식": "Process Engineering", "선행공정": "Process Engineering", "전극 제조 공정 이해": "Process Engineering",
    "r2r 공정": "Process Engineering", "r2r 공정 이해": "Process Engineering", "r2r 필름 성형": "Process Engineering",
    "전극 믹싱": "Process Engineering", "전극 코팅": "Process Engineering", "전극 부자재 이해": "Process Engineering",
    "전극 코터 검사기": "Process Engineering",
    "2차전지 소재 개발": "Materials Engineering", "재료 전공": "Materials Engineering", "용접 재료": "Materials Engineering",
    "물성 측정": "Materials Engineering",
    "edx": "EDX", "xrf": "XRF",                                    # SEM 과 같은 재료 분석 장비 → PARENT
    "전극 설비": "Manufacturing", "설비 유지보수": "Manufacturing",

    # ── 3단계 클러스터 ⑤ 전력·제어·통신·회로 (LGES BMS/System/전장부품, LGU AIDC전기/NW ↔ 전기·정보공학부
    #    '전력 및 에너지시스템의 기초'·'제어공학개론'·'통신의 기초'. 전공 raw 에 Control Engineering 은 이미 있다)
    "전력": "Power Systems", "power systems": "Power Systems", "전력 계통": "Power Systems", "전력 지식": "Power Systems",
    "전력전자": "Power Systems", "전력 변환": "Power Systems", "전력변환기기 동작원리": "Power Systems",
    "전원 회로 설계": "Power Systems", "dcdc 설계": "Power Systems", "ac/dc 회로 이론": "Power Systems", "전기 설비": "Power Systems",
    "제어": "Control Engineering", "제어공학": "Control Engineering", "control engineering": "Control Engineering",
    "control systems": "Control Engineering", "자동제어": "Control Engineering",
    "제어 회로 설계": "Control Engineering", "제어 프로그램 설계": "Control Engineering",
    "통신": "Telecommunications", "통신 공학": "Telecommunications", "통신공학": "Telecommunications",
    "communications engineering": "Telecommunications", "정보통신": "Telecommunications", "광통신공학": "Telecommunications",
    "무선통신": "Telecommunications", "이동통신": "Telecommunications",
    "5g": "Telecommunications", "lte": "Telecommunications", "통신 회로 설계": "Telecommunications",
    "ccna": "CCNA", "ccnp": "CCNP",                                # 네트워크 자격증 → PARENT Network
    "전기 지식": "Electrical Engineering", "전기 설계": "Electrical Engineering", "전기전자 전공": "Electrical Engineering",
    "전기 공학 관련 학과": "Electrical Engineering", "전기 관련 자격증": "Electrical Engineering",
    "전기회로 설계": "Electrical Engineering", "측정 회로 설계": "Electrical Engineering",
    "기능 안전 회로 설계": "Electrical Engineering", "emc 설계 평가": "Electrical Engineering",
    "orcad": "OrCAD",                                              # SmartSpice 와 같은 회로 도구 → PARENT

    # ── 3단계 클러스터 ⑥ 기계·설계 별칭 보강 (LGES 전장부품설계·설비기술·Pack개발 — 새 대표 표기 없음)
    "기계 지식": "Mechanical Engineering", "기구 지식": "Mechanical Engineering", "기구적인 지식": "Mechanical Engineering",
    "기계 전공": "Mechanical Engineering", "메카트로닉스 전공": "Mechanical Engineering", "강도설계": "Mechanical Engineering",
    "기계 설계": "Mechanical Design", "2d 설계": "Mechanical Design", "2d 도면 작성": "Mechanical Design",
    "3d tool": "Mechanical Design", "cad 활용 능력": "Mechanical Design", "solid works": "SolidWorks",
    "performance simulation": "Simulation", "mechanical properties modeling": "Simulation",

    # ── 3단계 클러스터 ⑦ 경영·마케팅·디자인 (HSAD 캠페인/광고제작, LGD 경영관리/HRM/ER, LGES 영업마케팅, LGU 사업기획
    #    ↔ 경영학과·디자인과. 전공 raw 에 Marketing·Accounting·Finance·Design 이 이미 있어 재추출 없이 이어진다)
    "경영": "Management", "management": "Management", "경영학": "Management",
    "마케팅": "Marketing", "marketing": "Marketing", "브랜딩": "Marketing", "브랜드": "Marketing",
    "광고": "Marketing", "소비자 트렌드": "Marketing", "시장조사": "Marketing",
    "영업": "Marketing", "b2b 영업": "Marketing",                    # 영업(Sales) 과목은 없다 — 마케팅으로 묶을지 A 판단
    "디지털 마케팅": "Digital Marketing", "digital marketing": "Digital Marketing",   # 경영학과 '디지털 마케팅' 과목 → PARENT Marketing
    "디지털 플랫폼": "Digital Marketing", "소셜 플랫폼": "Digital Marketing", "소셜 미디어": "Digital Marketing", "sns": "Digital Marketing",
    "경영지도사": "Management",
    "회계": "Accounting", "accounting": "Accounting", "공인회계사": "Accounting", "세무사": "Accounting",
    "세무회계": "Accounting", "전산 회계 관련 자격증": "Accounting",
    "재무": "Finance", "finance": "Finance", "재무관리": "Finance", "cfa": "Finance",
    "financial engineering": "Finance", "금융": "Finance",
    "인사관리": "Human Resources", "human resources": "Human Resources", "hrm": "Human Resources", "hr": "Human Resources",
    "노사관계": "Human Resources", "공인노무사": "Human Resources", "노동관계 법령 해석": "Human Resources",
    "임단협 합의서 작성": "Human Resources", "근로감독": "Human Resources",
    "디자인": "Design", "design": "Design", "디자인 tool": "Design", "시각디자인": "Design", "제품디자인": "Design",
    "ai tool": "LLM", "ai 도구": "LLM",                               # 광고제작·사업기획의 '생성형 AI 도구'
    "지표 분석": "Data Analysis", "소재 데이터 분석": "Data Analysis", "데이터 사이언스": "Data Analysis", "data science": "Data Analysis",
    # ✗ "데이터 분석 툴"·"데이터 분석·시각화 도구" 는 넣지 않았다: 도구 언급 하나로 Data Analysis 를 주면 HSAD 미디어(AI·Excel·PPT·도구)가
    #   역량 2개짜리 직무로 올라와 통계학과 입력에서 AI (AX) 를 밀어낸다 (집합 코사인은 역량이 적은 직무에 유리 — 2개 규칙을 둔 이유와 같다)

    # ═══ 팀원 확장 통합 (2026-09-16, main ec0874c·f5f06d8 의 CANON 확장을 3단계와 합친 것 — 결정 근거는 docs/20260916_어휘_3단계_초안.md 8절) ═══
    # ── 화학·소재: 그대로 채택
    "화공": "Chemical Engineering", "화학공": "Chemical Engineering", "기계공": "Mechanical Engineering", "전기전자": "Electrical Engineering",
    "auto cad": "AutoCAD", "재료 공학": "Materials Engineering", "신소재공학": "Materials Engineering", "신소재": "Materials Engineering",
    "배터리관리시스템": "BMS",
    "고분자공학": "Polymer Engineering", "금속재료공학": "Metallurgical Engineering",
    "세라믹": "Ceramics", "유리": "Glass", "glass": "Glass",
    # ✗ 화학→Chemistry, 배터리/전지→Battery 는 채택하지 않음: 전공 raw 가 화학 과목을 전부 Chemical Engineering 으로 내므로
    #   Chemistry·Battery 노드는 어느 전공과도 이어지지 않는다. 기존 매핑(→ Chemical Engineering / → Electrochemistry) 유지 + 별칭만 보강
    "chemistry": "Chemical Engineering", "전지": "Electrochemistry", "battery": "Electrochemistry",
    # ── 기계·제조
    # ✗ 열역학/유체역학/구조해석/동역학/메카트로닉스를 ME 의 자식 노드로 쪼개는 안은 채택하지 않음 (재생성 실측):
    #   직무 쪽에서 이 말을 요구하는 공고는 1~3건인데, 전공 쪽에서는 조선해양·원자핵·건설환경·바이오시스템이 유체역학·열역학 과목으로
    #   Mechanical Engineering 을 얻고 있어서, 쪼개면 이 4개 전공이 ME 를 요구하는 신입 직무 15건과 끊긴다 (추론은 위로만 — 규칙 ③).
    #   2단계 방식(과목명 수준의 세부 역학 → ME 별칭) 유지, 팀원 별칭만 보강
    "열전달": "Mechanical Engineering", "heat transfer": "Mechanical Engineering",
    "구조해석": "Mechanical Engineering", "동역학 해석": "Mechanical Engineering", "dynamics analysis": "Mechanical Engineering",
    "fluid dynamics": "Mechanical Engineering",
    "cfd": "CFD",                                                    # 전산 유체 — ME 의 자식 (팀원 최종안)
    "사출": "Injection Molding", "압출": "Extrusion",
    "자동화": "Automation",                                          # 팀원 안. 공고의 '자동화' 는 대부분 IT 자동화라 이 별칭이 실제로 걸리는 공고는 없다 (실측 0건)
    # ✗ catia/creo/solidworks/autocad → CAD 는 채택하지 않음: 2단계에서 도구 이름을 Mechanical Design 의 자식으로 두기로 했고
    #   (카드에 "CATIA (Mechanical Design 계열)" 로 보이게), 기계공학부가 Mechanical Design 을 정확히 기른다. "cad" 는 → Mechanical Design 유지
    # ── 전기·전자: 팀원 최종안(821a617)대로 전자·회로설계·전장은 Electrical Engineering 별칭 (2단계와 같은 방식). 별도 노드 없음
    "전자": "Electrical Engineering", "circuit design": "Electrical Engineering",
    "자동차 전장 시스템": "Electrical Engineering", "전장": "Electrical Engineering",
    "에너지공학": "Energy Engineering", "energy engineering": "Energy Engineering",
    # ── 디스플레이·광학·반도체
    "디스플레이": "Display", "display": "Display", "광학": "Optics", "반도체": "Semiconductor",
    "반도체 패키징": "Semiconductor Packaging", "패키징": "Semiconductor Packaging",   # 팀원 안. Packaging→Semiconductor→EE 두 단계지만 PyTorch→DL→ML 과 같은 선례
    # ── 통신·데이터센터
    "데이터센터": "Data Center",
    # ── 데이터·AI 도구
    "opencv": "Computer Vision",
    # ✗ tableau/google analytics/ga → Data Analysis 는 채택하지 않음: 도구 언급 하나로 Data Analysis 를 주면 HSAD 디지털 기획(AI·GA·Tableau·SQL)이
    #   컴퓨터공학부 입력에서 Smart Factory 를 밀어내 평가셋 #3·#9·I2 가 깨진다 (9/16 실측). "데이터 분석 툴" 을 뺀 것과 같은 원칙
    "mongodb": "Database", "apache spark": "Database",              # Spark 는 DB 가 아니라 분산 처리 엔진 — A 재검토 후보
    # ✗ pytorch/tensorflow → Machine Learning, postgresql → Database 직결은 채택하지 않음: 2단계 자식 노드(PyTorch → Deep Learning 등) 유지
    # ── 비즈니스: 영업은 Marketing 과 분리 (팀원 안) 하고 Marketing 의 자식으로 잇는다
    "영업": "Sales", "해외영업": "Sales", "b2b 영업": "Sales", "sales": "Sales",          # (3단계의 → Marketing 을 덮음)
    "crm": "CRM", "세일즈포스": "CRM",
    "재무회계": "Accounting",                                        # 팀원 안은 Finance — 재무회계(financial accounting)는 회계 과목

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
    "BMS": "Electrical Engineering",      # 9/16 팀원 안 채택 — BMS HW 공고는 회로 설계 (2단계 Electrochemistry 에서 이동)
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
    # ── 3단계 (2026-09-16 초안, A 검토 전)
    # Electrochemistry: 전기화학 과목은 화학부·화공·재료·에너지자원 4곳에 있지만 전공 raw 는 전부 Chemical Engineering 으로 묶었다
    #   (어휘 목록에 Electrochemistry 가 있었는데도). 재추출에 기대지 말고 한 홉으로 잇는다.
    "Electrochemistry": "Chemical Engineering", "Process Engineering": "Chemical Engineering",
    "EDX": "Materials Engineering", "XRF": "Materials Engineering",
    "Power Systems": "Electrical Engineering", "Telecommunications": "Electrical Engineering",
    "OrCAD": "Electrical Engineering",
    "CCNA": "Network", "CCNP": "Network",
    # 경영 4분야 → Management. 전공 raw 에 Marketing·Accounting·Finance 는 있고 Human Resources 는 없어서 (인사관리·노사관계론은
    # Management 로 묶임) HR 은 이 홉으로만 이어진다. 기술 쪽 Java→Programming 과 같은 꼴.
    "Marketing": "Management", "Accounting": "Management", "Finance": "Management", "Human Resources": "Management",
    "Digital Marketing": "Marketing",                # HSAD 캠페인 기획(브랜딩·광고·디지털/소셜 플랫폼)이 Marketing 하나로 뭉쳐 2개 규칙에 걸리던 것을 푼다
    # ── 팀원 확장 통합 (2026-09-16) — 전부 한 홉 (규칙 ①). 팀원 안의 두 단계(CFD→Fluid Dynamics→ME, Circuit Design→Electronics→EE)는 직결로 바꿈
    "Polymer Engineering": "Materials Engineering", "Metallurgical Engineering": "Materials Engineering",
    "Ceramics": "Materials Engineering", "Glass": "Materials Engineering",
    "Injection Molding": "Mechanical Engineering", "Extrusion": "Mechanical Engineering",
    "CFD": "Mechanical Engineering", "Automation": "Mechanical Engineering",
    "Display": "Electrical Engineering", "Semiconductor": "Electrical Engineering", "Semiconductor Packaging": "Semiconductor",
    "Energy Engineering": "Electrical Engineering",
    "Data Center": "Cloud",
    "Sales": "Marketing", "CRM": "Sales",
}

_canon_values = set(CANON.values())
_bad = [k for k in PARENT if k not in _canon_values] + [v for v in PARENT.values() if v not in _canon_values]
assert not _bad, f"PARENT 에 CANON 대표 표기가 아닌 이름이 있다: {_bad}"


def parent_of(skill: str) -> str | None:
    """상위 개념. 없으면 None. (한 단계만 — 규칙 ①)"""
    return PARENT.get(skill)


# ═════════════════════════════════════════════════════════════
# TRAIT_TO_SKILL — 성향(user_analysis.STANDARD_TRAITS) → 역량. IS_A 와 **다른 종류**의 관계
# ═════════════════════════════════════════════════════════════
# IS_A 는 분류("Oracle 은 Database 의 한 종류", 위로 올리면 항상 참).
# 이건 연관("수리적사고는 Statistics 를 시사한다", 경향일 뿐 틀릴 수 있음). 그래프로 그리면
#   (:Trait)-[:SUGGESTS]->(:Skill) — 새 노드 종류, 새 엣지. IS_A 와 섞지 않는다.
# 근거가 없다는 점이 결정적이다: 과목명은 성향을 가르치지 않는다 (그래서 전공 쪽에서 소프트 스킬을 뺐다).
# 그러므로 여기서 나온 태그는 **가중치 0.5** 로만 반영하고, 화면에 "성향에서 추정" 으로 표시한다.
# 30개 성향 중 역량으로 이을 근거가 있는 7개만. 창의성·공감·경청·안정지향 등은 잇지 않는다 — 억지로 이으면
# 9/15 소프트 스킬 사태(성악과 → Communication)의 재현이다.

TRAIT_TO_SKILL: dict[str, str] = {
    "수리적사고": "Statistics",
    "분석성": "Data Analysis",
    "논리성": "Algorithm",
    "탐구성": "Machine Learning",          # 약함 — A 판단으로 뺄 수 있음
    "조정능력": "Project Management",
    "주도성": "Project Management",
    "계획성": "Project Management",
}
_bad_t = [v for v in TRAIT_TO_SKILL.values() if v not in _canon_values]
assert not _bad_t, f"TRAIT_TO_SKILL 에 CANON 대표 표기가 아닌 이름이 있다: {_bad_t}"


# ═════════════════════════════════════════════════════════════
# 소프트 스킬 — 직무가 요구하는 태도 (extracted_raw 의 soft_skills) ↔ 학생 성향
# ═════════════════════════════════════════════════════════════
# 세 번째 관계. (:Trait)-[:MATCHES]->(:SoftSkill)<-[:WANTS]-(:Job) — 전공을 거치지 않고 성향에서 직무로 바로 간다.
# 양쪽이 "말한 것" 끼리 만난다: 공고가 "협업·문제해결" 을 직접 요구하고, 인터뷰가 "역할 나누고 일정 정리" 를 직접 관찰한다.
# 그래서 TRAIT_TO_SKILL(추론, 0.5)보다 근거가 낫다. 단, 직무 84건 중 44건에만 soft 데이터가 있고 빈 값이
# "요구 없음" 인지 "추출이 놓침" 인지 구분이 안 되므로 **점수에 더하지 않고 동점일 때만** 2차 기준으로 쓴다 (graph_store).
# 약점(direction=weakness)은 쓰지 않는다 — user_analysis 규칙 14 "약점을 직무 부적합으로 판단하지 않는다".

SOFT_CANON: dict[str, str] = {           # 공고 표현(소문자, 공백 제거) → 대표 표기. 실측 109개 표현 → 10개
    "커뮤니케이션": "Communication", "소통": "Communication", "소통능력": "Communication", "의사소통": "Communication",
    "설득": "Communication", "고객소통": "Communication", "협업커뮤니케이션": "Communication",
    "고객지향적커뮤니케이션": "Communication", "비즈니스의사소통": "Communication",
    "문제해결": "Problem Solving", "문제정의및해결": "Problem Solving", "문제해결과정즐김": "Problem Solving",
    "논리적사고": "Analytical Thinking", "분석적사고": "Analytical Thinking",
    "협업": "Collaboration", "협력": "Collaboration", "팀협업": "Collaboration", "협업문화에익숙함": "Collaboration", "팀워크": "Collaboration",
    "리더십": "Leadership",
    "적극성": "Initiative", "적극적인태도": "Initiative", "도전의지": "Initiative", "새로운시도즐김": "Initiative", "열정": "Initiative",
    "책임감": "Responsibility",
    "학습의지": "Growth Mindset", "성장의지": "Growth Mindset", "자기주도학습": "Growth Mindset",
    "창의성": "Creativity", "크리에이티브역량": "Creativity", "아이디어제시": "Creativity",
    "변화수용": "Adaptability", "변화대응": "Adaptability",
}
_SOFT_DROP = re.compile(r"영어|english|회화|능통|외국어")   # 어학은 태도가 아니다


def canonicalize_soft(term: str) -> str | None:
    """공고의 소프트 스킬 표현 → 대표 표기. 어학·미등록 표현은 None."""
    key = re.sub(r"\s+", "", (term or "").replace("\xa0", " ")).lower()
    if not key or _SOFT_DROP.search(key):
        return None
    return SOFT_CANON.get(key)


TRAIT_TO_SOFT: dict[str, str] = {         # user_analysis 성향 → 소프트 스킬. 근거 있는 17개만 (30개 중)
    "협력성": "Collaboration", "조정능력": "Collaboration",
    "주도성": "Leadership",
    "언어표현": "Communication", "설득력": "Communication", "발표력": "Communication", "경청": "Communication", "공감": "Communication",
    "문제해결": "Problem Solving",
    "분석성": "Analytical Thinking", "논리성": "Analytical Thinking",
    "도전성": "Initiative", "실행력": "Initiative",
    "지속성": "Responsibility",
    "성장지향": "Growth Mindset",
    "창의성": "Creativity",
    "변화적응": "Adaptability",
}
_soft_values = set(SOFT_CANON.values())
_bad_s = [v for v in TRAIT_TO_SOFT.values() if v not in _soft_values]
assert not _bad_s, f"TRAIT_TO_SOFT 에 SOFT_CANON 대표 표기가 아닌 이름이 있다: {_bad_s}"


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
