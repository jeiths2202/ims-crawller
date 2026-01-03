"""
Optimized Hybrid Search for Korean/Japanese/English
Uses character n-grams for better CJK language support
"""
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np
from typing import List, Dict, Tuple

class CJKTokenizer:
    """한국어/일본어/중국어 최적화 토크나이저"""

    @staticmethod
    def tokenize(text: str, use_ngrams: bool = True) -> List[str]:
        """
        CJK 언어 최적화 토큰화

        Args:
            text: 입력 텍스트
            use_ngrams: True면 문자 bi-gram 사용, False면 공백만

        Returns:
            토큰 리스트
        """
        # 소문자 변환
        text = text.lower()

        # 공백 기반 토큰
        tokens = text.split()

        if not use_ngrams:
            return tokens

        # 문자 bi-gram 추가 (한국어/일본어/중국어 대응)
        ngrams = []
        for token in tokens:
            # 영어/숫자는 그대로
            if re.match(r'^[a-z0-9]+$', token):
                ngrams.append(token)
            else:
                # CJK 문자는 bi-gram 생성
                for i in range(len(token) - 1):
                    ngrams.append(token[i:i+2])
                # 원본 토큰도 추가
                ngrams.append(token)

        return tokens + ngrams

class OptimizedHybridSearch:
    """한국어/일본어 최적화 하이브리드 검색"""

    def __init__(self,
                 semantic_model='paraphrase-multilingual-MiniLM-L12-v2',
                 bm25_weight=0.3,
                 semantic_weight=0.7,
                 use_ngrams=True):
        """
        Args:
            semantic_model: 시맨틱 임베딩 모델
            bm25_weight: BM25 점수 가중치
            semantic_weight: 시맨틱 점수 가중치
            use_ngrams: Character n-gram 사용 여부
        """
        print(f"Loading semantic model: {semantic_model}")
        self.semantic_model = SentenceTransformer(semantic_model)
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        self.use_ngrams = use_ngrams
        self.tokenizer = CJKTokenizer()

        self.documents = []
        self.contents = []
        self.bm25 = None
        self.embeddings = None

    def index_comments(self, comments: List[Dict]):
        """댓글 인덱싱"""
        if not comments:
            return

        self.documents = comments
        self.contents = [c['content'] for c in comments]

        # BM25 인덱싱 (CJK 토크나이저 사용)
        tokenized_contents = [
            self.tokenizer.tokenize(content, self.use_ngrams)
            for content in self.contents
        ]
        self.bm25 = BM25Okapi(tokenized_contents)

        # 시맨틱 임베딩
        print(f"Encoding {len(self.contents)} documents...")
        self.embeddings = self.semantic_model.encode(
            self.contents,
            convert_to_tensor=True,
            show_progress_bar=True
        )

        print(f"✅ Indexed {len(self.contents)} comments")

    def search(self, query: str, top_k: int = 5, threshold: float = 0.0) -> List[Tuple[Dict, float, Dict]]:
        """
        하이브리드 검색 (점수 분해 포함)

        Returns:
            List of (comment_dict, hybrid_score, score_breakdown)
        """
        if not self.documents:
            return []

        # BM25 검색
        tokenized_query = self.tokenizer.tokenize(query, self.use_ngrams)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_scores_norm = bm25_scores / (bm25_scores.max() + 1e-8)

        # 시맨틱 검색
        query_embedding = self.semantic_model.encode(query, convert_to_tensor=True)
        semantic_scores = util.cos_sim(query_embedding, self.embeddings)[0].cpu().numpy()

        # 하이브리드 점수
        hybrid_scores = (
            self.bm25_weight * bm25_scores_norm +
            self.semantic_weight * semantic_scores
        )

        # 상위 k개 선택
        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(hybrid_scores[idx])
            if score >= threshold:
                breakdown = {
                    'bm25': float(bm25_scores_norm[idx]),
                    'semantic': float(semantic_scores[idx]),
                    'hybrid': score
                }
                results.append((self.documents[idx], score, breakdown))

        return results


