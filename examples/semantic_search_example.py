"""
Semantic Search Example for IMS Issue Comments
Uses Sentence Transformers for multilingual semantic similarity
"""
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
import torch

class CommentSemanticSearch:
    """시맨틱 검색 엔진 for IMS 이슈 댓글"""

    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Args:
            model_name: 다국어 임베딩 모델
                - paraphrase-multilingual-MiniLM-L12-v2 (추천, 50+ 언어)
                - distiluse-base-multilingual-cased-v2 (더 빠름)
        """
        print(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def find_best_comments(self, comments, query, top_k=3, threshold=0.3):
        """
        쿼리와 가장 관련성 높은 댓글 찾기

        Args:
            comments: 댓글 리스트 [{'content': '...', 'author': '...', ...}]
            query: 검색 키워드 (한/영/일 혼용 가능)
            top_k: 상위 k개 반환
            threshold: 최소 유사도 (0~1, 0.3 이상 권장)

        Returns:
            List of (comment, score) tuples
        """
        if not comments:
            return []

        # 댓글 텍스트 추출
        contents = [c['content'] for c in comments]

        # 임베딩 생성
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        comment_embeddings = self.model.encode(contents, convert_to_tensor=True)

        # 코사인 유사도 계산
        cosine_scores = util.cos_sim(query_embedding, comment_embeddings)[0]

        # 상위 k개 선택
        top_results = torch.topk(cosine_scores, k=min(top_k, len(comments)))

        # 결과 필터링 (threshold 이상만)
        results = []
        for score, idx in zip(top_results.values, top_results.indices):
            score_value = score.item()
            if score_value >= threshold:
                results.append((comments[idx], score_value))

        return results

    def search_issue_file(self, issue_json_path, query, top_k=3):
        """
        IMS 이슈 JSON 파일에서 관련 댓글 검색

        Args:
            issue_json_path: 이슈 JSON 파일 경로
            query: 검색 쿼리
            top_k: 상위 k개 반환

        Returns:
            List of (comment_dict, similarity_score)
        """
        with open(issue_json_path, 'r', encoding='utf-8') as f:
            issue_data = json.load(f)

        comments = issue_data.get('comments', [])
        if not comments:
            print(f"No comments found in {issue_json_path}")
            return []

        return self.find_best_comments(comments, query, top_k)


# ============================================================
# 사용 예시
# ============================================================

if __name__ == "__main__":
    # 검색 엔진 초기화
    searcher = CommentSemanticSearch()

    # 예시 1: 단일 이슈 파일 검색
    issue_file = "data/crawl_sessions/OpenFrame_TPETIME_20260103_045204/347863_20260103_045306.json"
    query = "TPETIME 에러 원인"  # 한국어 쿼리

    print(f"\n🔍 Query: '{query}'")
    print("=" * 80)

    results = searcher.search_issue_file(issue_file, query, top_k=3)

    for i, (comment, score) in enumerate(results, 1):
        print(f"\n[{i}] 유사도: {score:.3f}")
        print(f"작성자: {comment.get('author', 'Unknown')}")
        print(f"날짜: {comment.get('created_date', 'N/A')}")
        print(f"내용 미리보기:\n{comment['content'][:200]}...")

    # 예시 2: 여러 이슈 검색 (세션 폴더 전체)
    print("\n\n" + "=" * 80)
    print("📁 Searching across all issues in session folder...")
    print("=" * 80)

    session_folder = Path("data/crawl_sessions/OpenFrame_TPETIME_20260103_045204")
    query2 = "timeout error solution"  # 영어 쿼리

    all_results = []
    for json_file in session_folder.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            issue = json.load(f)

        comments = issue.get('comments', [])
        if not comments:
            continue

        # 각 이슈에서 최고 점수 댓글만
        best_results = searcher.find_best_comments(comments, query2, top_k=1, threshold=0.4)

        if best_results:
            comment, score = best_results[0]
            all_results.append({
                'issue_id': issue.get('issue_id'),
                'title': issue.get('title'),
                'comment': comment,
                'score': score
            })

    # 점수순 정렬
    all_results.sort(key=lambda x: x['score'], reverse=True)

    print(f"\n🔍 Query: '{query2}'")
    print(f"Found {len(all_results)} relevant comments across {len(list(session_folder.glob('*.json')))} issues\n")

    for i, result in enumerate(all_results[:5], 1):  # Top 5
        print(f"\n[{i}] Issue {result['issue_id']}: {result['title'][:60]}...")
        print(f"    유사도: {result['score']:.3f}")
        print(f"    댓글: {result['comment']['content'][:150]}...")
