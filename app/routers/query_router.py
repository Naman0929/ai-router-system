import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class ExtractedParameters:
    lead_ids: List[str]
    plans: List[str]
    dates: List[str]
    numbers: List[float]
    entities: List[str]

class QueryParameterExtractor:
    def __init__(self):
        # Regex patterns for common parameter types
        self.patterns = {
            'lead_id': [
                r'lead[_\s]?(\w+)',
                r'lead\s*#?(\w+)',
                r'(\w*\d{3}\w*)',  # Patterns like 001, abc123, etc.
            ],
            'plan': [
                r'\b(basic|pro|enterprise|premium|starter)\b',
                r'([\w]+)\s*plan',
                r'tier\s*(\w+)'
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'phone': [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                r'$\d{3}$\s*\d{3}[-.]?\d{4}'
            ],
            'date': [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b\d{4}-\d{2}-\d{2}\b',
                r'\b(today|tomorrow|yesterday)\b'
            ],
            'number': [
                r'\b\d+\.?\d*\b'
            ],
            'currency': [
                r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
                r'\b\d+\s*(?:dollars?|usd|\$)\b'
            ]
        }
        
        # Known entities for different domains
        self.known_entities = {
            'lead_statuses': ['qualified', 'nurturing', 'closed_won', 'closed_lost', 'new', 'contacted'],
            'plan_types': ['basic', 'pro', 'enterprise', 'premium', 'starter', 'free'],
            'time_periods': ['today', 'yesterday', 'tomorrow', 'week', 'month', 'year'],
            'actions': ['get', 'fetch', 'retrieve', 'show', 'display', 'find', 'search', 'check']
        }
    
    def extract_all_parameters(self, query: str) -> ExtractedParameters:
        """Extract all possible parameters from query"""
        query_lower = query.lower()
        
        return ExtractedParameters(
            lead_ids=self._extract_lead_ids(query_lower),
            plans=self._extract_plans(query_lower),
            dates=self._extract_dates(query_lower),
            numbers=self._extract_numbers(query_lower),
            entities=self._extract_entities(query_lower)
        )
    
    def _extract_lead_ids(self, query: str) -> List[str]:
        """Extract lead IDs from query"""
        lead_ids = []
        
        for pattern in self.patterns['lead_id']:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                # Standardize lead ID format
                if match.isdigit():
                    lead_ids.append(f"lead_{match.zfill(3)}")
                elif not match.startswith('lead_'):
                    lead_ids.append(f"lead_{match}")
                else:
                    lead_ids.append(match)
        
        return list(set(lead_ids))  # Remove duplicates
    
    def _extract_plans(self, query: str) -> List[str]:
        """Extract plan names from query"""
        plans = []
        
        for pattern in self.patterns['plan']:
            matches = re.findall(pattern, query, re.IGNORECASE)
            plans.extend([match.lower() for match in matches if match.lower() in self.known_entities['plan_types']])
        
        return list(set(plans))
    
    def _extract_dates(self, query: str) -> List[str]:
        """Extract dates from query"""
        dates = []
        
        for pattern in self.patterns['date']:
            matches = re.findall(pattern, query, re.IGNORECASE)
            dates.extend(matches)
        
        return list(set(dates))
    
    def _extract_numbers(self, query: str) -> List[float]:
        """Extract numbers from query"""
        numbers = []
        
        for pattern in self.patterns['number']:
            matches = re.findall(pattern, query)
            for match in matches:
                try:
                    numbers.append(float(match))
                except ValueError:
                    continue
        
        return list(set(numbers))
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract known entities from query"""
        entities = []
        
        query_words = query.split()
        for category, entity_list in self.known_entities.items():
            for entity in entity_list:
                if entity in query or any(entity in word for word in query_words):
                    entities.append(f"{category}:{entity}")
        
        return entities
    
    def extract_for_tool(self, query: str, tool_name: str) -> Dict[str, Any]:
        """Extract parameters specific to a tool"""
        all_params = self.extract_all_parameters(query)
        
        if tool_name == "get_lead_status":
            return {
                "lead_id": all_params.lead_ids[0] if all_params.lead_ids else None,
                "all_lead_ids": all_params.lead_ids
            }
        
        elif tool_name == "get_pricing":
            return {
                "plan": all_params.plans[0] if all_params.plans else "basic",
                "all_plans": all_params.plans
            }
        
        elif tool_name == "search_leads":
            # Example additional tool
            return {
                "status_filter": self._extract_status_from_entities(all_params.entities),
                "date_range": all_params.dates
            }
        
        return {}
    
    def _extract_status_from_entities(self, entities: List[str]) -> Optional[str]:
        """Extract lead status from entities list"""
        for entity in entities:
            if entity.startswith("lead_statuses:"):
                return entity.split(":")[1]
        return None
    
    def suggest_missing_parameters(self, query: str, tool_name: str) -> List[str]:
        """Suggest what parameters might be missing for a tool"""
        suggestions = []
        params = self.extract_for_tool(query, tool_name)
        
        if tool_name == "get_lead_status":
            if not params.get("lead_id"):
                suggestions.append("Please specify a lead ID (e.g., 'lead_001' or just '001')")
        
        elif tool_name == "get_pricing":
            if not params.get("plan") or params.get("plan") == "basic":
                suggestions.append("Specify a plan type: basic, pro, or enterprise")
        
        return suggestions

class QueryIntent:
    """Determine the intent behind a query"""
    
    def __init__(self):
        self.intent_patterns = {
            'get_info': ['what is', 'tell me about', 'show me', 'get', 'fetch', 'retrieve'],
            'compare': ['compare', 'difference', 'vs', 'versus', 'better'],
            'list': ['list', 'show all', 'what are', 'give me all'],
            'help': ['help', 'how to', 'instructions', 'guide'],
            'update': ['update', 'change', 'modify', 'set'],
            'create': ['create', 'add', 'new', 'make'],
            'delete': ['delete', 'remove', 'cancel']
        }
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """Classify the intent of a query"""
        query_lower = query.lower()
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return {"intent": "unknown", "confidence": 0.0, "reasoning": "No recognizable intent patterns"}
        
        # Get the intent with highest score
        primary_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[primary_intent] / len(query_lower.split())
        
        return {
            "intent": primary_intent,
            "confidence": min(confidence, 1.0),
            "reasoning": f"Detected '{primary_intent}' intent based on keywords",
            "all_intents": intent_scores
        }
    
    def is_question(self, query: str) -> bool:
        """Determine if query is a question"""
        question_indicators = ['what', 'how', 'when', 'where', 'why', 'who', 'which', '?']
        query_lower = query.lower()
        
        return any(indicator in query_lower for indicator in question_indicators)