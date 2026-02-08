from typing import List, Dict, Any
from app.models.schemas import Response, RouteType

class GuardrailsService:
    def __init__(self):
        self.min_confidence_threshold = 0.3
        self.max_tokens_per_response = 500
        self.blocked_keywords = ["hack", "exploit", "illegal", "harmful"]
        self.cost_budget_per_user = 100  # Mock token budget
        self.user_token_usage = {}  # Mock usage tracking
    
    def apply_guardrails(self, query: str, response: Response, user_id: str = None) -> Dict[str, Any]:
        """Apply all guardrails and return validation result"""
        
        violations = []
        
        # 1. Confidence threshold check
        if response.confidence < self.min_confidence_threshold:
            violations.append(f"Response confidence {response.confidence} below threshold {self.min_confidence_threshold}")
        
        # 2. Hard refusal rules
        if self._contains_blocked_content(query) or self._contains_blocked_content(response.answer):
            violations.append("Content contains blocked keywords")
        
        # 3. Token budget enforcement
        if user_id:
            current_usage = self.user_token_usage.get(user_id, 0)
            estimated_tokens = len(response.answer.split()) * 1.3  # Rough token estimation
            
            if current_usage + estimated_tokens > self.cost_budget_per_user:
                violations.append(f"Token budget exceeded for user {user_id}")
        
        # 4. Output schema validation
        schema_valid = self._validate_response_schema(response)
        if not schema_valid:
            violations.append("Response schema validation failed")
        
        # 5. Response length check
        if len(response.answer) > self.max_tokens_per_response * 4:  # Rough char to token conversion
            violations.append("Response exceeds maximum length")
        
        if violations:
            return {
                "passed": False,
                "violations": violations,
                "safe_response": self._generate_safe_response()
            }
        
        # Update usage if passed
        if user_id:
            estimated_tokens = len(response.answer.split()) * 1.3
            self.user_token_usage[user_id] = current_usage + estimated_tokens
        
        return {"passed": True, "violations": []}
    
    def _contains_blocked_content(self, text: str) -> bool:
        """Check for blocked keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.blocked_keywords)
    
    def _validate_response_schema(self, response: Response) -> bool:
        """Validate response has required fields"""
        required_fields = ["answer", "confidence", "route_used", "reasoning_trace"]
        
        for field in required_fields:
            if not hasattr(response, field) or getattr(response, field) is None:
                return False
        
        # Check confidence is valid range
        if not 0 <= response.confidence <= 1:
            return False
        
        # Check route is valid
        if response.route_used not in RouteType:
            return False
        
        return True
    
    def _generate_safe_response(self) -> Response:
        """Generate a safe fallback response"""
        return Response(
            answer="I apologize, but I cannot process this request due to safety constraints.",
            confidence=1.0,
            route_used=RouteType.OUT_OF_SCOPE,
            reasoning_trace=["Request blocked by guardrails"]
        )