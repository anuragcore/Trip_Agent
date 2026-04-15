# Trip Agent

AI-powered travel planning assistant with a React/Tailwind frontend and FastAPI backend. Trip Agent uses intelligent orchestration to generate itineraries, weather-aware recommendations, cost estimates, and mission-style trip planning.

## Key Features

- Travel itinerary generation and planning
- Weather-aware recommendations
- Cost estimation and budgeting support
- AI orchestration with LLM integration
- React + Tailwind UI with a modern frontend experience
- FastAPI backend with Redis support for caching and state

## Tech Stack

- Backend: Python, FastAPI, Uvicorn, Redis
- Frontend: React, Vite, Tailwind CSS
- AI/LLM: Ollama-compatible model endpoint
- Configuration: dotenv environment variables

## Repository Structure

- `backend/` — FastAPI server, application logic, agent orchestration, services, and API routes
- `frontend/` — React application for trip form input, results display, weather details, and history

## Requirements

- Python 3.11+ (or compatible Python 3.x version)
- Node.js 18+ and npm
- Redis server
- Ollama model endpoint or compatible LLM service

## Local Setup

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in `backend/` with values such as:
   ```env
   OLLAMA_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   REDIS_HOST=localhost
   REDIS_PORT=6379
   API_PORT=8000
   LLM_TIMEOUT=60
   FALLBACK_MODE=true
   ```
4. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the development frontend:
   ```bash
   npm run dev
   ```

## Usage

- Open the frontend app in your browser from Vite when it starts
- Submit travel details through the UI
- The React app calls the FastAPI backend to generate and display trip recommendations
- Use the backend `/docs` route for API documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Notes

- Keep `.env` values secret and do not commit them to GitHub
- Add any additional integration details or deployment instructions as needed

