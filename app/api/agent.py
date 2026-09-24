from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.api import AgentExecuteRequest, AgentExecuteResponse
from app.services.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/api/agent", tags=["Agent Execution"])


@router.post("/execute", response_model=AgentExecuteResponse)
def execute_agent_command(
    request: AgentExecuteRequest,
    db: Session = Depends(get_db)
):
    """
    Triggers the LLM agent to interpret the prompt and formulate a tool call.
    The structural guardrail interceptor checks trust counters and enforces HITL gating.
    """
    try:
        result = AgentOrchestrator.execute_prompt(
            prompt=request.prompt,
            target_id=request.target_id,
            db_session=db
        )
        return AgentExecuteResponse(
            status=result.get("status", "executed"),
            message=result.get("message", "Processed intent"),
            action_type=result.get("action_type"),
            target_id=result.get("target_id"),
            intent_id=result.get("intent_id"),
            action_id=result.get("action_id"),
            autonomous=result.get("autonomous"),
            data=result.get("data")
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal agent execution error: {str(e)}")
