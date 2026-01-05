# PromptChess

## Overview
PromptChess is a Python Flask application that demonstrates integrating natural language reasoning with chess gameplay. It uses OpenAI's chat models to generate and validate chess moves through a JSON-based protocol.

## Architecture
- **Backend**: Python Flask server (`openai_proxy_service.py`) on port 5000
- **OpenAI Integration**: Wraps OpenAI Chat API for AI-powered chess moves
- **Chess Engine**: `chess_engine.py` - CLI-based chess game with human vs AI play

## Key Files
- `openai_proxy_service.py` - Main Flask server exposing chat endpoints
- `chess_engine.py` - Core chess game logic and CLI interface
- `modules/chess_core.py` - Board utilities and move validation
- `config.json` - Application configuration

## API Endpoints
- `GET /` - Service status and available endpoints
- `POST /chat` - Send chat prompts to OpenAI
- `POST /chat/init` - Initialize chat session with system messages
- `GET /chat/history` - Retrieve conversation history
- `POST /chat/append` - Add messages to conversation

## Environment Variables
- `OPENAI_API_KEY` (required) - Your OpenAI API key for AI features

## Running the Application
1. The Flask server runs on port 5000
2. Set the `OPENAI_API_KEY` environment variable
3. Use the workflow to start the server

## Recent Changes
- 2026-01-05: Initial Replit setup
  - Added Python 3.11 with required dependencies
  - Created requirements.txt
  - Modified startup to handle missing API key gracefully
  - Added home route with service status
