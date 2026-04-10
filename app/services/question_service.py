import json
import logging
from typing import List

from app.models.request import AnalysisRequest
from app.models.response import InterviewQuestion
from app.prompts.question_prompt import QUESTION_SYSTEM_PROMPT, QUESTION_USER_PROMPT_TEMPLATE
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


def _parse_questions_response(raw: str) -> List[dict]:
    """LLM 응답에서 JSON 배열을 추출하여 파싱."""
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


class QuestionService:
    """이력서-JD 갭 분석 기반 면접 질문 생성 서비스."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def generate_questions(self, request: AnalysisRequest) -> List[InterviewQuestion]:
        """이력서와 JD를 분석하여 예상 면접 질문 5~10개를 생성.

        Args:
            request: 분석 요청 데이터

        Returns:
            면접 질문 목록 (question, intent, answer_guide 포함)
        """
        user_prompt = QUESTION_USER_PROMPT_TEMPLATE.format(
            company_name=request.job_posting.company_name,
            job_title=request.job_posting.job_title,
            job_description=request.job_posting.description,
            required_skills=", ".join(request.job_posting.required_skills),
            preferred_qualifications=request.job_posting.preferred_qualifications or "없음",
            candidate_name=request.resume.name,
            introduction=request.resume.introduction or "없음",
            careers=_format_careers(request),
            skills=", ".join(request.resume.skills),
            projects=_format_projects(request),
        )

        logger.info("면접 질문 생성 LLM 호출 (application_id: %d)", request.application_id)
        raw_response = await self._llm.generate(QUESTION_SYSTEM_PROMPT, user_prompt)

        parsed = _parse_questions_response(raw_response)
        questions = [InterviewQuestion(**item) for item in parsed]

        logger.info(
            "면접 질문 생성 완료 (application_id: %d, 질문 수: %d)",
            request.application_id,
            len(questions),
        )
        return questions
