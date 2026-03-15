import pandas as pd
import mysql.connector as ms
import streamlit as st
import os
from collections import Counter
import re
from dotenv import load_dotenv
import bcrypt

load_dotenv()
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'), 
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4',
    'autocommit': True
}

@st.cache_resource
def format_big_number(num):
    """Formats large numbers into K, M, B, T string"""
    if num is None:
        return "0"
    
    # Ensure it's a number (handle strings if they slip in)
    try:
        num = float(num)
    except:
        return str(num)

    if num >= 1_000_000_000_000:
        return f"{num / 1_000_000_000_000:.2f}T"
    elif num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.2f}K"
    else:
        return f"{num:.0f}"

def get_db_connection():
    try:
        conn = ms.connect(**DB_CONFIG)
        return conn
    except ms.Error as e:
        st.error(f"Database Connection Failed: {e}")
        return None

def get_conn():
    conn = get_db_connection()
    if conn is None:
        return None
    if not conn.is_connected():
        conn.reconnect(attempts=3, delay=2)
    return conn

def get_channel_stats(channel_id):
    """Fetches high-level channel stats"""
    conn = get_conn()
    if conn:
        query = "SELECT * FROM channels WHERE channel_id = %s"
        df = pd.read_sql(query, conn, params=(channel_id,))
        return df.iloc[0] if not df.empty else None
    return None

def get_channel_videos(channel_id):
    """Fetches comprehensive video data"""
    conn = get_conn()
    if conn:
        query = f"""
        SELECT title, published_at, view_count, like_count, comment_count, 
               duration_seconds, engagement_rate, tags
        FROM videos 
        WHERE channel_id = '{channel_id}'
        ORDER BY published_at DESC
        """
        df = pd.read_sql(query, conn)
        df['published_at'] = pd.to_datetime(df['published_at'])
        
        # Est. Monthly Earnings (Approx logic: $2 RPM)
        df['est_earnings'] = (df['view_count'] / 1000) * 2
        
        # Duration in Minutes
        df['duration_min'] = df['duration_seconds'] / 60
        
        # Engagement Analysis Categories
        # Define thresholds
        avg_views = df['view_count'].mean()
        avg_eng = df['engagement_rate'].mean()
        
        def categorize(row):
            if row['view_count'] > avg_views and row['engagement_rate'] > avg_eng:
                return 'Viral Content 🚀'
            elif row['view_count'] > avg_views and row['engagement_rate'] < avg_eng:
                return 'High Views / Low Eng. 📉'
            elif row['view_count'] < avg_views and row['engagement_rate'] > avg_eng:
                return 'Loyal Fanbase (Low Views / High Eng.) ❤️'
            else:
                return 'Underperforming ⚠️'
                
        df['category'] = df.apply(categorize, axis=1)
        
        return df
    return pd.DataFrame()

def get_monthly_analytics(df):
    """Aggregates data by month for"""
    if df.empty: return pd.DataFrame()
    
    # Resample by Month
    monthly = df.set_index('published_at').resample('M').agg({
        'view_count': 'sum',
        'title': 'count', # This becomes Upload Frequency
        'est_earnings': 'sum',
        'engagement_rate': 'mean'
    }).reset_index()
    
    monthly.rename(columns={'title': 'upload_count'}, inplace=True)
    monthly['month_name'] = monthly['published_at'].dt.strftime('%Y-%m')
    return monthly

def compare_channels(channel_ids):
    """Fetches stats for multiple channels for comparison"""
    conn = get_conn()
    if conn and channel_ids:
        format_strings = ','.join(['%s'] * len(channel_ids))
        query = f"SELECT * FROM channels WHERE channel_id IN ({format_strings})"
        df = pd.read_sql(query, conn, params=tuple(channel_ids))
        return df
    return pd.DataFrame()

def get_all_channels_list():
    """Fetches a list of all channels (Name and ID) for the dropdown"""
    conn = get_conn()
    if conn:
        # We need both ID (for logic) and Name (for display)
        query = "SELECT channel_name, channel_id FROM channels ORDER BY channel_name"
        df = pd.read_sql(query, conn)
        return df
    return pd.DataFrame()

def get_seasonal_analytics(df):
    """Aggregates views by Month (Jan-Dec) for Seasonal Analysis"""
    if df.empty: return pd.DataFrame()
    
    # Extract Month Name
    df['month_name'] = df['published_at'].dt.month_name()
    # Extract Month Number for correct sorting (Jan=1, Feb=2)
    df['month_num'] = df['published_at'].dt.month
    
    seasonal = df.groupby(['month_num', 'month_name'])['view_count'].mean().reset_index()
    return seasonal.sort_values('month_num')

