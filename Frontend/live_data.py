import os
import googleapiclient.discovery as gac
import mysql.connector as ms
import pandas as pd
import isodate
from googleapiclient.errors import HttpError 
from dotenv import load_dotenv, find_dotenv

# Load env vars from parent folder
load_dotenv(find_dotenv())

# --- CONFIG ---
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'), 
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4',
    'autocommit': True
}

def get_db_connection():
    try:
        return ms.connect(**DB_CONFIG)
    except ms.Error as e:
        print(f"DB Connection Error: {e}")
        return None

def get_youtube_client():
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("CRITICAL ERROR: 'API_KEY' variable not found in .env file.")
        return None
    try:
        return gac.build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        print(f"Error building YouTube Client: {e}")
        return None

def sync_channel_data(channel_id):       
    youtube = get_youtube_client()
    if not youtube: return False

    # 1. FETCH CHANNEL DETAILS
    uploads_playlist = None
    try:
        # Request everything including brandingSettings
        req = youtube.channels().list(
            part="snippet,statistics,contentDetails,brandingSettings", 
            id=channel_id
        )
        res = req.execute()
        
        if not res.get('items'):
            print(f"Channel ID {channel_id} not found.")
            return False
        
        item = res['items'][0]
        stats = item['statistics']
        snippet = item['snippet']
        branding = item.get('brandingSettings', {}).get('channel', {})
        
        # ---------------------------------------------------------
        # 1. IMAGE (Backup Logic)
        # ---------------------------------------------------------
        thumbnails = snippet.get('thumbnails', {})
        channel_image = thumbnails.get('high', {}).get('url') or \
                            thumbnails.get('medium', {}).get('url') or \
                            thumbnails.get('default', {}).get('url') or \
                            "https://www.gstatic.com/youtube/img/branding/favicon/favicon_144x144.png"
        
        # ---------------------------------------------------------
        # 2. COUNTRY (Snippet -> Branding -> Unknown)
        # ---------------------------------------------------------
        country_code = snippet.get('country')
        if not country_code:
            country_code = branding.get('country')
        
        # If still missing, save 'Unknown'
        country_name = country_code if country_code else "Unknown"
        
        # ---------------------------------------------------------
        # 3. DATE (THE CRITICAL FIX FOR MYSQL) 
        # ---------------------------------------------------------
        raw_date = snippet.get('publishedAt')
        if raw_date:
            try:
                channel_created_at = pd.to_datetime(raw_date).strftime('%Y-%m-%d %H:%M:%S')
            except:
                channel_created_at = "2020-01-01 00:00:00"
        else:
            channel_created_at = "2020-01-01 00:00:00"

        # 4. REST OF DATA
        custom_url = snippet.get('customUrl') or branding.get('customUrl') or 'N/A'
        uploads_playlist = item['contentDetails']['relatedPlaylists']['uploads']
        subscribers = int(stats.get('subscriberCount', 0))
        total_views = int(stats.get('viewCount', 0))
        total_videos = int(stats.get('videoCount', 0))
        views_per_sub = total_views / subscribers if subscribers > 0 else 0
        # 5. DATABASE UPDATE
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            
            sql_channel = """
            INSERT INTO channels 
            (channel_id, channel_name, channel_created_at, channel_image, custom_url, subscribers, total_views, total_videos, country, playlist_id, views_per_sub)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            subscribers=VALUES(subscribers), 
            total_views=VALUES(total_views), 
            total_videos=VALUES(total_videos), 
            views_per_sub=VALUES(views_per_sub),
            channel_image=VALUES(channel_image),
            channel_created_at=VALUES(channel_created_at),  /* This updates the date */
            custom_url=VALUES(custom_url),
            country=VALUES(country)                         /* This updates the country */
            """
            
            cursor.execute(sql_channel, (
                channel_id, snippet['title'], channel_created_at, channel_image, custom_url,
                subscribers, total_views, total_videos, country_name, uploads_playlist, views_per_sub
            ))
            conn.commit()
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error fetching channel: {e}")
        return False

    # 2. FETCH VIDEOS (With 404 Protection)
    all_videos = []
    next_page_token = None
    
    try:
        while True:
            try:
                # Get Video IDs
                pl_req = youtube.playlistItems().list(
                    part='contentDetails', playlistId=uploads_playlist, 
                    maxResults=50, pageToken=next_page_token
                )
                pl_res = pl_req.execute()
            
            except HttpError as e:
                if e.resp.status == 404:
                    return True # EXIT SUCCESSFULLY
                else:
                    raise e # Re-raise other errors
            
            vid_ids = [i['contentDetails']['videoId'] for i in pl_res.get('items', [])]
            
            if vid_ids:
                # Get Video Stats
                vid_req = youtube.videos().list(
                    part='snippet,statistics,contentDetails', id=','.join(vid_ids)
                )
                vid_res = vid_req.execute()
                
                for v in vid_res.get('items', []):
                    stats = v['statistics']
                    content = v['contentDetails']
                    snippet = v['snippet']
                    
                    view_count = int(stats.get('viewCount', 0))
                    like_count = int(stats.get('likeCount', 0))
                    comment_count = int(stats.get('commentCount', 0))
                    try: 
                        duration_sec = isodate.parse_duration(content['duration']).total_seconds()
                    except: 
                        duration_sec = 0
                    
                    eng_rate = ((like_count + comment_count) / view_count * 100) if view_count > 0 else 0
                    
                    if duration_sec < 60: 
                        dur_cat = 'Short'
                    elif duration_sec < 300: 
                        dur_cat = 'Medium'
                    else: 
                        dur_cat = 'Long'
                    
                    # FIXED: Define pub_date from the video snippet
                    pub_date = snippet.get('publishedAt')
                    if pub_date:
                        try: 
                            pub_date = pd.to_datetime(pub_date).strftime('%Y-%m-%d %H:%M:%S')
                        except: 
                            pub_date = None
                    else:
                        pub_date = None

                    all_videos.append((
                        v['id'], channel_id, snippet['channelTitle'], snippet['title'],
                        pub_date, view_count, like_count, comment_count,
                        duration_sec, ",".join(snippet.get('tags', [])),
                        eng_rate, dur_cat
                    ))
            
            next_page_token = pl_res.get('nextPageToken')
            if not next_page_token: break

        # 3. LOAD VIDEOS TO DB
        if all_videos:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                sql_video = """
                INSERT INTO videos 
                (video_id, channel_id, channel_title, title, published_at, view_count, 
                like_count, comment_count, duration_seconds, tags, engagement_rate, duration_category) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                view_count=VALUES(view_count), like_count=VALUES(like_count), 
                engagement_rate=VALUES(engagement_rate)
                """
                cursor.executemany(sql_video, all_videos)
                conn.commit()
                cursor.close()
                conn.close()
                print(f"✅ Synced {len(all_videos)} videos.")

    except Exception as e:
        print(f"Error fetching videos: {e}")
        return False

    return True
# Add this to etl/live_data.py

def update_channel_image_only(channel_id):
    youtube = get_youtube_client()
    if not youtube: 
        return False
    try:
        # Request ONLY the snippet (where the image lives)
        req = youtube.channels().list(part="snippet", id=channel_id)
        res = req.execute()
        
        if not res.get('items'):
            return False
            
        snippet = res['items'][0]['snippet']
        
        # Extract Image
        channel_image = snippet['thumbnails'].get('high', {}).get('url', '')
        if not channel_image:
             channel_image = snippet['thumbnails'].get('medium', {}).get('url', '')

        # Update ONLY the image column in DB
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            sql = "UPDATE channels SET channel_image = %s WHERE channel_id = %s"
            cursor.execute(sql, (channel_image, channel_id))
            conn.commit()
            cursor.close()
            conn.close()
            print("Image updated!")
            return True

    except Exception as e:
        print(f"Error fetching image: {e}")
        return False