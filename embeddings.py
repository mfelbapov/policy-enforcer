"""
RAG Implementation: Embeddings and Retrieval

FDE-Level Concepts Demonstrated:
1. Embedding model selection (Voyage vs OpenAI tradeoffs)
2. Input type distinction (document vs query)
3. Confidence thresholding (refuse rather than hallucinate)
4. Chunk metadata preservation
"""

import json
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config import (
    VOYAGE_API_KEY,
    VOYAGE_MODEL,
    RETRIEVAL_CONFIDENCE_THRESHOLD,
    TOP_K_CHUNKS,
)

# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class PolicyChunk:
    """A chunk of policy document with metadata."""
    id: str
    category: str
    title: str
    content: str
    embedding: Optional[np.ndarray] = None


@dataclass
class RetrievalResult:
    """Result from RAG retrieval with confidence score."""
    chunk: PolicyChunk
    score: float
    
    @property
    def is_confident(self) -> bool:
        """Check if retrieval confidence meets threshold."""
        return self.score >= RETRIEVAL_CONFIDENCE_THRESHOLD


# =============================================================================
# Embedding Client
# =============================================================================

class EmbeddingClient:
    """
    Client for generating embeddings.
    
    FDE Note: We use Voyage AI because it outperforms OpenAI embeddings
    for enterprise/legal/financial content. See their benchmarks:
    https://docs.voyageai.com/docs/embeddings
    
    Key insight: Voyage uses separate input_type for documents vs queries.
    This asymmetric embedding improves retrieval accuracy.
    """
    
    def __init__(self):
        self._client = None
        self._use_mock = not VOYAGE_API_KEY
        
        if not self._use_mock:
            try:
                import voyageai
                self._client = voyageai.Client(api_key=VOYAGE_API_KEY)
            except ImportError:
                print("Warning: voyageai not installed. Using mock embeddings.")
                self._use_mock = True
    
    def embed_documents(self, texts: list[str]) -> list[np.ndarray]:
        """
        Embed documents for indexing.
        
        FDE Note: input_type="document" tells Voyage these are the 
        knowledge base items, not search queries. This matters for
        asymmetric retrieval.
        """
        if self._use_mock:
            return self._mock_embed(texts)
        
        response = self._client.embed(
            texts,
            model=VOYAGE_MODEL,
            input_type="document"  # Critical: document vs query
        )
        return [np.array(emb) for emb in response.embeddings]
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a search query.
        
        FDE Note: input_type="query" optimizes the embedding for 
        searching against documents. Different from document embeddings.
        """
        if self._use_mock:
            return self._mock_embed([query])[0]
        
        response = self._client.embed(
            [query],
            model=VOYAGE_MODEL,
            input_type="query"  # Critical: optimized for search
        )
        return np.array(response.embeddings[0])
    
    def _mock_embed(self, texts: list[str]) -> list[np.ndarray]:
        """
        Mock embeddings for testing without API key.
        
        FDE Note: In production, you'd never use this. But for demos
        and local testing, it lets you validate the pipeline.
        """
        # Create deterministic embeddings based on text content
        embeddings = []
        for text in texts:
            # Simple hash-based mock (NOT for production)
            np.random.seed(hash(text) % (2**32))
            emb = np.random.randn(1024)
            emb = emb / np.linalg.norm(emb)  # Normalize
            embeddings.append(emb)
        return embeddings


# =============================================================================
# Policy Index
# =============================================================================

class PolicyIndex:
    """
    Vector index for policy documents.
    
    FDE-Level Design Decisions:
    1. We store full metadata with each chunk (not just text)
    2. We normalize embeddings so dot product = cosine similarity
    3. We return confidence scores, not just results
    4. We support "I don't know" via thresholding
    """
    
    def __init__(self, policy_path: str = "data/policies.json"):
        self.embedding_client = EmbeddingClient()
        self.chunks: list[PolicyChunk] = []
        self._embedding_matrix: Optional[np.ndarray] = None
        
        self._load_policies(policy_path)
        self._build_index()
    
    def _load_policies(self, path: str) -> None:
        """Load policy documents from JSON."""
        policy_file = Path(__file__).parent / path
        
        with open(policy_file, "r") as f:
            data = json.load(f)
        
        for policy in data["policies"]:
            self.chunks.append(PolicyChunk(
                id=policy["id"],
                category=policy["category"],
                title=policy["title"],
                content=policy["content"],
            ))
    
    def _build_index(self) -> None:
        """
        Build the vector index.
        
        FDE Note: In production, you'd use a proper vector DB
        (Pinecone, Weaviate, pgvector). For demos, numpy is fine.
        """
        texts = [chunk.content for chunk in self.chunks]
        embeddings = self.embedding_client.embed_documents(texts)
        
        for chunk, embedding in zip(self.chunks, embeddings):
            chunk.embedding = embedding
        
        # Stack into matrix for efficient batch similarity
        self._embedding_matrix = np.stack(embeddings)
    
    def search(self, query: str, top_k: int = TOP_K_CHUNKS) -> list[RetrievalResult]:
        """
        Search for relevant policy chunks.
        
        FDE Note: We return scores with results so the caller can
        decide whether to use them. This is critical for preventing
        hallucination - if no chunk is relevant, we should say so.
        """
        query_embedding = self.embedding_client.embed_query(query)
        
        # Compute similarities (dot product = cosine for normalized vectors)
        scores = np.dot(self._embedding_matrix, query_embedding)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append(RetrievalResult(
                chunk=self.chunks[idx],
                score=float(scores[idx])
            ))
        
        return results
    
    def search_with_threshold(
        self, 
        query: str, 
        top_k: int = TOP_K_CHUNKS
    ) -> tuple[list[RetrievalResult], bool]:
        """
        Search with confidence threshold check.
        
        Returns:
            results: List of retrieval results
            is_confident: True if at least one result meets threshold
            
        FDE Note: This is the function you use in production.
        If is_confident is False, the agent should refuse to answer
        rather than hallucinate.
        """
        results = self.search(query, top_k)
        is_confident = any(r.is_confident for r in results)
        return results, is_confident


# =============================================================================
# Convenience Function
# =============================================================================

# Global index instance (lazy loaded)
_policy_index: Optional[PolicyIndex] = None

def get_policy_index() -> PolicyIndex:
    """Get or create the global policy index."""
    global _policy_index
    if _policy_index is None:
        _policy_index = PolicyIndex()
    return _policy_index


def search_policies(query: str) -> tuple[list[dict], bool]:
    """
    Search policies and return results with confidence.
    
    Returns:
        results: List of dicts with chunk info and scores
        is_confident: Whether results meet confidence threshold
    """
    index = get_policy_index()
    results, is_confident = index.search_with_threshold(query)
    
    return [
        {
            "id": r.chunk.id,
            "category": r.chunk.category,
            "title": r.chunk.title,
            "content": r.chunk.content,
            "score": r.score,
            "is_confident": r.is_confident,
        }
        for r in results
    ], is_confident


# =============================================================================
# Demo / Test
# =============================================================================

if __name__ == "__main__":
    # Quick test of the embeddings system
    print("Testing Policy Index...")
    
    index = PolicyIndex()
    
    test_queries = [
        "Can I fly first class to London?",
        "What's the meal expense limit?",
        "Who can approve a $5000 purchase?",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results, confident = index.search_with_threshold(query, top_k=2)
        print(f"Confident: {confident}")
        for r in results:
            print(f"  [{r.score:.3f}] {r.chunk.title}: {r.chunk.content[:80]}...")
