import logging
from typing import List

from app.config import get_settings
from app.vectordb.client import ChromaDBClient, get_chroma_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hirescope_rag"


class RAGService:
    """벡터 DB 기반 유사 문서 검색 서비스.

    ChromaDB가 연결되지 않은 경우 빈 컨텍스트를 반환하여 graceful fallback 처리.
    """

    def __init__(self, chroma_client: ChromaDBClient) -> None:
        self._client = chroma_client

    async def search_similar(self, query: str, top_k: int = 3) -> List[str]:
        """쿼리와 유사한 문서를 벡터 DB에서 검색.

        Args:
            query: 검색 쿼리 텍스트 (직무명, 기술스택 등)
            top_k: 반환할 최대 문서 수

        Returns:
            유사 문서 텍스트 목록. 연결 실패 또는 결과 없으면 빈 리스트.
        """
        if not self._client.is_connected:
            logger.debug("ChromaDB 미연결 — 빈 RAG 컨텍스트 반환")
            return []

        results = self._client.query(
            collection_name=COLLECTION_NAME,
            query_texts=[query],
            n_results=top_k,
        )
        logger.debug("RAG 검색 결과 %d개 반환", len(results))
        return results


def get_rag_service() -> RAGService:
    """FastAPI Depends용 RAG 서비스 팩토리."""
    settings = get_settings()
    client = get_chroma_client(host=settings.chroma_host, port=settings.chroma_port)
    return RAGService(chroma_client=client)
