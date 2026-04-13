"""이력서 요약 프롬프트 모듈.

검증 완료된 시스템 프롬프트와 유저 프롬프트 빌더를 제공한다.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.request import ResumeData, JobPostingData

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


def _format_careers(resume: "ResumeData") -> str:
    """경력 목록을 사람이 읽기 좋은 텍스트로 변환."""
    if not resume.careers:
        return "경력 없음"
    lines = []
    for c in resume.careers:
        end = c.end_date or "현재"
        lines.append(
            f"- {c.company_name} | {c.job_title} | {c.rank} | {c.start_date} ~ {end}"
        )
        if c.description:
            lines.append(f"  담당업무: {c.description}")
        if c.achievements:
            lines.append(f"  정량적 성과: {c.achievements}")
    return "\n".join(lines)


def _format_educations(resume: "ResumeData") -> str:
    """학력 목록을 사람이 읽기 좋은 텍스트로 변환."""
    if not resume.educations:
        return "학력 정보 없음"
    lines = []
    for e in resume.educations:
        major = f" / {e.major}" if e.major else ""
        degree = f" ({e.degree})" if e.degree else ""
        end = e.end_date or "재학 중"
        lines.append(f"- {e.school_name}{major}{degree} ({e.start_date} ~ {end})")
    return "\n".join(lines)


def _format_skills(resume: "ResumeData") -> str:
    """기술 스택 목록을 사람이 읽기 좋은 텍스트로 변환."""
    if not resume.skills:
        return "기술 정보 없음"
    return ", ".join(
        f"{s.skill_name} ({s.level}, {s.duration_months}개월)" for s in resume.skills
    )


def _format_projects(resume: "ResumeData") -> str:
    """프로젝트 목록을 사람이 읽기 좋은 텍스트로 변환."""
    if not resume.projects:
        return "프로젝트 경험 없음"
    lines = []
    for p in resume.projects:
        role = f" | {p.role}" if p.role else ""
        period = f" | {p.period}" if p.period else ""
        lines.append(f"- {p.project_name}{role}{period}")
        if p.tech_stack:
            lines.append(f"  사용기술: {', '.join(p.tech_stack)}")
        if p.achievement_description:
            lines.append(f"  성과: {p.achievement_description}")
    return "\n".join(lines)


def _format_certifications(resume: "ResumeData") -> str:
    """자격증 목록을 사람이 읽기 좋은 텍스트로 변환."""
    if not resume.certifications:
        return "없음"
    return ", ".join(
        f"{c.name}({c.issuer or ''})" for c in resume.certifications
    )


def build_user_prompt(
    resume: "ResumeData",
    job_posting: "JobPostingData",
) -> str:
    """이력서와 JD 데이터를 받아 요약 생성용 유저 프롬프트를 생성한다.

    Args:
        resume: 이력서 데이터 모델
        job_posting: 채용 공고 데이터 모델

    Returns:
        LLM에 전달할 유저 프롬프트 텍스트
    """
    return f"""아래 이력서를 채용 공고 관점에서 3~5문장으로 요약해주세요.

## 채용 공고 (JD)

**회사명**: {job_posting.company_name}
**직무명**: {job_posting.job_title}
**요구 기술 스택**: {', '.join(job_posting.required_skills) or '없음'}
**우대 사항**: {job_posting.preferred_qualifications or '없음'}

## 이력서

**지원자명**: {resume.name}
**자기소개**:
{resume.summary or '없음'}

**경력 사항**:
{_format_careers(resume)}

**학력**:
{_format_educations(resume)}

**보유 기술**:
{_format_skills(resume)}

**프로젝트 경험**:
{_format_projects(resume)}

**자격증**: {_format_certifications(resume)}

JD 적합성을 중심으로 강점과 약점을 균형 있게 서술하고, JSON 형식으로만 응답해주세요."""
