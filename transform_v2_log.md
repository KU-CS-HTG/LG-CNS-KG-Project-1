(.venv) PS C:\Users\Admin\Documents\Project_1\LG-CNS-KG-Project-1> python .\transform_v2.py 
① normalize: 공고 13건 → 직무 40건 → staged_jobs.json
  [1/40] AI (AX)
  [2/40] Robotics (RX)
  [3/40] Consulting
  [4/40] DX Engineer
  [5/40] Cloud Application Modernization
  [6/40] Architect
  [7/40] ERP
  [8/40] Smart Factory
  [9/40] Convergence Engineer
  [10/40] Digital Marketing
  [11/40] 클라우드 인프라 사업 개발
  [12/40] SAP 프로젝트 관리자(PM/IM)
  [13/40] SAP 모듈 컨설턴트 / 운영
  [14/40] Salesforce 솔루션 컨설팅 및 PM
  [15/40] Salesforce 영업 플랫폼 구축 및 AX 전문가
  [16/40] MS Active Directory(AD) 이행/운영
  [17/40] 생명보험 업무전문가 및 시스템엔지니어
  [18/40] 손해보험 업무전문가 및 시스템엔지니어
  [19/40] 증권 업무전문가 및 시스템엔지니어
  [20/40] 해외사업이행 PM
  [21/40] Application Architect
  [22/40] AI Architect
  [23/40] Global Core Banking PM / PMO
  [24/40] Global Core Banking Business Analyst
  [25/40] Software Engineer - PM / 응용촐괄 및 PL
  [26/40] Software Engineer - 분석/설계
  [27/40] Infrastructure Architect
  [28/40] Data Architect
  [29/40] Cloud & DevOps Architect
  [30/40] 메신저 서비스 개발/운영
  [31/40] AI
  [32/40] Robotics (RX)
  [33/40] Business Development
  [34/40] DX Engineer
  [35/40] Cloud Application Modernization
  [36/40] Architecture
  [37/40] Smart Factory
  [38/40] Smart Logistics
  [39/40] ERP
  [40/40] IT Service
② extract: 40건 → extracted_raw.json

── 품질 리포트 ──
  skill 고유 218개 / 1회만 등장 175개 (80%)
    ↑ 이 비율이 70%를 넘으면 그래프가 거의 연결되지 않는다. 60% 이하를 목표로.
  상위 10: ['AI', 'Java', 'React', 'LLM', 'Cloud', 'MSA', 'Git', 'Vue.js', 'Kubernetes', 'Python']
  같은 role_key인데 job_family 불일치: 2건 ['lg-cns--erp', 'lg-cns--smart-factory']
  환각 의심: 11건
  duties 0개: ['1001677-증권-업무전문가-및-시스템엔지니어', '1000409-it-service']
  문장이라 제외됨: 13개 (예: ['AI 관련 플랫폼 구축 또는 프로젝트 수행', 'Digital Channel Management', 'IT 기본 역량'])

③④ curate: 40건 → curated_jobs.jsonl