def compare_search_methods(comments: List[Dict], query: str):
    """다양한 검색 방법 비교"""

    print(f"\n{'='*80}")
    print(f"🔍 Query: '{query}'")
    print(f"{'='*80}\n")

    # 1. Semantic only
    print("【1】 Semantic Search Only (100% Semantic)")
    print("-" * 80)
    semantic_only = OptimizedHybridSearch(
        bm25_weight=0.0,
        semantic_weight=1.0
    )
    semantic_only.index_comments(comments)
    results_semantic = semantic_only.search(query, top_k=3)

    for i, (comment, score, breakdown) in enumerate(results_semantic, 1):
        print(f"\n[{i}] Score: {score:.3f} (Semantic: {breakdown['semantic']:.3f})")
        print(f"    작성자: {comment.get('author', 'Unknown')}")
        print(f"    내용: {comment['content'][:150]}...")

    # 2. Hybrid (no n-grams)
    print(f"\n\n{'='*80}")
    print("【2】 Hybrid Search (30% BM25 + 70% Semantic, 공백 토큰만)")
    print("-" * 80)
    hybrid_basic = OptimizedHybridSearch(
        bm25_weight=0.3,
        semantic_weight=0.7,
        use_ngrams=False  # 공백만
    )
    hybrid_basic.index_comments(comments)
    results_hybrid_basic = hybrid_basic.search(query, top_k=3)

    for i, (comment, score, breakdown) in enumerate(results_hybrid_basic, 1):
        print(f"\n[{i}] Score: {score:.3f} (BM25: {breakdown['bm25']:.3f}, Semantic: {breakdown['semantic']:.3f})")
        print(f"    작성자: {comment.get('author', 'Unknown')}")
        print(f"    내용: {comment['content'][:150]}...")

    # 3. Hybrid (with n-grams)
    print(f"\n\n{'='*80}")
    print("【3】 Hybrid Search (30% BM25 + 70% Semantic, Character N-grams)")
    print("-" * 80)
    hybrid_ngrams = OptimizedHybridSearch(
        bm25_weight=0.3,
        semantic_weight=0.7,
        use_ngrams=True  # N-gram 사용
    )
    hybrid_ngrams.index_comments(comments)
    results_hybrid_ngrams = hybrid_ngrams.search(query, top_k=3)

    for i, (comment, score, breakdown) in enumerate(results_hybrid_ngrams, 1):
        print(f"\n[{i}] Score: {score:.3f} (BM25: {breakdown['bm25']:.3f}, Semantic: {breakdown['semantic']:.3f})")
        print(f"    작성자: {comment.get('author', 'Unknown')}")
        print(f"    내용: {comment['content'][:150]}...")

    # 4. BM25 dominant
    print(f"\n\n{'='*80}")
    print("【4】 Keyword-Focused Hybrid (60% BM25 + 40% Semantic, N-grams)")
    print("-" * 80)
    hybrid_keyword = OptimizedHybridSearch(
        bm25_weight=0.6,
        semantic_weight=0.4,
        use_ngrams=True
    )
    hybrid_keyword.index_comments(comments)
    results_hybrid_keyword = hybrid_keyword.search(query, top_k=3)

    for i, (comment, score, breakdown) in enumerate(results_hybrid_keyword, 1):
        print(f"\n[{i}] Score: {score:.3f} (BM25: {breakdown['bm25']:.3f}, Semantic: {breakdown['semantic']:.3f})")
        print(f"    작성자: {comment.get('author', 'Unknown')}")
        print(f"    내용: {comment['content'][:150]}...")


if __name__ == "__main__":
    # 실제 데이터 로드
    issue_file = "data/crawl_sessions/OpenFrame_TPETIME_20260103_045204/347863_20260103_045306.json"

    with open(issue_file, 'r', encoding='utf-8') as f:
        issue = json.load(f)

    comments = issue.get('comments', [])

    # 다양한 쿼리 테스트
    test_queries = [
        "TPETIME 에러 원인",           # 한국어
        "timeout error solution",      # 영어
        "batch job failure",           # 기술 용어
        "문제 해결 방법"                # 한국어 일반
    ]

    for query in test_queries:
        compare_search_methods(comments, query)
        print("\n\n" + "="*80 + "\n")
