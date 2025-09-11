# SnapCook

SnapCook is a webapp that helps you figure out what meals you can cook with the ingredients in your fridge. Now built with FastAPI backend for better scalability and API access.

## Features
- Upload a photo of your fridge via REST API
- Automatically detect ingredients using OpenAI API
- Generate a clean list of items with confidence scores
- Get recipe suggestions based on available ingredients
- RESTful API for integration with other applications

## Architecture
- **Backend**: FastAPI with OpenAI integration
- **Frontend**: Simple HTML/JavaScript interface
- **API**: RESTful endpoints for ingredient detection and recipe suggestions

## Getting Started

### Backend Setup
1. Clone this repository
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
   pip install --upgrade pip
   pip install .
   ```
3. Create a `.env` file in the project root to store your API keys (never commit this file):
   ```
   OPENAI_API_KEY=sk-xxxxxxx
   ```
4. Run the FastAPI backend:
   ```bash
   uvicorn backend.main:app --reload
   ```
   The API will be available at `http://localhost:8000`

### Frontend Setup
1. Open `frontend/index.html` in your web browser
2. Or serve it with a simple HTTP server:
   ```bash
   # Python 3
   cd frontend
   python -m http.server 3000
   ```
   Then visit `http://localhost:3000`

## API Endpoints

### `GET /health`
Health check endpoint

### `POST /detect-ingredients`
Upload an image and detect ingredients
- **Body**: Form data with `file` (image) and optional `user_hint` (string)
- **Response**: JSON with ingredients list and processing time

### `POST /suggest-recipes`
Get recipe suggestions based on ingredient list
- **Body**: JSON array of ingredient names
- **Response**: JSON with recipe suggestions

### `POST /analyze-and-suggest`
Combined endpoint: detect ingredients and get recipe suggestions
- **Body**: Form data with `file` (image) and optional `user_hint` (string)
- **Response**: JSON with ingredients and recipe suggestions

## Roadmap
- Manual editing of detected and missing ingredients
- More accurate food recognition
- Recipe database integration
- Support for multiple fridge photos
- Saving favorite recipes
- Multi-image support to scan shelves individually and merge results.
- Track quantities and freshness dates with another photo or OCR from labels.

## License
This project is licensed under the MIT License.