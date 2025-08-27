"""
SnapCook – a tiny webapp that:
1) uploads a fridge photo
2) detects ingredients with OpenAI API
3) presents the ingredient list and approximate amount
4) suggests recipes to cook (local heuristics OR OpenAI API if API key provided)

Run locally:
  python -m venv .venv && source .venv/bin/activate   # (on Windows: .venv\\Scripts\\activate)
  pip install -U streamlit ultralytics pillow requests python-dotenv openai
  create .env with OpenAI API key: OPENAI_API_KEY=sk-xxxxxxx
  streamlit run main.py

Environment:
  # created an .env file for external ingredient recognition and recipe API

Notes:
  - The default model is ChatGPT.
  - Results will be approximate; we can later fine-tune OpenAI API structured model output.
"""

import os, base64
import time
from typing import List, Dict, Tuple

from PIL import Image
import streamlit as st

from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # reads the .env file
api_key = os.getenv("OPENAI_API_KEY")   
client = OpenAI(api_key=api_key)

class Ingredient(BaseModel):
    name: str
    amount: str # one cup, two tablespoons, three pieces, etc.
    confidence: float

class IngredientList(BaseModel):
    ingredients: List[Ingredient]


def openai_extract_ingredients(pil_image, user_hint: str = "") -> list[dict]:
    """
    Sends the image to OpenAI and returns [{'name': str, 'amount': str, 'confidence': float?}, ...]
    """
    # Encode image to base64 data URL (PNG)
    from io import BytesIO
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    img_str_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    data_url = f"data:image/png;base64,{img_str_b64}"

    # System + user instruction
    sys = (
        "You are a careful kitchen assistant. Identify edible ingredients visibly present in the photo. "
        "Avoid guessing brands or flavors you cannot see. Prefer generic ingredient names (e.g., 'milk', 'eggs', 'broccoli'). "
        "Ignore utensils and containers unless their contents are clearly visible. Return JSON only."
    )
    if user_hint:
        sys += f" User hints: {user_hint}"

    response = client.responses.parse(
        model = "gpt-5-nano",
        instructions = sys,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "List ingredients you can see and their approximate amount."},
                {"type": "input_image", "image_url": data_url, "detail": "low"}, # low = 85 tokens budget (512x512 px)
            ],
        }],
        text_format=IngredientList,
    )
    return(response.output_parsed)


def detect_ingredients(image: Image.Image) -> Tuple[List[str]]:
    """
    Keep the same signature as UI expects.
    Returns (ingredients: List[str]).
    """
    findings = openai_extract_ingredients(image)
    return findings


# --- Recipe suggestion engines ---



# ----------------- Streamlit UI -----------------

st.set_page_config(page_title="SnapCook", page_icon="🥬", layout="wide")
st.title("🥬 SnapCook – What's in my fridge?")
st.caption("Upload a photo, detect ingredients, and get recipe ideas. Built with Streamlit + ChatGPT.")

with st.sidebar:
    st.header("Settings")
    user_hint = st.text_input("Optional hint (e.g., 'top shelf is sauces')", "")

uploaded = st.file_uploader("Upload a fridge photo", type=["jpg", "jpeg", "png"])

col1, col2 = st.columns([1, 1])

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    col1.subheader("Original")
    col1.image(img, use_container_width=True)

    with st.spinner("Detecting ingredients..."):
        try:
            start = time.time()
            output = detect_ingredients(img)
            dt = time.time() - start
        except Exception as e:
            st.error(f"Detection failed: {e}")
            output

    st.subheader("Ingredients found")
    if output and hasattr(output, "ingredients"):
        for item in output.ingredients:
            # name, amount, confidence = item
            st.write(f"- {item.name}: {item.amount} (confidence: {item.confidence:.2f})")
    else:
        st.info("No obvious ingredients detected. Try a clearer photo, or fine-tune the model later.")

    st.subheader("Recipe suggestions")
    recipes = []
    # if use_external:
    #     recipes = spoonacular_recipes(ingredients)
    # if not recipes:
    #     recipes = suggest_local_recipes(ingredients)

    if recipes:
        for r in recipes:
            with st.container(border=True):
                st.markdown(f"### {r['title']}")
                needs = ", ".join(sorted(r.get("needs", [])))
                if needs:
                    st.markdown(f"**Core ingredients:** {needs}")
                opt = ", ".join(sorted(r.get("optional", [])))
                if opt:
                    st.markdown(f"_Optional:_ {opt}")
                st.write(r.get("instructions", ""))
                if r.get("image"):
                    st.image(r["image"], width=256)
                if r.get("id") and SPOON_KEY:
                    st.link_button("Open on Spoonacular", f"https://spoonacular.com/recipes/{r['title'].replace(' ', '-')}-{r['id']}")
    else:
        st.info("No recipes matched well. Consider toggling the external API or adding more ingredients manually.")

else:
    st.info("Upload a photo of your fridge to get started.")

st.divider()
with st.expander("How it works / Roadmap"):
    st.markdown(
        """
        **Pipeline**
        1. **Detection**: ChatGPT on your uploaded image. We map raw classes → ingredients.
        2. **Recipes**: Either local heuristics (offline) or Spoonacular/Edamam (if API keys are set).

        **Accuracy tips**
        - Use a close, well-lit photo.
        - Train or fine-tune a custom model on fridge items you care about.
        - Add more mappings to `CLASS_TO_INGREDIENT` and more local recipes over time.

        **Next steps**
        - Manual editing of detected and missing ingredients.
        - Separate frontend from backend (e.g., React for UI, FastAPI for API).
        - Persist sessions and favorite recipes (SQLite + SQLModel/FastAPI backend).
        - Introduce streaming for real-time ingredient detection and recipe suggestions.
        - Multi-image support to scan shelves individually and merge results.
        - Track quantities and freshness dates with another photo or OCR from labels.
        """
    )
