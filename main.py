import os
import json
import random
from datetime import datetime
import pytz

from cloudinary_api import get_images_from_folder
from facebook_api import post_to_facebook
from email_alerter import send_email_alert

CONFIG_FILE = "docs/config.json"
STATE_FILE = "docs/state.json"

def load_json(filepath, default):
    if not os.path.exists(filepath):
        return default
    with open(filepath, "r") as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(filepath, data):
    # Ensure dir exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def get_us_time():
    us_east = pytz.timezone('US/Eastern')
    return datetime.now(us_east)

def check_schedule(state, config, current_time):
    """
    Returns True if we should post right now.
    """
    today_str = current_time.strftime("%Y-%m-%d")
    
    # Reset daily count if new day
    if state.get("day_date") != today_str:
        state["day_date"] = today_str
        state["daily_count"] = 0
        state["daily_target_reached"] = False

    frequency = int(config.get("frequency", 6))
    
    if state["daily_count"] >= frequency:
        # We hit our target for today
        if not state.get("daily_target_reached"):
            state["daily_target_reached"] = True
            save_json(STATE_FILE, state)
            send_email_alert(
                "Daily Posting Completed", 
                f"Successfully posted {frequency} times today. Task completed for {today_str}."
            )
        return False
        
    # Sleep mode (1 AM to 6 AM US time)
    if 1 <= current_time.hour < 6:
        print("Nighttime. Sleeping.")
        return False

    last_post_time_str = state.get("last_run")
    if last_post_time_str:
        last_post_time = datetime.fromisoformat(last_post_time_str)
        diff = current_time - last_post_time
        hours_since = diff.total_seconds() / 3600
        if hours_since < 1:
            print(f"Only {hours_since:.2f} hours since last post. Minimum gap is 1h. Skipping.")
            return False
            
    # Random probability logic to spread posts throughout the 19 active hours (6am to 1am)
    # Remaining hours = 24 - current_time.hour (roughly)
    # If we need 6 posts in 19 hours, probability is ~ 6/19. Let's simplify:
    # 40% chance every hour it wakes up
    if random.random() > 0.4:
        print("Random schedule says: Not this hour.")
        return False

    return True

def main():
    print("Running Automation Check...")
    
    config = load_json(CONFIG_FILE, {"frequency": 6, "captions": [], "cloudinary_folder": ""})
    state = load_json(STATE_FILE, {"posted": [], "last_run": None, "day_date": None, "daily_count": 0, "daily_target_reached": False})
    
    current_time = get_us_time()
    
    if not check_schedule(state, config, current_time):
        print("Conditions not met to post at this time.")
        return
        
    print("Proceeding to post...")
    
    folder = config.get("cloudinary_folder")
    if not folder:
        print("No Cloudinary folder configured.")
        return
        
    # Get all images, oldest first
    all_images = get_images_from_folder(folder)
    
    # Filter out already posted
    posted_ids = [p["public_id"] for p in state.get("posted", [])]
    unposted_images = [img for img in all_images if img["public_id"] not in posted_ids]
    
    images_left = len(unposted_images)
    print(f"Found {images_left} unposted images out of {len(all_images)} total.")
    
    if images_left < 7:
        send_email_alert(
            "WARNING: Low Image Inventory", 
            f"Only {images_left} images left in the folder '{folder}'. Please upload more images soon!"
        )
        
    if images_left == 0:
        print("No unposted images left. Exiting.")
        return
        
    image_to_post = unposted_images[0]
    
    # Select Caption
    captions = config.get("captions", [])
    if not captions:
        print("No captions configured.")
        return
        
    # Cycle through captions
    caption_index = len(state.get("posted", [])) % len(captions)
    caption_to_post = captions[caption_index].strip()
    
    try:
        post_url = post_to_facebook(image_to_post["url"], caption_to_post)
        
        # Update state
        post_record = {
            "public_id": image_to_post["public_id"],
            "url": post_url,
            "time": current_time.isoformat(),
            "caption": caption_to_post
        }
        state.setdefault("posted", []).insert(0, post_record) # Insert at beginning for UI
        state["last_run"] = current_time.isoformat()
        state["daily_count"] += 1
        
        save_json(STATE_FILE, state)
        print("Workflow completed and state saved.")
        
    except Exception as e:
        print(f"Error during posting workflow: {e}")
        send_email_alert(
            "CRITICAL: Facebook Post Failed",
            f"The automation script failed to post after retries.<br><br>Error details:<br>{str(e)}"
        )

if __name__ == "__main__":
    main()
