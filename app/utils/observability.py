import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from app.models.schemas import Response, RouteType

class ObservabilityLogger:
    def __init__(self):
        self.logs = []
    
    def log_query_processing(self, 
                           query_id: str,
                           query: str,
                           route_chosen: RouteType,
                           tools_used: List[str],
                           chunks_retrieved: int,
                           response: Response,
                           processing_time_ms: float,
                           user_id: str = None) -> None:
        """Log structured information about query processing"""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_id": query_id,
            "user_id": user_id,
            "query": query,
            "route_chosen": route_chosen.value,
            "tools_used": tools_used,
            "chunks_retrieved": chunks_retrieved,
            "response_confidence": response.confidence,
            "processing_time_ms": processing_time_ms,
            "reasoning_trace": response.reasoning_trace,
            "guardrails_passed": True,  # Would be set based on actual guardrail results
            "cost_estimate": self._estimate_cost(query, response.answer)
        }
        
        self.logs.append(log_entry)

        # In production grade systems - would be sent to logging service, metrics system, etc.
        print(f"[OBSERVABILITY] {json.dumps(log_entry, indent=2)}")
    
    def _estimate_cost(self, query: str, response: str) -> float:
        """Estimate cost based on token usage"""
        # Rough estimation: 1 token ≈ 4 characters, Gemini 2.0 Flash costs ~$0.002/1K tokens
        total_chars = len(query) + len(response)
        estimated_tokens = total_chars / 4
        estimated_cost = (estimated_tokens / 1000) * 0.002
        return round(estimated_cost, 6)
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics from logged data"""
        if not self.logs:
            return {"message": "No data available"}
        
        total_queries = len(self.logs)
        route_distribution = {}
        avg_confidence = 0
        avg_processing_time = 0
        total_cost = 0
        
        for log in self.logs:
            route = log["route_chosen"]
            route_distribution[route] = route_distribution.get(route, 0) + 1
            avg_confidence += log["response_confidence"]
            avg_processing_time += log["processing_time_ms"]
            total_cost += log["cost_estimate"]
        
        return {
            "total_queries": total_queries,
            "route_distribution": route_distribution,
            "avg_confidence": round(avg_confidence / total_queries, 3),
            "avg_processing_time_ms": round(avg_processing_time / total_queries, 2),
            "total_estimated_cost": round(total_cost, 4),
            "recent_queries": self.logs[-5:]  # Last 5 queries
        }

class FeedbackSystem:
    def __init__(self):
        self.feedback_data = []
    
    def store_feedback(self, query_id: str, rating: int, comment: str = None) -> None:
        """Store user feedback"""
        feedback_entry = {
            "query_id": query_id,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.feedback_data.append(feedback_entry)
        
    def get_feedback_insights(self) -> Dict[str, Any]:
        """Analyze feedback patterns"""
        if not self.feedback_data:
            return {"message": "No feedback data available"}
        
        positive_feedback = sum(1 for f in self.feedback_data if f["rating"] > 0)
        negative_feedback = sum(1 for f in self.feedback_data if f["rating"] < 0)
        total_feedback = len(self.feedback_data)
        
        return {
            "total_feedback": total_feedback,
            "positive_rate": round(positive_feedback / total_feedback, 3),
            "negative_rate": round(negative_feedback / total_feedback, 3),
            "recent_feedback": self.feedback_data[-5:]
        }
    
    def improvement_suggestions(self) -> List[str]:
        """Suggest improvements based on feedback patterns"""
        suggestions = []
        
        if not self.feedback_data:
            return ["Collect more user feedback to generate suggestions"]
        
        negative_feedback = [f for f in self.feedback_data if f["rating"] < 0]
        negative_rate = len(negative_feedback) / len(self.feedback_data)
        
        if negative_rate > 0.3:
            suggestions.append("High negative feedback rate - review routing accuracy")
        
        if negative_rate > 0.5:
            suggestions.append("Consider adjusting confidence thresholds")
            suggestions.append("Review document quality and coverage")
        
        # Analyze comments for common themes
        comments = [f["comment"] for f in negative_feedback if f["comment"]]
        if any("slow" in comment.lower() for comment in comments):
            suggestions.append("Optimize response time - users report slowness")
        
        if any("wrong" in comment.lower() or "incorrect" in comment.lower() for comment in comments):
            suggestions.append("Improve answer accuracy - review groundedness checks")
        
        return suggestions if suggestions else ["System performing well based on feedback"]