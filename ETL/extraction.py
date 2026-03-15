import googleapiclient.discovery as gac
import json, os, re
from dotenv import load_dotenv 

# get youtube api key
load_dotenv()
API_KEY = os.getenv("API_KEY")
youtube = gac.build("youtube", "v3", developerKey=API_KEY)

def getUserKeywords():
    user_input = input("Enter topics (separated by comma): ")
    
    # Clean up the input (remove spaces, split by comma)
    keywords = [k.strip() for k in user_input.split(',') if k.strip()]
    
    if not keywords:
        print("No keywords entered. Exiting...")
        exit()
        
    print(f"Searching for: {keywords}")
    return keywords
def searchChannelsByKeywords(keywords):
    found_channel_ids = set() 
    
    for keyword in keywords:
        print(f"Searching for Official Channel: '{keyword}'...")
        try:
            # 1. Get Top 5 Candidates
            request = youtube.search().list(
                part="snippet",
                q=keyword,
                type="channel",
                maxResults=5, 
                order="relevance"
            )
            response = request.execute()
            
            if not response.get('items'):
                print(f" -> No channels found for {keyword}")
                continue

            # 2. Get Statistics for these 5 to find the real one
            candidate_ids = [item['snippet']['channelId'] for item in response['items']]
            
            stats_request = youtube.channels().list(
                part="statistics,snippet",
                id=','.join(candidate_ids)
            )
            stats_response = stats_request.execute()
            
            # 3. Filter: Pick the one with Highest Subscribers
            best_channel = None
            max_subs = -1
            
            for item in stats_response.get('items', []):
                subs = int(item['statistics'].get('subscriberCount', 0))
                
                if subs > max_subs:
                    max_subs = subs
                    best_channel = item
            
            # 4. Save ONLY the winner
            if best_channel:
                title = best_channel['snippet']['title']
                c_id = best_channel['id']
                print(f"   -> Selected: {title} ({max_subs:,} Subs)")
                found_channel_ids.add(c_id)

        except Exception as e:
            print(f"Error searching for {keyword}: {e}")
            
    unique_ids = list(found_channel_ids)
    print(f"Total Unique Channels Found: {len(unique_ids)}")
    return unique_ids

def getChannelDetails(ch_id):
    request = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=ch_id
    )
    response = request.execute()
    
    if not response['items']:
        return None
    return response['items'][0]

def getAllVideos(uploads_playlist_id):
    all_videos = []
    next_page_token = None
    
    while True:
        # Get list of Video IDs
        res = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        
        video_ids = []
        for item in res['items']:
            video_ids.append(item['contentDetails']['videoId'])
        
        # Get actual Stats 
        if video_ids:
            stats_res = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            for video in stats_res['items']:
                all_videos.append(video)
        
        # Check if there are more pages
        next_page_token = res.get('nextPageToken')
        if not next_page_token:
            break 
            
    return all_videos

def main():
    # Create folder
    if not os.path.exists('raw_data'):
        os.makedirs('raw_data')

    # Ask User for Topics
    keywords = getUserKeywords()

    # Find Channels Automatically
    channel_ids = searchChannelsByKeywords(keywords)

    # Generating Each channels and their videos details
    for ch_id in channel_ids:
        print(f"\nProcessing: {ch_id}")
        
        try:
            # get channel data
            channel_data = getChannelDetails(ch_id)
            if not channel_data:
                print(f"Channel not found: {ch_id}")
                continue
            
            # generate filenames
            channel_name = channel_data['snippet']['title']
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', channel_name)
            channel_file = f"raw_data/raw_data_{safe_name}.json"
            video_file = f"raw_data/raw_videos_{safe_name}.json"

            # Check if channel name exist or not
            if os.path.exists(channel_file) and os.path.exists(video_file):
                print(f"Skipping existing: {channel_name}")
                continue

            print(f"Channel name: {channel_name}")

            # save channel data
            with open(channel_file, "w", encoding='utf-8') as f:
                json.dump([channel_data], f, indent=4)
            
            # get video data
            uploads_id = channel_data['contentDetails']['relatedPlaylists']['uploads']
            video_data = getAllVideos(uploads_id)
            
            # save video data
            with open(video_file, "w", encoding='utf-8') as f:
                json.dump(video_data, f, indent=4)
            print(f"Saved {len(video_data)} Videos")

        except Exception as e:
            print(f"Error processing {ch_id}: {e}")

main()