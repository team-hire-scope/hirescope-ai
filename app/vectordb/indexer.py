import logging
from typing import List, Optional

from app.vectordb.client import ChromaDBClient, get_chroma_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hirescope_rag"


class VectorIndexer:
    """RAG용 데이터를 벡터 DB에 인덱싱하는 유틸리티.

    JD 사례, 우수 이력서 패턴 등을 인덱싱하여 RAG 품질 향상에 활용할 수 있다.
    """

    def __init__(self, client: Optional[ChromaDBClient] = None) -> None:
        self._client = client or get_chroma_client()

    async def index_documents(self, documents: List[str], ids: List[str]) -> bool:
        """문서 목록을 벡터 DB에 인덱싱한다.

        Args:
            documents: 인덱싱할 텍스트 목록
            ids: 각 문서의 고유 ID

        Returns:
            인덱싱 성공 여부
        """
        logger.info("문서 인덱싱 시작: %d개", len(documents))
        return self._client.add_documents(
            collection_name=COLLECTION_NAME,
            documents=documents,
            ids=ids,
        )

    async def index_job_descriptions(self, jd_texts: List[str]) -> bool:
        """채용 공고 JD를 벡터 DB에 인덱싱한다.

        Args:
            jd_texts: JD 텍스트 목록

        Returns:
            인덱싱 성공 여부
        """
        if not jd_texts:
            return False
        ids = [f"jd_{i}" for i in range(len(jd_texts))]
        logger.info("JD 인덱싱 시작: %d개", len(jd_texts))
        return self._client.add_documents(
            collection_name=COLLECTION_NAME,
            documents=jd_texts,
            ids=ids,
            metadatas=[{"type": "job_description"} for _ in jd_texts],
        )

    async def index_resume_patterns(self, resume_texts: List[str]) -> bool:
        """우수 이력서 패턴을 벡터 DB에 인덱싱한다.

        Args:
            resume_texts: 이력서 텍스트 목록

        Returns:
            인덱싱 성공 여부
        """
        if not resume_texts:
            return False
        ids = [f"resume_{i}" for i in range(len(resume_texts))]
        logger.info("이력서 패턴 인덱싱 시작: %d개", len(resume_texts))
        return self._client.add_documents(
            collection_name=COLLECTION_NAME,
            documents=resume_texts,
            ids=ids,
            metadatas=[{"type": "resume_pattern"} for _ in resume_texts],
        )
