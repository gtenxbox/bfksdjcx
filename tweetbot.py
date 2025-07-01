import os
import json
import logging
from datetime import datetime
from pytz import timezone, utc
from PIL import Image
import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
BANANA_IMAGE = 'banana.png'
PROGRESS_STATE = 'progress_state.json'
ACTIVITY_LOG = 'activity.log'

# Set up logging
logging.basicConfig(filename=ACTIVITY_LOG, level=logging.INFO, format='%(asctime)s %(message)s')

PST = timezone('US/Pacific')

def get_year_progress():
    now = datetime.utcnow()
    year_start = datetime(now.year, 1, 1)
    year_end = datetime(now.year + 1, 1, 1)
    days_passed = (now - year_start).total_seconds()
    year_length = (year_end - year_start).total_seconds()
    percent = (days_passed / year_length) * 100
    return int(percent), percent

def load_last_percent():
    if not os.path.exists(PROGRESS_STATE):
        return None
    try:
        with open(PROGRESS_STATE, 'r') as f:
            data = json.load(f)
            return data.get('last_percent')
    except json.JSONDecodeError:
        return None

def save_last_percent(percent):
    with open(PROGRESS_STATE, 'w') as f:
        json.dump({'last_percent': percent}, f)

def crop_banana(percent):
    img = Image.open(BANANA_IMAGE)
    width, height = img.size
    total_pixels = width * height
    reveal_pixels = int((percent / 100) * total_pixels)
    max_square = min(width, height)
    square_pixels = max_square * max_square
    if reveal_pixels <= square_pixels:
        side = int(reveal_pixels ** 0.5)
        box = (0, 0, side, side)
    else:
        extra_pixels = reveal_pixels - square_pixels
        extra_width = extra_pixels // max_square
        box = (0, 0, max_square + extra_width, max_square)
        box = (box[0], box[1], min(box[2], width), min(box[3], height))
    cropped = img.crop(box)
    cropped_path = f'banana_cropped_{percent}.png'
    cropped.save(cropped_path)
    return cropped_path

def tweet_progress(percent, percent_float, image_path, pst_time_str):
    caption = f"{datetime.utcnow().year} is {percent}% approved on the banana scale (PST: {pst_time_str})"
    # v1.1: Authenticate for media upload
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    # Upload media using v1.1 endpoint
    media = api.media_upload(image_path)
    media_id = media.media_id_string
    # v2: Authenticate for tweet creation
    client = tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    # Post tweet with media using v2 endpoint
    response = client.create_tweet(text=caption, media_ids=[media_id])
    log_msg = f"[PST: {pst_time_str}] Tweeted: {caption} with image {image_path} | Tweet response: {response}"
    logging.info(log_msg)
    print(log_msg)
    return log_msg

def main():
    now_utc = datetime.now(utc)
    now_pst = now_utc.astimezone(PST)
    pst_time_str = now_pst.strftime('%Y-%m-%d %H:%M:%S %Z')
    percent, percent_float = get_year_progress()
    last_percent = load_last_percent()
    if last_percent is not None and percent <= last_percent:
        log_msg = f"[PST: {pst_time_str}] No new percent to tweet. Last: {last_percent}, Current: {percent}"
        logging.info(log_msg)
        print(log_msg)
        return
    image_path = crop_banana(percent)
    tweet_log = tweet_progress(percent, percent_float, image_path, pst_time_str)
    save_last_percent(percent)

if __name__ == '__main__':
    main() 