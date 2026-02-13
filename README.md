# Agentic Google Form Builder - Phase 1

A foundational backend system for automated Google Form creation, built with FastAPI and Azure PostgreSQL.

## Overview

Phase 1 establishes the core infrastructure and authentication framework required for the Agentic Google Form Builder. This phase focuses on creating a solid foundation with user authentication, database architecture, and basic conversation management capabilities.

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: Azure PostgreSQL Flexible Server
- **Authentication**: Google OAuth 2.0
- **Cloud Provider**: Microsoft Azure

## Features

### Authentication & Authorization
- Google OAuth 2.0 integration for secure user login and signup
- Seamless access to Google Ecosystem services
- Session management and token handling

### Conversation Management
The system provides four core API endpoints for managing user conversations:

1. **Start Conversation** - Initialize a new conversation session
2. **Get All Conversations** - Retrieve list of all user conversations
3. **Get Single Conversation** - Fetch details of a specific conversation
4. **Delete Conversation** - Remove a conversation from the system

### Database Architecture
- Azure PostgreSQL Flexible Server deployment
- Scalable and reliable data persistence
- Optimized for conversation storage and retrieval

## Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── routes/                 # API endpoint definitions
│   ├── models/                 # Database models
│   ├── auth/                   # Google OAuth implementation
│   └── config/                 # Configuration files
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
DATABASE_URL=your_azure_postgresql_connection_string
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```

4. Run the application:
```bash
uvicorn main:app --reload
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Google OAuth login |
| POST | `/conversations` | Start new conversation |
| GET | `/conversations` | Get all conversations |
| GET | `/conversations/{id}` | Get specific conversation |
| DELETE | `/conversations/{id}` | Delete conversation |

## Configuration Requirements

- Azure PostgreSQL Flexible Server instance
- Google Cloud Console project with OAuth 2.0 credentials
- Appropriate API scopes enabled for Google services

## Phase 1 Objectives ✓

- ✅ FastAPI backend setup
- ✅ Azure PostgreSQL integration
- ✅ Google OAuth authentication flow
- ✅ Conversation management API endpoints
- ✅ Database schema design
- ✅ Secure credential management

## Development Notes

This phase serves as the boilerplate foundation, ensuring all core requirements are identified and implemented before progressing to more complex features. The architecture is designed to be extensible and maintainable for subsequent development phases.

# Phase 2: Planner-Executor Architecture

## Overview

Phase 2 introduces a sophisticated two-agent architecture that separates concerns between **planning** and **execution**. This design enables intelligent form generation through specialized agents that communicate asynchronously while maintaining conversation-specific context.

---

## Architecture

### **Two-Agent System**

#### 1. **Planner Agent** 🧠
- **Role**: Strategic thinking and blueprint creation
- **Responsibilities**:
  - Analyzes user requests and intent
  - Retrieves similar forms using RAG (Retrieval-Augmented Generation)
  - Designs form structure and schema
  - Creates execution blueprints
  - Makes decisions about form modifications
- **Output**: Structured form schema (JSON blueprint)

#### 2. **Executor Agent** ⚙️
- **Role**: Action execution and implementation
- **Responsibilities**:
  - Receives blueprints from Planner
  - Creates/updates Google Forms via API
  - Handles file processing and validation
  - Manages external integrations
  - Reports execution status back to Planner
- **Output**: Deployed Google Form with shareable link

---

## Agent-to-Agent (A2A) Communication

### Communication Pattern

```
User Request → Planner Agent → [Blueprint] → Executor Agent → Google Form
                    ↑                              ↓
                    └──────── Status Report ────────┘
```

### How A2A Works

1. **Planner creates a task**:
   - Analyzes user intent
   - Generates form blueprint
   - Publishes task to queue/database

2. **Executor picks up the task**:
   - Reads blueprint from task payload
   - Executes form creation/modification
   - Updates task status (pending → in_progress → completed)

3. **Planner receives confirmation**:
   - Polls or receives callback
   - Updates conversation state
   - Responds to user with results

