import json
import logging
from typing import Tuple

from app.models.request import AnalysisRequest
from app.models.response import ScoreItem, ScoreDetail
from app.prompts.scoring_prompt import SCORING_SYSTEM_PROMPT, build_user_prompt
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


def _parse_score_response(raw: str) -> ScoreDetail:
    """LLM 응답 JSON을 ScoreDetail 모델로 변환한다.

    기대 JSON 구조:
    {
      "scores": {
        "job_fit": {"score": ..., "reason": ...},
        ...
      }
    }

    Args:
        raw: LLM 응답 텍스트 (JSON 펜스 제거 후)

    Returns:
        파싱된 ScoreDetail 모델

    Raises:
        ValueError: JSON 파싱 실패 또는 필드 누락 시
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}\n원본 응답:\n{raw}") from e

    scores = data.get("scores", data)  # "scores" 키가 없으면 최상위에서 직접 파싱 시도

    required_keys = {
        "job_fit", "career_consistency", "skill_match",
        "quantitative_achievement", "document_quality",
    }
    missing = required_keys - set(scores.keys())
    if missing:
        raise ValueError(f"점수 JSON에 필수 키 누락: {missing}\n원본:\n{raw}")

    return ScoreDetail(
        job_fit=ScoreItem(**scores["job_fit"]),
        career_consistency=ScoreItem(**scores["career_consistency"]),
        skill_match=ScoreItem(**scores["skill_match"]),
        quantitative_achievement=ScoreItem(**scores["quantitative_achievement"]),
        document_quality=ScoreItem(**scores["document_quality"]),
    )


class ScoringService:
    """5대 기준 점수 산정 서비스.

    llm_service와 rag_service를 주입받아 이력서+JD를 분석하고
    5개 기준별 점수(ScoreDetail)와 단순 평균 총점을 반환한다.
    JSON 파싱 실패 시 1회 재시도한다.
    """

    def __init__(self, llm_service: LLMService, rag_service: RAGService) -> None:
        self._llm = llm_service
        self._rag = rag_service

    async def score(self, request: AnalysisRequest) -> Tuple[ScoreDetail, float]:
        """이력서와 JD를 분석하여 5대 기준 점수 및 단순 평균 총점을 반환.

        Args:
            request: 분석 요청 데이터

        Returns:
            (ScoreDetail, total_score) 튜플 — total_score는 5개 점수의 단순 평균

        Raises:
            ValueError: LLM 응답 파싱 2회 모두 실패 시
        """
        # RAG 컨텍스트 검색
        rag_results = await self._rag.search_similar(
            f"{request.job_posting.job_title} {' '.join(request.job_posting.required_skills)}"
        )
        rag_context = "\n".join(f"- {doc}" for doc in rag_results) if rag_results else ""

        user_prompt = build_user_prompt(
            resume=request.resume,
            job_posting=request.job_posting,
            rag_context=rag_context,
        )

        # LLM 호출 + 파싱 실패 시 1회 재시도
        for attempt in range(1, 3):
            logger.info(
                "점수 산정 LLM 호출 (application_id: %d, 시도: %d/2)",
                request.application_id,
                attempt,
            )
            raw_response = await self._llm.generate(SCORING_SYSTEM_PROMPT, user_prompt)

            try:
                score_detail = _parse_score_response(raw_response)
                break
            except ValueError as e:
                logger.error(
                    "점수 JSON 파싱 실패 (application_id: %d, 시도: %d/2): %s",
                    request.application_id,
                    attempt,
                    e,
                )
                if attempt == 2:
                    raise

        total_score = round(
            (
                score_detail.job_fit.score
                + score_detail.career_consistency.score
                + score_detail.skill_match.score
                + score_detail.quantitative_achievement.score
                + score_detail.document_quality.score
            )
            / 5,
            1,
        )

        logger.info(
            "점수 산정 완료 (application_id: %d, 총점: %.1f)",
            request.application_id,
            total_score,
        )
        return score_detail, total_score
