#!/usr/bin/env python3
"""
Simple test script for the SnapCook FastAPI backend
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_detect_ingredients(image_path):
    """Test ingredient detection with an image file"""
    print(f"Testing ingredient detection with {image_path}...")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {'user_hint': 'This is my fridge'}
            
            response = requests.post(f"{API_BASE_URL}/detect-ingredients", files=files, data=data)
            
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Processing time: {result['processing_time']:.2f}s")
            print("Ingredients found:")
            for ingredient in result['ingredients']:
                print(f"  - {ingredient['name']}: {ingredient['amount']} (confidence: {ingredient['confidence']:.2f})")
        else:
            print(f"Error: {response.text}")
    except FileNotFoundError:
        print(f"Image file not found: {image_path}")
    except Exception as e:
        print(f"Error: {e}")
    print()

def test_suggest_recipes():
    """Test recipe suggestions"""
    print("Testing recipe suggestions...")
    
    test_ingredients = ["eggs", "cheese", "lettuce", "broccoli"]
    
    response = requests.post(
        f"{API_BASE_URL}/suggest-recipes",
        json=test_ingredients,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("Recipe suggestions:")
        for recipe in result['recipes']:
            print(f"  - {recipe['title']}")
            print(f"    Needs: {', '.join(recipe['needs'])}")
            if recipe['optional']:
                print(f"    Optional: {', '.join(recipe['optional'])}")
            print(f"    Instructions: {recipe['instructions']}")
            print()
    else:
        print(f"Error: {response.text}")
    print()

if __name__ == "__main__":
    print("SnapCook API Test Suite")
    print("=" * 40)
    
    # Test basic endpoints
    test_health()
    test_suggest_recipes()
    
    # Test with an image if available
    # Uncomment and provide a path to test image detection:
    # test_detect_ingredients("path/to/your/test/image.jpg")
    
    print("Tests completed!")
