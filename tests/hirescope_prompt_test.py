"""
HireScope 프롬프트 테스트 스크립트
LM Studio에서 Gemma 4 26B-A4B를 로드한 뒤 실행하세요.

사용법:
1. LM Studio에서 Gemma 4 26B-A4B 모델 로드
2. Local Server 탭에서 서버 시작 (기본 포트 1234)
3. pip install openai
4. python tests/hirescope_prompt_test.py
"""

import json
import time

from openai import OpenAI

# ============================================================
# LM Studio 연결 설정
# ============================================================
client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",  # LM Studio는 키 검증 안 함
)

MODEL = "gemma-4-26b-a4b-it"  # LM Studio에 로드된 모델명

# ============================================================
# 샘플 데이터: 지원자 이력서
# ============================================================
SAMPLE_RESUME = """
[지원자 정보]
이름: 김민수
자기소개: 5년차 백엔드 개발자로, Java/Spring 기반 대규모 트래픽 처리 경험이 있습니다. 최근에는 MSA 전환 프로젝트를 리드하며 시스템 안정성을 개선했습니다.

[경력]
1. 회사: 네이버클라우드 | 직무: 백엔드 개발자 | 직급: 시니어 | 기간: 2022.03 ~ 현재
   담당업무: 클라우드 인프라 API 서버 개발 및 운영, 모놀리식 아키텍처를 MSA로 전환하는 프로젝트 리드
   정량적 성과: 일일 API 호출량 500만 건 처리 시스템 안정화, 배포 파이프라인 개선으로 배포 시간 60% 단축

2. 회사: 카카오 | 직무: 서버 개발자 | 직급: 주니어 | 기간: 2020.01 ~ 2022.02
   담당업무: 카카오톡 선물하기 결제 시스템 백엔드 개발
   정량적 성과: Redis 캐싱 도입으로 API 응답 시간 40% 개선, 동시 접속자 10만명 대응 부하 테스트 및 최적화

[학력]
서울대학교 / 컴퓨터공학 / 학사 (2016.03 ~ 2020.02)

[기술 스택]
- Java (상, 60개월)
- Spring Boot (상, 48개월)
- Python (중, 24개월)
- Kubernetes (중, 18개월)
- PostgreSQL (상, 48개월)
- Redis (상, 36개월)
- Kafka (중, 12개월)
- AWS (중, 24개월)

[프로젝트]
1. MSA 전환 프로젝트 | 테크 리드 | 2023.01 ~ 2023.12
   사용기술: Spring Cloud, Kubernetes, Kafka, gRPC
   성과: 서비스 장애 복구 시간 80% 단축, 배포 주기 주 1회에서 일 3회로 개선

2. 실시간 알림 시스템 | 메인 개발자 | 2022.06 ~ 2022.12
   사용기술: Spring WebFlux, Redis Pub/Sub, WebSocket
   성과: 초당 5만건 메시지 처리, 메시지 지연시간 50ms 이하 달성

[자격증]
- AWS Solutions Architect Associate (AWS, 2023.05)
- 정보처리기사 (2019.11)
"""

# ============================================================
# 샘플 데이터: 채용 공고 (JD)
# ============================================================
SAMPLE_JD = """
[회사명] 토스 (Toss)
[직무명] 서버 플랫폼 엔지니어

[직무 설명]
토스의 핵심 금융 서비스를 지탱하는 서버 플랫폼을 개발하고 운영합니다.
대규모 트래픽 환경에서 안정적이고 확장 가능한 시스템을 설계하며,
MSA 환경에서 서비스 간 통신, 모니터링, 배포 자동화를 담당합니다.

[요구 기술 스택]
- Java 또는 Kotlin
- Spring Boot / Spring Cloud
- Kubernetes 운영 경험
- 대규모 트래픽 처리 경험 (일일 1,000만 건 이상)
- RDBMS (MySQL 또는 PostgreSQL)
- 메시지 큐 (Kafka, RabbitMQ 등)

[우대 사항]
- MSA 전환 경험
- gRPC 또는 서비스 메시 경험
- 모니터링 시스템 구축 경험 (Grafana, Prometheus)
- 금융 도메인 경험
"""


