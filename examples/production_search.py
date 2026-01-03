"""
Production-Ready Hybrid Search
Optimized for Korean/Japanese/English IMS issues
"""
import sys
import io

# Fix Windows console encoding (only if not already set)
if sys.platform == 'win32' and not isinstance(sys.stdout, io.TextIOWrapper):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, ValueError):
        # Already wrapped or not available
        pass

import json
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util
import numpy as np
from typing import List, Dict, Tuple

class ProductionHybridSearch:
    """
    프로덕션용 하이브리드 검색

    Features:
    - Character N-grams for CJK languages
    - Balanced BM25 (30%) + Semantic (70%)
    - Multi-language support (Korean/Japanese/English)
    """

    def __init__(self):
        """Initialize with optimal settings"""
        self.semantic_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2'
        )
        self.bm25_weight = 0.3
        self.semantic_weight = 0.7

        self.documents = []
        self.contents = []
        self.bm25 = None
        self.embeddings = None

    def _tokenize(self, text: str) -> List[str]:
        """
        CJK-optimized tokenization with character n-grams

        Args:
            text: Input text

        Returns:
            List of tokens including bi-grams for CJK characters
        """
        text = text.lower()
        tokens = text.split()

        ngrams = []
        for token in tokens:
            if re.match(r'^[a-z0-9]+$', token):
                # English/numbers: use as-is
                ngrams.append(token)
            else:
                # CJK characters: generate bi-grams
                for i in range(len(token) - 1):
                    ngrams.append(token[i:i+2])
                ngrams.append(token)

        return tokens + ngrams

    def index_comments(self, comments: List[Dict], show_progress: bool = False):
        """
        Index comments for search

        Args:
            comments: List of comment dicts with 'content' field
            show_progress: Show progress bar for encoding
        """
        if not comments:
            return

        self.documents = comments
        self.contents = [c['content'] for c in comments]

        # BM25 indexing
        tokenized_contents = [self._tokenize(content) for content in self.contents]
        self.bm25 = BM25Okapi(tokenized_contents)

        # Semantic embeddings
        self.embeddings = self.semantic_model.encode(
            self.contents,
            convert_to_tensor=True,
            show_progress_bar=show_progress
        )

    def search(self,
               query: str,
               top_k: int = 5,
               threshold: float = 0.0,
               return_scores: bool = False) -> List:
        """
        Hybrid search with BM25 + Semantic

        Args:
            query: Search query (Korean/Japanese/English)
            top_k: Number of results to return
            threshold: Minimum score (0~1)
            return_scores: Include score breakdown in results

        Returns:
            List of (comment_dict, score) or (comment_dict, score, breakdown)
        """
        if not self.documents:
            return []

        # BM25 scores
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_scores_norm = bm25_scores / (bm25_scores.max() + 1e-8)

        # Semantic scores
        query_embedding = self.semantic_model.encode(query, convert_to_tensor=True)
        semantic_scores = util.cos_sim(query_embedding, self.embeddings)[0].cpu().numpy()

        # Hybrid scores
        hybrid_scores = (
            self.bm25_weight * bm25_scores_norm +
            self.semantic_weight * semantic_scores
        )

        # Top-k selection
        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(hybrid_scores[idx])
            if score >= threshold:
                if return_scores:
                    breakdown = {
                        'bm25': float(bm25_scores_norm[idx]),
                        'semantic': float(semantic_scores[idx]),
                        'hybrid': score
                    }
                    results.append((self.documents[idx], score, breakdown))
                else:
                    results.append((self.documents[idx], score))

        return results

    def search_issue_file(self,
                          issue_file_path: str,
                          query: str,
                          top_k: int = 3) -> List[Tuple[Dict, float]]:
        """
        Search comments in a single issue JSON file

        Args:
            issue_file_path: Path to issue JSON file
            query: Search query
            top_k: Number of results

        Returns:
            List of (comment, score) tuples
        """
        with open(issue_file_path, 'r', encoding='utf-8') as f:
            issue = json.load(f)

        comments = issue.get('comments', [])
        if not comments:
            return []

        self.index_comments(comments)
        return self.search(query, top_k=top_k)

    def search_session_folder(self,
                              session_folder_path: str,
                              query: str,
                              top_k_per_issue: int = 1,
                              overall_top_k: int = 10) -> List[Dict]:
        """
        Search across all issues in a session folder

        Args:
            session_folder_path: Path to crawl session folder
            query: Search query
            top_k_per_issue: Best comments per issue
            overall_top_k: Final top results across all issues

        Returns:
            List of dicts with issue_id, title, comment, score
        """
        session_folder = Path(session_folder_path)
        all_results = []

        for json_file in session_folder.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                issue = json.load(f)

            comments = issue.get('comments', [])
            if not comments:
                continue

            # Search in this issue
            self.index_comments(comments)
            issue_results = self.search(query, top_k=top_k_per_issue)

            if issue_results:
                for comment, score in issue_results:
                    all_results.append({
                        'issue_id': issue.get('issue_id'),
                        'title': issue.get('title'),
                        'product': issue.get('product'),
                        'status': issue.get('status'),
                        'comment': comment,
                        'score': score,
                        'file_path': str(json_file)
                    })

        # Sort by score and return top-k
        all_results.sort(key=lambda x: x['score'], reverse=True)
        return all_results[:overall_top_k]


