
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os
import time
import uuid
from dotenv import load_dotenv

from app.models.schemas import Query, Response, Feedback, RouteType, ToolCall
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.tool_service import ToolService
from app.routers.guardrails import GuardrailsService
from app.utils.observability import ObservabilityLogger, FeedbackSystem
from app.utils.feedback import FeedbackStorage, FeedbackAnalyzer

load_dotenv()

port = int(os.environ.get("PORT", 8000))

app = FastAPI(title="Intelligent Query Router AI System", version="1.0.0")

# Initialize services
llm_service = LLMService(api_key=os.getenv("GEMINI_API_KEY", "demo-key"))
rag_service = RAGService()
tool_service = ToolService()
guardrails = GuardrailsService()
logger = ObservabilityLogger()
feedback_system = FeedbackSystem()
feedback_storage = FeedbackStorage()
feedback_analyzer = FeedbackAnalyzer(feedback_storage)

@app.post("/query", response_model=Response)
async def process_query(query: Query):
    """Main query processing endpoint"""
    
    start_time = time.time()
    query_id = str(uuid.uuid4())
    reasoning_trace = []
    tools_used = []
    chunks_retrieved = 0
    
    try:
        # Route the query
        route_decision = llm_service.route_query(query.text)
        reasoning_trace.append(f"Routed to {route_decision.route.value}: {route_decision.reasoning}")
        
        response = None
        
        # Process based on route
        if route_decision.route == RouteType.FACT_FROM_DOCS:
            # RAG processing with groundedness check
            retrieval_result = rag_service.retrieve(query.text)
            chunks_retrieved = len(retrieval_result.chunks)
            
            if not retrieval_result.grounded:
                response = Response(
                    answer="I don't have enough reliable information to answer that question.",
                    confidence=retrieval_result.confidence,
                    route_used=route_decision.route,
                    reasoning_trace=reasoning_trace + ["Insufficient grounded information in retrieved chunks"],
                    sources=[],
                    query_id=query_id
                )
            else:
                answer = llm_service.generate_answer(query.text, retrieval_result.chunks)
                
                # Groundedness check
                is_grounded = llm_service.check_groundedness(query.text, retrieval_result.chunks, answer)
                
                if not is_grounded:
                    answer = "I don't have enough information to answer that question accurately."
                    reasoning_trace.append("Generated answer failed groundedness check")
                else:
                    reasoning_trace.append("Answer passed groundedness check")
                
                response = Response(
                    answer=answer,
                    confidence=retrieval_result.confidence,
                    route_used=route_decision.route,
                    reasoning_trace=reasoning_trace,
                    sources=[f"Document chunk {i}" for i in range(len(retrieval_result.chunks))],
                    query_id=query_id
                )
        
        elif route_decision.route == RouteType.STRUCTURED_DATA:
            # Tool calling with parameter extraction
            tool_call = tool_service.should_use_tool(query.text)
            
            if tool_call:

                tools_used.append(tool_call.tool_name)
                tool_result = tool_service.execute_tool(tool_call)
                
                if "error" in tool_result:
                    answer = f"I encountered an error: {tool_result['error']}"
                    confidence = 0.2
                else:
                    answer = f"Here's the information: {tool_result}"
                    confidence = 0.9
                
                response = Response(
                    answer=answer,
                    confidence=confidence,
                    route_used=route_decision.route,
                    reasoning_trace=reasoning_trace + [f"Used tool: {tool_call.tool_name}"],
                    tool_calls=[tool_call],
                    query_id=query_id
                )
            else:
                response = Response(
                    answer="I can help with lead status and pricing information. Please specify what you'd like to know.",
                    confidence=0.7,
                    route_used=route_decision.route,
                    reasoning_trace=reasoning_trace + ["No specific tool identified for structured data request"],
                    query_id=query_id
                )
        
        elif route_decision.route == RouteType.SMALL_TALK:
            # Direct LLM response
            answer = llm_service.generate_answer(query.text)
            response = Response(
                answer=answer,
                confidence=0.8,
                route_used=route_decision.route,
                reasoning_trace=reasoning_trace + ["Generated conversational response"],
                query_id=query_id
            )
        
        elif route_decision.route == RouteType.OUT_OF_SCOPE:
            # Refusal
            response = Response(
                answer="I'm sorry, but I can't help with that request. I'm designed to assist with document questions, lead information, and pricing queries.",
                confidence=1.0,
                route_used=route_decision.route,
                reasoning_trace=reasoning_trace + ["Request determined to be out of scope"],
                query_id=query_id
            )
        
        # Apply guardrails
        guardrail_result = guardrails.apply_guardrails(query.text, response, query.user_id)
        
        if not guardrail_result["passed"]:
            reasoning_trace.append(f"Guardrails blocked response: {guardrail_result['violations']}")
            response = guardrail_result["safe_response"]
            response.query_id = query_id
        
        # Log for observability
        processing_time = (time.time() - start_time) * 1000
        logger.log_query_processing(
            query_id=query_id,
            query=query.text,
            route_chosen=route_decision.route,
            tools_used=tools_used,
            chunks_retrieved=chunks_retrieved,
            response=response,
            processing_time_ms=processing_time,
            user_id=query.user_id
        )
        
        return response
        
    except Exception as e:
        error_response = Response(
            answer="I'm sorry, I encountered an error processing your request.",
            confidence=0.0,
            route_used=RouteType.OUT_OF_SCOPE,
            reasoning_trace=reasoning_trace + [f"Error: {str(e)}"],
            query_id=query_id
        )
        
        processing_time = (time.time() - start_time) * 1000
        logger.log_query_processing(
            query_id=query_id,
            query=query.text,
            route_chosen=RouteType.OUT_OF_SCOPE,
            tools_used=tools_used,
            chunks_retrieved=chunks_retrieved,
            response=error_response,
            processing_time_ms=processing_time,
            user_id=query.user_id
        )
        
        return error_response

@app.post("/feedback")
async def submit_feedback(feedback: Feedback):
    """Submit user feedback"""
    try:
        feedback_system.store_feedback(feedback.query_id, feedback.rating, feedback.comment)
        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics")
async def get_analytics():
    """Get system analytics"""
    return {
        "query_analytics": logger.get_analytics(),
        "feedback_insights": feedback_storage.get_feedback_stats(),
        "feedback_trends": feedback_analyzer.analyze_feedback_trends(),
        "improvement_suggestions": feedback_analyzer._generate_improvement_suggestions(feedback_storage.get_all_feedback())
    }

@app.get("/feedback/{query_id}")
async def get_query_feedback(query_id: str):
    """Get feedback for a specific query"""
    feedback = feedback_storage.get_feedback_by_query(query_id)
    if feedback:
        return feedback
    else:
        raise HTTPException(status_code=404, detail="Feedback not found for this query")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "services": ["llm", "rag", "tools", "guardrails", "feedback"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)