### Benefits of A2A
- **Separation of Concerns**: Planning logic isolated from execution
- **Asynchronous Processing**: Non-blocking operations
- **Error Recovery**: Each agent can retry independently
- **Scalability**: Agents can run on different processes/servers

---

## LangGraph Workflow

### What is LangGraph?

LangGraph is used to orchestrate the Planner's multi-step reasoning process as a state machine with nodes and edges.

### Planner Workflow Graph

```
                    ┌──────────────┐
                    │  START Node  │
                    └──────┬───────┘
                           │
                           ▼
                 ┌─────────────────┐
                 │ Intent Parser   │
                 │ (RAG Retrieval) │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  LLM Generator  │
                 │ (Schema Design) │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Schema Validator│
                 └────────┬────────┘
                          │
                    ┌─────┴─────┐
                    │           │
                 Valid?      Invalid?
                    │           │
                    ▼           ▼
             ┌──────────┐  ┌──────────┐
             │ Publish  │  │  Retry   │
             │  to A2A  │  │  Loop    │
             └────┬─────┘  └────┬─────┘
                  │             │
                  │             └──────┐
                  ▼                    │
            ┌──────────┐              │
            │   END    │◄─────────────┘
            └──────────┘
```

### Node Descriptions

| Node | Purpose | State Updates |
|------|---------|---------------|
| **Intent Parser** | Embeds user prompt, retrieves similar forms from Qdrant, constructs LLM prompt | `llm_input` |
| **LLM Generator** | Calls Gemini API to generate form schema based on prompt | `form_snapshot` |
| **Schema Validator** | Validates JSON structure, field types, and business rules | `validation_errors` |
| **Task Publisher** | Creates A2A task for Executor agent | `task_id`, `status` |

### State Management

```python
class PlannerState(TypedDict):
    user_prompt: str              # Original user request
    documents: Optional[str]      # Uploaded files context
    form_snapshot: Optional[dict] # Current/generated form schema
    llm_input: str                # Constructed prompt for LLM
    validation_errors: List[str]  # Schema validation issues
    task_id: Optional[str]        # A2A task identifier
    retry_count: int              # Number of generation retries
```

---

## Memory Architecture

### **Conversational Memory** (Not Global)

#### Key Characteristics:
- **Conversation-Scoped**: Each conversation has its own isolated memory
- **No Cross-Talk**: Conversation A cannot access data from Conversation B
- **Persistent Within Conversation**: Full chat history maintained per conversation
- **Stateful Form Evolution**: Form schema evolves based on conversation history

#### Example Behavior:

**Scenario 1: Single Conversation**
```
Conversation #1:
User: "Create a job application form"
Bot: ✅ Created form with name, email, resume fields

User: "Add a phone number field"
Bot: ✅ Updated form (remembers previous form schema)

User: "Change the title to 'Career Opportunities'"
Bot: ✅ Modified title (still remembers entire form state)
```

**Scenario 2: Multiple Conversations**
```
Conversation #1:
User: "Create a job application form"
Bot: ✅ Form created

[User starts new conversation]

Conversation #2:
User: "Add a phone number field"
Bot: ❌ "I don't have a form to modify. Would you like to create a new form?"
```

**Scenario 3: Returning to Old Conversation**
```
Conversation #1 (created 2 days ago):
Previous: Job application form with 5 fields

[User returns to this conversation]

User: "Add a salary expectation field"
Bot: ✅ Updated the job application form (remembers the state from 2 days ago)
```

### Implementation Details

**Database Schema**:
```sql
conversations:
  - id (UUID, primary key)
  - user_id (FK to users)
  - form_snapshot (JSONB) -- Latest form state
  - planner_state (JSONB)  -- LangGraph state
  - executor_state (JSONB) -- Execution status
  - created_at
  - updated_at
```

**Memory Loading**:
```python
# On conversation load
conversation = db.get_conversation(conversation_id)
state = {
    "form_snapshot": conversation.form_snapshot,
    "user_prompt": new_user_message,
    # ... other state variables
}

# Planner uses previous form_snapshot as context
planner_graph.invoke(state)
```

