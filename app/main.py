import logging

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.analysis_router import router as analysis_router

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HireScope AI",
    description="이력서 + JD 분석 AI 서버 (LM Studio 로컬 LLM 기반)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router, prefix="/api")


@app.on_event("startup")
async def startup_event() -> None:
    """앱 시작 시 LM Studio 연결 상태를 확인하고 로그로 출력."""
    logger.info("HireScope AI 서버 시작")
    logger.info("LM Studio URL: %s", settings.lm_studio_base_url)
    logger.info("사용 모델: %s", settings.lm_studio_model)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # LM Studio /v1/models 엔드포인트로 연결 확인
            base = settings.lm_studio_base_url.rstrip("/")
            response = await client.get(f"{base}/models")
            if response.status_code == 200:
                logger.info("LM Studio 연결 성공 (상태 코드: %d)", response.status_code)
            else:
                logger.warning(
                    "LM Studio 응답 이상 (상태 코드: %d)", response.status_code
                )
    except Exception as e:
        logger.warning(
            "LM Studio 연결 확인 실패: %s — 서버가 실행 중인지 확인하세요.", e
        )


@app.get("/health", tags=["헬스체크"])
async def health_check() -> dict:
    """서버 상태 확인 엔드포인트."""
    return {
        "status": "ok",
        "model": settings.lm_studio_model,
        "lm_studio_url": settings.lm_studio_base_url,
    }
