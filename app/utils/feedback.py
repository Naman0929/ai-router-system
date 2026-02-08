import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models.schemas import Feedback

class FeedbackStorage:
    def __init__(self, storage_file: str = "feedback_data.json"):
        self.storage_file = storage_file
        self.feedback_data = self._load_feedback()
    
    def _load_feedback(self) -> List[Dict[str, Any]]:
        """Load feedback from JSON file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_feedback(self) -> None:
        """Save feedback to JSON file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.feedback_data, f, indent=2)
        except Exception as e:
            print(f"Error saving feedback: {e}")
    
    def store_feedback(self, feedback: Feedback) -> bool:
        """Store user feedback"""
        try:
            feedback_entry = {
                "query_id": feedback.query_id,
                "rating": feedback.rating,
                "comment": feedback.comment,
                "timestamp": datetime.utcnow().isoformat(),
                "id": len(self.feedback_data) + 1
            }
            
            self.feedback_data.append(feedback_entry)
            self._save_feedback()
            return True
        except Exception as e:
            print(f"Error storing feedback: {e}")
            return False
    
    def get_feedback_by_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get feedback for specific query"""
        for feedback in self.feedback_data:
            if feedback["query_id"] == query_id:
                return feedback
        return None
    
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """Get all feedback"""
        return self.feedback_data
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        if not self.feedback_data:
            return {
                "total_feedback": 0,
                "positive_rate": 0,
                "negative_rate": 0,
                "average_rating": 0
            }
        
        total = len(self.feedback_data)
        positive = sum(1 for f in self.feedback_data if f["rating"] > 0)
        negative = sum(1 for f in self.feedback_data if f["rating"] < 0)
        total_rating = sum(f["rating"] for f in self.feedback_data)
        
        return {
            "total_feedback": total,
            "positive_rate": round(positive / total, 3) if total > 0 else 0,
            "negative_rate": round(negative / total, 3) if total > 0 else 0,
            "average_rating": round(total_rating / total, 2) if total > 0 else 0,
            "recent_feedback": self.feedback_data[-5:] if self.feedback_data else []
        }

class FeedbackAnalyzer:
    def __init__(self, feedback_storage: FeedbackStorage):
        self.storage = feedback_storage
    
    def analyze_feedback_trends(self) -> Dict[str, Any]:
        """Analyze feedback trends over time"""
        feedback_data = self.storage.get_all_feedback()
        
        if not feedback_data:
            return {"message": "No feedback data available for analysis"}
        
        # Group by date
        daily_stats = {}
        for feedback in feedback_data:
            date = feedback["timestamp"][:10]  # Get just the date part
            if date not in daily_stats:
                daily_stats[date] = {"positive": 0, "negative": 0, "total": 0}
            
            daily_stats[date]["total"] += 1
            if feedback["rating"] > 0:
                daily_stats[date]["positive"] += 1
            elif feedback["rating"] < 0:
                daily_stats[date]["negative"] += 1
        
        return {
            "daily_feedback": daily_stats,
            "total_days_with_feedback": len(daily_stats),
            "improvement_suggestions": self._generate_improvement_suggestions(feedback_data)
        }
    
    def _generate_improvement_suggestions(self, feedback_data: List[Dict[str, Any]]) -> List[str]:
        """Generate improvement suggestions based on feedback"""
        suggestions = []
        
        negative_feedback = [f for f in feedback_data if f["rating"] < 0]
        if not negative_feedback:
            return ["System performing well - no negative feedback detected"]
        
        # Analyze negative feedback comments
        negative_comments = [f["comment"] for f in negative_feedback if f.get("comment")]
        
        # Common issue detection
        common_issues = {
            "accuracy": ["wrong", "incorrect", "inaccurate", "error"],
            "speed": ["slow", "timeout", "delay", "wait"],
            "relevance": ["irrelevant", "off-topic", "unrelated"],
            "completeness": ["incomplete", "missing", "partial"]
        }
        
        issue_counts = {issue: 0 for issue in common_issues}
        
        for comment in negative_comments:
            if comment:
                comment_lower = comment.lower()
                for issue, keywords in common_issues.items():
                    if any(keyword in comment_lower for keyword in keywords):
                        issue_counts[issue] += 1
        
        # Generate suggestions based on most common issues
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                if issue == "accuracy":
                    suggestions.append(f"Improve answer accuracy - {count} accuracy complaints detected")
                elif issue == "speed":
                    suggestions.append(f"Optimize response time - {count} speed complaints detected")
                elif issue == "relevance":
                    suggestions.append(f"Improve query routing - {count} relevance complaints detected")
                elif issue == "completeness":
                    suggestions.append(f"Enhance document coverage - {count} completeness complaints detected")
        
        if len(negative_feedback) / len(feedback_data) > 0.3:
            suggestions.append("High negative feedback rate - consider system review")
        
        return suggestions if suggestions else ["Review negative feedback comments for specific issues"]