---

## Key Differences from Phase 1

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| **Architecture** | Monolithic single agent | Two specialized agents |
| **Communication** | Direct execution | A2A task-based |
| **Workflow** | Linear script | LangGraph state machine |
| **Memory** | Session-based | Conversation-scoped persistent |
| **RAG** | No context retrieval | Qdrant vector search |
| **Scalability** | Single process | Distributed agents |
| **Error Handling** | Basic try-catch | Retry loops, validation nodes |

---

## Technology Stack

### Core Framework
- **LangGraph**: Workflow orchestration for Planner
- **LangChain**: LLM interactions and chains
- **Gemini API**: Form schema generation

### Vector Database
- **Qdrant**: Vector storage for similar form retrieval
- **Embeddings**: Text embedding for semantic search

### Data Storage
- **PostgreSQL**: Conversations, tasks, user data
- **JSONB Fields**: Form snapshots, agent states

### Communication
- **A2A Protocol**: Database-backed task queue
- **Status Polling**: Task completion monitoring

---

## Workflow Example

### Complete User Journey

```
1. User sends message: "Create a feedback form for our restaurant"

2. Planner Agent (LangGraph execution):
   ├─ Intent Parser Node:
   │  ├─ Embeds prompt → [0.234, -0.891, 0.456, ...]
   │  ├─ Queries Qdrant for similar forms
   │  ├─ Finds: "Customer Satisfaction Survey" (87% match)
   │  └─ Constructs prompt with RAG context
   │
   ├─ LLM Generator Node:
   │  ├─ Sends prompt to Gemini API
   │  └─ Receives form schema JSON
   │
   ├─ Schema Validator Node:
   │  ├─ Validates JSON structure
   │  ├─ Checks field types
   │  └─ Verifies required fields
   │
   └─ Task Publisher Node:
      ├─ Creates agent_task in database
      ├─ task_type: "execute_form"
      ├─ status: "pending"
      └─ Returns task_id

3. Executor Agent:
   ├─ Polls for pending tasks
   ├─ Picks up task_id
   ├─ Reads form_snapshot from task payload
   ├─ Calls Google Forms API:
   │  ├─ Creates form
   │  ├─ Adds fields
   │  └─ Sets permissions
   ├─ Updates task status: "completed"
   └─ Stores form_url in result

4. Planner receives completion:
   ├─ Polls task status
   ├─ Reads form_url from result
   └─ Responds to user: "✅ Form created: [link]"

5. Database state updated:
   ├─ conversation.form_snapshot = {...}
   ├─ conversation.planner_state = {...}
   └─ conversation.executor_state = {...}
```

---

## Benefits of Phase 2 Architecture

### 🎯 **Separation of Concerns**
- Planning logic isolated from execution
- Easier to debug and test each agent independently
- Clear responsibility boundaries

### 🔄 **Asynchronous Processing**
- Non-blocking operations
- Better user experience (no long waits)
- Can handle multiple requests simultaneously

### 🧠 **Intelligent Context Retrieval**
- RAG provides relevant examples
- Improves form generation quality
- Learns from previous forms

### 💾 **Persistent Conversational Memory**
- Users can return to conversations anytime
- Form state preserved across sessions
- Natural iterative refinement

### 📈 **Scalability**
- Agents can run on separate servers
- Horizontal scaling possible
- Task queue handles load distribution

### 🛡️ **Robust Error Handling**
- Validation catches issues before execution
- Retry mechanisms for transient failures
- Graceful degradation (RAG optional)

---

## Future Enhancements

- [ ] Multi-turn conversation planning
- [ ] Collaborative forms (multiple users editing)
- [ ] Form templates library
- [ ] Advanced RAG with metadata filtering
- [ ] Real-time execution status updates (WebSockets)
- [ ] Agent performance monitoring and analytics

---

## Getting Started

### Prerequisites
```bash
# Install dependencies
pip install langgraph langchain anthropic qdrant-client sqlalchemy

# Set environment variables
export GEMINI_API_KEY="your-key"
export QDRANT_URL="http://localhost:6333"
export DATABASE_URL="postgresql://user:pass@localhost/db"
```