# ============================================================
# CLI Usage Example
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Search IMS issue comments')
    parser.add_argument('-q', '--query', required=True, help='Search query')
    parser.add_argument('-f', '--file', help='Single issue JSON file')
    parser.add_argument('-s', '--session', help='Session folder path')
    parser.add_argument('-k', '--top-k', type=int, default=5, help='Number of results')
    parser.add_argument('--scores', action='store_true', help='Show score breakdown')

    args = parser.parse_args()

    searcher = ProductionHybridSearch()

    if args.file:
        # Single file search
        print(f"🔍 Searching in: {args.file}")
        print(f"Query: '{args.query}'\n")

        results = searcher.search_issue_file(args.file, args.query, top_k=args.top_k)

        for i, (comment, score) in enumerate(results, 1):
            print(f"[{i}] Score: {score:.3f}")
            print(f"    작성자: {comment.get('author', 'Unknown')}")
            print(f"    날짜: {comment.get('created_date', 'N/A')}")
            print(f"    내용: {comment['content'][:200]}...")
            print()

    elif args.session:
        # Session folder search
        print(f"🔍 Searching in session: {args.session}")
        print(f"Query: '{args.query}'\n")

        results = searcher.search_session_folder(
            args.session,
            args.query,
            overall_top_k=args.top_k
        )

        for i, result in enumerate(results, 1):
            print(f"[{i}] Issue {result['issue_id']}: {result['title'][:60]}...")
            print(f"    제품: {result['product']}")
            print(f"    상태: {result['status']}")
            print(f"    점수: {result['score']:.3f}")
            print(f"    댓글: {result['comment']['content'][:150]}...")
            print()

    else:
        # Default: search in latest session
        base_dir = Path("data/crawl_sessions")
        sessions = sorted(base_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not sessions:
            print("No crawl sessions found")
            sys.exit(1)

        latest_session = sessions[0]
        print(f"🔍 Searching in latest session: {latest_session.name}")
        print(f"Query: '{args.query}'\n")

        results = searcher.search_session_folder(
            str(latest_session),
            args.query,
            overall_top_k=args.top_k
        )

        for i, result in enumerate(results, 1):
            print(f"[{i}] Issue {result['issue_id']}: {result['title'][:60]}...")
            print(f"    점수: {result['score']:.3f}")
            print(f"    댓글: {result['comment']['content'][:150]}...")
            print()
