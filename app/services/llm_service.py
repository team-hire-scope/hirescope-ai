import asyncio
import logging
import re
import time

from openai import AsyncOpenAI, APIConnectionError, APIStatusError

from app.config import get_settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2


def _strip_json_fences(text: str) -> str:
    """LLM 응답에서 ```json ... ``` 또는 ``` ... ``` 래핑을 제거한다."""
    text = text.strip()
    # ```json ... ``` 패턴
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


class LLMService:
    """LM Studio OpenAI 호환 API 호출 서비스.

    openai SDK를 사용하되 base_url을 LM Studio 주소로 설정하여
    로컬 LLM(Gemma 4 26B-A4B 등)을 호출한다.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key="lm-studio",  # LM Studio는 API 키 검증 안 함
            base_url=settings.lm_studio_base_url,
        )
        self._model = settings.lm_studio_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        logger.info(
            "LLM 서비스 초기화 (모델: %s, base_url: %s, temperature: %.1f)",
            self._model,
            settings.lm_studio_base_url,
            self._temperature,
        )

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """LLM에 프롬프트를 전달하고 응답 텍스트를 반환한다.

        연결 실패 시 최대 2회 재시도한다.
        응답에 포함된 ```json ... ``` 래핑을 자동으로 제거한다.

        Args:
            system_prompt: 역할/지시를 담은 시스템 프롬프트
            user_prompt: 실제 분석 요청 내용

        Returns:
            LLM이 생성한 텍스트 응답 (JSON 펜스 제거 후)

        Raises:
            RuntimeError: 재시도 후에도 호출 실패 시
        """
        last_error: Exception = RuntimeError("LLM 호출 실패")

        for attempt in range(1, _MAX_RETRIES + 2):  # 1, 2, 3 (최초 1회 + 재시도 2회)
            try:
                start = time.time()
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    # response_format 미사용: LM Studio가 json_object 미지원
                )
                elapsed = time.time() - start
                usage = response.usage
                token_info = (
                    f"입력 {usage.prompt_tokens} / 출력 {usage.completion_tokens} / 합계 {usage.total_tokens} 토큰"
                    if usage
                    else "토큰 정보 없음"
                )
                logger.info(
                    "LLM 호출 완료 (%.2f초, %s, 시도: %d/%d)",
                    elapsed,
                    token_info,
                    attempt,
                    _MAX_RETRIES + 1,
                )

                raw = response.choices[0].message.content or ""
                return _strip_json_fences(raw)

            except (APIConnectionError, APIStatusError) as e:
                last_error = e
                logger.warning(
                    "LLM 호출 실패 (시도 %d/%d): %s",
                    attempt,
                    _MAX_RETRIES + 1,
                    e,
                )
                if attempt <= _MAX_RETRIES:
                    await asyncio.sleep(1.0 * attempt)  # 재시도 전 대기
            except Exception as e:
                last_error = e
                logger.error("LLM 예상치 못한 오류 (시도 %d): %s", attempt, e)
                if attempt <= _MAX_RETRIES:
                    await asyncio.sleep(1.0 * attempt)

        raise RuntimeError(f"LLM 호출 {_MAX_RETRIES + 1}회 모두 실패: {last_error}") from last_error


def get_llm_service() -> LLMService:
    """FastAPI Depends용 LLM 서비스 팩토리."""
    return LLMService()
