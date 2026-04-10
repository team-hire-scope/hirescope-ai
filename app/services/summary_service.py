import logging

from app.models.request import AnalysisRequest
from app.prompts.summary_prompt import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT_TEMPLATE
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


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


class SummaryService:
    """이력서 핵심 요약 생성 서비스."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def summarize(self, request: AnalysisRequest) -> str:
        """이력서 핵심 정보를 3~5문장으로 요약.

        Args:
            request: 분석 요청 데이터

        Returns:
            이력서 요약 텍스트 (3~5문장)
        """
        user_prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(
            candidate_name=request.resume.name,
            introduction=request.resume.introduction or "없음",
            careers=_format_careers(request),
            educations=_format_educations(request),
            skills=", ".join(request.resume.skills),
            projects=_format_projects(request),
            certifications=_format_certifications(request),
        )

        logger.info("이력서 요약 LLM 호출 (application_id: %d)", request.application_id)
        summary = await self._llm.generate(SUMMARY_SYSTEM_PROMPT, user_prompt)
        summary = summary.strip()

        logger.info("이력서 요약 완료 (application_id: %d)", request.application_id)
        return summary
