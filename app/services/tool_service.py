import json
from typing import Dict, Any, Optional
from app.models.schemas import ToolCall

class ToolService:
    def __init__(self):
        # Mock database
        self.leads_db = {
            "lead_001": {"status": "qualified", "score": 85, "contact": "john@example.com"},
            "lead_002": {"status": "nurturing", "score": 45, "contact": "jane@example.com"},
            "lead_003": {"status": "closed_won", "score": 95, "contact": "bob@example.com"}
        }
        
        self.pricing_db = {
            "basic": {"price": "$10/month", "features": ["API access", "Email support"]},
            "pro": {"price": "$25/month", "features": ["API access", "Priority support", "Analytics"]},
            "enterprise": {"price": "$100/month", "features": ["Unlimited API", "24/7 support", "Custom features"]}
        }
    
    def get_lead_status(self, lead_id: str) -> Dict[str, Any]:
        """Get lead status from mock database"""
        if not isinstance(lead_id, str):
            raise ValueError("lead_id must be a string")
        
        if lead_id not in self.leads_db:
            return {"error": f"Lead {lead_id} not found"}
        
        return self.leads_db[lead_id]
    
    def get_pricing(self, plan: str) -> Dict[str, Any]:
        """Get pricing information for a plan"""
        if not isinstance(plan, str):
            raise ValueError("plan must be a string")
        
        plan = plan.lower()
        if plan not in self.pricing_db:
            return {"error": f"Plan '{plan}' not found. Available plans: basic, pro, enterprise"}
        
        return self.pricing_db[plan]
    
    def execute_tool(self, tool_call: ToolCall) -> Dict[str, Any]:
        """Execute a tool call with input validation"""
        
        # Allow list of available tools
        available_tools = {
            "get_lead_status": self.get_lead_status,
            "get_pricing": self.get_pricing
        }
        
        if tool_call.tool_name not in available_tools:
            return {"error": f"Tool '{tool_call.tool_name}' not available"}
        
        try:
            tool_func = available_tools[tool_call.tool_name]
            
            # Input validation based on tool
            if tool_call.tool_name == "get_lead_status":
                if "lead_id" not in tool_call.parameters:
                    return {"error": "Missing required parameter: lead_id"}
                return tool_func(tool_call.parameters["lead_id"])
            
            elif tool_call.tool_name == "get_pricing":
                if "plan" not in tool_call.parameters:
                    return {"error": "Missing required parameter: plan"}
                return tool_func(tool_call.parameters["plan"])
            
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def should_use_tool(self, query: str) -> Optional[ToolCall]:
        """Determine if query needs a tool call"""
        
        query_lower = query.lower()
        
        # Lead status patterns
        if any(phrase in query_lower for phrase in ["lead status", "lead_", "check lead"]):
            # Try to extract lead ID
            import re
            lead_match = re.search(r'lead[_\s]?(\w+)', query_lower)
            if lead_match:
                return ToolCall(
                    tool_name="get_lead_status",
                    parameters={"lead_id": f"lead_{lead_match.group(1).zfill(3)}"}
                )
        
        # Pricing patterns
        if any(phrase in query_lower for phrase in ["pricing", "price", "cost", "plan"]):
            # Try to extract plan name
            for plan in ["basic", "pro", "enterprise"]:
                if plan in query_lower:
                    return ToolCall(
                        tool_name="get_pricing",
                        parameters={"plan": plan}
                    )
            
            # Default to asking for clarification if no specific plan mentioned
            return ToolCall(
                tool_name="get_pricing",
                parameters={"plan": "basic"}  # the default plan
            )
        
        return None
    
