import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.request import AnalysisRequest
from app.models.response import AnalysisResponse
from app.services.llm_service import LLMService, get_llm_service
from app.services.question_service import QuestionService
from app.services.rag_service import RAGService, get_rag_service
from app.services.scoring_service import ScoringService
from app.services.summary_service import SummaryService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["분석"])


@router.post(
    "/analysis",
    response_model=AnalysisResponse,
    summary="이력서 + JD 분석",
    description="이력서와 채용 공고를 분석하여 점수, 요약, 면접 질문을 반환합니다.",
)
async def analyze(
    request: AnalysisRequest,
    llm_service: LLMService = Depends(get_llm_service),
    rag_service: RAGService = Depends(get_rag_service),
) -> AnalysisResponse:
    """이력서 + JD 통합 분석 엔드포인트.

    scoring_service → question_service → summary_service 순서로 순차 호출하고
    각 단계의 소요 시간을 로깅한다. total_score는 5개 점수의 단순 평균으로 계산한다.

    Args:
        request: Spring Boot에서 전달받은 분석 요청 데이터
        llm_service: LLM 서비스 (DI)
        rag_service: RAG 검색 서비스 (DI)

    Returns:
        점수, 요약, 면접 질문을 담은 분석 결과

    Raises:
        HTTPException 422: 입력 데이터 검증 실패 또는 LLM 응답 파싱 실패
        HTTPException 500: 분석 처리 중 내부 오류
    """
    logger.info("분석 요청 수신 (application_id: %d)", request.application_id)

    scoring_service = ScoringService(llm_service=llm_service, rag_service=rag_service)
    question_service = QuestionService(llm_service=llm_service)
    summary_service = SummaryService(llm_service=llm_service)

    try:
        # 1. 점수 산정
        t0 = time.time()
        score_detail, total_score = await scoring_service.score(request)
        logger.info(
            "점수 산정 완료 (application_id: %d, 총점: %.1f, 소요: %.2f초)",
            request.application_id,
            total_score,
            time.time() - t0,
        )

        # 2. 면접 질문 생성
        t0 = time.time()
        interview_questions = await question_service.generate_questions(request)
        logger.info(
            "면접 질문 생성 완료 (application_id: %d, %d개, 소요: %.2f초)",
            request.application_id,
            len(interview_questions),
            time.time() - t0,
        )

        # 3. 이력서 요약
        t0 = time.time()
        summary = await summary_service.summarize(request)
        logger.info(
            "이력서 요약 완료 (application_id: %d, 소요: %.2f초)",
            request.application_id,
            time.time() - t0,
        )

    except ValueError as e:
        logger.error(
            "분석 데이터 파싱 오류 (application_id: %d): %s",
            request.application_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"LLM 응답 파싱 실패: {e}",
        ) from e
    except Exception as e:
        logger.error(
            "분석 처리 중 오류 (application_id: %d): %s",
            request.application_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 처리 중 오류가 발생했습니다.",
        ) from e

    response = AnalysisResponse(
        application_id=request.application_id,
        total_score=total_score,
        scores=score_detail,
        summary=summary,
        interview_questions=interview_questions,
    )

    logger.info(
        "분석 완료 (application_id: %d, 총점: %.1f, 질문: %d개)",
        request.application_id,
        total_score,
        len(interview_questions),
    )
    return response
