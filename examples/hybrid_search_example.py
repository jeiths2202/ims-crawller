"""
Hybrid Search Example: BM25 (Keyword) + Semantic Search (Dense)
Best accuracy for RAG systems
"""
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np
from typing import List, Dict, Tuple

class HybridSearchEngine:
    """하이브리드 검색 엔진: 키워드 + 시맨틱 검색 결합"""

    def __init__(self,
                 semantic_model='paraphrase-multilingual-MiniLM-L12-v2',
                 bm25_weight=0.3,
                 semantic_weight=0.7):
        """
        Args:
            semantic_model: 시맨틱 임베딩 모델
            bm25_weight: BM25 점수 가중치 (0~1)
            semantic_weight: 시맨틱 점수 가중치 (0~1)
        """
        print(f"Loading semantic model: {semantic_model}")
        self.semantic_model = SentenceTransformer(semantic_model)
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight

        # 인덱스 데이터
        self.documents = []  # 원본 댓글 딕셔너리
        self.contents = []   # 댓글 텍스트
        self.bm25 = None
        self.embeddings = None

    def index_comments(self, comments: List[Dict]):
        """
        댓글 리스트 인덱싱

        Args:
            comments: 댓글 리스트 [{'content': '...', 'author': '...', ...}]
        """
        if not comments:
            return

        self.documents = comments
        self.contents = [c['content'] for c in comments]

        # BM25 인덱싱 (키워드 기반)
        tokenized_contents = [content.split() for content in self.contents]
        self.bm25 = BM25Okapi(tokenized_contents)

        # 시맨틱 임베딩 생성
        print(f"Encoding {len(self.contents)} documents...")
        self.embeddings = self.semantic_model.encode(
            self.contents,
            convert_to_tensor=True,
            show_progress_bar=True
        )

        print(f"✅ Indexed {len(self.contents)} comments")

    def search(self, query: str, top_k: int = 5, threshold: float = 0.0) -> List[Tuple[Dict, float]]:
        """
        하이브리드 검색: BM25 + 시맨틱 스코어 결합

        Args:
            query: 검색 쿼리
            top_k: 상위 k개 반환
            threshold: 최소 점수 (0~1)

        Returns:
            List of (comment_dict, hybrid_score) tuples
        """
        if not self.documents:
            return []

        # 1. BM25 검색 (키워드 기반)
        tokenized_query = query.split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        # 정규화 (0~1)
        bm25_scores = bm25_scores / (bm25_scores.max() + 1e-8)

        # 2. 시맨틱 검색 (의미 기반)
        query_embedding = self.semantic_model.encode(query, convert_to_tensor=True)
        semantic_scores = util.cos_sim(query_embedding, self.embeddings)[0]
        semantic_scores = semantic_scores.cpu().numpy()

        # 3. 하이브리드 점수 계산 (가중 평균)
        hybrid_scores = (
            self.bm25_weight * bm25_scores +
            self.semantic_weight * semantic_scores
        )

        # 4. 상위 k개 선택
        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

        # 5. threshold 필터링
        results = []
        for idx in top_indices:
            score = float(hybrid_scores[idx])
            if score >= threshold:
                results.append((self.documents[idx], score))

        return results

    def explain_scores(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        검색 결과와 함께 BM25/시맨틱 개별 점수 표시 (디버깅용)

        Returns:
            List of dicts with detailed scores
        """
        if not self.documents:
            return []

        # 개별 점수 계산
        tokenized_query = query.split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_scores = bm25_scores / (bm25_scores.max() + 1e-8)

        query_embedding = self.semantic_model.encode(query, convert_to_tensor=True)
        semantic_scores = util.cos_sim(query_embedding, self.embeddings)[0].cpu().numpy()

        hybrid_scores = (
            self.bm25_weight * bm25_scores +
            self.semantic_weight * semantic_scores
        )

        # 상위 k개
        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                'content': self.documents[idx]['content'][:200],
                'author': self.documents[idx].get('author', 'Unknown'),
                'bm25_score': float(bm25_scores[idx]),
                'semantic_score': float(semantic_scores[idx]),
                'hybrid_score': float(hybrid_scores[idx]),
                'full_comment': self.documents[idx]
            })

        return results


# ============================================================
# Reciprocal Rank Fusion (RRF) 방식
# ============================================================

class RRFHybridSearch(HybridSearchEngine):
    """
    Reciprocal Rank Fusion을 사용한 하이브리드 검색
    점수 결합 대신 순위 결합 (더 robust)
    """

    def search_rrf(self, query: str, top_k: int = 5, k: int = 60) -> List[Tuple[Dict, float]]:
        """
        RRF 알고리즘으로 하이브리드 검색

        Args:
            query: 검색 쿼리
            top_k: 상위 k개 반환
            k: RRF 파라미터 (기본값 60)

        Returns:
            List of (comment_dict, rrf_score) tuples
        """
        if not self.documents:
            return []

        # BM25 순위
        tokenized_query = query.split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_ranks = np.argsort(bm25_scores)[::-1]

        # 시맨틱 순위
        query_embedding = self.semantic_model.encode(query, convert_to_tensor=True)
        semantic_scores = util.cos_sim(query_embedding, self.embeddings)[0].cpu().numpy()
        semantic_ranks = np.argsort(semantic_scores)[::-1]

        # RRF 점수 계산
        rrf_scores = np.zeros(len(self.documents))

        for rank, doc_idx in enumerate(bm25_ranks):
            rrf_scores[doc_idx] += 1 / (k + rank + 1)

        for rank, doc_idx in enumerate(semantic_ranks):
            rrf_scores[doc_idx] += 1 / (k + rank + 1)

        # 상위 k개 선택
        top_indices = np.argsort(rrf_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append((self.documents[idx], float(rrf_scores[idx])))

        return results


# ============================================================
# 사용 예시
# ============================================================

if __name__ == "__main__":
    # 예시 데이터 로드
    issue_file = "data/crawl_sessions/OpenFrame_TPETIME_20260103_045204/347863_20260103_045306.json"

    with open(issue_file, 'r', encoding='utf-8') as f:
        issue = json.load(f)

    comments = issue.get('comments', [])

    # ===== 방법 1: 가중 평균 하이브리드 =====
    print("=" * 80)
    print("🔍 Hybrid Search: Weighted Average (BM25 + Semantic)")
    print("=" * 80)

    engine = HybridSearchEngine(
        bm25_weight=0.3,      # 키워드 매칭 30%
        semantic_weight=0.7   # 시맨틱 유사도 70%
    )
    engine.index_comments(comments)

    query = "TPETIME 에러 원인"
    results = engine.search(query, top_k=3)

    print(f"\nQuery: '{query}'")
    for i, (comment, score) in enumerate(results, 1):
        print(f"\n[{i}] 하이브리드 점수: {score:.3f}")
        print(f"작성자: {comment.get('author', 'Unknown')}")
        print(f"내용: {comment['content'][:200]}...")

    # 점수 분해 (디버깅)
    print("\n\n" + "=" * 80)
    print("📊 Score Breakdown (Explain)")
    print("=" * 80)

    explained = engine.explain_scores(query, top_k=3)
    for i, result in enumerate(explained, 1):
        print(f"\n[{i}]")
        print(f"  BM25 Score (키워드): {result['bm25_score']:.3f}")
        print(f"  Semantic Score (의미): {result['semantic_score']:.3f}")
        print(f"  Hybrid Score (최종): {result['hybrid_score']:.3f}")
        print(f"  Content: {result['content']}...")

    # ===== 방법 2: RRF 하이브리드 =====
    print("\n\n" + "=" * 80)
    print("🔍 Hybrid Search: Reciprocal Rank Fusion (RRF)")
    print("=" * 80)

    rrf_engine = RRFHybridSearch()
    rrf_engine.index_comments(comments)

    rrf_results = rrf_engine.search_rrf(query, top_k=3)

    print(f"\nQuery: '{query}'")
    for i, (comment, score) in enumerate(rrf_results, 1):
        print(f"\n[{i}] RRF 점수: {score:.4f}")
        print(f"작성자: {comment.get('author', 'Unknown')}")
        print(f"내용: {comment['content'][:200]}...")
