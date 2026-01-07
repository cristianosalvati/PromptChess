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

## Testing
- **Test Framework**: pytest with pytest-html for reports
- **Test Location**: `tests/` directory
- **Run Tests**: `./run_tests.sh [opzione]`
  - `all` - Tutti i test + report HTML
  - `summary` - Riepilogo rapido
  - `components` - Sezione 3 (Componenti)
  - `functions` - Sezione 2 (Funzionalità)
  - `flow` - Sezione 5 (Flusso Operativo)
  - `hallucinations` - Sezione 6 (Gestione Hallucinations)
  - `legacy` - Test migrati da chess_test.py

## Webapp Multi-User (webapp/)
- **Server**: Flask webapp su porta 5000
- **Autenticazione**: MongoDB Atlas con password hashing PBKDF2
- **Sessioni di gioco**: Isolate per utente con persistenza MongoDB

### Servizi
- `webapp/services/login_service.py` - Autenticazione e profili utente
- `webapp/services/session_manager.py` - Gestione sessioni di gioco multi-utente

### API Endpoints
- `POST /login` - Login utente
- `POST /register` - Registrazione nuovo utente
- `GET /menu` - Menu principale
- `GET /profile` - Profilo utente
- `POST /game/new` - Crea nuova partita
- `GET /game/<id>` - Pagina partita
- `POST /api/game/<id>/move` - Invia mossa e ricevi risposta AI
- `GET /api/game/<id>/state` - Stato corrente partita

## Recent Changes
- 2026-01-07: Webapp multi-utente completa
  - Login/registrazione con MongoDB Atlas
  - Gestione profili e statistiche
  - Sessioni di gioco isolate per utente
  - API per mosse con integrazione LLM
  - Persistenza partite su MongoDB
- 2026-01-06: Creata suite di test completa
  - 66 unit test organizzati per categoria
  - Script run_tests.sh per esecuzione
  - Migrato modules/chess_test.py a tests/test_legacy.py
- 2026-01-05: Initial Replit setup
  - Added Python 3.11 with required dependencies
  - Created requirements.txt
  - Modified startup to handle missing API key gracefully
  - Added home route with service status
