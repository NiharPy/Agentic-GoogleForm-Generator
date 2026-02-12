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
