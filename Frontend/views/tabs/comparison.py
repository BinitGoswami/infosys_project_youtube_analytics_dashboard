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

def render_comparison(df_videos, df_monthly, stats, ch_id):
        st.markdown('<h3 style="color:#00E5FF; margin-bottom:20px;">Competitive Visual Analysis</h3>', unsafe_allow_html=True)
        
        df_channels = get_all_channels_list()
        current_name = stats['channel_name']
        competitor_options = df_channels[df_channels['channel_name'] != current_name]['channel_name']
        
        c_sel, _ = st.columns([2, 2])
        with c_sel:
            comp_name = st.selectbox(
                "Select Competitor", 
                options=competitor_options, 
                index=None, 
                placeholder="Select Competitor Channel",
                label_visibility="collapsed"
            )
        
        if comp_name:
            channel_map = dict(zip(df_channels['channel_name'], df_channels['channel_id']))
            id2 = channel_map[comp_name]
            comp_df = compare_channels([ch_id, id2])
            
            if not comp_df.empty:
                # Shared Black Box Legend Style
                def get_legend_style(position="right"):
                    return dict(
                        yanchor="top", y=0.99,
                        xanchor="left" if position == "left" else "right",
                        x=0.01 if position == "left" else 0.99,
                        bgcolor="rgba(0,0,0,0.8)",
                        bordercolor="#333",
                        borderwidth=1,
                        font=dict(color='white', size=11)
                    )
                st.write("###")
    
                # --- ROW 1: DONUT PIE CHARTS ---
                col_p1, col_p2 = st.columns(2)
                
                with col_p1:
                    fig_subs = px.pie(comp_df, values='subscribers', names='channel_name', 
                                    hole=0.5, color_discrete_sequence=['#D90368', '#00E5FF'])
                    fig_subs.update_layout(
                        title=dict(text="SUBSCRIBERS", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                        paper_bgcolor="rgba(0,0,0,0)",
                        legend=get_legend_style("left")  # Legend at Top-Left for long names
                    )
                    st.plotly_chart(fig_subs, use_container_width=True)
    
                with col_p2:
                    fig_views = px.pie(comp_df, values='total_views', names='channel_name', 
                                    hole=0.5, color_discrete_sequence=['#822FAF', '#009688'])
                    fig_views.update_layout(
                        title=dict(text="VIEWS", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                        paper_bgcolor="rgba(0,0,0,0)",
                        legend=get_legend_style("left")
                    )
                    st.plotly_chart(fig_views, use_container_width=True)
    
                # --- ROW 2: EFFICIENCY BAR CHART ---
                st.write("###")
                comp_df['avg_views'] = comp_df['total_views'] / comp_df['total_videos']
                
                fig_eff = px.bar(comp_df, x='channel_name', y='avg_views', color='channel_name',
                                color_discrete_map={current_name: '#D90368', comp_name: '#00E5FF'})
                
                fig_eff.update_layout(
                    title=dict(text="CONTENT EFFICIENCY", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=get_legend_style("right"),
                    xaxis=dict(title=dict(text="Channel Name", font=dict(color='#00E5FF')), tickfont=dict(color='white')),
                    yaxis=dict(title=dict(text="Avg Views per Video", font=dict(color='#00E5FF')), tickfont=dict(color='white'), gridcolor='#333')
                )
                st.plotly_chart(fig_eff, use_container_width=True)
    
                # --- ROW 3: GROWTH SCALABILITY (RADAR/LINE) ---
                st.write("###")
                metrics = ['Subscribers', 'Total Views', 'Total Videos']
                ch1_data = comp_df[comp_df['channel_name'] == current_name].iloc[0]
                ch2_data = comp_df[comp_df['channel_name'] == comp_name].iloc[0]
    
                fig_radar = go.Figure()
                # Normalized metrics for side-by-side comparison
                fig_radar.add_trace(go.Scatter(x=metrics, y=[1, 1, 1], name=current_name, line=dict(color='#D90368', width=4)))
                fig_radar.add_trace(go.Scatter(x=metrics, y=[
                    ch2_data['subscribers']/ch1_data['subscribers'] if ch1_data['subscribers']>0 else 1,
                    ch2_data['total_views']/ch1_data['total_views'] if ch1_data['total_views']>0 else 1,
                    ch2_data['total_videos']/ch1_data['total_videos'] if ch1_data['total_videos']>0 else 1
                ], name=comp_name, line=dict(color='#00E5FF', width=4)))
    
                fig_radar.update_layout(
                    title=dict(text="PERFORMANCE SCALABILITY", font=dict(color='#00E5FF', size=18), x=0.5, xanchor='center'),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=get_legend_style("right"),
                    xaxis=dict(title=dict(text="Metric Category", font=dict(color='#00E5FF')), tickfont=dict(color='white')),
                    yaxis=dict(title=dict(text="Performance Scale", font=dict(color='#00E5FF')), tickfont=dict(color='white'), gridcolor='#333')
                )
                st.plotly_chart(fig_radar, use_container_width=True)
    
        st.write("###")
    
    # --- TAB 5: RECOMMENDATION (THE GROWTH ENGINE) ---