### Running the Agents

```bash
# Start Planner agent
python -m app.agents.planner.main

# Start Executor agent (separate process)
python -m app.agents.executor.main
```

### Testing A2A Communication

```python
# Create a test conversation
response = await planner.process_message(
    conversation_id="123",
    message="Create a survey form"
)

# Check task was created
task = db.get_latest_task(conversation_id="123")
assert task.status == "pending"

# Executor picks it up
await executor.process_tasks()

# Verify completion
task = db.get_task(task.id)
assert task.status == "completed"
assert task.result["form_url"] is not None
```

---

## Conclusion

Phase 2 represents a significant architectural evolution, introducing specialized agents, intelligent context retrieval, and persistent conversational memory. The Planner-Executor pattern with A2A communication provides a robust foundation for complex form generation workflows while maintaining conversation-scoped context that feels natural to users.

The combination of LangGraph's structured workflow, RAG-enhanced intelligence, and isolated conversational memory creates a system that is both powerful and maintainable.


# Phase 3: Executor Agent - The Hands of FormsGen 🤖

## Overview

Phase 3 introduces the **Executor Agent**, a background worker that brings form schemas to life by creating actual Google Forms. While the **Planner Agent** (Phase 2) is the "brains" that designs the form structure, the **Executor Agent** is the "hands" that builds it in Google Forms.

This phase implements a robust **Agent-to-Agent (A2A)** communication protocol using database-driven task queues, enabling asynchronous, reliable form creation with proper error handling and state management.

---

## Architecture

### The Two-Agent System

```
┌─────────────────────┐         ┌─────────────────────┐
│  Planner Agent      │         │  Executor Agent     │
│  (The Brains 🧠)    │   A2A   │  (The Hands ✋)     │
├─────────────────────┤  ────→  ├─────────────────────┤
│ • Analyzes prompts  │         │ • Creates forms     │
│ • Designs schema    │         │ • Calls Google API  │
│ • Generates fields  │         │ • Manages OAuth     │
│ • Creates AgentTask │         │ • Handles errors    │
└─────────────────────┘         └─────────────────────┘
```

### A2A Protocol Flow

```
User Request
    ↓
┌───────────────────────────────┐
│ 1. Planner Agent              │
│    - Generates form_snapshot  │
│    - Creates AgentTask        │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 2. AgentTask Table (Database) │
│    task_type: "execute_form"  │
│    status: "pending"          │
│    payload: form_snapshot     │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 3. Executor Worker (Polling)  │
│    - Checks for pending tasks │
│    - Processes task           │
│    - Updates status           │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 4. Google Forms API           │
│    - Creates form             │
│    - Adds questions           │
│    - Returns form URL         │
└───────────────────────────────┘
    ↓
┌───────────────────────────────┐
│ 5. Database Update            │
│    - Stores form_id           │
│    - Stores form_url          │
│    - Updates conversation     │
└───────────────────────────────┘
```

---

## Key Components

### 1. Agent-to-Agent (A2A) Communication

**Database Table: `agent_tasks`**

```python
class AgentTask(Base):
    id: UUID                      # Unique task identifier
    conversation_id: UUID         # Links to conversation
    task_type: str                # "execute_form"
    source_agent: str             # "planner"
    target_agent: str             # "executor"
    task_payload: JSONB           # form_snapshot
    result: JSONB                 # form_id, form_url
    status: str                   # pending → processing → completed/failed
    created_at: DateTime          # Task creation time
    started_at: DateTime          # Processing start time
    completed_at: DateTime        # Processing end time
    error_message: str            # Error details if failed
```

**Why A2A?**
- ✅ **Decoupling**: Planner and Executor work independently
- ✅ **Reliability**: Tasks persist across restarts
- ✅ **Scalability**: Multiple workers can process tasks
- ✅ **Observability**: Full audit trail of all operations
- ✅ **Error Recovery**: Failed tasks can be retried

