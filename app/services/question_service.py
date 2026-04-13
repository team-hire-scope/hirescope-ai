import json
import logging
from typing import List

from app.models.request import AnalysisRequest
from app.models.response import InterviewQuestion
from app.prompts.question_prompt import QUESTION_SYSTEM_PROMPT, build_user_prompt
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def _parse_questions_response(raw: str) -> List[InterviewQuestion]:
    """LLM 응답 JSON에서 면접 질문 목록을 추출하여 파싱한다.

    기대 JSON 구조:
    {
      "interview_questions": [
        {"question": ..., "intent": ..., "answer_guide": ...}
      ]
    }

    Args:
        raw: LLM 응답 텍스트 (JSON 펜스 제거 후)

    Returns:
        InterviewQuestion 목록

    Raises:
        ValueError: JSON 파싱 실패 또는 필드 누락 시
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}\n원본 응답:\n{raw}") from e

    # {"interview_questions": [...]} 또는 직접 배열 [...] 모두 허용
    if isinstance(data, list):
        items = data
    else:
        items = data.get("interview_questions", [])

    if not items:
        raise ValueError(f"interview_questions 목록이 비어 있음\n원본:\n{raw}")

    return [InterviewQuestion(**item) for item in items]


class QuestionService:
    """이력서-JD 갭 분석 기반 면접 질문 생성 서비스.

    STAR 기법 기반 행동면접 질문을 7~10개 생성한다.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def generate_questions(self, request: AnalysisRequest) -> List[InterviewQuestion]:
        """이력서와 JD를 분석하여 예상 면접 질문 7~10개를 생성한다.

        Args:
            request: 분석 요청 데이터

        Returns:
            면접 질문 목록 (question, intent, answer_guide 포함)

        Raises:
            ValueError: LLM 응답 파싱 실패 시
        """
        user_prompt = build_user_prompt(
            resume=request.resume,
            job_posting=request.job_posting,
        )

        logger.info("면접 질문 생성 LLM 호출 (application_id: %d)", request.application_id)
        raw_response = await self._llm.generate(QUESTION_SYSTEM_PROMPT, user_prompt)

        try:
            questions = _parse_questions_response(raw_response)
        except ValueError as e:
            logger.error(
                "면접 질문 JSON 파싱 실패 (application_id: %d): %s",
                request.application_id,
                e,
            )
            raise

        logger.info(
            "면접 질문 생성 완료 (application_id: %d, 질문 수: %d개)",
            request.application_id,
            len(questions),
        )
        return questions
