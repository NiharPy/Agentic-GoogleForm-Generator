from app.agents.planner.base_node import BaseNode
from app.agents.planner.state import PlannerState
from app.core.embedding_client import EmbeddingClient
from app.core.qdrant_client import QdrantClient
import json
import logging

logger = logging.getLogger(__name__)

embedder = EmbeddingClient()
qdrant = QdrantClient()


async def intent_parser_node(state: PlannerState) -> PlannerState:
    """
    Enhanced intent parser with RAG:
    1. Embeds the user prompt
    2. Retrieves similar forms from Qdrant
    3. Includes relevant examples in the LLM prompt
    4. Constructs structured prompt with system instructions
    """
    
    prompt = state["user_prompt"]
    documents = state.get("documents")
    existing_snapshot = state.get("form_snapshot")
    
    # ----------------------------
    # 1️⃣ Retrieve Similar Forms (RAG) - Optional, fail gracefully
    # ----------------------------
    similar_forms_context = ""
    
    # Only attempt RAG if not the first form (to avoid errors on empty Qdrant)
    if existing_snapshot is None:
        try:
            # Embed the user prompt
            query_embedding = await embedder.embed(prompt)
            logger.info(f"Successfully embedded user prompt (dimension: {len(query_embedding)})")
            
            # Retrieve similar forms from Qdrant
            similar_forms = await qdrant.retrieve_similar(
                query_vector=query_embedding,
                limit=3,  # Top 3 most similar forms
                score_threshold=0.5  # Only forms with >50% similarity
            )
            
            if similar_forms:
                logger.info(f"✅ Found {len(similar_forms)} similar forms for context")
                
                # Format similar forms as examples
                examples = []
                for i, form in enumerate(similar_forms, 1):
                    examples.append(f"""
Example {i} (Similarity: {form['score']:.2%}):
{json.dumps(form['form_snapshot'], indent=2)}
""")
                
                similar_forms_context = f"""
SIMILAR FORMS FROM DATABASE (Use these as reference):
{''.join(examples)}

Note: These are real forms from our database that are similar to what the user is asking for.
Use them as inspiration for structure and field types, but create a unique form based on the user's specific request.
"""
            else:
                logger.info("No similar forms found in Qdrant (score threshold not met)")
                
        except Exception as e:
            logger.warning(f"RAG retrieval skipped or failed: {e}")
            logger.info("Continuing without RAG context (this is normal for the first few forms)")
    else:
        logger.info("Updating existing form, skipping RAG retrieval")
    
    # ----------------------------
    # 2️⃣ Build System Instructions
    # ----------------------------
    system_prompt = """You are a Google Forms generator AI. Your job is to convert user requests into structured form schemas.

CRITICAL RULES:
1. ALWAYS return ONLY valid JSON, no explanations, no markdown
2. The JSON must follow the exact schema below
3. If updating an existing form, modify it based on the user's request
4. If creating a new form, generate all necessary fields

OUTPUT SCHEMA:
{
  "title": "Form Title",
  "description": "Optional form description",
  "fields": [
    {
      "id": "unique_field_id",
      "type": "text|email|phone|number|dropdown|checkbox|radio|date|time|file|rating|paragraph",
      "label": "Question text",
      "placeholder": "Optional placeholder text",
      "required": true|false,
      "options": ["Option 1", "Option 2"],  // Only for dropdown, checkbox, radio
      "validation": {  // Optional
        "min": 1,
        "max": 100,
        "pattern": "regex pattern"
      }
    }
  ],
  "settings": {
    "allow_multiple_responses": false,
    "collect_email": true,
    "confirmation_message": "Thank you for your response!"
  }
}

FIELD TYPES REFERENCE:
- text: Short text input (names, titles)
- paragraph: Long text input (comments, descriptions)
- email: Email address with validation
- phone: Phone number
- number: Numeric input with min/max
- dropdown: Select one from dropdown list
- checkbox: Select multiple options
- radio: Select one option (radio buttons)
- date: Date picker
- time: Time picker
- file: File upload
- rating: Star rating (1-5 or 1-10)

GENERATION GUIDELINES:
- Use clear, concise labels
- Set appropriate required flags
- Include validation where needed
- Use descriptive field IDs (field_1, field_2, etc.)
- For dropdowns/radio/checkbox, provide 3-7 relevant options
- Add helpful placeholders for text fields
- Include a confirmation message in settings

EXAMPLES:

User: "Create a job application form"
Response:
{
  "title": "Job Application Form",
  "description": "Please fill out this form to apply for the position",
  "fields": [
    {
      "id": "field_1",
      "type": "text",
      "label": "Full Name",
      "placeholder": "Enter your full name",
      "required": true
    },
    {
      "id": "field_2",
      "type": "email",
      "label": "Email Address",
      "required": true
    },
    {
      "id": "field_3",
      "type": "phone",
      "label": "Phone Number",
      "required": true
    },
    {
      "id": "field_4",
      "type": "dropdown",
      "label": "Position Applying For",
      "required": true,
      "options": ["Software Engineer", "Product Manager", "Designer", "Other"]
    },
    {
      "id": "field_5",
      "type": "number",
      "label": "Years of Experience",
      "required": true,
      "validation": {"min": 0, "max": 50}
    },
    {
      "id": "field_6",
      "type": "file",
      "label": "Upload Resume (PDF)",
      "required": true
    },
    {
      "id": "field_7",
      "type": "paragraph",
      "label": "Why do you want to work here?",
      "required": false
    }
  ],
  "settings": {
    "allow_multiple_responses": false,
    "collect_email": true,
    "confirmation_message": "Thank you for applying! We'll review your application and get back to you soon."
  }
}

User: "Add a rating field from 1 to 5"
Existing form: {"title": "Feedback", "fields": [{"id": "field_1", "type": "text", "label": "Name"}]}
Response:
{
  "title": "Feedback",
  "fields": [
    {
      "id": "field_1",
      "type": "text",
      "label": "Name",
      "required": false
    },
    {
      "id": "field_2",
      "type": "rating",
      "label": "Rate your experience",
      "required": false,
      "validation": {"min": 1, "max": 5}
    }
  ]
}

REMEMBER:
- Return ONLY the JSON object
- No markdown code blocks
- No explanations before or after
- Generate unique IDs for new fields
- Preserve existing field IDs when modifying
"""
    
    # ----------------------------
    # 3️⃣ Construct Full Prompt
    # ----------------------------
    if existing_snapshot:
        # Updating existing form
        full_prompt = f"""{system_prompt}

{similar_forms_context if similar_forms_context else ""}

TASK: Update the existing form based on the user's request.

USER REQUEST:
{prompt}

EXISTING FORM (modify this):
{json.dumps(existing_snapshot, indent=2)}

{f"ADDITIONAL CONTEXT FROM DOCUMENTS:\n{documents}\n" if documents else ""}

Return the COMPLETE updated form as JSON. Include all existing fields unless explicitly asked to remove them.
Only modify what the user requests - preserve everything else.
"""
    else:
        # Creating new form
        full_prompt = f"""{system_prompt}

{similar_forms_context if similar_forms_context else ""}

TASK: Create a new form based on the user's request.

USER REQUEST:
{prompt}

{f"ADDITIONAL CONTEXT FROM DOCUMENTS:\n{documents}\n" if documents else ""}

Return the complete form schema as JSON.
Generate appropriate fields based on the user's needs.
"""
    
    logger.info(f"Intent parser constructed prompt | RAG context included: {len(similar_forms_context) > 0}")
    
    return {
        **state,
        "llm_input": full_prompt
    }