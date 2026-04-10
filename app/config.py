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

    # LLM 설정
    openai_api_key: str = Field(default="lm-studio", description="OpenAI API 키 (로컬 LLM 사용 시 임의 값)")
    llm_model: str = Field(default="gemma-3-27b-it", description="사용할 LLM 모델명")
    llm_base_url: str = Field(default="http://localhost:1234/v1", description="LLM API 베이스 URL (LM Studio 기본값)")

    # Vector DB 설정
    vector_db_type: str = Field(default="chroma", description="벡터 DB 유형")
    chroma_host: str = Field(default="localhost", description="ChromaDB 호스트")
    chroma_port: int = Field(default=8001, description="ChromaDB 포트")

    # Redis 설정
    redis_url: str = Field(default="redis://localhost:6379", description="Redis 연결 URL")

    # CORS 설정
    allowed_origins: str = Field(
        default="http://localhost:8080,http://localhost:3000",
        description="허용할 오리진 목록 (쉼표 구분)",
    )

    def get_allowed_origins(self) -> List[str]:
        """허용 오리진 목록을 리스트로 반환."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """싱글턴 설정 인스턴스 반환."""
    return Settings()
