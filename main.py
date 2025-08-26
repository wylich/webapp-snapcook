"""
SnapCook – a tiny webapp that:
1) uploads a fridge photo
2) detects ingredients with YOLOv8 (Ultralytics)
3) cleans the ingredient list
4) suggests recipes to cook (local heuristics OR Spoonacular/Edamam if API key provided)

Run locally:
  python -m venv .venv && source .venv/bin/activate   # (on Windows: .venv\\Scripts\\activate)
  pip install -U streamlit ultralytics pillow requests python-dotenv
  streamlit run app.py

Optional:
  # If you want higher accuracy for produce, install:
  # pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121  (or cpu wheels)

Environment:
  # create a .env file if you want to use an external recipe API
  SPOONACULAR_KEY=your_api_key_here
  EDAMAM_APP_ID=xxx
  EDAMAM_APP_KEY=yyy

Notes:
  - The default model is YOLOv8n pretrained on COCO; it recognizes many foods/containers.
  - Results will be approximate; you can later fine-tune on a custom “fridge” dataset.
"""

import os
import io
import time
from typing import List, Dict, Tuple

import streamlit as st
from PIL import Image

# Lazy import so Streamlit can start fast
YOLO = None

def load_model():
    global YOLO
    if YOLO is None:
        from ultralytics import YOLO as _YOLO
        YOLO = _YOLO("yolov8n.pt")  # tiny, fast. swap to yolov8m.pt for accuracy
    return YOLO

# Map YOLO class names -> normalized ingredient names (extend over time)
CLASS_TO_INGREDIENT = {
    "apple": "apple",
    "banana": "banana",
    "broccoli": "broccoli",
    "carrot": "carrot",
    "orange": "orange",
    "pizza": "leftover pizza",
    "cake": "cake",
    "bottle": "bottle (unspecified)",
    "wine glass": "wine (opened)",
    "cup": "yogurt/pudding cup (unspecified)",
    "bowl": "bowl (unspecified)",
    "sandwich": "sandwich",
    "hot dog": "sausage",
    "donut": "donut",
    "egg": "eggs",
    "knife": None,
    "spoon": None,
    "fork": None,
}

# Simple synonyms/normalizer
SYNONYMS = {
    "bell pepper": "capsicum",
    "courgette": "zucchini",
}

BASIC_PANTRY = {"salt", "pepper", "oil", "water", "butter"}


def dedupe_and_clean(items: List[str]) -> List[str]:
    out = []
    seen = set()
    for x in items:
        if not x:
            continue
        x = x.strip().lower()
        x = SYNONYMS.get(x, x)
        if x in ("bottle (unspecified)", "bowl (unspecified)", "yogurt/pudding cup (unspecified)"):
            # skip containers unless confident
            continue
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def detect_ingredients(image: Image.Image, conf: float = 0.35) -> Tuple[List[str], Image.Image]:
    """Run YOLO detection and return ingredient list + annotated image."""
    model = load_model()
    results = model.predict(image, conf=conf, verbose=False)
    if not results:
        return [], image

    r = results[0]
    labels = []
    for box in r.boxes:
        cls_id = int(box.cls[0].item())
        score = float(box.conf[0].item())
        name = r.names[cls_id]
        mapped = CLASS_TO_INGREDIENT.get(name, name)  # fallback to raw class name
        if mapped:
            labels.append(mapped)
    # Render annotated image
    annotated = r.plot()  # numpy array (BGR)
    annotated_img = Image.fromarray(annotated[:, :, ::-1])
    return dedupe_and_clean(labels), annotated_img


# --- Recipe suggestion engines ---
import requests
from dotenv import load_dotenv
load_dotenv()

SPOON_KEY = os.getenv("SPOONACULAR_KEY")
EDAMAM_ID = os.getenv("EDAMAM_APP_ID")
EDAMAM_KEY = os.getenv("EDAMAM_APP_KEY")

