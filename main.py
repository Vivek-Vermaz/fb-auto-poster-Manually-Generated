import os
import json
import random
import time
from datetime import datetime
import pytz

from cloudinary_api import get_images_from_folder, delete_image
from facebook_api import post_to_facebook, post_comment_to_facebook
from email_alerter import send_email_alert
from gemini_api import generate_caption

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
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def get_us_time():
    us_east = pytz.timezone('US/Eastern')
    return datetime.now(us_east)

def check_schedule(page_state, frequency, current_time, page_name):
    """
    Returns True if we should post right now for this specific page.
    """
    today_str = current_time.strftime("%Y-%m-%d")
    
    # Reset daily count if new day
    if page_state.get("day_date") != today_str:
        page_state["day_date"] = today_str
        page_state["daily_count"] = 0
        page_state["daily_target_reached"] = False

    frequency = int(frequency)
    
    if page_state["daily_count"] >= frequency:
        # We hit our target for today
        if not page_state.get("daily_target_reached"):
            page_state["daily_target_reached"] = True
            send_email_alert(
                f"[{page_name}] Daily Posting Completed", 
                f"Successfully posted {frequency} times today. Task completed for {today_str}."
            )
    # Peak Hours Scheduling (9 AM - 12 PM, 5 PM - 9 PM US Eastern)
    hour = current_time.hour
    is_morning_peak = (9 <= hour < 12)
    is_evening_peak = (17 <= hour < 21)
    
    if not (is_morning_peak or is_evening_peak):
        print(f"[{page_name}] Not during peak hours ({hour}:00 EST). Sleeping.")
        return False

    last_post_time_str = page_state.get("last_run")
    if last_post_time_str:
        last_post_time = datetime.fromisoformat(last_post_time_str)
        diff = current_time - last_post_time
        hours_since = diff.total_seconds() / 3600
        if hours_since < 1:
            print(f"[{page_name}] Only {hours_since:.2f} hours since last post. Skipping.")
            return False
            
    # Random probability logic
    if random.random() > 0.4:
        print(f"[{page_name}] Random schedule says: Not this hour.")
        return False

    return True

