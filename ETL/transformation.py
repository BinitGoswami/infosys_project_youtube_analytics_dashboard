import pandas as pd
import os

def transformData():
    # 1. SETUP PATHS
    cleaned_folder = 'cleaned_data'
    transformed_folder = 'transformed_data'
    
    videos_clean_path = os.path.join(cleaned_folder, 'videos_cleaned.csv')
    channels_clean_path = os.path.join(cleaned_folder, 'channels_cleaned.csv')
    
    videos_trans_path = os.path.join(transformed_folder, 'videos_transformed.csv')
    channels_trans_path = os.path.join(transformed_folder, 'channels_transformed.csv')

    # Ensure output folder exists
    if not os.path.exists(transformed_folder):
        os.makedirs(transformed_folder)

    # 2. CHECK SOURCES
    if not os.path.exists(videos_clean_path) or not os.path.exists(channels_clean_path):
        print("Error: Cleaned data not found. Please run 'cleaning.py' first.")
        return

    print("Reading cleaned data...")
    try:
        df_videos_clean = pd.read_csv(videos_clean_path)
        df_channels_clean = pd.read_csv(channels_clean_path)
    except pd.errors.EmptyDataError:
        print("Error: Cleaned files are empty.")
        return

    # 3. LOAD EXISTING TRANSFORMED DATA (To avoid duplicates)
    existing_video_ids = []
    existing_channel_ids = []
    df_videos_existing = pd.DataFrame()
    df_channels_existing = pd.DataFrame()
    
    # Load Existing Videos
    if os.path.exists(videos_trans_path):
        try:
            df_videos_existing = pd.read_csv(videos_trans_path)
            if 'video_id' in df_videos_existing.columns:
                existing_video_ids = df_videos_existing['video_id'].astype(str).tolist()
            print(f" -> Found {len(df_videos_existing)} videos already transformed.")
        except:
            pass # File might be corrupted or empty, start fresh

    # Load Existing Channels
    if os.path.exists(channels_trans_path):
        try:
            df_channels_existing = pd.read_csv(channels_trans_path)
            if 'channel_id' in df_channels_existing.columns:
                existing_channel_ids = df_channels_existing['channel_id'].astype(str).tolist()
            print(f" -> Found {len(df_channels_existing)} channels already transformed.")
        except:
            pass

    # 4. FILTER FOR NEW DATA ONLY
    # Ensure IDs are strings for comparison
    df_videos_clean['video_id'] = df_videos_clean['video_id'].astype(str)
    df_channels_clean['channel_id'] = df_channels_clean['channel_id'].astype(str)

    if existing_video_ids:
        df_videos_new = df_videos_clean[~df_videos_clean['video_id'].isin(existing_video_ids)].copy()
    else:
        df_videos_new = df_videos_clean.copy()

    if existing_channel_ids:
        df_channels_new = df_channels_clean[~df_channels_clean['channel_id'].isin(existing_channel_ids)].copy()
    else:
        df_channels_new = df_channels_clean.copy()

    print(f"\nProcessing: Found {len(df_channels_new)} New channels and {len(df_videos_new)} New videos.")

    if len(df_videos_new) == 0 and len(df_channels_new) == 0:
        print("Everything is up to date. No changes made.")
        return

    # 5. APPLY TRANSFORMATIONS
    
    # A. Transform Videos
    if len(df_videos_new) > 0:
        # Engagement Rate
        df_videos_new['engagement_rate'] = ((df_videos_new['like_count'] + df_videos_new['comment_count']) / df_videos_new['view_count']).fillna(0) * 100
        
        # Duration Category Helper
        def categorize_duration(seconds):
            if seconds < 60: return 'Short'
            elif seconds < 300: return 'Medium'
            else: return 'Long'
        
        if 'duration_seconds' in df_videos_new.columns:
            df_videos_new['duration_category'] = df_videos_new['duration_seconds'].apply(categorize_duration)
        
        # Add Date Metadata
        df_videos_new['published_at'] = pd.to_datetime(df_videos_new['published_at'])
        df_videos_new['year'] = df_videos_new['published_at'].dt.year
        df_videos_new['month'] = df_videos_new['published_at'].dt.month_name()

    # B. Transform Channels
    if len(df_channels_new) > 0:
        df_channels_new['views_per_sub'] = (df_channels_new['total_views'] / df_channels_new['subscribers']).fillna(0)

    # 6. SAVE (APPEND MODE IS SAFE HERE BECAUSE WE ALREADY FILTERED)
    
    # Append Videos
    if not df_videos_new.empty:
        header = not os.path.exists(videos_trans_path)
        df_videos_new.to_csv(videos_trans_path, mode='a', header=header, index=False)
        print(f" -> Appended {len(df_videos_new)} videos to {videos_trans_path}")

    # Append Channels
    if not df_channels_new.empty:
        header = not os.path.exists(channels_trans_path)
        df_channels_new.to_csv(channels_trans_path, mode='a', header=header, index=False)
        print(f" -> Appended {len(df_channels_new)} channels to {channels_trans_path}")

    print("\nTransformation Update Complete!")

transformData()