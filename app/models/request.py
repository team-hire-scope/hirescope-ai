from typing import List, Optional

from pydantic import BaseModel, Field


class CareerData(BaseModel):
    """경력 정보."""

    company_name: str = Field(description="회사명")
    job_title: str = Field(description="직무 (예: 백엔드 개발자)")
    rank: str = Field(description="직급 (예: 시니어, 주니어, 인턴)")
    start_date: str = Field(description="입사일 (YYYY-MM)")
    end_date: Optional[str] = Field(default=None, description="퇴사일 (YYYY-MM), 재직 중이면 None")
    description: Optional[str] = Field(default=None, description="담당 업무 설명")
    achievements: Optional[str] = Field(default=None, description="정량적 성과 (수치 포함)")


class EducationData(BaseModel):
    """학력 정보."""

    school_name: str = Field(description="학교명")
    major: Optional[str] = Field(default=None, description="전공")
    degree: Optional[str] = Field(default=None, description="학위 (학사/석사/박사 등)")
    start_date: str = Field(description="입학일 (YYYY-MM)")
    end_date: Optional[str] = Field(default=None, description="졸업일 (YYYY-MM), 재학 중이면 None")


class SkillData(BaseModel):
    """기술 스택 정보."""

    skill_name: str = Field(description="기술명 (예: Java, Spring Boot)")
    level: str = Field(description="숙련도 (상/중/하)")
    duration_months: int = Field(description="사용 기간 (개월)")


class ProjectData(BaseModel):
    """프로젝트 정보."""

    project_name: str = Field(description="프로젝트명")
    role: Optional[str] = Field(default=None, description="담당 역할 (예: 테크 리드, 메인 개발자)")
    period: Optional[str] = Field(default=None, description="프로젝트 기간 (예: 2023.01 ~ 2023.12)")
    tech_stack: List[str] = Field(default_factory=list, description="사용 기술 목록")
    achievement_description: Optional[str] = Field(default=None, description="성과 설명")


class CertificationData(BaseModel):
    """자격증 정보."""

    name: str = Field(description="자격증명")
    issuer: Optional[str] = Field(default=None, description="발급 기관")
    acquired_date: Optional[str] = Field(default=None, description="취득일 (YYYY-MM)")


class ResumeData(BaseModel):
    """이력서 데이터."""

    name: str = Field(description="지원자 이름")
    summary: Optional[str] = Field(default=None, description="자기소개 요약")
    careers: List[CareerData] = Field(default_factory=list, description="경력 목록")
    educations: List[EducationData] = Field(default_factory=list, description="학력 목록")
    skills: List[SkillData] = Field(default_factory=list, description="보유 기술 스택 목록")
    projects: List[ProjectData] = Field(default_factory=list, description="프로젝트 목록")
    certifications: List[CertificationData] = Field(default_factory=list, description="자격증 목록")


class JobPostingData(BaseModel):
    """채용 공고 데이터."""

    company_name: str = Field(description="회사명")
    job_title: str = Field(description="채용 직무명")
    description: str = Field(description="직무 설명 (JD 본문)")
    required_skills: List[str] = Field(default_factory=list, description="요구 기술 스택")
    preferred_qualifications: Optional[str] = Field(default=None, description="우대 사항")


class AnalysisRequest(BaseModel):
    """Spring Boot에서 전달받는 분석 요청 모델."""

    application_id: int = Field(description="지원서 ID")
    resume: ResumeData = Field(description="이력서 데이터")
    job_posting: JobPostingData = Field(description="채용 공고 데이터")