def get_top_keywords(df):
    """Extracts most common words from Video Titles"""
    if df.empty: return pd.DataFrame()
    
    # Combine all titles into one string
    text = " ".join(df['title'].dropna()).lower()
    # Remove special characters
    text = re.sub(r'[^\w\s]', '', text)
    
    # Basic Stopwords to ignore
    stopwords = {'the', 'and', 'to', 'of', 'a', 'in', 'is', 'for', 'on', 'with', 'my', 'it', 'this', 'that', 'video', 'how', 'i'}
    
    words = [w for w in text.split() if w not in stopwords and len(w) > 2]
    
    # Count frequency
    common_words = Counter(words).most_common(10)
    
    return pd.DataFrame(common_words, columns=['Word', 'Count'])

def get_duration_clustering(df):
    """
    Classifies videos based on Duration and Engagement 
    Clusters: Short & Snappy, Deep Dives, Long & Boring, Regular
    """
    if df.empty: return pd.DataFrame()
    
    # Calculate median engagement to determine what is "High" vs "Low" for this specific channel
    eng_median = df['engagement_rate'].median()
    
    def classify(row):
        duration = row['duration_min']
        eng = row['engagement_rate']
        
        # Logic from idea.docx [cite: 126-128]
        if duration < 5 and eng > eng_median:
            return "Short & Snappy ⚡"        # < 5 mins, High Eng
        elif duration > 15 and eng > eng_median:
            return "Deep Dives 🧠"            # > 15 mins, High Eng
        elif duration > 20 and eng < eng_median:
            return "Long & Boring 😴"         # > 20 mins, Low Eng
        else:
            return "Standard Video 📹"
            
    df['duration_cluster'] = df.apply(classify, axis=1)
    return df

def init_user_db():
    """Creates users table and ensures channel_id column exists"""
    conn = get_conn()
    if conn:
        cursor = conn.cursor()
        
        # 1. Create/Update Users Table with channel_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email VARCHAR(255) PRIMARY KEY,
                password_hash TEXT,
                name VARCHAR(255),
                auth_type VARCHAR(50),
                channel_id VARCHAR(255)
            )
        """)
        
        # Migration: Ensure channel_id exists if table was created previously
        try:
            cursor.execute("SHOW COLUMNS FROM users LIKE 'channel_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN channel_id VARCHAR(255)")
                conn.commit()
        except Exception as e:
            print(f"Migration Error: {e}")

        conn.commit()
        cursor.close()
        conn.close()

def create_user(email, password, name, auth_type='email'):
    """Now saves the NAME too"""
    conn = get_conn()
    if conn:
        cursor = conn.cursor()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8') if password else None
        try:
            # Updated Query to include Name
            cursor.execute(
                "INSERT INTO users (email, password_hash, name, auth_type) VALUES (%s, %s, %s, %s)", 
                (email, hashed, name, auth_type)
            )
            conn.commit()
            return True
        except:
            return False 
        finally:
            conn.close()

def get_my_channel(user_email):
    """Finds the channel_id directly from the users table"""
    conn = get_conn()
    if not conn: return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT channel_id FROM users WHERE email = %s LIMIT 1"
        cursor.execute(query, (user_email,))
        result = cursor.fetchone()
        
        if result:
            return result['channel_id']
        return None
    except Exception as e:
        print(f"Error checking user DB: {e}")
        return None
    finally:
        conn.close()

def get_user_name(email):
    """New helper to get name from DB"""
    conn = get_conn()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return result[0]
    return email.split('@')[0] # Fallback

def google_user_exists(email):
    """Checks if a Google user has signed up before"""
    conn = get_conn()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

def link_user_channel(email, channel_id, channel_name):
    """Links a User to a Channel by updating the USERS table"""
    conn = get_conn()
    if conn:
        cursor = conn.cursor()
        try:
            # Step 1: Ensure the Channel exists in the channels table
            cursor.execute("SELECT channel_id FROM channels WHERE channel_id = %s", (channel_id,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO channels 
                    (channel_id, channel_name, subscribers, total_views, total_videos) 
                    VALUES (%s, %s, 0, 0, 0)
                    """,
                    (channel_id, channel_name)
                )

            # Step 2: Update the USER table to link this channel
            cursor.execute("UPDATE users SET channel_id = %s WHERE email = %s", (channel_id, email))
            
            conn.commit()
            print(f"SUCCESS: User {email} is now linked to {channel_id}")
            return True
            
        except Exception as e:
            print(f"Linking Error: {e}")
            return False
        finally:
            conn.close()

def verify_user(email, password):
    if not email or not password:
        return False
    conn = get_conn()
    if not conn: 
        return False
    try:
        cursor = conn.cursor(dictionary=True)
        # 1. IDENTIFY: Find the user in the database
        cursor.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        
        if result and result['password_hash']:
            # 2. MATCH: Verify the password against the stored hash
            return bcrypt.checkpw(password.encode('utf-8'), result['password_hash'].encode('utf-8'))
        return False
    except Exception as e:
        print(f"Login error: {e}")
        return False
    finally:
        conn.close()