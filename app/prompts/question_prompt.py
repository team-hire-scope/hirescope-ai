"""면접 질문 생성 프롬프트 모듈.

검증 완료된 시스템 프롬프트와 유저 프롬프트 빌더를 제공한다.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.request import ResumeData, JobPostingData

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


def build_user_prompt(
    resume: "ResumeData",
    job_posting: "JobPostingData",
) -> str:
    """이력서와 JD 데이터를 받아 면접 질문 생성용 유저 프롬프트를 생성한다.

    Args:
        resume: 이력서 데이터 모델
        job_posting: 채용 공고 데이터 모델

    Returns:
        LLM에 전달할 유저 프롬프트 텍스트
    """
    return f"""아래 이력서와 채용 공고를 분석하여 예상 면접 질문을 7~10개 생성해주세요.

## 채용 공고 (JD)

**회사명**: {job_posting.company_name}
**직무명**: {job_posting.job_title}
**직무 설명**:
{job_posting.description}

**요구 기술 스택**: {', '.join(job_posting.required_skills) or '없음'}
**우대 사항**: {job_posting.preferred_qualifications or '없음'}

## 이력서

**지원자명**: {resume.name}
**자기소개**:
{resume.summary or '없음'}

**경력 사항**:
{_format_careers(resume)}

**보유 기술**:
{_format_skills(resume)}

**프로젝트 경험**:
{_format_projects(resume)}

## 분석 지침

1. 이력서와 JD 간의 갭(기술, 경험, 역량)을 우선 파악하세요.
2. 갭 영역에 대한 검증 질문을 우선 생성하세요.
3. 이력서의 강점도 심층 검증하는 질문을 포함하세요.
4. STAR 기법으로 답변할 수 있는 행동면접 질문을 중심으로 작성하세요.
5. 각 질문의 의도와 이상적인 답변 방향을 구체적으로 작성하세요.

JSON 형식으로만 응답해주세요."""