def main():
    print("Running Multi-Page Automation Check...")
    
    config = load_json(CONFIG_FILE, {"pages": []})
    state = load_json(STATE_FILE, {"pages": {}})
    
    # Load Facebook Credentials Secret
    fb_creds_json = os.environ.get("FB_PAGES_CREDENTIALS")
    if not fb_creds_json:
        print("FB_PAGES_CREDENTIALS environment variable not set. Exiting.")
        return
        
    try:
        fb_creds = json.loads(fb_creds_json)
    except json.JSONDecodeError:
        print("Failed to parse FB_PAGES_CREDENTIALS JSON. Check the secret formatting.")
        return

    current_time = get_us_time()
    state_changed = False
    config_changed = False
    
    pages = config.get("pages", [])
    
    # --- AUTO-PROVISIONING ---
    existing_page_names = [p.get("page_name") for p in pages]
    for secret_page_name in fb_creds.keys():
        if secret_page_name not in existing_page_names:
            print(f"Auto-provisioning new page from secrets: '{secret_page_name}'")
            pages.append({
                "page_name": secret_page_name,
                "cloudinary_folder": "",
                "frequency": 6,
                "ai_prompt": "",
                "captions": []
            })
            config_changed = True
            existing_page_names.append(secret_page_name)
    
    config["pages"] = pages
    
    if not pages:
        print("No pages configured in docs/config.json and no secrets found.")
        return
        
    for page_config in pages:
        page_name = page_config.get("page_name")
        print(f"--- Evaluating Page: {page_name} ---")
        
        if not page_name:
            continue
            
        if page_name not in fb_creds:
            print(f"[{page_name}] Credentials not found in FB_PAGES_CREDENTIALS secret. Skipping.")
            continue
            
        page_creds = fb_creds[page_name]
        fb_page_id = page_creds.get("id")
        fb_page_token = page_creds.get("token")
        
        if not fb_page_id or not fb_page_token:
            print(f"[{page_name}] Incomplete credentials (missing id or token). Skipping.")
            continue

        # Initialize state for this page if it doesn't exist
        if page_name not in state["pages"]:
            state["pages"][page_name] = {
                "posted": [], "last_run": None, "day_date": None, 
                "daily_count": 0, "daily_target_reached": False
            }
            
        page_state = state["pages"][page_name]
        frequency = page_config.get("frequency", 6)

        # Handle Refresh Only command
        is_refresh_only = os.environ.get("REFRESH_ONLY") == "true"
        
        # Get latest image count from Cloudinary
        folder = page_config.get("cloudinary_folder")
        if folder:
            all_images = get_images_from_folder(folder)
            # Since we now delete images from Cloudinary after posting, 
            # everything in the folder is considered 'unposted'.
            unposted_images = all_images
            
            images_left = len(unposted_images)
            if page_state.get("images_left") != images_left:
                page_state["images_left"] = images_left
                state_changed = True
            
            print(f"[{page_name}] Inventory Check: {images_left} images remaining.")

        if is_refresh_only:
            continue # Move to next page to refresh its count too

        # Check if this is a forced test post
        test_page_target = os.environ.get("TEST_PAGE_NAME")
        is_test_run = (test_page_target == page_name)

        if not is_test_run:
            if not check_schedule(page_state, frequency, current_time, page_name):
                continue
        else:
            print(f"[{page_name}] 🚀 FORCE TEST POST COMMAND RECEIVED! Bypassing schedule.")
            
        print(f"[{page_name}] Conditions met. Proceeding to post...")
        
        if not folder:
            print(f"[{page_name}] No Cloudinary folder configured.")
            continue
            
        if images_left < 7:
            send_email_alert(
                f"[{page_name}] WARNING: Low Image Inventory", 
                f"Only {images_left} images left in the folder '{folder}'. Please upload more!"
            )
            
        if images_left == 0:
            print(f"[{page_name}] No unposted images left. Skipping.")
            continue
            
        image_to_post = unposted_images[0]
        
        image_to_post = unposted_images[0]
        
        caption_to_post = None
        first_comment_to_post = None
        used_bulk_caption_index = -1
        
        ai_prompt = page_config.get("ai_prompt", "").strip()
        
        if ai_prompt:
            print(f"[{page_name}] AI Prompt found. Generating dynamic caption via Gemini...")
            try:
                gemini_data = generate_caption(image_to_post["url"], ai_prompt)
                caption_to_post = gemini_data.get("caption")
                first_comment_to_post = gemini_data.get("first_comment")
                print(f"[{page_name}] Gemini AI Caption & Comment generated successfully.")
            except Exception as ai_e:
                print(f"[{page_name}] WARNING: Gemini AI generation failed: {ai_e}")
                send_email_alert(
                    f"[{page_name}] Gemini AI Error", 
                    f"The robot tried to generate an AI caption but Google's API blocked it.<br><br><b>Exact Error:</b><br>{str(ai_e)}"
                )
                caption_to_post = None # Force fallback
                first_comment_to_post = None
                
        if not caption_to_post:
            captions = page_config.get("captions", [])
            if not captions or len(captions) == 0:
                print(f"[{page_name}] No Bulk Captions configured. Using random emojis fallback.")
                num_emojis = random.randint(4, 5)
                fallback_emojis = ["🔥", "😎", "💯", "🚀", "✨", "😍", "🙌", "💥", "💪", "🌟", "🚗", "🏆", "👌"]
                caption_to_post = "".join(random.choices(fallback_emojis, k=num_emojis))
            else:
                used_bulk_caption_index = len(page_state.get("posted", [])) % len(captions)
                caption_to_post = captions[used_bulk_caption_index].strip()
        
        try:
            post_id, post_url = post_to_facebook(
                image_to_post["url"], 
                caption_to_post, 
                fb_page_id, 
                fb_page_token
            )
            
            # Post First Comment if generated
            if first_comment_to_post and post_id:
                print(f"[{page_name}] Posting First Comment to boost engagement...")
                post_comment_to_facebook(post_id, first_comment_to_post, fb_page_token)
            
            # Post-processing: Destructive Deletions as requested
            print(f"[{page_name}] Deleting posted image from Cloudinary...")
            delete_image(image_to_post["public_id"])
            
            if used_bulk_caption_index >= 0:
                print(f"[{page_name}] Deleting used Bulk Caption from config...")
                page_config["captions"].pop(used_bulk_caption_index)
                config_changed = True
            
            # Update state
            post_record = {
                "public_id": image_to_post["public_id"],
                "url": post_url,
                "time": current_time.isoformat(),
                "caption": caption_to_post
            }
            page_state.setdefault("posted", []).insert(0, post_record)
            page_state["last_run"] = current_time.isoformat()
            page_state["daily_count"] += 1
            state_changed = True
            
            print(f"[{page_name}] Workflow completed successfully.")
            
            # --- ANTI-SPAM PACING ---
            if not is_test_run and not is_refresh_only:
                sleep_time = random.randint(30, 90)
                print(f"PACING: Sleeping for {sleep_time} seconds before checking next page to avoid Facebook spam flags...")
                time.sleep(sleep_time)
                
        except Exception as e:
            print(f"[{page_name}] Error during posting workflow: {e}")
            send_email_alert(
                f"[{page_name}] CRITICAL: Facebook Post Failed",
                f"The automation script failed to post after retries.<br><br>Error:<br>{str(e)}"
            )

    if state_changed:
        save_json(STATE_FILE, state)
        print("Overall state saved.")
        
    if config_changed:
        save_json(CONFIG_FILE, config)
        print("Config updated (captions deleted) and saved.")

if __name__ == "__main__":
    main()
