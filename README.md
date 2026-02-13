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