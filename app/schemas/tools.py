from typing import Literal, Union, Optional
from pydantic import BaseModel, Field


class PurgeAction(BaseModel):
    action_name: Literal["purge"] = Field(
        default="purge",
        description="Action to permanently mark a queue item as purged."
    )
    target_id: int = Field(..., description="The ID of the queue item to purge.")
    reason: str = Field(default="Stale or corrupted item purge", description="Explanation of why this is being purged.")


class MarkPostedAction(BaseModel):
    action_name: Literal["mark_posted"] = Field(
        default="mark_posted",
        description="Action to mark a pending queue item as successfully posted."
    )
    target_id: int = Field(..., description="The ID of the queue item marked as posted.")
    reason: str = Field(default="Content successfully published to channel", description="Explanation of posting.")


class RetryAction(BaseModel):
    action_name: Literal["retry"] = Field(
        default="retry",
        description="Action to retry a failed queue item by setting its status back to PENDING."
    )
    target_id: int = Field(..., description="The ID of the queue item to retry.")
    reason: str = Field(default="Retrying failed item", description="Explanation for retry attempt.")


class MarkFailedAction(BaseModel):
    action_name: Literal["mark_failed"] = Field(
        default="mark_failed",
        description="Action to mark a queue item as failed."
    )
    target_id: int = Field(..., description="The ID of the queue item marked as failed.")
    reason: str = Field(default="Item execution failed", description="Explanation for failure.")


ToolCallIntent = Union[PurgeAction, MarkPostedAction, RetryAction, MarkFailedAction]


class GenericToolIntent(BaseModel):
    action_name: str = Field(..., description="The name of the tool/action (e.g. purge, mark_posted, retry)")
    target_id: int = Field(..., description="Target content_queue item ID")
    reason: Optional[str] = Field(default="Agent tool execution", description="Reason for the mutation")
