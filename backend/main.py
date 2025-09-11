"""
SnapCook FastAPI Backend

A REST API that:
1) accepts uploaded fridge photos
2) detects ingredients with OpenAI API  
3) returns structured ingredient data
4) provides recipe suggestions

Run with: uvicorn backend.main:app --reload
"""

import os
import base64
import io
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

client = OpenAI(api_key=api_key)

# Pydantic models for API responses
class Ingredient(BaseModel):
    name: str
    amount: str
    confidence: float

class IngredientList(BaseModel):
    ingredients: List[Ingredient]

class Recipe(BaseModel):
    title: str
    needs: List[str]
    optional: List[str] = []
    instructions: str
    image: Optional[str] = None
    id: Optional[int] = None

class DetectionResponse(BaseModel):
    ingredients: List[Ingredient]
    processing_time: float

class RecipeResponse(BaseModel):
    recipes: List[Recipe]

# Create FastAPI app
app = FastAPI(
    title="SnapCook API",
    description="Detect ingredients from fridge photos and get recipe suggestions",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def openai_extract_ingredients(pil_image: Image.Image, user_hint: str = "") -> IngredientList:
    """
    Sends the image to OpenAI and returns structured ingredient data
    """
    # Encode image to base64 data URL (PNG)
    buffered = io.BytesIO()
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
        model="gpt-4o-mini",
        instructions=sys,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "List ingredients you can see and their approximate amount."},
                {"type": "input_image", "image_url": data_url, "detail": "low"},
            ],
        }],
        text_format=IngredientList,
    )

    return response.output_parsed

# Sample local recipes for suggestions
LOCAL_RECIPES = [
    {
        "title": "Simple Veggie Stir-Fry",
        "needs": ["broccoli", "carrot", "garlic", "soy sauce"],
        "optional": ["onion", "ginger"],
        "instructions": "Stir-fry aromatics, add chopped veggies, splash soy + water, cook till crisp-tender.",
    },
    {
        "title": "Cheesy Omelette", 
        "needs": ["eggs"],
        "optional": ["cheese", "spinach"],
        "instructions": "Beat eggs, cook gently, add fillings, fold and serve.",
    },
    {
        "title": "Fresh Salad",
        "needs": ["lettuce"],
        "optional": ["cucumber", "carrot", "cheese"],
        "instructions": "Chop vegetables, mix together, add dressing of choice.",
    },
    {
        "title": "Pan-Seared Salmon",
        "needs": ["salmon"],
        "optional": ["lemon", "garlic", "butter", "herbs"],
        "instructions": "Season salmon fillets, heat oil in pan, cook skin-side down 4 mins, flip and cook 3 mins more. Finish with lemon and herbs.",
    },
    {
        "title": "Creamy Mushroom Risotto",
        "needs": ["mushroom", "rice"],
        "optional": ["milk", "cheese", "onion", "garlic", "butter"],
        "instructions": "Sauté mushrooms and onions, add rice and stir. Gradually add warm milk/broth, stirring constantly until creamy. Finish with cheese.",
    },
    {
        "title": "Roasted Potatoes",
        "needs": ["potatoes"],
        "optional": ["garlic", "herbs", "butter"],
        "instructions": "Cut potatoes into chunks, toss with oil and seasoning. Roast at 220°C (425°F) for 25-30 mins until golden and crispy.",
    },
    {
        "title": "Salmon and Potato Bake",
        "needs": ["salmon", "potatoes"],
        "optional": ["milk", "cheese", "herbs"],
        "instructions": "Layer sliced potatoes in baking dish, place salmon on top. Pour milk over, season, and bake at 200°C (400°F) for 30-35 mins.",
    },
    {
        "title": "Mushroom Cream Sauce",
        "needs": ["mushroom", "milk"],
        "optional": ["garlic", "butter", "herbs"],
        "instructions": "Sauté sliced mushrooms until golden, add garlic, pour in milk and simmer until thickened. Season with herbs.",
    },
    {
        "title": "Tropical Pineapple Salsa",
        "needs": ["pineapple"],
        "optional": ["cucumber", "red chili pepper", "lime"],
        "instructions": "Dice pineapple and mix with chopped cucumber and chili. Add lime juice and let flavors meld for 15 mins.",
    },
    {
        "title": "Creamy Mashed Potatoes",
        "needs": ["potatoes", "milk"],
        "optional": ["butter", "cheese"],
        "instructions": "Boil potatoes until tender, drain and mash. Gradually add warm milk and butter until smooth and creamy.",
    },
    {
        "title": "Pineapple Glazed Salmon",
        "needs": ["salmon", "pineapple"],
        "optional": ["garlic", "soy sauce"],
        "instructions": "Make glaze with pineapple juice and soy sauce. Brush on salmon and bake at 200°C (400°F) for 12-15 mins until flaky.",
    },
    {
        "title": "Mushroom and Potato Gratin",
        "needs": ["mushroom", "potatoes", "milk"],
        "optional": ["cheese", "garlic", "herbs"],
        "instructions": "Layer sliced potatoes and mushrooms, pour seasoned milk over layers. Top with cheese and bake until golden.",
    },
]

def suggest_recipes(ingredients: List[str]) -> List[Recipe]:
    """
    Simple recipe matching based on available ingredients
    """
    available = set(ingredient.lower() for ingredient in ingredients)
    recipes = []
    
    for recipe_data in LOCAL_RECIPES:
        needs = set(need.lower() for need in recipe_data["needs"])
        optional = set(opt.lower() for opt in recipe_data.get("optional", []))
        
        # Check if we have at least some core ingredients
        matched_needs = needs & available
        if len(matched_needs) / len(needs) >= 0.5:  # At least 50% match
            recipes.append(Recipe(
                title=recipe_data["title"],
                needs=list(recipe_data["needs"]),
                optional=list(recipe_data.get("optional", [])),
                instructions=recipe_data["instructions"]
            ))
    
    return recipes

@app.get("/")
async def root():
    return {"message": "SnapCook API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "snapcook-api"}

@app.post("/detect-ingredients", response_model=DetectionResponse)
async def detect_ingredients(
    file: UploadFile = File(...),
    user_hint: str = Form("")
):
    """
    Upload an image and detect ingredients using OpenAI
    """
    import time
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        start_time = time.time()
        
        # Read and process the image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # Extract ingredients
        result = openai_extract_ingredients(image, user_hint)
        
        processing_time = time.time() - start_time
        
        return DetectionResponse(
            ingredients=result.ingredients,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/suggest-recipes", response_model=RecipeResponse)
async def get_recipe_suggestions(ingredients: List[str]):
    """
    Get recipe suggestions based on ingredient list
    """
    try:
        recipes = suggest_recipes(ingredients)
        return RecipeResponse(recipes=recipes)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recipe suggestion failed: {str(e)}")

@app.post("/analyze-and-suggest")
async def analyze_and_suggest(
    file: UploadFile = File(...),
    user_hint: str = Form("")
):
    """
    Combined endpoint: detect ingredients and suggest recipes in one call
    """
    try:
        # First detect ingredients
        detection_result = await detect_ingredients(file, user_hint)
        
        # Extract ingredient names for recipe suggestions
        ingredient_names = [ing.name for ing in detection_result.ingredients]
        
        # Get recipe suggestions
        recipe_result = await get_recipe_suggestions(ingredient_names)
        
        return {
            "ingredients": detection_result.ingredients,
            "processing_time": detection_result.processing_time,
            "recipes": recipe_result.recipes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
