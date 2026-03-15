import pandas as pd
import json, os, isodate 

def clean_data():
    raw_folder = 'raw_data'
    cleaned_folder = 'cleaned_data'
    
    if not os.path.exists(cleaned_folder):
        os.makedirs(cleaned_folder)

    # load existing data
    channels_path = os.path.join(cleaned_folder, 'channels_cleaned.csv')
    videos_path = os.path.join(cleaned_folder, 'videos_cleaned.csv')

    existing_channel_ids = set()
    existing_video_ids = set()

    if os.path.exists(channels_path):
        try:
            df_existing_c = pd.read_csv(channels_path)
            existing_channel_ids = set(df_existing_c['channel_id'].astype(str))
            print(f"Found {len(existing_channel_ids)} existing channels.")
        except:
            pass

    if os.path.exists(videos_path):
        try:
            df_existing_v = pd.read_csv(videos_path)
            existing_video_ids = set(df_existing_v['video_id'].astype(str))
            print(f"Found {len(existing_video_ids)} existing videos.")
        except:
            pass

    new_channel_rows = []
    new_video_rows = []

    for filename in os.listdir(raw_folder):
        file_path = os.path.join(raw_folder, filename)
        
        if not filename.endswith('.json'):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Skipping bad file {filename}: {e}")
            continue

        # --- PROCESS CHANNELS ---
        if filename.startswith("raw_data_"):
            try:
                item = data[0] 
                if item['id'] in existing_channel_ids:
                    continue

                snippet = item['snippet']
                stats = item['statistics']
                thumbnails = snippet.get('thumbnails', {})

                # 🧠 SMART IMAGE LOGIC (High -> Medium -> Default -> Fallback)
                image_url = thumbnails.get('high', {}).get('url') or \
                            thumbnails.get('medium', {}).get('url') or \
                            thumbnails.get('default', {}).get('url') or \
                            "https://www.gstatic.com/youtube/img/branding/favicon/favicon_144x144.png"

                channel_row = {
                    'channel_id': item['id'],
                    'channel_name': snippet['title'],
                    
                    # --- NEW FIELDS ---
                    'channel_created_at': snippet.get('publishedAt'),
                    'channel_image': image_url,
                    'custom_url': snippet.get('customUrl', 'N/A'),
                    # ------------------
                    
                    'subscribers': int(stats.get('subscriberCount', 0)),
                    'total_views': int(stats.get('viewCount', 0)),
                    'total_videos': int(stats.get('videoCount', 0)),
                    'country': snippet.get('country', 'Unknown'), 
                    'playlist_id': item['contentDetails']['relatedPlaylists']['uploads']
                }
                new_channel_rows.append(channel_row)
                existing_channel_ids.add(item['id']) 

            except Exception as e:
                print(f"Error in {filename}: {e}")

        # --- PROCESS VIDEOS ---
        elif filename.startswith("raw_videos_"):
            for item in data:
                try:
                    if item['id'] in existing_video_ids:
                        continue

                    snippet = item['snippet']
                    stats = item['statistics']
                    content = item['contentDetails']
                    
                    video_row = {
                        'video_id': item['id'],
                        'channel_id': snippet.get('channelId', 'Unknown'),
                        'title': snippet['title'],
                        'published_at': snippet['publishedAt'],
                        'view_count': int(stats.get('viewCount', 0)),
                        'like_count': int(stats.get('likeCount', 0)),
                        'comment_count': int(stats.get('commentCount', 0)),
                        'duration_seconds': isodate.parse_duration(content['duration']).total_seconds(),
                        'channel_title': snippet['channelTitle'],
                        'tags': ",".join(snippet.get('tags', [])) 
                    }
                    new_video_rows.append(video_row)
                    existing_video_ids.add(item['id'])

                except Exception as e:
                    pass 

    # Save Results
    if new_channel_rows:
        df_new_channels = pd.DataFrame(new_channel_rows)
        header = not os.path.exists(channels_path)
        df_new_channels.to_csv(channels_path, mode='a', header=header, index=False)
        print(f"Added {len(df_new_channels)} NEW channels.")
    else:
        print(" -> No new channels found.")

    if new_video_rows:
        df_new_videos = pd.DataFrame(new_video_rows)
        header = not os.path.exists(videos_path)
        df_new_videos.to_csv(videos_path, mode='a', header=header, index=False)
        print(f"Added {len(df_new_videos)} new videos.")
    else:
        print(" -> No new videos found.")

clean_data()