# ============================================================
# 프롬프트 1: 점수화 (Scoring) — scores 래퍼 구조
# ============================================================
SCORING_SYSTEM_PROMPT = """당신은 이력서 분석 전문가입니다. 지원자의 이력서와 채용 공고(JD)를 비교 분석하여 5가지 기준으로 점수를 매깁니다.

## 평가 기준 (각 1~100점)
1. 직무 적합도: JD가 요구하는 역할과 지원자의 경력/프로젝트 경험의 일치도
2. 경력 일관성: 경력 흐름의 논리적 연결성 (직무 연관성, 이직 빈도, 경력 공백, 직급 변화)
3. 기술 스택 매칭: JD 요구 기술과 보유 기술의 일치도 (필수 기술 보유, 숙련도, 사용 기간)
4. 정량적 성과: 수치로 표현된 구체적이고 검증 가능한 성과의 존재 여부
5. 문서 품질: 내용의 명확성, 구체성, 적절한 분량

## 점수 가이드라인
- 90~100: 해당 기준에서 탁월함. 거의 완벽한 일치 또는 뛰어난 수준
- 70~89: 우수함. 대부분의 요구사항을 충족
- 50~69: 보통. 일부 충족하지만 부족한 부분 존재
- 30~49: 미흡. 상당한 갭이 존재
- 1~29: 매우 부족. 거의 관련 없음

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 포함하지 마세요.

{
  "scores": {
    "job_fit": {"score": 점수, "reason": "근거 (2~3문장)"},
    "career_consistency": {"score": 점수, "reason": "근거 (2~3문장)"},
    "skill_match": {"score": 점수, "reason": "근거 (2~3문장)"},
    "quantitative_achievement": {"score": 점수, "reason": "근거 (2~3문장)"},
    "document_quality": {"score": 점수, "reason": "근거 (2~3문장)"}
  }
}

## Few-shot 예시
입력: Python 주니어 개발자가 시니어 Java 백엔드 포지션에 지원
출력:
{
  "scores": {
    "job_fit": {"score": 25, "reason": "JD는 시니어 Java 백엔드를 요구하나, 지원자는 Python 주니어 경력만 보유. 직무 역할과 기술 수준 모두 불일치."},
    "career_consistency": {"score": 45, "reason": "Python 개발 경력은 일관되나, Java 백엔드로의 전환 근거가 부족함."},
    "skill_match": {"score": 20, "reason": "필수 요구 기술인 Java, Spring Boot 경험 없음. Python만 보유하여 기술 스택 매칭이 매우 낮음."},
    "quantitative_achievement": {"score": 42, "reason": "일부 수치적 성과가 있으나 구체성이 부족하고 JD 관련 성과가 아님."},
    "document_quality": {"score": 60, "reason": "문서 구조는 적절하나 지원 직무와의 연관성을 드러내는 내용이 부족함."}
  }
}"""

SCORING_USER_PROMPT = f"""아래 이력서와 채용 공고를 분석하여 점수를 매겨주세요.

## 이력서
{SAMPLE_RESUME}

## 채용 공고 (JD)
{SAMPLE_JD}"""


# ============================================================
# 프롬프트 2: 예상 면접 질문 (Interview Questions)
# ============================================================
QUESTION_SYSTEM_PROMPT = """당신은 기술 면접관입니다. 지원자의 이력서와 채용 공고(JD)를 분석하여, 실제 면접에서 물어볼 만한 예상 질문을 생성합니다.

## 질문 생성 원칙
1. 이력서와 JD 사이의 갭(부족한 부분)을 파고드는 질문을 포함합니다.
2. 이력서에 기재된 성과의 구체적 기여도를 확인하는 질문을 포함합니다.
3. STAR 기법(Situation-Task-Action-Result) 기반의 행동 면접 질문을 우선합니다.
4. 단순 지식 확인형 질문은 피하고, 경험과 사고 과정을 물어보는 질문을 생성합니다.
5. 질문은 7~10개를 생성합니다.

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 포함하지 마세요.

{
  "interview_questions": [
    {
      "question": "면접 질문",
      "intent": "이 질문의 의도 (1문장)",
      "answer_guide": "좋은 답변의 방향 (2~3문장)"
    }
  ]
}"""

QUESTION_USER_PROMPT = f"""아래 이력서와 채용 공고를 분석하여 예상 면접 질문을 생성해주세요.

## 이력서
{SAMPLE_RESUME}

## 채용 공고 (JD)
{SAMPLE_JD}"""


