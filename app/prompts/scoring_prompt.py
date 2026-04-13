"""점수 산정 프롬프트 모듈.

검증 완료된 시스템 프롬프트와 유저 프롬프트 빌더를 제공한다.
total_score는 LLM에게 맡기지 않고 코드에서 직접 계산한다.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.request import ResumeData, JobPostingData

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
    rag_context: str = "",
) -> str:
    """이력서와 JD 데이터를 받아 점수 산정용 유저 프롬프트를 생성한다.

    Args:
        resume: 이력서 데이터 모델
        job_posting: 채용 공고 데이터 모델
        rag_context: RAG 검색 결과 컨텍스트 (없으면 빈 문자열)

    Returns:
        LLM에 전달할 유저 프롬프트 텍스트
    """
    rag_section = ""
    if rag_context:
        rag_section = f"\n## 유사 직무 참고 데이터\n{rag_context}\n"

    return f"""다음 이력서와 채용 공고를 분석하여 5가지 기준으로 점수를 산정해주세요.

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

**학력**:
{_format_educations(resume)}

**보유 기술**:
{_format_skills(resume)}

**프로젝트 경험**:
{_format_projects(resume)}

**자격증**: {_format_certifications(resume)}
{rag_section}
위 정보를 바탕으로 5가지 기준별 점수와 근거를 JSON 형식으로 출력해주세요."""