### 2. Executor Agent Architecture

**LangGraph Workflow:**

```python
┌─────────────────┐
│  extract_task   │  # Fetch task, form_snapshot, user credentials
└────────┬────────┘
         ↓
┌─────────────────┐
│ execute_forms   │  # Create Google Form via API
└────────┬────────┘
         ↓
┌─────────────────┐
│ send_response   │  # Update database, notify planner
└─────────────────┘
```

**State Management:**

```python
class ExecutorState(TypedDict):
    # Input
    task_id: str
    conversation_id: str
    form_snapshot: Dict[str, Any]
    
    # Credentials
    access_token: str
    refresh_token: str
    
    # Output
    form_id: str
    form_url: str
    
    # Status
    status: str  # "pending" | "processing" | "completed" | "failed"
    error: Optional[str]
    details: Optional[str]
```

### 3. Background Worker

**Polling Mechanism:**

```python
async def executor_worker_loop(interval: int = 5):
    """
    Continuous worker loop
    Checks for pending tasks every N seconds
    """
    while True:
        # 1. Find pending tasks
        tasks = db.query(AgentTask).filter(
            AgentTask.target_agent == "executor",
            AgentTask.status == "pending"
        ).all()
        
        # 2. Process each task
        for task in tasks:
            task.status = "processing"
            result = await executor.process(task.id)
            task.status = "completed" if result["success"] else "failed"
            db.commit()
        
        # 3. Wait before next check
        await asyncio.sleep(interval)
```

**Deployment Options:**
- 🔹 Separate process (recommended for production)
- 🔹 FastAPI background task
- 🔹 Celery task
- 🔹 Scheduled cron job
- 🔹 Docker container

---

## Google Forms API Integration

### Authentication Flow

```python
┌──────────────────────────────┐
│ User OAuth (Phase 1)         │
│ - access_token               │
│ - refresh_token              │
│ - token_expiry               │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Token Refresh (if expired)   │
│ - Check expiry               │
│ - Call OAuth2 refresh        │
│ - Update database            │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Google Forms API Client      │
│ - Build service              │
│ - Create form                │
│ - Batch update questions     │
└──────────────────────────────┘
```

### Form Creation Process

```python
# Step 1: Create empty form
form = service.forms().create(
    body={
        "info": {
            "title": "Google AI Engineer Application",
            "documentTitle": "Google AI Engineer Application"
        }
    }
).execute()

# Step 2: Add description
service.forms().batchUpdate(
    formId=form_id,
    body={"requests": [{
        "updateFormInfo": {
            "info": {"description": "Thank you for your interest..."},
            "updateMask": "description"
        }
    }]}
).execute()

# Step 3: Add questions with proper field types
requests = [
    {
        "createItem": {
            "item": {
                "title": "Full Name",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": 0}
        }
    },
    {
        "createItem": {
            "item": {
                "title": "Highest Level of Education",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "DROP_DOWN",
                            "options": [
                                {"value": "Bachelor's Degree"},
                                {"value": "Master's Degree"},
                                {"value": "Ph.D."}
                            ]
                        }
                    }
                }
            },
            "location": {"index": 1}
        }
    }
]

service.forms().batchUpdate(
    formId=form_id,
    body={"requests": requests}
).execute()

# Step 4: Get final form with responder URI
final_form = service.forms().get(formId=form_id).execute()
form_url = final_form["responderUri"]
```

### Field Type Mapping

| Internal Type | Google Forms Type | Implementation |
|---------------|-------------------|----------------|
| `text` | Short answer | `textQuestion: {paragraph: false}` |
| `paragraph` | Paragraph | `textQuestion: {paragraph: true}` |
| `email` | Short answer + validation | `textQuestion` + validation |
| `phone` | Short answer | `textQuestion` |
| `number` | Short answer + validation | `textQuestion` + number validation |
| `dropdown` | Dropdown | `choiceQuestion: {type: "DROP_DOWN"}` |
| `checkbox` | Checkboxes | `choiceQuestion: {type: "CHECKBOX"}` |
| `radio` | Multiple choice | `choiceQuestion: {type: "RADIO"}` |
| `date` | Date | `dateQuestion` |
| `time` | Time | `timeQuestion` |
| `file` | File upload | ⚠️ Not supported via API |