LOCAL_RECIPES = [
    {
        "title": "Simple Veggie Stir-Fry",
        "needs": {"broccoli", "carrot", "garlic", "soy sauce"},
        "optional": {"onion", "ginger"},
        "instructions": "Stir-fry aromatics, add chopped veggies, splash soy + water, cook till crisp-tender.",
    },
    {
        "title": "Cheesy Omelette",
        "needs": {"eggs"},
        "optional": {"cheese", "spinach"},
        "instructions": "Beat eggs, cook gently, add fillings, fold and serve.",
    },
    {
        "title": "Banana Pancakes",
        "needs": {"banana", "eggs", "flour"},
        "optional": {"milk"},
        "instructions": "Mash banana, whisk with eggs and flour, fry small pancakes.",
    },
]


def score_recipe(recipe: Dict, have: set) -> float:
    needs = recipe["needs"]
    optional = recipe.get("optional", set())
    have_needs = len(needs & have)
    missing_needs = len(needs - have)
    have_opt = len(optional & have)
    # prioritize covering needs; small bonus for optionals
    return have_needs * 10 + have_opt * 2 - missing_needs * 20


def suggest_local_recipes(ingredients: List[str], k: int = 5) -> List[Dict]:
    have = set(ingredients) | BASIC_PANTRY
    scored = sorted(LOCAL_RECIPES, key=lambda r: score_recipe(r, have), reverse=True)
    # filter out recipes that miss more than half of needed items
    out = []
    for r in scored:
        needs = r["needs"]
        if len(needs & have) / max(1, len(needs)) >= 0.5:
            out.append(r)
    return out[:k]


def spoonacular_recipes(ingredients: List[str], k: int = 5) -> List[Dict]:
    if not SPOON_KEY:
        return []
    try:
        q = ",".join(ingredients)
        url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={q}&number={k}&apiKey={SPOON_KEY}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data:
            results.append({
                "title": item.get("title"),
                "needs": set(),
                "optional": set(),
                "instructions": "Open link for instructions.",
                "id": item.get("id"),
                "image": item.get("image"),
                "missedIngredientCount": item.get("missedIngredientCount"),
            })
        return results
    except Exception:
        return []


# ----------------- Streamlit UI -----------------

st.set_page_config(page_title="SnapCook", page_icon="🥬", layout="wide")
st.title("🥬 SnapCook – What's in my fridge?")
st.caption("Upload a photo, detect ingredients, and get recipe ideas. Built with Streamlit + YOLOv8.")

with st.sidebar:
    st.header("Settings")
    conf = st.slider("Detection confidence", 0.1, 0.8, 0.35, 0.05)
    use_external = st.checkbox("Use external recipe API (if configured)", value=False)

uploaded = st.file_uploader("Upload a fridge photo", type=["jpg", "jpeg", "png"])

col1, col2 = st.columns([1, 1])

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    col1.subheader("Original")
    col1.image(img, use_container_width=True)

    with st.spinner("Detecting ingredients..."):
        try:
            start = time.time()
            ingredients, annotated = detect_ingredients(img, conf=conf)
            dt = time.time() - start
        except Exception as e:
            st.error(f"Detection failed: {e}")
            ingredients, annotated = [], img

    col2.subheader("Detections")
    col2.image(annotated, use_container_width=True)

    st.subheader("Ingredients found")
    if ingredients:
        st.write(", ".join(ingredients))
    else:
        st.info("No obvious ingredients detected. Try a clearer photo, or fine-tune the model later.")

    st.subheader("Recipe suggestions")
    recipes = []
    if use_external:
        recipes = spoonacular_recipes(ingredients)
    if not recipes:
        recipes = suggest_local_recipes(ingredients)

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
        1. **Detection**: Ultralytics YOLOv8n on your uploaded image. We map raw classes → ingredients.
        2. **Cleaning**: Deduplicate, drop containers, normalize names.
        3. **Recipes**: Either local heuristics (offline) or Spoonacular/Edamam (if API keys are set).

        **Accuracy tips**
        - Use a close, well-lit photo.
        - Train or fine-tune a custom model on fridge items you care about (Ultralytics makes this straightforward).
        - Add more mappings to `CLASS_TO_INGREDIENT` and more local recipes over time.

        **Next steps**
        - 
        - Track quantities and freshness dates with another photo or OCR from labels.
        - Persist sessions and favorite recipes (SQLite + SQLModel/FastAPI backend).
        - Multi-image support to scan shelves individually and merge results.
        """
    )