# ============================================================
# 프롬프트 3: 이력서 요약 (Summary)
# ============================================================
SUMMARY_SYSTEM_PROMPT = """당신은 HR 컨설턴트입니다. 지원자의 이력서를 채용 공고(JD) 관점에서 요약합니다.

## 요약 원칙
1. 3~5문장으로 핵심만 요약합니다.
2. JD와의 적합성을 중심으로 강점과 약점을 균형 있게 서술합니다.
3. 구체적인 수치나 사실을 포함하여 근거를 제시합니다.

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 포함하지 마세요.

{
  "summary": "요약 텍스트 (3~5문장)"
}"""

SUMMARY_USER_PROMPT = f"""아래 이력서를 채용 공고 관점에서 요약해주세요.

## 이력서
{SAMPLE_RESUME}

## 채용 공고 (JD)
{SAMPLE_JD}"""


# ============================================================
# 테스트 실행
# ============================================================
def _strip_json_fences(text: str) -> str:
    """```json ... ``` 래핑을 제거한다."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄(```json 또는 ```) 과 마지막 줄(```) 제거
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return text


def call_llm(system_prompt: str, user_prompt: str, test_name: str):
    """LM Studio API를 호출하고 JSON 결과를 파싱한다."""
    print(f"\n{'=' * 60}")
    print(f"테스트: {test_name}")
    print(f"{'=' * 60}")

    start = time.time()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
    except Exception as e:
        print(f"API 호출 실패: {e}")
        print("LM Studio 서버가 실행 중인지, 모델이 로드되어 있는지 확인하세요.")
        return None

    elapsed = time.time() - start
    raw = response.choices[0].message.content.strip()

    print(f"응답 시간: {elapsed:.1f}초")
    print(f"토큰 수: {response.usage.total_tokens if response.usage else 'N/A'}")
    print(f"\n--- 원본 응답 ---")
    print(raw)

    # JSON 파싱 시도
    try:
        cleaned = _strip_json_fences(raw)
        parsed = json.loads(cleaned)
        print(f"\n--- JSON 파싱 성공 ---")
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        return parsed
    except json.JSONDecodeError as e:
        print(f"\n--- JSON 파싱 실패: {e} ---")
        print("프롬프트를 조정하여 JSON 출력을 개선해야 합니다.")
        return None


def main():
    print("=" * 60)
    print("HireScope 프롬프트 테스트")
    print(f"모델: {MODEL}")
    print("LM Studio: http://localhost:1234")
    print("=" * 60)

    # 1. 점수화 테스트
    scoring_result = call_llm(
        SCORING_SYSTEM_PROMPT,
        SCORING_USER_PROMPT,
        "점수화 (Scoring)",
    )

    # 2. 면접 질문 테스트
    question_result = call_llm(
        QUESTION_SYSTEM_PROMPT,
        QUESTION_USER_PROMPT,
        "예상 면접 질문 (Interview Questions)",
    )

    # 3. 이력서 요약 테스트
    summary_result = call_llm(
        SUMMARY_SYSTEM_PROMPT,
        SUMMARY_USER_PROMPT,
        "이력서 요약 (Summary)",
    )

    # 결과 종합
    print(f"\n{'=' * 60}")
    print("테스트 결과 종합")
    print(f"{'=' * 60}")
    print(f"점수화 JSON 파싱: {'성공' if scoring_result else '실패'}")
    print(f"면접 질문 JSON 파싱: {'성공' if question_result else '실패'}")
    print(f"이력서 요약 JSON 파싱: {'성공' if summary_result else '실패'}")

    if scoring_result:
        scores = scoring_result.get("scores", {})
        if scores:
            raw_scores = [v.get("score", 0) for v in scores.values()]
            total = round(sum(raw_scores) / len(raw_scores), 1) if raw_scores else 0
            print(f"\n총점 (5개 평균): {total}점")
            for key, val in scores.items():
                print(f"  {key}: {val.get('score', 'N/A')}점")

    if question_result:
        questions = question_result.get("interview_questions", [])
        print(f"\n생성된 면접 질문 수: {len(questions)}개")

    if summary_result:
        summary = summary_result.get("summary", "")
        print(f"\n요약: {summary[:120]}{'...' if len(summary) > 120 else ''}")


if __name__ == "__main__":
    main()
