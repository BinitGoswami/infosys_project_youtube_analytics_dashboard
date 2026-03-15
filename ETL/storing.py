import pandas as pd
import mysql.connector as ms
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'), 
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4'
}

def connectDB():
    try:
        conn = ms.connect(**DB_CONFIG)
        return conn
    except ms.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# --- NEW HELPER FUNCTION: This does the "Part by Part" work ---
def batch_execute(cursor, sql, data_list, batch_size=1000):
    """
    Takes a huge list (e.g., 50,000 rows) and sends it in small parts
    (e.g., 1,000 rows) so the connection doesn't break.
    """
    total_records = len(data_list)
    
    # Loop from 0 to Total in steps of 1000
    for i in range(0, total_records, batch_size):
        # Slice the list: Get next 1000 rows
        batch = data_list[i : i + batch_size]
        
        try:
            # Send ONLY this small part
            cursor.executemany(sql, batch)
            print(f"   -> Inserted batch {i} to {i + len(batch)} (of {total_records})")
        except ms.Error as e:
            print(f"   Error in batch {i}: {e}")

def storeData():
    transformed_folder = 'transformed_data'
    channels_file = os.path.join(transformed_folder, 'channels_transformed.csv')
    videos_file = os.path.join(transformed_folder, 'videos_transformed.csv')

    if not os.path.exists(channels_file) or not os.path.exists(videos_file):
        print("Error: Transformed data files not found.")
        return

    conn = connectDB()
    if not conn: return
    cursor = conn.cursor()

    try:
        # ==========================================
        # 1. STORE CHANNELS
        # ==========================================
        print("\nProcessing Channels...")
        df_channels = pd.read_csv(channels_file)
        
        # Clean Data
        df_channels = df_channels.replace([float('inf'), float('-inf')], 0)
        df_channels = df_channels.where(pd.notnull(df_channels), None)

        channel_data = []
        channel_sql = """
        INSERT IGNORE INTO channels 
        (channel_id, channel_name, channel_created_at, channel_image, custom_url, subscribers, total_views, total_videos, country, playlist_id, views_per_sub) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for _, row in df_channels.iterrows():
            created_at = row.get('channel_created_at')
            if created_at:
                try: created_at = pd.to_datetime(created_at).strftime('%Y-%m-%d %H:%M:%S')
                except: created_at = None
            
            val = (
                row['channel_id'], row['channel_name'], created_at, 
                row['channel_image'], row['custom_url'], row['subscribers'], 
                row['total_views'], row['total_videos'], row['country'], 
                row['playlist_id'], row['views_per_sub']
            )
            channel_data.append(val)

        # USE BATCH EXECUTE (Part by Part)
        if channel_data:
            batch_execute(cursor, channel_sql, channel_data, batch_size=1000)
            conn.commit()
            print("Channels Saved Successfully.")

        # ==========================================
        # 2. STORE VIDEOS
        # ==========================================
        print("\nProcessing Videos...")
        df_videos = pd.read_csv(videos_file)
        df_videos = df_videos.replace([float('inf'), float('-inf')], 0)
        df_videos = df_videos.where(pd.notnull(df_videos), None)

        video_data = []
        video_sql = """
        INSERT IGNORE INTO videos 
        (video_id, channel_id, channel_title, title, published_at, view_count, like_count, comment_count, duration_seconds, tags, engagement_rate, duration_category) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for _, row in df_videos.iterrows():
            pub_date = row['published_at']
            if pub_date:
                try: pub_date = pd.to_datetime(pub_date).strftime('%Y-%m-%d %H:%M:%S')
                except: pub_date = None

            val = (
                row['video_id'], row['channel_id'], row['channel_title'], 
                row['title'], pub_date, row['view_count'], row['like_count'], 
                row['comment_count'], row['duration_seconds'], row['tags'], 
                row['engagement_rate'], row['duration_category']
            )
            video_data.append(val)

        # USE BATCH EXECUTE (Part by Part)
        if video_data:
            # batch_size=1000 means it takes 1000 rows at a time
            batch_execute(cursor, video_sql, video_data, batch_size=1000)
            conn.commit()
            print("Videos Saved Successfully.")

    except ms.Error as err:
        print(f"Database Error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("\nDatabase connection closed.")

storeData()