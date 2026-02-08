import numpy as np
from sentence_transformers import SentenceTransformer
import os
from typing import List
from sklearn.metrics.pairwise import cosine_similarity
from app.models.schemas import RetrievalResult

class RAGService:
    def __init__(self):
        print("Initializing RAG with manual embeddings...")
        
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        print("Loading sentence transformer model...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        print("Model loaded")
        
        # Load documents and create embeddings
        self.documents = self._load_documents()
        print(f"Creating embeddings for {len(self.documents)} documents...")
        
        # Create embeddings with error handling
        try:
            self.doc_embeddings = self.encoder.encode(
                self.documents, 
                convert_to_tensor=False,
                show_progress_bar=True,
                batch_size=1  # Process one at a time to avoid memory issues
            )
            print("Document embeddings created successfully")
        except Exception as e:
            print(f"Error creating embeddings: {e}")
            # Fallback to create dummy embeddings
            self.doc_embeddings = np.random.rand(len(self.documents), 384)
            print("Using fallback embeddings")
        self.confidence_threshold = 0.5
    
    def _load_documents(self) -> List[str]:
        """Load documents from data directory"""
        docs = []
        
        # Try to load from files
        for doc_file in ["data/documents/sample_docs.txt", "data/documents/additional_docs.txt"]:
            if os.path.exists(doc_file):
                print(f"Loading {doc_file}...")
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
                    docs.extend(chunks)
                print(f"Loaded {len(chunks)} chunks from {doc_file}")
        
        # Fallback docs if files don't exist
        if not docs:
            print("Using fallback documents...")
            docs = [
                "Our company offers three pricing tiers: Basic at $10/month, Pro at $25/month, and Enterprise at $100/month.",
                "Customer support is available 24/7 via email and chat. Phone support is available for Enterprise customers.",
                "We provide API access to all customers. Rate limits are 100 requests/hour for Basic, 1000 for Pro, and unlimited for Enterprise.",
                "Our privacy policy ensures that we never sell customer data to third parties. We use encryption for all data in transit and at rest.",
                "Refunds are available within 30 days of purchase. No questions asked for annual subscriptions.",
                "Lead management system tracks prospects through the sales pipeline.",
                "Enterprise customers get dedicated account managers and custom integrations.",
                "Our API supports REST endpoints for all major operations.",
                "Data retention policy keeps customer information for 90 days after subscription ends.",
                "Technical support includes phone, email, and chat channels."
            ]
        
        return docs
    
    def retrieve(self, query: str, top_k: int = 3) -> RetrievalResult:
        """Retrieve relevant documents using manual embedding similarity"""
        
        try:
            print(f"Processing query: {query[:50]}...")
            
            # Encode the query with error handling
            try:
                query_embedding = self.encoder.encode(
                    [query], 
                    convert_to_tensor=False,
                    batch_size=1
                )
            except Exception as e:
                print(f"Error encoding query: {e}")
                # Fallback: keyword based retrieval
                return self._fallback_keyword_search(query, top_k)
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_embedding, self.doc_embeddings)[0]
            
            # Get top-k most similar documents
            top_indices = np.argsort(similarities)[::-1][:top_k]
            top_chunks = [self.documents[i] for i in top_indices]
            top_similarities = [float(similarities[i]) for i in top_indices]
            
            print(f"Top similarities: {[f'{s:.3f}' for s in top_similarities]}")
            
            # Calculate average confidence
            avg_confidence = float(np.mean(top_similarities)) if top_similarities else 0.0
            grounded = avg_confidence >= self.confidence_threshold
            
            return RetrievalResult(
                chunks=top_chunks,
                confidence=avg_confidence,
                grounded=grounded
            )
            
        except Exception as e:
            print(f"RAG retrieval error: {e}")
            # Fallback to keyword search
            return self._fallback_keyword_search(query, top_k)
    
    def _fallback_keyword_search(self, query: str, top_k: int) -> RetrievalResult:
        """Fallback keyword-based search if embeddings fail"""
        print("Using fallback keyword search...")
        
        query_words = set(word.lower() for word in query.split() if len(word) > 2)
        
        doc_scores = []
        for i, doc in enumerate(self.documents):
            doc_words = set(word.lower() for word in doc.split() if len(word) > 2)
            
            # Calculate overlap
            intersection = query_words.intersection(doc_words)
            union = query_words.union(doc_words)
            score = len(intersection) / len(union) if union else 0
            
            doc_scores.append((score, doc))
        
        # Sort and get top results
        doc_scores.sort(key=lambda x: x[0], reverse=True)
        top_docs = [doc for score, doc in doc_scores[:top_k] if score > 0.05]
        
        confidence = min(doc_scores[0][0] if doc_scores else 0.0, 1.0)
        
        return RetrievalResult(
            chunks=top_docs,
            confidence=float(confidence),
            grounded=confidence >= self.confidence_threshold
        )