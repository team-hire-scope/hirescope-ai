# HireScope AI

Spring Boot 백엔드로부터 이력서 + JD 데이터를 받아 LLM으로 분석하고, **점수 / 면접 질문 / 요약**을 JSON으로 반환하는 Python FastAPI 기반 AI 분석 서버입니다.

## 구성

- **LLM**: LM Studio (localhost:1234) 에서 로컬 서빙되는 Gemma 4 26B-A4B 모델
- **API 호환**: OpenAI SDK (base_url만 LM Studio로 변경)
- **벡터 DB**: ChromaDB (RAG 기능 — 없어도 정상 동작)
- **Python**: 3.9+

## 프로젝트 구조

```
hirescope-ai/
├── app/
│   ├── main.py              # FastAPI 앱, CORS, 헬스체크
│   ├── config.py            # 환경변수 설정 (pydantic-settings)
│   ├── routers/
│   │   └── analysis_router.py   # POST /api/analysis
│   ├── services/
│   │   ├── llm_service.py       # LM Studio 호출 (재시도, 토큰 로깅)
│   │   ├── scoring_service.py   # 5대 기준 점수 산정
│   │   ├── question_service.py  # 면접 질문 7~10개 생성
│   │   ├── summary_service.py   # 이력서 3~5문장 요약
│   │   └── rag_service.py       # ChromaDB 유사 문서 검색
│   ├── prompts/
│   │   ├── scoring_prompt.py    # 점수 산정 프롬프트 + build_user_prompt
│   │   ├── question_prompt.py   # 면접 질문 프롬프트 + build_user_prompt
│   │   └── summary_prompt.py    # 요약 프롬프트 + build_user_prompt
│   ├── models/
│   │   ├── request.py       # AnalysisRequest (이력서 + JD)
│   │   └── response.py      # AnalysisResponse (점수 + 질문 + 요약)
│   └── vectordb/
│       ├── client.py        # ChromaDB 클라이언트 래퍼
│       └── indexer.py       # RAG 인덱싱 유틸리티
└── tests/
    └── hirescope_prompt_test.py  # LM Studio 직접 호출 프롬프트 테스트
```

## 실행 방법

### 1. 사전 준비

```bash
# Python 가상환경 생성 및 활성화
python3.9 -m venv .venv
source .venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에서 LM_STUDIO_MODEL을 실제 모델명으로 수정
```

### 2. LM Studio 서버 시작

1. LM Studio 앱 열기
2. **Gemma 4 26B-A4B** 모델 로드
3. **Local Server** 탭 → **Start Server** 클릭
4. 기본 포트 `1234` 확인

### 3. FastAPI 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버 시작 시 LM Studio 연결 상태가 로그로 출력됩니다.

### 4. Docker로 실행

```bash
docker build -t hirescope-ai .
docker run -p 8000:8000 --env-file .env hirescope-ai
```

> **주의**: Docker 컨테이너에서 호스트의 LM Studio에 접근하려면 `.env`의 `LM_STUDIO_BASE_URL`을 `http://host.docker.internal:1234/v1`로 변경하세요.

## API 사용법

### 헬스체크

```
GET /health
```

```json
{
  "status": "ok",
  "model": "gemma-4-26b-a4b-it",
  "lm_studio_url": "http://localhost:1234/v1"
}
```

### 이력서 + JD 분석

```
POST /api/analysis
Content-Type: application/json
```

**요청 예시**:

```json
{
  "application_id": 1,
  "resume": {
    "name": "김민수",
    "summary": "5년차 백엔드 개발자, Java/Spring 기반 대규모 트래픽 처리 경험",
    "careers": [
      {
        "company_name": "네이버클라우드",
        "job_title": "백엔드 개발자",
        "rank": "시니어",
        "start_date": "2022-03",
        "end_date": null,
        "description": "클라우드 인프라 API 서버 개발 및 운영",
        "achievements": "배포 파이프라인 개선으로 배포 시간 60% 단축"
      }
    ],
    "educations": [
      {
        "school_name": "서울대학교",
        "major": "컴퓨터공학",
        "degree": "학사",
        "start_date": "2016-03",
        "end_date": "2020-02"
      }
    ],
    "skills": [
      {"skill_name": "Java", "level": "상", "duration_months": 60},
      {"skill_name": "Spring Boot", "level": "상", "duration_months": 48}
    ],
    "projects": [
      {
        "project_name": "MSA 전환 프로젝트",
        "role": "테크 리드",
        "period": "2023.01 ~ 2023.12",
        "tech_stack": ["Spring Cloud", "Kubernetes", "Kafka"],
        "achievement_description": "서비스 장애 복구 시간 80% 단축"
      }
    ],
    "certifications": [
      {"name": "AWS Solutions Architect Associate", "issuer": "AWS", "acquired_date": "2023-05"}
    ]
  },
  "job_posting": {
    "company_name": "토스",
    "job_title": "서버 플랫폼 엔지니어",
    "description": "대규모 트래픽 환경에서 안정적인 서버 플랫폼 개발 및 운영",
    "required_skills": ["Java", "Spring Boot", "Kubernetes", "Kafka"],
    "preferred_qualifications": "MSA 전환 경험, gRPC 경험"
  }
}
```

**응답 예시**:

```json
{
  "application_id": 1,
  "total_score": 84.2,
  "scores": {
    "job_fit":                  {"score": 88, "reason": "..."},
    "career_consistency":       {"score": 85, "reason": "..."},
    "skill_match":              {"score": 82, "reason": "..."},
    "quantitative_achievement": {"score": 90, "reason": "..."},
    "document_quality":         {"score": 76, "reason": "..."}
  },
  "summary": "5년차 Java/Spring 백엔드 개발자로...",
  "interview_questions": [
    {
      "question": "MSA 전환 프로젝트에서 가장 어려웠던 기술적 도전은 무엇이었나요?",
      "intent": "테크 리드로서의 문제 해결 능력과 MSA 전환 실제 경험을 검증",
      "answer_guide": "STAR 기법으로 구체적인 장애 상황, 해결 방법, 결과를 수치로 제시하면 좋습니다."
    }
  ]
}
```

### API 문서

서버 실행 후 아래 URL에서 Swagger UI를 확인할 수 있습니다.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 프롬프트 직접 테스트

LM Studio 서버를 켠 상태에서 아래 명령으로 프롬프트 검증 스크립트를 실행할 수 있습니다.

```bash
python tests/hirescope_prompt_test.py
```

## 환경변수 목록

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `LM_STUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio API 주소 |
| `LM_STUDIO_MODEL` | `gemma-4-26b-a4b-it` | 로드된 모델명 |
| `LLM_TEMPERATURE` | `0.3` | LLM 온도 (낮을수록 일관된 점수) |
| `LLM_MAX_TOKENS` | `2000` | 최대 출력 토큰 수 |
| `CHROMA_HOST` | `localhost` | ChromaDB 호스트 |
| `CHROMA_PORT` | `8000` | ChromaDB 포트 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 연결 URL |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | CORS 허용 오리진 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
