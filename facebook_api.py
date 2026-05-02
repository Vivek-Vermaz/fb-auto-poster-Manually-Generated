import os
import time
import requests

def post_to_facebook(image_url, caption, page_id, access_token, retries=2):
    """
    Uploads an image via URL to a Facebook Page along with a caption.
    Includes retry logic.
    """
    if not page_id or not access_token:
        raise ValueError("page_id or access_token not provided")
        
    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    
    data = {
        'message': caption,
        'url': image_url, # Graph API allows passing an external image URL directly
        'access_token': access_token
    }
    
    for attempt in range(retries + 1):
        print(f"Attempting to post to Facebook (Attempt {attempt + 1}/{retries + 1})...")
        try:
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                post_id = result.get('post_id')
                print(f"Successfully posted to Facebook! Post ID: {post_id}")
                post_url = f"https://facebook.com/{post_id}"
                return post_id, post_url
            else:
                print(f"Failed to post to Facebook. Status: {response.status_code}")
                print(response.text)
                if attempt == retries:
                    raise Exception(f"Facebook API Error: {response.text}")
                time.sleep(10) # wait 10 seconds before retry
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            if attempt == retries:
                raise
            time.sleep(10)

def post_comment_to_facebook(post_id, comment_text, access_token, retries=2):
    """
    Posts a comment to an existing Facebook post via the Graph API.
    """
    if not post_id or not comment_text or not access_token:
        print("Missing parameters for posting comment. Skipping.")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
    data = {
        'message': comment_text,
        'access_token': access_token
    }
    
    for attempt in range(retries + 1):
        print(f"Attempting to post First Comment (Attempt {attempt + 1}/{retries + 1})...")
        try:
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                print("Successfully posted First Comment to Facebook!")
                return True
            else:
                print(f"Failed to post comment. Status: {response.status_code}")
                print(response.text)
                if attempt == retries:
                    return False
                time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Network error while commenting: {e}")
            if attempt == retries:
                return False
            time.sleep(5)

if __name__ == "__main__":
    pass
