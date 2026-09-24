from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AgentExecuteRequest(BaseModel):
    prompt: str = Field(..., description="Prompt or instruction for the agent")
    target_id: Optional[int] = Field(None, description="Optional target ID in content_queue")


class AgentExecuteResponse(BaseModel):
    status: str = Field(..., description="Execution status: 'executed', 'paused', 'blocked', or 'error'")
    message: str = Field(..., description="Human-readable message or tool simulation result")
    action_type: Optional[str] = None
    target_id: Optional[int] = None
    intent_id: Optional[str] = None
    action_id: Optional[str] = None
    autonomous: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None


class PendingActionResponse(BaseModel):
    intent_id: str
    action_type: str
    target_row_id: int
    reason: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    status: str
    created_at: Optional[str] = None


class ApproveResponse(BaseModel):
    status: str
    message: str
    action_id: str
    action_type: str
    target_id: int
    trust_count: int
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None


class RestoreRequest(BaseModel):
    action_id: str = Field(..., description="The specific action_id (UUID) to reverse")


class RestoreResponse(BaseModel):
    status: str
    success: bool
    message: str
    action_id: str
    action_type: str
    target_id: int
    restored_state: Dict[str, Any]
    new_trust_count: int


class ContentQueueItem(BaseModel):
    id: int
    content_text: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TrustStoreItem(BaseModel):
    action_type: str
    success_count: int


class ActionLogItem(BaseModel):
    action_id: str
    action_type: str
    target_row_id: Optional[int] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    executed_at: Optional[str] = None
