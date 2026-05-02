import os
import requests
import base64
import json

def generate_caption(image_url, prompt):
    """
    Downloads the image from Cloudinary, converts to base64, and uses the raw REST API
    to call Gemini to completely bypass the deprecated Python SDK bugs.
    Returns a dictionary: {"caption": "...", "first_comment": "..."}
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
        f"You are an expert social media manager. I need you to write a caption AND a first comment for the attached image, based strictly on the following direction:\n\n"
        f"DIRECTION: {prompt}\n\n"
        f"CRITICAL INSTRUCTIONS:\n"
        f"1. Generate completely unique, highly relevant hashtags for the caption to avoid spam filters.\n"
        f"2. The 'first_comment' should be an engaging question or poll related to the image to spark conversation.\n"
        f"3. You must output RAW JSON ONLY. Do not include markdown formatting, backticks, or conversational text. Use exactly these two keys: \"caption\" and \"first_comment\".\n"
        f"Example format:\n"
        f"{{\n"
        f"  \"caption\": \"Your amazing caption here with #unique #hashtags\",\n"
        f"  \"first_comment\": \"Your engaging question here?\"\n"
        f"}}"
    )
    
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
    
    models_to_try = [
        'gemini-3.0-flash',
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash'
    ]
    
    headers = {"Content-Type": "application/json"}
    last_error = ""
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        print(f"Trying Gemini model via REST: {model_name}...")
        
        api_response = requests.post(url, json=payload, headers=headers)
        
        if api_response.status_code == 200:
            data = api_response.json()
            try:
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean up potential markdown blocks if the AI disobeyed
                if raw_text.startswith("```json"):
                    raw_text = raw_text.replace("```json", "", 1)
                if raw_text.startswith("```"):
                    raw_text = raw_text.replace("```", "", 1)
                if raw_text.endswith("```"):
                    raw_text = raw_text[::-1].replace("```", "", 1)[::-1]
                
                parsed_json = json.loads(raw_text.strip())
                return parsed_json
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                last_error = f"Unexpected response format from Google: {e}\nRaw Text: {data}"
                print(last_error)
                continue
        else:
            last_error = f"Model {model_name} failed with {api_response.status_code}: {api_response.text}"
            print(last_error)
            continue
            
    raise Exception(f"All Gemini models failed. Last error: {last_error}")

if __name__ == "__main__":
    pass
