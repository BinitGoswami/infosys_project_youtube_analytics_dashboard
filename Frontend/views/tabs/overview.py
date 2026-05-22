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

def render_overview(df_videos, df_monthly, stats, ch_id):
        
        # A. Prepare Data
        if not df_videos.empty:
            avg_len = df_videos['duration_min'].mean()
            total_earn = df_videos['est_earnings'].sum()
        else:
            avg_len = 0.0
            total_earn = 0.0
    
        country_code = stats.get('country', 'N/A')
        country_name = country_code # (Assuming you handled the pycountry logic or kept it simple)
        if country_code and len(country_code) == 2:
            try:
                c_obj = pc.countries.get(alpha_2=country_code)
                country_name = c_obj.name if c_obj else country_code
            except: pass
    
        created_raw = stats.get('channel_created_at')
        if created_raw:
            try: joined_date = pd.to_datetime(created_raw).strftime('%d %b %Y')
            except: joined_date = str(created_raw)
        else: joined_date = "N/A"
    
        # B. THE 6 BOXES (2 Rows x 3 Cols)
        
        # Row 1
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        metrics_row1 = [
            ("Subscribers", format_big_number(stats['subscribers'])),
            ("Total Views", format_big_number(stats['total_views'])),
            ("Est. Revenue", f"$ {format_big_number(total_earn)}") 
        ]
        for col, (lbl, val) in zip([r1_c1, r1_c2, r1_c3], metrics_row1):
            col.markdown(f'<div class="kpi-card"><div class="kpi-lbl">{lbl}</div><div class="kpi-val">{val}</div></div>', unsafe_allow_html=True)
            
        st.write("######") # Spacer
        
        # Row 2
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        metrics_row2 = [
            ("Avg Duration", f"{avg_len:.1f} min"),
            ("Country", country_name),
            ("Created On", joined_date)
        ]
        for col, (lbl, val) in zip([r2_c1, r2_c2, r2_c3], metrics_row2):
            col.markdown(f'<div class="kpi-card"><div class="kpi-lbl">{lbl}</div><div class="kpi-val">{val}</div></div>', unsafe_allow_html=True)
        
        st.write("###")
        
        # Only show graphs if we have data
        if not df_videos.empty:
            # ...TAB 1: OVERVIEW...
    
            # GROWTH TRAJECTORY
            if not df_monthly.empty:
                # 1. Calculate Ranges with Buffer
                max_views = df_monthly['view_count'].max()
                
                # Top Headroom (10%)
                y_max = max_views * 1.1 
                
                y_buffer = max_views * 0.05 
                
                x_min = df_monthly['published_at'].min()
                x_max = df_monthly['published_at'].max()
    
                fig = go.Figure()
    
                fig.add_trace(go.Scatter(
                    x=df_monthly['published_at'], 
                    y=df_monthly['view_count'],
                    mode='lines+markers',
                    name='Views',
                    line=dict(color='#00E5FF', width=3, shape='spline'),
                    
                    # High Visibility Markers
                    marker=dict(
                        size=6, 
                        color='white', 
                        line=dict(width=1, color='#00E5FF')
                    ),
                    
                    fill='tozeroy',
                    fillcolor='rgba(0, 229, 255, 0.1)'
                ))
    
                fig.update_layout(
                    title=dict(
                        text="Growth Trajectory",
                        font=dict(size=20, color='#00E5FF', family="Inter, sans-serif"),
                        x=0.5, 
                        xanchor='center', 
                        y=0.95
                    ),
                    paper_bgcolor='#1A1A1A', 
                    plot_bgcolor='#1A1A1A',
                    height=350,
                    margin=dict(l=20, r=20, t=50, b=20),
                    
                    xaxis=dict(
                        title=dict(text="Date", font=dict(color='#00E5FF')),
                        showgrid=False, 
                        linecolor='#333',
                        tickfont=dict(color='white'),
                        range=[x_min, x_max], 
                        showspikes=False
                    ),
                    
                    yaxis=dict(
                        title=dict(text="Total Views", font=dict(color='#00E5FF')),
                        showgrid=True, 
                        gridcolor='#333', 
                        gridwidth=1,
                        
                        # CHANGE: Show the Zero Line explicitly
                        zeroline=True,
                        zerolinecolor='#555', # Visible line at 0
                        zerolinewidth=1,
                        
                        tickfont=dict(color='white'),
                        
                        # CHANGE: Start range BELOW zero to lift the dots
                        range=[-y_buffer, y_max] 
                    ),
                    hovermode="closest"
                )
    
                st.plotly_chart(fig, width='stretch')
                
            else:
                st.info("No growth data available yet.")
            st.write("###")
            
            # 1. PREPARE DATA (Top 10 by Views)
            top_df = df_videos.sort_values(by='view_count', ascending=False).head(10)[['title', 'view_count', 'published_at']].copy()
            
            if not top_df.empty:
                top_df.insert(0, 'Rank', range(1, len(top_df) + 1))
                
                # 2. BUILD HTML
                table_html = '<div class="custom-table-container">'
                table_html += '<div class="custom-header"><h5>Top Performing Videos</h5></div>'
                
                table_html += '<table class="styled-table">'
                table_html += '<thead>'
                table_html += '<tr>'
                table_html += '<th width="10%" class="col-center">Rank</th>'
                table_html += '<th width="60%" class="col-left">Video</th>'
                table_html += '<th width="15%" class="col-center">Views</th>'
                table_html += '<th width="15%" class="col-center">Date</th>'
                table_html += '</tr>'
                table_html += '</thead>'
                table_html += '<tbody>'
                
                for index, row in top_df.iterrows():
                    rank = row['Rank']
                    title = row['title']
                    views = f"{row['view_count']:,}"
                    date = row['published_at'].strftime("%d %b %Y") 
                    
                    table_html += '<tr>'
                    table_html += f'<td class="col-center">{rank}</td>'
                    table_html += f'<td class="col-left">{title}</td>'
                    table_html += f'<td class="col-center">{views}</td>'
                    table_html += f'<td class="col-center">{date}</td>'
                    table_html += '</tr>'
                
                table_html += '</tbody></table></div>'
                
                # 3. RENDER
                st.markdown(table_html, unsafe_allow_html=True)
    
            else:
                st.info("No video data found.")
    
    # --- TAB 2: STRATEGY ---
