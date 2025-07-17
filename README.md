# PromptChess

PromptChess is a demo project that showcases how to integrate natural language reasoning with a complex task—simulating a full game of chess. It leverages OpenAI's chat models to generate and validate moves, all orchestrated via a simple JSON-based protocol.

## Table of Contents

* [Overview](#overview)
* [Features](#features)
* [Architecture](#architecture)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Usage](#usage)
* [File Structure](#file-structure)
* [Configuration](#configuration)
* [Examples](#examples)
* [Contributing](#contributing)
* [License](#license)

## Overview

PromptChess demonstrates how a Python application can:

1. **Represent** a chess game entirely in JSON.
2. **Send** chess positions and move prompts to an AI language model.
3. **Receive** and parse AI-generated moves, validating legality and updating the board state.
4. **Provide** human-readable commentary and game feedback.

The core engine, **chess\_engine.py**, handles game logic and move validation. The **openai\_proxy\_service.py** client wraps calls to the OpenAI Chat API, maintaining session history and token management.

## Features

* JSON-based board representation (lists of piece coordinates by color)
* Interactive CLI for human vs. AI play
* Move legality checks and check/checkmate detection
* AI-driven move generation via OpenAI chat completions
* Configurable OpenAI model, temperature, and token limits
* Detailed move commentary and opponent feedback

## Architecture

1. **Client (`openai_proxy_service.py`)**

   * Wraps OpenAI chat completions in a Flask-based service (or internal function).
   * Manages conversation history, system messages, and dynamic token budgeting.
   * Exposes endpoints (or functions) to send message arrays and receive AI responses.

2. **Engine (`chess_engine.py`)**

   * Maintains the board as an 8×8 Pandas DataFrame.
   * Alternates turns between the human player and the AI engine.
   * Converts board states to/from JSON for transmission.
   * Invokes the client to request AI moves in a structured JSON format.
   * Parses and validates AI responses, handling retries and model upgrades on failure.

## Prerequisites

* Python 3.8 or newer
* `pip` for package installation

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/promptchess.git
   cd promptchess
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the OpenAI proxy service** (in one terminal):

   ```bash
   python openai_proxy_service.py
   ```

   This will listen on the default port (e.g., `http://localhost:5000`).

2. **Run the chess engine** (in another terminal):

   ```bash
   python chess_engine.py
   ```

3. **Play a game**:

   * Input moves in the format: `<PieceCode> <from> <to>` (e.g., `P a2 a4`).
   * The engine will display the board and prompt you for moves.
   * The AI will respond with its move, commentary, and update the board.

## File Structure

```
promptchess/
├── chess_engine.py       # Core game loop and logic
├── chess_core.py         # Board utilities and move validation
├── openai_proxy_service.py # OpenAI Chat API wrapper
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Configuration

* **Environment Variables**

  * `OPENAI_API_KEY`: Your OpenAI API key (required).
  * Optional `.env` file support via `python-dotenv`.

* **Model Settings** (in `openai_proxy_service.py`)

  * `DEFAULT_MODEL`, `DEFAULT_TEMPERATURE`, and token limits can be adjusted.

## Examples

### Initial Board Payload (JSON)

```json
{
  "neri": { "pedoni": ["a7","b7",...], "re": ["e8"], ... },
  "bianchi": { "pedoni": ["a2","b2",...], "re": ["e1"], ... }
}
```

### Move Request

```json
POST /move
{
  "board": { ... },
  "white_move": "e2-e4"
}
```

### AI Response

```json
{
  "mossa_proposta": "e7-e5",
  "neri": { ... },
  "bianchi": { ... },
  "commento_giocatore": "A standard center response...",
  "messaggio_avversario": "Your move!"
}
```

## Contributing

Contributions are welcome! Please open issues for bugs or feature requests, and submit pull requests for enhancements.

## License

This project is Free.
