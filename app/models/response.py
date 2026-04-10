from typing import List

from pydantic import BaseModel, Field


class ScoreCriteria(BaseModel):
    """개별 평가 기준 점수 및 근거."""

    score: float = Field(description="점수 (1~100)", ge=1, le=100)
    reason: str = Field(description="점수 산정 근거")


class ScoreDetail(BaseModel):
    """5대 평가 기준 상세 점수."""

    job_fit: ScoreCriteria = Field(description="직무 적합도")
    career_consistency: ScoreCriteria = Field(description="경력 일관성")
    skill_match: ScoreCriteria = Field(description="기술 스택 매칭")
    quantitative_achievement: ScoreCriteria = Field(description="정량적 성과")
    document_quality: ScoreCriteria = Field(description="문서 품질")


class InterviewQuestion(BaseModel):
    """면접 질문 및 가이드."""

    question: str = Field(description="면접 질문")
    intent: str = Field(description="질문 의도")
    answer_guide: str = Field(description="STAR 기법 기반 답변 가이드")


class AnalysisResponse(BaseModel):
    """분석 결과 응답 모델."""

    application_id: int = Field(description="지원서 ID")
    total_score: float = Field(description="종합 점수 (1~100)", ge=1, le=100)
    scores: ScoreDetail = Field(description="5대 기준 상세 점수")
    summary: str = Field(description="이력서 핵심 요약 (3~5문장)")
    interview_questions: List[InterviewQuestion] = Field(description="예상 면접 질문 목록")
