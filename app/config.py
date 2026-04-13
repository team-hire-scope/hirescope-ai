from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 환경 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LM Studio 설정
    lm_studio_base_url: str = Field(
        default="http://localhost:1234/v1",
        description="LM Studio OpenAI 호환 API 베이스 URL",
    )
    lm_studio_model: str = Field(
        default="gemma-4-26b-a4b-it",
        description="LM Studio에 로드된 모델명",
    )
    llm_temperature: float = Field(
        default=0.3,
        description="LLM 온도 (점수 일관성을 위해 낮게 설정)",
    )
    llm_max_tokens: int = Field(
        default=2000,
        description="LLM 최대 출력 토큰 수",
    )

    # ChromaDB 설정
    chroma_host: str = Field(default="localhost", description="ChromaDB 호스트")
    chroma_port: int = Field(default=8000, description="ChromaDB 포트")

    # Redis 설정
    redis_url: str = Field(default="redis://localhost:6379", description="Redis 연결 URL")

    # CORS 설정
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="허용할 오리진 목록 (쉼표 구분)",
    )

    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨 (DEBUG/INFO/WARNING/ERROR)")

    def get_allowed_origins(self) -> List[str]:
        """허용 오리진 목록을 리스트로 반환."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """싱글턴 설정 인스턴스 반환."""
    return Settings()
