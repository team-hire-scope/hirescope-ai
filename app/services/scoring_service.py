import json
import logging
from typing import Any, Dict

from app.models.request import AnalysisRequest
from app.models.response import ScoreCriteria, ScoreDetail
from app.prompts.scoring_prompt import SCORING_SYSTEM_PROMPT, SCORING_USER_PROMPT_TEMPLATE
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# 5대 기준 가중치 (균등 20%)
SCORE_WEIGHTS = {
    "job_fit": 0.20,
    "career_consistency": 0.20,
    "skill_match": 0.20,
    "quantitative_achievement": 0.20,
    "document_quality": 0.20,
}


def _format_careers(request: AnalysisRequest) -> str:
    """경력 정보를 프롬프트용 텍스트로 변환."""
    if not request.resume.careers:
        return "경력 없음"
    lines = []
    for c in request.resume.careers:
        end = c.end_date or "현재"
        desc = f" — {c.description}" if c.description else ""
        lines.append(f"- {c.company_name} | {c.position} ({c.start_date} ~ {end}){desc}")
    return "\n".join(lines)


def _format_educations(request: AnalysisRequest) -> str:
    """학력 정보를 프롬프트용 텍스트로 변환."""
    if not request.resume.educations:
        return "학력 정보 없음"
    lines = []
    for e in request.resume.educations:
        major = f" / {e.major}" if e.major else ""
        degree = f" ({e.degree})" if e.degree else ""
        end = e.end_date or "재학 중"
        lines.append(f"- {e.institution}{major}{degree} ({e.start_date} ~ {end})")
    return "\n".join(lines)


def _format_projects(request: AnalysisRequest) -> str:
    """프로젝트 정보를 프롬프트용 텍스트로 변환."""
    if not request.resume.projects:
        return "프로젝트 경험 없음"
    lines = []
    for p in request.resume.projects:
        tech = f" [기술: {', '.join(p.tech_stack)}]" if p.tech_stack else ""
        desc = f"\n  {p.description}" if p.description else ""
        lines.append(f"- {p.name}{tech}{desc}")
    return "\n".join(lines)


def _format_certifications(request: AnalysisRequest) -> str:
    """자격증 정보를 프롬프트용 텍스트로 변환."""
    if not request.resume.certifications:
        return "없음"
    return ", ".join(
        f"{c.name}({c.issuer or ''})" for c in request.resume.certifications
    )


def _parse_score_response(raw: str) -> Dict[str, Any]:
    """LLM 응답에서 JSON을 추출하여 파싱."""
    raw = raw.strip()
    # 코드 블록 제거
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


class ScoringService:
    """5대 기준 점수 산정 서비스."""

    def __init__(self, llm_service: LLMService, rag_service: RAGService) -> None:
        self._llm = llm_service
        self._rag = rag_service

    async def score(self, request: AnalysisRequest) -> tuple[ScoreDetail, float]:
        """이력서와 JD를 분석하여 5대 기준 점수 및 총점을 반환.

        Args:
            request: 분석 요청 데이터

        Returns:
            (ScoreDetail, total_score) 튜플
        """
        # RAG 컨텍스트 검색
        rag_results = await self._rag.search_similar(
            f"{request.job_posting.job_title} {' '.join(request.job_posting.required_skills)}"
        )
        rag_context = ""
        if rag_results:
            rag_context = "\n## 유사 직무 참고 데이터\n" + "\n".join(
                f"- {doc}" for doc in rag_results
            )

        user_prompt = SCORING_USER_PROMPT_TEMPLATE.format(
            company_name=request.job_posting.company_name,
            job_title=request.job_posting.job_title,
            job_description=request.job_posting.description,
            required_skills=", ".join(request.job_posting.required_skills),
            preferred_qualifications=request.job_posting.preferred_qualifications or "없음",
            candidate_name=request.resume.name,
            introduction=request.resume.introduction or "없음",
            careers=_format_careers(request),
            educations=_format_educations(request),
            skills=", ".join(request.resume.skills),
            projects=_format_projects(request),
            certifications=_format_certifications(request),
            rag_context=rag_context,
        )

        logger.info("점수 산정 LLM 호출 (application_id: %d)", request.application_id)
        raw_response = await self._llm.generate(SCORING_SYSTEM_PROMPT, user_prompt)

        parsed = _parse_score_response(raw_response)

        score_detail = ScoreDetail(
            job_fit=ScoreCriteria(**parsed["job_fit"]),
            career_consistency=ScoreCriteria(**parsed["career_consistency"]),
            skill_match=ScoreCriteria(**parsed["skill_match"]),
            quantitative_achievement=ScoreCriteria(**parsed["quantitative_achievement"]),
            document_quality=ScoreCriteria(**parsed["document_quality"]),
        )

        total_score = round(
            score_detail.job_fit.score * SCORE_WEIGHTS["job_fit"]
            + score_detail.career_consistency.score * SCORE_WEIGHTS["career_consistency"]
            + score_detail.skill_match.score * SCORE_WEIGHTS["skill_match"]
            + score_detail.quantitative_achievement.score * SCORE_WEIGHTS["quantitative_achievement"]
            + score_detail.document_quality.score * SCORE_WEIGHTS["document_quality"],
            1,
        )

        logger.info("점수 산정 완료 (application_id: %d, 총점: %.1f)", request.application_id, total_score)
        return score_detail, total_score
