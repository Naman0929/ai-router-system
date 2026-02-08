import google.genai as genai
import json
import os
from typing import Dict, Any, List
from app.models.schemas import RouteType, RouteDecision

class LLMService:
    def __init__(self, api_key: str):
        if api_key != "demo-key":
            try:
                self.client = genai.Client(api_key=api_key)
                self.model_id = 'gemini-2.0-flash'
                self.has_client = True
                print("Gemini client initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Gemini: {e}")
                self.client = None
                self.has_client = False
        else:
            print("Using demo mode (no Gemini API key)")
            self.client = None
            self.has_client = False
    
    def route_query(self, query: str) -> RouteDecision:
        """Classify query into appropriate route with reasoning"""
        
        # Rule-based pre filtering for efficiency
        if self._is_greeting(query):
            return RouteDecision(
                route=RouteType.SMALL_TALK,
                confidence=0.95,
                reasoning="Detected greeting/small talk pattern"
            )
        
        # Route to STRUCTURED_DATA for specific patterns
        if self._has_specific_structured_keywords(query):
            return RouteDecision(
                route=RouteType.STRUCTURED_DATA,
                confidence=0.85,
                reasoning="Contains specific structured data keywords (lead_ID or specific plan names)"
            )
        
        # For RAG
        if self._needs_document_search(query):
            return RouteDecision(
                route=RouteType.FACT_FROM_DOCS,
                confidence=0.8,
                reasoning="Query needs document retrieval for factual information"
            )
        
        # Simple rule based fallback if no Gemini key
        if not self.has_client:
            return self._rule_based_routing(query)
        
        # LLM based classification for complex cases
        prompt = f"""
        Classify this query into one category with reasoning:
        
        Query: "{query}"
        
        Categories:
        - FACT_FROM_DOCS: Factual questions that need document retrieval (pricing info, policies, features, support info)
        - STRUCTURED_DATA: Requests for specific data lookups (lead_001 status, specific account info)
        - SMALL_TALK: Greetings, casual conversation, general questions
        - OUT_OF_SCOPE: Inappropriate, harmful, or completely unrelated content
        
        Respond in JSON format:
        {{
            "route": "category_name",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            result = json.loads(response.text)
            return RouteDecision(**result)
            
        except Exception as e:
            print(f"Gemini routing failed: {e}")
            return self._rule_based_routing(query)
    
    def _rule_based_routing(self, query: str) -> RouteDecision:
        """Fallback routing without LLM"""
        query_lower = query.lower()
        
        # Check for specific lead IDs first
        if 'lead_' in query_lower and any(char.isdigit() for char in query):
            return RouteDecision(
                route=RouteType.STRUCTURED_DATA,
                confidence=0.9,
                reasoning="Query contains specific lead ID - using structured data lookup"
            )
        
        # Queries that go to document search
        if any(word in query_lower for word in ['pricing', 'price', 'cost', 'plan', 'support', 'help', 'policy', 'feature']):
            return RouteDecision(
                route=RouteType.FACT_FROM_DOCS,
                confidence=0.8,
                reasoning="Query about company information - using document retrieval"
            )
        
        return RouteDecision(
            route=RouteType.FACT_FROM_DOCS,
            confidence=0.6,
            reasoning="Default to document retrieval"
        )
    
    def _is_greeting(self, query: str) -> bool:
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'how are you']
        return any(greeting in query.lower() for greeting in greetings)
    
    def _has_specific_structured_keywords(self, query: str) -> bool:
        """Only very specific structured data queries"""
        query_lower = query.lower()
        
        # Look for specific lead IDs
        if 'lead_' in query_lower and any(char.isdigit() for char in query):
            return True
        
        # Look for specific plan names in context of "status" or "get"
        specific_plans = ['basic plan', 'pro plan', 'enterprise plan']
        if any(plan in query_lower for plan in specific_plans) and ('status' in query_lower or 'get' in query_lower):
            return True
            
        return False
    
    def _needs_document_search(self, query: str) -> bool:
        """Check if query needs document retrieval"""
        doc_keywords = ['pricing', 'price', 'cost', 'plan', 'support', 'help', 'policy', 'feature', 'about', 'what are', 'tell me', 'how much', 'refund', 'api', 'contact']
        return any(keyword in query.lower() for keyword in doc_keywords)
    
    def check_groundedness(self, query: str, context: List[str], answer: str) -> bool:
        """Check if the answer is grounded in the retrieved context"""

        # Simple keyword based check without LLM
        if not self.has_client:
            return len(context) > 0  # Basic check
        
        # LLM based groundedness check
        context_text = "\n".join(context)
        
        prompt = f"""
        Query: {query}
        Context: {context_text}
        Proposed Answer: {answer}
        
        Is the proposed answer fully supported by the given context? 
        Consider:
        - Are all facts in the context found in the answer?
        - Is there speculation or information not in the context?
        
        Respond only with: YES or NO
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return "YES" in response.text.upper()
            
        except:
            return len(context) > 0
    
    def generate_answer(self, query: str, context: List[str] = None) -> str:
        """Generate answer with or without context"""

        if not self.has_client:
            # fallback for small talk
            if context:
                return f"Based on our documentation: {' '.join(context[0].split()[:50])}..." if context else "No relevant information found."
            else:
                return "Hello! I'm here to help you with questions about our services. How can I assist you today?"
        
        if context:
            context_text = "\n".join(context)
            prompt = f"""
            Based on the following context, answer the query clearly and concisely.
            
            Context: {context_text}
            Query: {query}
            
            Answer:
            """
        else:
            prompt = f"""
            Provide a helpful, friendly conversational response to: {query}
            
            Keep it brief and welcoming.
            """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text.strip()
            
        except Exception as e:
            print(f"Gemini generation failed: {e}")
            if context:
                # Extract key info from first context chunk for fallback
                first_context = context[0] if context else ""
                return f"Based on our documentation: {first_context[:200]}..."
            else:
                return "Hello! I'm here to help you with questions about our services. How can I assist you today?"