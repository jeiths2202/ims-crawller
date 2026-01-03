"""
Vector Database Example using ChromaDB
For large-scale IMS issue search with metadata filtering
"""
import json
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions

class IMSVectorDatabase:
    """IMS 이슈용 벡터 데이터베이스"""

    def __init__(self, db_path="data/vector_db"):
        """
        Args:
            db_path: ChromaDB 저장 경로
        """
        # ChromaDB 클라이언트 초기화 (영구 저장)
        self.client = chromadb.PersistentClient(path=db_path)

        # 다국어 임베딩 함수
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        # 컬렉션 생성 (또는 기존 컬렉션 로드)
        self.collection = self.client.get_or_create_collection(
            name="ims_comments",
            embedding_function=self.embedding_fn,
            metadata={"description": "IMS issue comments with metadata"}
        )

    def index_session_folder(self, session_folder_path):
        """
        크롤링 세션 폴더 전체를 벡터 DB에 인덱싱

        Args:
            session_folder_path: 세션 폴더 경로 (예: data/crawl_sessions/OpenFrame_...)
        """
        session_folder = Path(session_folder_path)
        indexed_count = 0

        for json_file in session_folder.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                issue = json.load(f)

            issue_id = issue.get('issue_id')
            comments = issue.get('comments', [])

            if not comments:
                continue

            # 각 댓글을 개별 문서로 인덱싱
            for i, comment in enumerate(comments):
                doc_id = f"{issue_id}_comment_{i}"
                content = comment.get('content', '')

                if not content:
                    continue

                # 메타데이터 구성
                metadata = {
                    'issue_id': str(issue_id),
                    'title': issue.get('title', '')[:100],  # ChromaDB는 문자열 길이 제한 있음
                    'product': issue.get('product', ''),
                    'status': issue.get('status', ''),
                    'author': comment.get('author', ''),
                    'created_date': comment.get('created_date', ''),
                    'comment_index': i
                }

                # 인덱싱
                self.collection.add(
                    documents=[content],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                indexed_count += 1

        print(f"✅ Indexed {indexed_count} comments from {len(list(session_folder.glob('*.json')))} issues")

    def search(self, query, n_results=10, filters=None):
        """
        시맨틱 검색 + 메타데이터 필터링

        Args:
            query: 검색 쿼리 (한/영/일 혼용 가능)
            n_results: 반환할 결과 수
            filters: 메타데이터 필터 (예: {'product': 'OpenFrame Batch', 'status': 'Closed'})

        Returns:
            List of search results with content, metadata, and distance
        """
        where_filter = filters if filters else None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        # 결과 포맷팅
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],  # 낮을수록 유사
                'similarity': 1 - results['distances'][0][i]  # 0~1로 정규화
            })

        return formatted_results

    def get_stats(self):
        """데이터베이스 통계"""
        count = self.collection.count()
        return {
            'total_comments': count,
            'collection_name': self.collection.name
        }


# ============================================================
# 사용 예시
# ============================================================

if __name__ == "__main__":
    # 벡터 DB 초기화
    db = IMSVectorDatabase()

    # 1. 세션 폴더 인덱싱
    print("📂 Indexing session folder...")
    session_folder = "data/crawl_sessions/OpenFrame_TPETIME_20260103_045204"
    db.index_session_folder(session_folder)

    # 통계 확인
    stats = db.get_stats()
    print(f"\n📊 Database Stats: {stats}")

    # 2. 기본 시맨틱 검색
    print("\n" + "=" * 80)
    print("🔍 Example 1: Basic Semantic Search")
    print("=" * 80)

    query1 = "TPETIME 에러 해결 방법"
    results1 = db.search(query1, n_results=5)

    print(f"\nQuery: '{query1}'")
    for i, result in enumerate(results1, 1):
        print(f"\n[{i}] 유사도: {result['similarity']:.3f}")
        print(f"이슈 ID: {result['metadata']['issue_id']}")
        print(f"제목: {result['metadata']['title']}")
        print(f"작성자: {result['metadata']['author']}")
        print(f"내용: {result['content'][:150]}...")

    # 3. 메타데이터 필터링 검색
    print("\n" + "=" * 80)
    print("🔍 Example 2: Filtered Search (Closed issues only)")
    print("=" * 80)

    query2 = "timeout error"
    results2 = db.search(
        query2,
        n_results=5,
        filters={'status': 'Closed'}  # Closed 이슈만
    )

    print(f"\nQuery: '{query2}' (Status=Closed)")
    for i, result in enumerate(results2, 1):
        print(f"\n[{i}] 유사도: {result['similarity']:.3f}")
        print(f"이슈 ID: {result['metadata']['issue_id']}")
        print(f"상태: {result['metadata']['status']}")
        print(f"내용: {result['content'][:150]}...")

    # 4. 제품별 검색
    print("\n" + "=" * 80)
    print("🔍 Example 3: Product-Specific Search")
    print("=" * 80)

    query3 = "batch job failure"
    results3 = db.search(
        query3,
        n_results=5,
        filters={'product': 'OpenFrame Batch'}
    )

    print(f"\nQuery: '{query3}' (Product=OpenFrame Batch)")
    for i, result in enumerate(results3, 1):
        print(f"\n[{i}] 유사도: {result['similarity']:.3f}")
        print(f"제품: {result['metadata']['product']}")
        print(f"내용: {result['content'][:150]}...")
