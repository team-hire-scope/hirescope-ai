import json
import logging

from app.models.request import AnalysisRequest
from app.prompts.summary_prompt import SUMMARY_SYSTEM_PROMPT, build_user_prompt
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def _parse_summary_response(raw: str) -> str:
    """LLM 응답 JSON에서 요약 텍스트를 추출한다.

    기대 JSON 구조:
    {
      "summary": "요약 텍스트 (3~5문장)"
    }

    Args:
        raw: LLM 응답 텍스트 (JSON 펜스 제거 후)

    Returns:
        요약 텍스트 문자열

    Raises:
        ValueError: JSON 파싱 실패 또는 summary 키 누락 시
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 — 텍스트를 그대로 반환 (프롬프트 미준수 케이스)
        logger.warning("요약 JSON 파싱 실패, 원본 텍스트를 그대로 사용합니다.")
        return raw.strip()

    summary = data.get("summary", "")
    if not summary:
        raise ValueError(f"summary 필드가 비어 있음\n원본:\n{raw}")
    return summary


class SummaryService:
    """이력서 핵심 요약 생성 서비스.

    JD 관점에서 이력서를 3~5문장으로 요약한다.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def summarize(self, request: AnalysisRequest) -> str:
        """이력서 핵심 정보를 JD 관점에서 3~5문장으로 요약한다.

        Args:
            request: 분석 요청 데이터

        Returns:
            이력서 요약 텍스트 (3~5문장)

        Raises:
            ValueError: LLM 응답 파싱 실패 시
        """
        user_prompt = build_user_prompt(
            resume=request.resume,
            job_posting=request.job_posting,
        )

        logger.info("이력서 요약 LLM 호출 (application_id: %d)", request.application_id)
        raw_response = await self._llm.generate(SUMMARY_SYSTEM_PROMPT, user_prompt)

        summary = _parse_summary_response(raw_response)

        logger.info("이력서 요약 완료 (application_id: %d)", request.application_id)
        return summary
