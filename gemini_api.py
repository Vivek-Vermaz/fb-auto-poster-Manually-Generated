import os
import requests
import google.generativeai as genai
from io import BytesIO

def init_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=api_key)

def generate_caption(image_url, prompt):
    """
    Downloads the image from the URL into memory, sends it to Gemini 1.5 Flash 
    along with the prompt, and returns the generated caption.
    """
    init_gemini()
    
    # 1. Download image into memory
    print("Downloading image for AI analysis...")
    response = requests.get(image_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download image from {image_url}")
        
    image_bytes = response.content
    
    # Determine mime type based on URL (Cloudinary usually serves jpg/png/webp)
    mime_type = "image/jpeg"
    if ".png" in image_url.lower():
        mime_type = "image/png"
    elif ".webp" in image_url.lower():
        mime_type = "image/webp"

    # 2. Prepare payload for Gemini
    image_part = {
        "mime_type": mime_type,
        "data": image_bytes
    }
    
    # 3. Call Gemini with Fallbacks
    print(f"Sending image and prompt to Gemini: '{prompt}'")
    
    # Add a system-like instruction to ensure it only returns the caption and no conversational filler
    full_prompt = (
        f"You are an expert social media manager. Write a caption for the attached image based strictly on the following direction:\n\n"
        f"DIRECTION: {prompt}\n\n"
        f"Output ONLY the caption text. Do not include quotes, explanations, or introductory phrases."
    )
    
    models_to_try = [
        'gemini-1.5-flash-latest', 
        'gemini-1.5-flash',
        'gemini-1.0-pro-vision-latest',
        'gemini-pro-vision'
    ]
    
    for model_name in models_to_try:
        try:
            print(f"Trying Gemini model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            result = model.generate_content([full_prompt, image_part])
            caption = result.text.strip()
            return caption
        except Exception as e:
            print(f"Model {model_name} failed: {str(e)}")
            continue
            
    raise Exception("All Gemini models failed. Please check your API key permissions and region.")

if __name__ == "__main__":
    # Local test
    # print(generate_caption("https://example.com/image.jpg", "Write a short hype caption"))
    pass
