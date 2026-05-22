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

def render_strategy(df_videos, df_monthly, stats, ch_id):
        if df_videos.empty: st.stop()
    
        # --- ROW 1: UPLOAD FREQUENCY (Full Width) ---
        if not df_monthly.empty:
            # 1. Create the Bar Chart
            fig_freq = px.bar(df_monthly, x='published_at', y='upload_count', 
                            color='view_count', 
                            color_continuous_scale='Turbo', # Rainbow Gradient
                            )
            
            fig_freq.update_traces(
                marker_line_width=1.5, 
                marker_line_color='#1A1A1A', # Dark border to separate bars
                opacity=1
            )
    
            # Calculate dynamic range for "Lifted" look
            y_max = df_monthly['upload_count'].max()
            y_buffer = y_max * 0.05 # 5% buffer below zero
    
            # 2. Apply Designer Styling
            fig_freq.update_layout(
                title=dict(
                    text="Upload Frequency",
                    font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"), # Cyan Title
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', # Transparent (Shows CSS Grey)
                plot_bgcolor='rgba(0,0,0,0)',
                height=400, # Slightly taller since it's full width
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(
                    title=dict(text="Date", font=dict(color='#00E5FF')),
                    showgrid=False, 
                    tickfont=dict(color='white')
                ),
                yaxis=dict(
                    title=dict(text="Uploads", font=dict(color='#00E5FF')),
                    showgrid=True, gridcolor='#333',
                    tickfont=dict(color='white'),
                    range=[-y_buffer, y_max * 1.1],
                    zeroline=False
                ),
                coloraxis_colorbar=dict(
                    title=dict(text="Views", font=dict(color='#AAA')),
                    tickfont=dict(color='#AAA')
                )
            )
    
            fig_freq.add_hline(
                y=0, 
                line_color="#333", 
                line_width=1, 
                layer="above" # This forces it to be visible on top
            )
    
            st.plotly_chart(fig_freq, use_container_width=True)
        else:
            st.info("No frequency data.")
        
        st.write("###") # Spacer between graphs
    
        # --- ROW 2: ENGAGEMENT SCATTER (Full Width) ---
        fig_corr = px.scatter(df_videos, x='like_count', y='comment_count', 
                            hover_data=['title'], 
                            color_discrete_sequence=['#FF007F']) # Purple Dots
        
        # Add borders to dots for neon effect
        fig_corr.update_traces(marker=dict(size=6, line=dict(width=1, color='white'), opacity=0.8))
        
        # Apply Designer Styling
        fig_corr.update_layout(
            title=dict(
                text="Engagement Correlation",
                font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"), # Cyan Title
                x=0.5, xanchor='center', y=0.95
            ),
            paper_bgcolor='rgba(0,0,0,0)', # Transparent (Shows CSS Grey)
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis=dict(
                title=dict(text="Likes", font=dict(color='#00E5FF')),
                showgrid=False,
                tickfont=dict(color='white')
            ),
            yaxis=dict(
                title=dict(text="Comments", font=dict(color='#00E5FF')),
                showgrid=True, gridcolor='#333',
                tickfont=dict(color='white')
            )
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    
        st.write("###") # Spacer
    
        # --- ROW 3: BEST UPLOAD STRATEGY (Combo Chart: Day vs Hour) ---
        if not df_videos.empty:
            # 1. Prepare Data
            df_videos['day_name'] = df_videos['published_at'].dt.day_name()
            df_videos['hour'] = df_videos['published_at'].dt.hour
            
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            # Metric 1 (Bars)
            daily_views = df_videos.groupby('day_name')['view_count'].mean().reindex(days_order).fillna(0)
            
            # Metric 2 (Line)
            hourly_perf = df_videos.groupby(['day_name', 'hour'])['view_count'].mean().reset_index()
            # Handle empty data case for reindexing
            if not hourly_perf.empty:
                best_hour_idx = hourly_perf.groupby('day_name')['view_count'].idxmax()
                best_hours = hourly_perf.loc[best_hour_idx].set_index('day_name').reindex(days_order).fillna(0)
            else:
                best_hours = pd.DataFrame({'hour': [0]*7}, index=days_order)
    
            fig_combo = go.Figure()
    
            # BAR TRACE (Avg Views)
            fig_combo.add_trace(go.Bar(
                x=daily_views.index,
                y=daily_views.values,
                name='Avg Views',
                marker_color='rgba(130, 47, 175, 0.6)', 
                marker_line_color="#ABAF2F",            
                marker_line_width=1.5,
                yaxis='y1' 
            ))
    
            # LINE TRACE (Best Hour)
            fig_combo.add_trace(go.Scatter(
                x=best_hours.index,
                y=best_hours['hour'],
                name='Best Hour',
                mode='lines+markers',
                line=dict(color='#34FF01', width=4), 
                marker=dict(size=10, color='white', line=dict(width=2, color='#34FF01')),
                yaxis='y2' 
            ))
    
            # 3. Designer Layout
            fig_combo.update_layout(
                title=dict(
                    text="Best Upload Strategy (Day vs Hour)",
                    font=dict(size=20, color='#00E5FF', family="Inter, sans-serif"),
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                height=600,
                
                margin=dict(l=30, r=60, t=40, b=80), # Added bottom margin
                
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(color='white', size=14),
                    title=dict(text="Day of Week", font=dict(color='#00E5FF'), standoff=20)
                ),
                
                # Left Axis (Views)
                yaxis=dict(
                    title=dict(text="Avg Views", font=dict(color="#F2FF03")),
                    showgrid=True, gridcolor='#333',
                    tickfont=dict(color='white'),
                    side='left'
                ),
                
                # Right Axis (Hours)
                yaxis2=dict(
                    title=dict(text="Best Time (24h)", font=dict(color="#34FF01")),
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    tickfont=dict(color='white'),
                    range=[0, 24] 
                ),
                
                # 🟢 LEGEND: Top-Right & "Container" Look
                legend=dict(
                    orientation="v",       
                    yanchor="top", y=0.95, 
                    xanchor="right", x=0.99, # Shifted to Right
                    bgcolor="rgba(0,0,0,0.9)", # Dark Black Container
                    bordercolor="#555",
                    borderwidth=1,
                    font=dict(color='white')
                )
            )
            
            st.plotly_chart(fig_combo, use_container_width=True)
        
        st.write("###") # Spacer
    
        # --- ROW 4: AUDIENCE BEHAVIOR (Side-by-Side Pies) ---
        c_season, c_mix = st.columns(2)
        
        # 1. LEFT SIDE: SEASONAL TRENDS
        with c_season:
            df_seasonal = get_seasonal_analytics(df_videos)
            if not df_seasonal.empty:
                fig_season = px.pie(df_seasonal, 
                                    values='view_count', 
                                    names='month_name', 
                                    hole=0.6,
                                    color_discrete_sequence=px.colors.sequential.Turbo
                                )
                
                fig_season.update_traces(
                    textposition='outside', 
                    textinfo='label+percent',
                    texttemplate='%{label}<br>%{percent}',
                    marker=dict(line=dict(color='#1A1A1A', width=2))
                )
                
                fig_season.update_layout(
                    title=dict(
                        text="Seasonal Trends",
                        font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                        x=0.5, xanchor='center', y=0.95
                    ),
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    
                    # 🔥 INCREASED HEIGHT TO 500px
                    height=500,
                    
                    # 🔥 INCREASED MARGINS (Prevents label clipping)
                    margin=dict(l=60, r=60, t=80, b=80),
                    showlegend=False
                )
                st.plotly_chart(fig_season, use_container_width=True)
            else:
                st.info("Not enough data for seasonal trends.")
    
        # 2. RIGHT SIDE: ENGAGEMENT MIX (Likes vs Comments)
        with c_mix:
            total_likes = df_videos['like_count'].sum()
            total_comments = df_videos['comment_count'].sum()
            
            if total_likes + total_comments > 0:
                # Create simple dataframe for the pie chart
                mix_data = pd.DataFrame({
                    'Type': ['Likes', 'Comments'],
                    'Count': [total_likes, total_comments]
                })
                
                fig_mix = px.pie(mix_data, 
                                values='Count', 
                                names='Type', 
                                hole=0.6,
                                color_discrete_sequence=['#00E5FF', '#D90368'] 
                            )
                
                fig_mix.update_traces(
                    textposition='outside', 
                    textinfo='label+percent',
                    texttemplate='%{label}<br>%{value:.2s}', 
                    marker=dict(line=dict(color='#1A1A1A', width=2))
                )
                
                fig_mix.update_layout(
                    title=dict(
                        text="Engagement Mix",
                        font=dict(size=18, color='#D90368', family="Inter, sans-serif"), 
                        x=0.5, xanchor='center', y=0.95
                    ),
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    
                    # 🔥 INCREASED HEIGHT TO 500px
                    height=500,
                    
                    # 🔥 INCREASED MARGINS
                    margin=dict(l=60, r=60, t=80, b=80),
                    showlegend=False
                )
                st.plotly_chart(fig_mix, use_container_width=True)
            else:
                st.info("No engagement data found.")
    
        st.write("###") # Spacer
        
        # --- ROW 5: TRENDING TOPICS (Vertical Fixed Color) ---
        df_keywords = get_top_keywords(df_videos)
        if not df_keywords.empty:
            # 1. Create Vertical Bar Chart
            fig_words = px.bar(df_keywords, 
                                x='Word', 
                                y='Count'
                                )
            
            # 2. Styling: Fixed Color + White Border
            fig_words.update_traces(
                marker_color='#822FAF', # 🟣 FIXED NEON PURPLE COLOR
                marker_line_color="#6A00FF", 
                marker_line_width=1.5, 
                opacity=1
            )
            
            # 3. Designer Layout
            fig_words.update_layout(
                title=dict(
                    text="Trending Topics",
                    font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                margin=dict(l=20, r=20, t=60, b=60),
                
                xaxis=dict(
                    title=dict(text="Keywords", font=dict(color='#00E5FF', size=14)), 
                    tickfont=dict(color='white', size=12), 
                    showgrid=False
                ),
                
                yaxis=dict(
                    title=dict(text="Frequency", font=dict(color='#00E5FF', size=14)), 
                    tickfont=dict(color='white'), 
                    showgrid=True, 
                    gridcolor='#333'
                )
            )
            st.plotly_chart(fig_words, use_container_width=True)
    
        st.write("###") # Spacer
    
        # --- ROW 6: VIDEO DURATION CLUSTERING (Full Width) ---
        df_clustered = get_duration_clustering(df_videos)
        if not df_clustered.empty:
            df_clustered['duration_cluster'] = df_clustered['duration_cluster'].replace({
                "Short & Snappy ⚡": "Short & Snappy",
                "Deep Dives 🧠": "Deep Dives",
                "Long & Boring 😴": "Long & Boring",
                "Standard Video 📹": "Standard Video"
            })
            fig_cluster = px.scatter(df_clustered, x='duration_min', y='engagement_rate', 
                                   color='duration_cluster', 
                                   hover_data=['title'], 
                                   color_discrete_map={"Short & Snappy": "#00CC96", "Deep Dives": "#AB63FA", "Long & Boring": "#EF553B", "Standard Video": "#636EFA"})
            
            # Add vertical line at 15 mins (YouTube standard)
            fig_cluster.add_vline(x=15, line_dash="dash", line_color="white", opacity=0.3)
            
            fig_cluster.update_layout(
                title=dict(
                    text="Video Duration Clustering",
                    font=dict(size=18, color='#00E5FF', family="Inter, sans-serif"),
                    x=0.5, xanchor='center', y=0.95
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(title=dict(text="Duration (Mins)", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=False),
                yaxis=dict(title=dict(text="Engagement Rate", font=dict(color='#00E5FF')), tickfont=dict(color='white'), showgrid=True, gridcolor='#333'),
                
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99,
                    bgcolor="rgba(0,0,0,0.8)", # Semi-transparent black box
                    bordercolor="#333",
                    borderwidth=1,
                    font=dict(color='white')
                )
            )
            st.plotly_chart(fig_cluster, use_container_width=True)
    
            st.write("###") # Spacer
    
    # --- TAB 3: PERFORMANCE ---
