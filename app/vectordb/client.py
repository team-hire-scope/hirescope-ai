import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb 패키지를 찾을 수 없습니다. RAG 기능이 비활성화됩니다.")


class ChromaDBClient:
    """ChromaDB 클라이언트 래퍼.

    연결 실패 시 앱은 정상 기동되며, 모든 메서드는 graceful fallback을 제공한다.
    """

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self._client: Optional[object] = None
        self._host = host
        self._port = port
        self._connect()

    def _connect(self) -> None:
        """ChromaDB에 연결을 시도한다. 실패해도 앱은 계속 실행된다."""
        if not CHROMADB_AVAILABLE:
            return
        try:
            self._client = chromadb.HttpClient(host=self._host, port=self._port)
            self._client.heartbeat()  # 연결 확인
            logger.info("ChromaDB 연결 성공 (%s:%d)", self._host, self._port)
        except Exception as e:
            logger.warning("ChromaDB 연결 실패 (RAG 비활성화): %s", e)
            self._client = None

    @property
    def is_connected(self) -> bool:
        """ChromaDB 연결 상태 반환."""
        return self._client is not None

    def get_or_create_collection(self, name: str) -> Optional[object]:
        """컬렉션 조회 또는 생성.

        Args:
            name: 컬렉션 이름

        Returns:
            컬렉션 객체. 연결 실패 시 None.
        """
        if not self.is_connected:
            return None
        try:
            return self._client.get_or_create_collection(name=name)
        except Exception as e:
            logger.error("컬렉션 조회/생성 실패 (%s): %s", name, e)
            return None

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        ids: List[str],
        metadatas: Optional[List[dict]] = None,
    ) -> bool:
        """문서를 컬렉션에 추가한다.

        Args:
            collection_name: 대상 컬렉션 이름
            documents: 추가할 문서 텍스트 목록
            ids: 각 문서의 고유 ID 목록
            metadatas: 각 문서의 메타데이터 (선택)

        Returns:
            추가 성공 여부
        """
        collection = self.get_or_create_collection(collection_name)
        if collection is None:
            return False
        try:
            collection.add(documents=documents, ids=ids, metadatas=metadatas)
            logger.info("문서 %d개 추가 완료 (컬렉션: %s)", len(documents), collection_name)
            return True
        except Exception as e:
            logger.error("문서 추가 실패 (컬렉션: %s): %s", collection_name, e)
            return False

    def query(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 3,
    ) -> List[str]:
        """유사 문서를 벡터 검색한다.

        Args:
            collection_name: 검색할 컬렉션 이름
            query_texts: 검색 쿼리 텍스트 목록
            n_results: 반환할 결과 수

        Returns:
            유사 문서 텍스트 목록. 연결 실패 또는 오류 시 빈 리스트.
        """
        collection = self.get_or_create_collection(collection_name)
        if collection is None:
            return []
        try:
            results = collection.query(query_texts=query_texts, n_results=n_results)
            documents = results.get("documents", [[]])
            return documents[0] if documents else []
        except Exception as e:
            logger.error("벡터 검색 실패 (컬렉션: %s): %s", collection_name, e)
            return []


_client_instance: Optional[ChromaDBClient] = None


def get_chroma_client(host: str = "localhost", port: int = 8000) -> ChromaDBClient:
    """싱글턴 ChromaDB 클라이언트를 반환한다."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ChromaDBClient(host=host, port=port)
    return _client_instance
