import os
import requests
import base64

def generate_caption(image_url, prompt):
    """
    Downloads the image from Cloudinary, converts to base64, and uses the raw REST API
    to call Gemini to completely bypass the deprecated Python SDK bugs.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
    print("Downloading image for AI analysis...")
    response = requests.get(image_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download image from {image_url}")
        
    image_bytes = response.content
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    mime_type = "image/jpeg"
    if ".png" in image_url.lower():
        mime_type = "image/png"
    elif ".webp" in image_url.lower():
        mime_type = "image/webp"

    print(f"Sending image and prompt to Gemini REST API: '{prompt}'")
    
    full_prompt = (
        f"You are an expert social media manager. Write a caption for the attached image based strictly on the following direction:\n\n"
        f"DIRECTION: {prompt}\n\n"
        f"Output ONLY the caption text. Do not include quotes, explanations, or introductory phrases."
    )
    
    # Using the raw REST API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": full_prompt},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64_image
                    }
                }
            ]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    
    api_response = requests.post(url, json=payload, headers=headers)
    
    if api_response.status_code != 200:
        raise Exception(f"Google API Error {api_response.status_code}: {api_response.text}")
        
    data = api_response.json()
    
    try:
        caption = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return caption
    except (KeyError, IndexError) as e:
        raise Exception(f"Unexpected response format from Google: {data}")

if __name__ == "__main__":
    pass