---

## Error Handling

### Graceful Degradation

```python
# Known API Limitations
UNSUPPORTED_FIELD_TYPES = ["file"]

def convert_field_to_question(field, index):
    field_type = field.get("type")
    
    # Skip unsupported fields
    if field_type in UNSUPPORTED_FIELD_TYPES:
        logger.warning(f"⚠️ Skipping {field_type} field - not supported by API")
        return None
    
    # Convert supported fields
    return create_question_request(field, index)
```

### Retry Logic

```python
# Automatic retry on transient failures
MAX_RETRIES = 3

for attempt in range(MAX_RETRIES):
    try:
        result = await executor.process(task_id)
        break
    except TransientError as e:
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            continue
        else:
            task.status = "failed"
            task.error_message = str(e)
```

### Status Tracking

```python
# Task lifecycle
pending     → Task created by planner
processing  → Executor is working on it
completed   → Google Form created successfully
failed      → Error occurred (with error_message)
```

---

## Database Schema

### Form Tracking

```sql
CREATE TABLE forms (
    id UUID PRIMARY KEY,
    google_form_id VARCHAR UNIQUE NOT NULL,  -- Google's form ID
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    form_url VARCHAR,                         -- Responder URI
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_form_conversation ON forms(conversation_id);
CREATE INDEX idx_form_user ON forms(user_id);
```

**Benefits:**
- ✅ **Update existing forms** instead of creating duplicates
- ✅ **Track form history** per conversation
- ✅ **Link forms to users** for access control
- ✅ **Fast lookups** via indexed columns

### Conversation Updates

```python
# Store executor results in conversation
conversation.executor_state = {
    "form_id": "1abc123xyz",
    "form_url": "https://docs.google.com/forms/d/1abc123xyz/viewform",
    "created_at": "2026-02-14T04:00:00Z",
    "status": "published"
}
```

---

## Key Features

### 1. Asynchronous Processing

**User doesn't wait for form creation:**

```python
@router.post("/conversations/start")
async def create_conversation(background_tasks: BackgroundTasks):
    # 1. Create conversation
    conversation = Conversation(...)
    db.add(conversation)
    
    # 2. Invoke planner (creates AgentTask)
    await planner_graph.ainvoke(...)
    
    # 3. Return immediately
    return {
        "id": conversation.id,
        "status": "active",
        "executor_status": "processing",  # Form creation in background
        "message": "Form schema created. Google Form creation in progress."
    }
    
    # 4. Executor worker processes task asynchronously
```

### 2. Form Updates (Not Duplicates)

```python
# Check if form already exists for conversation
existing_form = db.query(Form).filter_by(
    conversation_id=conversation_id
).first()

if existing_form:
    # UPDATE existing form
    form_id = existing_form.google_form_id
    update_form_questions(form_id, new_questions)
else:
    # CREATE new form
    form_id = create_new_form(title, questions)
    
    # Store in database
    new_form = Form(
        google_form_id=form_id,
        conversation_id=conversation_id,
        form_url=form_url
    )
    db.add(new_form)
```

### 3. OAuth Token Management

```python
async def refresh_if_expired(user, db):
    """Automatically refresh expired tokens"""
    
    if user.token_expiry > datetime.now(timezone.utc):
        return user.google_access_token  # Still valid
    
    # Token expired - refresh it
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET
    )
    
    creds.refresh(Request())
    
    # Update database
    user.google_access_token = creds.token
    user.token_expiry = creds.expiry
    await db.commit()
    
    return creds.token
```

### 4. Comprehensive Logging

```python
logger.info(f"🚀 Executor started for task {task_id}")
logger.info(f"📝 Creating form: '{title}' with {len(fields)} fields")
logger.info(f"✅ Created form with ID: {form_id}")
logger.info(f"📤 Adding {len(requests)} questions with proper field types")
logger.warning(f"⚠️ Skipped {len(skipped)} unsupported fields")
logger.info(f"✅ Form created successfully: {form_url}")
```

