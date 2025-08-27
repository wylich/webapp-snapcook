# SnapCook

SnapCook is a simple webapp that helps you figure out what meals you can cook with the ingredients in your fridge.

## Features
- Upload a photo of your fridge
- Automatically detect ingredients
- Generate a clean list of items
- Suggest recipes based on what you have

## Getting Started
1. Clone this repository
2. Create a virtual environment and install the dependencies
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root to store your API keys (never commit this file):
   ```
   OPENAI_API_KEY=sk-xxxxxxx
   ```
4. Run the app
   ```bash
   streamlit run main.py
   ```
5. Open the provided local URL in your browser

## Roadmap
- Manual editing of detected ingredients
- More accurate food recognition
- Recipe database integration
- Support for multiple fridge photos
- Saving favorite recipes

## License
This project is licensed under the MIT License.