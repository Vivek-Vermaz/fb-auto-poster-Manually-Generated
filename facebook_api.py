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
                # Generate post URL (Format: https://facebook.com/{page_id}/posts/{post_id_part2})
                # Note: post_id usually contains page_id_post_id
                post_url = f"https://facebook.com/{post_id}"
                return post_url
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

if __name__ == "__main__":
    pass
