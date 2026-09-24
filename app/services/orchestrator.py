import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.queue import ContentQueue, ContentStatus
from app.schemas.tools import GenericToolIntent
from app.services.interceptor import process_agent_intent


class AgentOrchestrator:
    """
    Translates user prompts into Pydantic-validated tool intents and dispatches them
    through the structural guardrail interceptor.
    """

    @staticmethod
    def parse_action_type(prompt: str) -> str:
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["purge", "delete", "remove", "cleanup", "corrupt"]):
            return "purge"
        elif any(word in prompt_lower for word in ["mark posted", "mark_posted", "posted", "publish"]):
            return "mark_posted"
        elif any(word in prompt_lower for word in ["retry", "re-try", "re-run"]):
            return "retry"
        elif any(word in prompt_lower for word in ["fail", "mark failed", "mark_failed"]):
            return "mark_failed"
        return "purge"  # default fallback

    @staticmethod
    def extract_target_id_from_text(prompt: str) -> Optional[int]:
        match = re.search(r'\b(?:id|row|item|number|target)?\s*#?\s*(\d+)\b', prompt, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    @classmethod
    def execute_prompt(
        cls,
        prompt: str,
        target_id: Optional[int],
        db_session: Session
    ) -> Dict[str, Any]:
        action_type = cls.parse_action_type(prompt)
        prompt_lower = prompt.lower()
        is_bulk = any(w in prompt_lower for w in ["all", "everything", "bulk", "cleanup", "corrupted"]) and target_id is None

        # 1. Single Target ID provided directly or extracted from text
        if target_id is None and not is_bulk:
            target_id = cls.extract_target_id_from_text(prompt)

        if target_id is not None:
            # Single tool call intent
            intent = GenericToolIntent(
                action_name=action_type,
                target_id=target_id,
                reason=f"LLM intent from prompt: '{prompt}'"
            )
            return process_agent_intent(intent, db_session)

        # 2. Bulk instruction requested
        if is_bulk:
            # Structural constraint: Tool schema only permits single-item mutations.
            # The agent loops across rows, but each mutation is individually intercepted!
            items = db_session.query(ContentQueue).all()
            if not items:
                return {
                    "status": "executed",
                    "message": "Queue is empty. No items to process.",
                    "data": {"processed_count": 0}
                }

            intercepted_results: List[Dict[str, Any]] = []
            paused_count = 0
            executed_count = 0

            for item in items:
                intent = GenericToolIntent(
                    action_name=action_type,
                    target_id=item.id,
                    reason=f"Bulk LLM intent for row {item.id} from prompt: '{prompt}'"
                )
                res = process_agent_intent(intent, db_session)
                intercepted_results.append(res)
                if res.get("status") == "paused":
                    paused_count += 1
                elif res.get("status") == "executed":
                    executed_count += 1

            if paused_count > 0:
                return {
                    "status": "paused",
                    "message": f"Bulk {action_type} intercepted: {paused_count} actions queued for HITL approval ({executed_count} executed autonomously).",
                    "action_type": action_type,
                    "autonomous": False,
                    "data": {
                        "total_items": len(items),
                        "paused_count": paused_count,
                        "executed_count": executed_count,
                        "results": intercepted_results
                    }
                }
            else:
                return {
                    "status": "executed",
                    "message": f"Bulk {action_type} completed: {executed_count} items executed autonomously.",
                    "action_type": action_type,
                    "autonomous": True,
                    "data": {
                        "total_items": len(items),
                        "executed_count": executed_count,
                        "results": intercepted_results
                    }
                }

        # Fallback if no target ID could be resolved
        first_item = db_session.query(ContentQueue).first()
        if not first_item:
            raise ValueError("No content_queue items found to execute action on.")

        intent = GenericToolIntent(
            action_name=action_type,
            target_id=first_item.id,
            reason=f"Default fallback intent from prompt: '{prompt}'"
        )
        return process_agent_intent(intent, db_session)