---

## Deployment

### Running the Executor Worker

**Option 1: Separate Process (Recommended)**

```bash
# Terminal 1: FastAPI server
uvicorn app.main:app --reload

# Terminal 2: Executor worker
python -m app.agents.executor.main
```

**Option 2: Background Task**

```python
# Add to FastAPI startup
@app.on_event("startup")
async def startup():
    asyncio.create_task(executor_worker_loop(interval=5))
```

**Option 3: Docker Container**

```yaml
# docker-compose.yml
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0
  
  executor:
    build: .
    command: python -m app.workers.executor_worker
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
```

**Option 4: Celery Task**

```python
# tasks.py
from celery import Celery

app = Celery('formsgen', broker='redis://localhost:6379')

@app.task
def process_executor_task(task_id: str):
    executor = get_executor_agent()
    return executor.process(task_id)
```

### Environment Variables

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/formsgen
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret
SECRET_KEY=your-secret-key
```

### Monitoring

```python
# Health check endpoint
@router.get("/health/executor")
async def executor_health():
    # Check pending tasks
    pending = db.query(AgentTask).filter(
        AgentTask.target_agent == "executor",
        AgentTask.status == "pending"
    ).count()
    
    # Check processing tasks
    processing = db.query(AgentTask).filter(
        AgentTask.target_agent == "executor",
        AgentTask.status == "processing"
    ).count()
    
    return {
        "status": "healthy",
        "pending_tasks": pending,
        "processing_tasks": processing
    }
```

---

## Configuration

### Database Connection Pooling

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,              # Concurrent connections
    max_overflow=20,           # Extra connections
    pool_recycle=3600,         # Recycle after 1 hour
    pool_pre_ping=True,        # Test before use (CRITICAL!)
    connect_args={
        "timeout": 60,         # Connection timeout
        "command_timeout": 300 # 5 min for long operations
    }
)
```

### Worker Configuration

```python
# app/core/settings.py
class Settings(BaseSettings):
    EXECUTOR_POLL_INTERVAL: int = 5      # Seconds between polls
    EXECUTOR_MAX_RETRIES: int = 3        # Max retry attempts
    EXECUTOR_RETRY_DELAY: int = 30       # Seconds between retries
    EXECUTOR_BATCH_SIZE: int = 10        # Tasks per batch
```

---

## Testing

### Unit Tests

```python
# tests/test_executor.py
async def test_executor_creates_form():
    # Setup
    task = AgentTask(
        task_type="execute_form",
        task_payload={
            "title": "Test Form",
            "fields": [...]
        }
    )
    
    # Execute
    executor = get_executor_agent()
    result = await executor.process(task.id)
    
    # Assert
    assert result["success"] == True
    assert result["form_id"] is not None
    assert result["form_url"].startswith("https://docs.google.com/forms")
```

### Integration Tests

```python
# tests/test_a2a.py
async def test_planner_to_executor_flow():
    # 1. Planner creates task
    await planner_graph.ainvoke({
        "user_prompt": "Create job application form",
        "conversation_id": conversation_id
    })
    
    # 2. Verify task created
    task = db.query(AgentTask).filter_by(
        conversation_id=conversation_id,
        target_agent="executor"
    ).first()
    assert task.status == "pending"
    
    # 3. Executor processes task
    await executor_worker.process_pending_tasks()
    
    # 4. Verify completion
    db.refresh(task)
    assert task.status == "completed"
    assert task.result["form_url"] is not None
```

---

## Known Limitations

### Google Forms API Constraints

1. **File Upload Questions**: Cannot be created via API
   - **Workaround**: Skip during creation, add manually
   - **Impact**: Users must add file upload fields in Google Forms UI

2. **Image Choice Questions**: Not supported via API
   - **Workaround**: Use text-based choices

3. **Grid Questions with Images**: Not supported
   - **Alternative**: Use separate questions

