import logging
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMService(ABC):
    """LLM 호출 추상 인터페이스. 다른 LLM 제공자로 교체 시 이 클래스를 구현."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """LLM에 프롬프트를 전달하고 응답 텍스트를 반환.

        Args:
            system_prompt: 역할/지시를 담은 시스템 프롬프트
            user_prompt: 실제 분석 요청 내용

        Returns:
            LLM이 생성한 텍스트 응답
        """


class OpenAIService(LLMService):
    """OpenAI 호환 LLM 서비스 구현체. OpenAI API 및 LM Studio 등 로컬 LLM 지원."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.llm_base_url,
        )
        self._model = settings.llm_model
        logger.info("LLM 서비스 초기화 완료 (모델: %s, base_url: %s)", self._model, settings.llm_base_url)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """OpenAI Chat Completions API를 호출하여 응답을 반환.

        Args:
            system_prompt: 역할/지시를 담은 시스템 프롬프트
            user_prompt: 실제 분석 요청 내용

        Returns:
            GPT가 생성한 텍스트 응답
        """
        logger.debug("LLM 호출 시작 (모델: %s)", self._model)
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        result = response.choices[0].message.content or ""
        logger.debug("LLM 호출 완료 (응답 길이: %d자)", len(result))
        return result


def get_llm_service() -> LLMService:
    """FastAPI Depends용 LLM 서비스 팩토리."""
    return OpenAIService()
