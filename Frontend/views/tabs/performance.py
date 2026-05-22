import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pycountry as pc
from analytics import format_big_number, get_channel_stats, get_channel_videos, get_monthly_analytics, compare_channels, get_seasonal_analytics, get_top_keywords, get_duration_clustering, get_all_channels_list
import live_data
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

def render_performance(df_videos, df_monthly, stats, ch_id):
        if df_videos.empty: st.stop() 
    
        # 1: Clean the category column (Remove Emojis)
        df_videos['category'] = df_videos['category'].replace({
            'Viral Content 🚀': 'Viral Content',
            'Underperforming ⚠️': 'Underperforming',
            'Loyal Fanbase (Low Views / High Eng.) ❤️': 'Loyal Fanbase', # Handle potential long names
            'Loyal Fanbase ❤️': 'Loyal Fanbase',
            'High Views / Low Eng. 📉': 'High Views',
            'High Views 📉': 'High Views'
        })
    
        # 2: Create Chart with Clean Keys
        fig_cat = px.scatter(df_videos, x='view_count', y='engagement_rate', 
                           color='category', 
                           hover_data=['title'], 
                           color_discrete_map={
                               'Viral Content': '#00CC96', 
                               'Underperforming': '#EF553B', 
                               'Loyal Fanbase': '#AB63FA', 
                               'High Views': '#FFA15A'
                           })
        
        # 3: Apply the "Black Box Legend" Layout
        fig_cat.update_layout(
            title=dict(
                text="Performance Matrix",
                font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                x=0.5, xanchor='center', y=0.95
            ),
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            height=450,
            margin=dict(l=20, r=20, t=50, b=20),
            
            xaxis=dict(
                title=dict(text="View Count", font=dict(color='#00E5FF')), 
                tickfont=dict(color='white'), 
                showgrid=False
            ),
            yaxis=dict(
                title=dict(text="Engagement Rate", font=dict(color='#00E5FF')), 
                tickfont=dict(color='white'), 
                showgrid=True, 
                gridcolor='#333'
            ),
            
            # THE LEGEND BOX (Top Right)
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="#333",
                borderwidth=1,
                font=dict(color='white')
            )
        )
        st.plotly_chart(fig_cat, use_container_width=True)
        
        st.write("###")
        
        st.markdown('<h3 style="color:#00E5FF; font-size:20px; margin-bottom:15px;">Recent Trend Analysis</h3>', unsafe_allow_html=True)
        
        if len(df_videos) > 0:
            # 1. CALCULATE METRICS
            recent_videos = df_videos.head(10)
            
            # Trend Logic
            is_improving = recent_videos['view_count'].mean() > df_videos['view_count'].mean()
            trend_status = "Improving" if is_improving else "Declining"
            trend_color = "#00CC96" if is_improving else "#EF553B"
            
            # Best Video (Title + Truncate if too long)
            best_vid_title = df_videos.loc[df_videos['view_count'].idxmax()]['title']
            if len(best_vid_title) > 45: best_vid_title = best_vid_title[:45] + "..."
            
            # Highest Engagement (Title + Truncate)
            best_eng_title = df_videos.loc[df_videos['engagement_rate'].idxmax()]['title']
            if len(best_eng_title) > 45: best_eng_title = best_eng_title[:45] + "..."
    
            # 2. CSS FOR CARDS
            st.markdown("""
            <style>
            .trend-card {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 15px;
                padding: 25px 20px;
                height: 180px; /* Fixed height for alignment */
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                transition: transform 0.3s ease, border-color 0.3s ease;
            }
            .trend-card:hover {
                border-color: #D90368; /* Pink Glow on Hover */
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(217, 3, 104, 0.2);
            }
            .trend-label {
                color: #888;
                font-size: 13px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                margin-bottom: 15px;
            }
            .trend-value {
                color: #fff;
                font-size: 18px;
                font-weight: 600;
                line-height: 1.4;
                
                /* Limit lines to 3 */
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            </style>
            """, unsafe_allow_html=True)
    
            # 3. RENDER CARDS IN COLUMNS
            c1, c2, c3 = st.columns(3)
    
            with c1:
                st.markdown(f"""
                <div class="trend-card">
                    <div class="trend-label">Overall Trend</div>
                    <div class="trend-value" style="color: {trend_color}; font-size: 24px;">{trend_status}</div>
                </div>
                """, unsafe_allow_html=True)
    
            with c2:
                st.markdown(f"""
                <div class="trend-card">
                    <div class="trend-label">Most Viewed Video</div>
                    <div class="trend-value" title="{df_videos.loc[df_videos['view_count'].idxmax()]['title']}">
                        "{best_vid_title}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
            with c3:
                st.markdown(f"""
                <div class="trend-card">
                    <div class="trend-label">Highest Engagement</div>
                    <div class="trend-value" title="{df_videos.loc[df_videos['engagement_rate'].idxmax()]['title']}">
                        "{best_eng_title}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        else:
            st.info("Not enough data for trend analysis.")
    
        st.write("###")
    
    # --- TAB 4: COMPARISON (Optimized Layout) ---