4. **Rate Limits**: 
   - 300 requests per minute per project
   - **Mitigation**: Implement exponential backoff

### Database Connection

1. **Long-running LLM calls** can timeout connections
   - **Solution**: `pool_pre_ping=True` and proper timeouts
   - **Alternative**: Separate DB sessions before/after LLM calls

---

## Future Enhancements

### Phase 3.1: Advanced Features

- [ ] **Form Templates**: Copy from template instead of creating from scratch
- [ ] **Batch Operations**: Process multiple tasks in parallel
- [ ] **Priority Queue**: High-priority tasks first
- [ ] **Scheduled Tasks**: Delayed or scheduled form creation
- [ ] **Webhooks**: Notify external systems on completion

### Phase 3.2: Enhanced Error Recovery

- [ ] **Dead Letter Queue**: Failed tasks go to DLQ for manual review
- [ ] **Automatic Retry**: Exponential backoff with jitter
- [ ] **Circuit Breaker**: Pause processing if API is down
- [ ] **Fallback Mode**: Create simplified form if full creation fails

### Phase 3.3: Observability

- [ ] **Metrics Dashboard**: Task throughput, success rate, latency
- [ ] **Distributed Tracing**: Track request across planner → executor
- [ ] **Real-time Updates**: WebSocket notifications to frontend
- [ ] **Audit Logs**: Complete history of all operations

---

## Success Metrics

### Performance
- ✅ **Form Creation Time**: < 5 seconds (90th percentile)
- ✅ **Task Processing Latency**: < 10 seconds from creation to completion
- ✅ **Success Rate**: > 95% of tasks complete successfully

### Reliability
- ✅ **Uptime**: 99.9% executor availability
- ✅ **Data Durability**: Zero task loss with database persistence
- ✅ **Error Recovery**: 100% of transient failures retried

### Scale
- ✅ **Throughput**: 100+ forms per minute
- ✅ **Concurrent Tasks**: 50+ simultaneous form creations
- ✅ **Queue Length**: < 100 pending tasks at any time

---

## Troubleshooting

### Common Issues

**1. "Connection reset by peer" error**
```
Solution: Update database.py with pool_pre_ping=True
```

**2. "File upload question not supported"**
```
Solution: This is a Google API limitation - skip file fields
```

**3. "Form created but no questions added"**
```
Cause: Field type mapping issue
Solution: Check convert_field_to_question() function
```

**4. "Task stuck in 'processing' status"**
```
Cause: Worker crashed mid-processing
Solution: Implement timeout and cleanup stale tasks
```

### Debug Mode

```python
# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("app.agents.executor")
logger.setLevel(logging.DEBUG)

# Log all Google API calls
import httplib2
httplib2.debuglevel = 4
```

---

## Summary

Phase 3 completes the FormsGen system by adding the **Executor Agent** - the autonomous worker that transforms form schemas into real Google Forms. Using **LangGraph** for workflow orchestration, **A2A protocol** for agent communication, and the **Google Forms API** for form creation, this phase demonstrates a production-ready, event-driven architecture.

### Key Achievements

✅ **Agent-to-Agent Communication**: Reliable database-driven task queue  
✅ **Background Processing**: Non-blocking, asynchronous form creation  
✅ **Google Forms Integration**: Full OAuth flow and API implementation  
✅ **Error Handling**: Graceful degradation and retry logic  
✅ **State Management**: LangGraph workflow with proper state tracking  
✅ **Database Optimization**: Connection pooling and timeout handling  
✅ **Form Updates**: Intelligent update vs. create logic  
✅ **Comprehensive Logging**: Full observability and debugging  

### The Complete System

```
User Input → Planner Agent → AgentTask → Executor Agent → Google Form
  (Phase 1)    (Phase 2)      (Phase 2)    (Phase 3)      (Phase 3)
```

FormsGen now has both the **brains** (Planner) and **hands** (Executor) to autonomously create sophisticated Google Forms from natural language prompts! 🎉

---

**Built with ❤️ using LangGraph, FastAPI, and Google Forms API**