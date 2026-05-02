import os
import requests

def send_telegram_alert(message):
    """
    Sends a message via Telegram Bot.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram credentials not set. Skipping Telegram alert.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram alert sent successfully.")
            return True
        else:
            print(f"Failed to send Telegram alert: {response.text}")
            return False
    except Exception as e:
        print(f"Exception while sending Telegram alert: {e}")
        return False

if __name__ == "__main__":
    pass
