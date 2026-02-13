# app/agents/planner/nodes/llm_inference.py

import json
import re
from typing import Any, Dict

from sqlalchemy import select
from app.core.gemini_client import GeminiClient
from app.core.embedding_client import EmbeddingClient
from app.core.qdrant_client import QdrantClient
from app.models.conversation import Conversation
from app.core.database import AsyncSessionLocal
from app.agents.planner.state import PlannerState
import logging

logger = logging.getLogger(__name__)

llm = GeminiClient()
embedder = EmbeddingClient()
# Initialize Qdrant client (this will create collection if it doesn't exist)
qdrant = QdrantClient()


# ---------- JSON Extraction Utility ----------

def extract_json(text: str) -> Dict[str, Any]:
    """
    Safely extracts JSON from LLM output.
    Handles:
    - Markdown fences
    - Extra explanation text
    - Leading/trailing noise
    """

    if not text:
        raise ValueError("Empty LLM response")

    text = text.strip()

    # Remove markdown fences
    if text.startswith("```"):
        text = re.sub(r"```json|```", "", text).strip()

    # Attempt direct parse
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Parsed JSON is not an object")
        return parsed
    except json.JSONDecodeError:
        pass

    # Extract first JSON object block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        parsed = json.loads(match.group())
        if not isinstance(parsed, dict):
            raise ValueError("Extracted JSON is not an object")
        return parsed

    raise ValueError("Planner returned invalid JSON")


# ---------- Main Node ----------

async def llm_inference_node(state: PlannerState) -> PlannerState:
    """
    Hardened planner node with improved embedding error handling.
    - Defensive LLM handling
    - Auto JSON repair (1 retry)
    - Async DB commit
    - Embedding + Qdrant storage (with graceful failure)
    - Clear error propagation
    
    IMPORTANT: Uses conversation_id as Qdrant point ID.
    This ensures each conversation has exactly ONE point in Qdrant that gets updated,
    not multiple duplicate points.
    """

    # ----------------------------
    # 1️⃣ LLM Generation
    # ----------------------------
    try:
        llm_output_raw = await llm.generate(state["llm_input"])
        logger.info("LLM generation completed successfully")
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return {**state, "error": "llm_failure", "details": str(e)}

    if not llm_output_raw:
        return {**state, "error": "empty_llm_response"}

    # ----------------------------
    # 2️⃣ JSON Parse + Repair
    # ----------------------------
    try:
        parsed_output = extract_json(llm_output_raw)
        logger.info("JSON parsing successful")

    except Exception:
        # Repair attempt
        logger.warning("Initial JSON parsing failed, attempting repair")
        repair_prompt = f"""
You must convert the following text into STRICT valid JSON.
Return ONLY valid JSON.
No explanation. No markdown.

{llm_output_raw}
"""

        try:
            repaired_output = await llm.generate(repair_prompt)
            parsed_output = extract_json(repaired_output)
            logger.info("JSON repair successful")
        except Exception as e:
            logger.error(f"JSON repair failed: {e}")
            return {
                **state,
                "error": "invalid_json",
                "raw_output": llm_output_raw
            }

    # ----------------------------
    # 3️⃣ Save Snapshot in DB
    # ----------------------------
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == state["conversation_id"]
                )
            )

            conversation = result.scalar_one_or_none()

            if not conversation:
                return {**state, "error": "conversation_not_found"}

            conversation.form_snapshot = parsed_output
            await db.commit()
            await db.refresh(conversation)
            
            logger.info(f"📝 Form snapshot saved to database for conversation {state['conversation_id']}")

    except Exception as e:
        logger.error(f"Database save failed: {e}")
        return {**state, "error": "db_error", "details": str(e)}

    # ----------------------------
    # 4️⃣ Embedding (with graceful failure)
    # ----------------------------
    embedding = None
    try:
        form_text = json.dumps(parsed_output)
        embedding = await embedder.embed(form_text)
        logger.info(f"✅ Embedding generated successfully (dimension: {len(embedding)})")
    except Exception as e:
        logger.warning(f"⚠️ Embedding generation failed: {e}")
        logger.info("Continuing without embedding storage (form is still saved in DB)")
        # Don't return error - form is saved, embedding is optional

    # ----------------------------
    # 5️⃣ Qdrant Storage (UPSERT using conversation_id as point ID)
    # ----------------------------
    if embedding:
        try:
            # Verify embedding dimension matches Qdrant collection
            if len(embedding) != qdrant.vector_size:
                logger.error(
                    f"⚠️ Embedding dimension mismatch: "
                    f"generated {len(embedding)}, expected {qdrant.vector_size}"
                )
                logger.info("Skipping Qdrant storage due to dimension mismatch")
            else:
                # CRITICAL: Use conversation_id as the Qdrant point ID
                # This ensures UPSERT behavior - updates existing point instead of creating duplicates
                await qdrant.store_embedding(
                    conversation_id=state["conversation_id"],  # This is used as point ID
                    vector=embedding,
                    payload=parsed_output
                )
                logger.info(
                    f"✅ Embedding stored/updated in Qdrant for conversation {state['conversation_id']}"
                )
                
        except Exception as e:
            logger.warning(f"⚠️ Qdrant storage failed: {e}")
            logger.info("Continuing without Qdrant storage (form is still saved in DB)")
            # Don't return error - form is saved, Qdrant is optional
    else:
        logger.info("Skipping Qdrant storage (no embedding available)")

    # ----------------------------
    # 6️⃣ Success
    # ----------------------------
    return {
        **state,
        "llm_output": parsed_output,
        "error": None
    }