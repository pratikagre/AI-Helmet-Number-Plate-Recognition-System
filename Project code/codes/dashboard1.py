import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

def dashboard_tab(conn, cursor):
    """Enhanced Dashboard Page for Safety Analytics"""
    st.title("📊 Safety Analytics Dashboard")
    st.markdown("""
    <style>
        .dashboard-header {
            text-align: center;
            color: white;
            margin-bottom: 2rem;
        }
        .plot-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .metric-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
        }
        .stSelectbox > div > div {
            background-color: rgba(255, 255, 255, 0.1) !important;
        }
    </style>
    <h3 class="dashboard-header">Real-time Safety Monitoring & Performance Analytics</h3>
    """, unsafe_allow_html=True)
    
    # Load data from database
    @st.cache_data(ttl=300)
    def load_data():
        query = "SELECT timestamp, vehicle_count, person_count, helmet_detected FROM detection_records ORDER BY timestamp"
        df = pd.read_sql(query, conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['week'] = df['timestamp'].dt.isocalendar().week
        df['month'] = df['timestamp'].dt.month_name()
        df['helmet_status'] = df['helmet_detected'].map({1: 'With Helmet', 0: 'No Helmet'})
        return df
    
    df = load_data()
    
    # Date range filter
    min_date = df['date'].min()
    max_date = df['date'].max()
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    
    # Additional filters
    st.sidebar.header("🔍 Filters")
    days_of_week = st.sidebar.multiselect(
        "Select Days of Week",
        options=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        default=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    )
    
    time_range = st.sidebar.slider(
        "Select Time Range (24h format)",
        0, 23, (0, 23))
    
    # Filter data
    filtered_df = df[(df['date'] >= start_date) & 
                    (df['date'] <= end_date) &
                    (df['day_of_week'].isin(days_of_week)) &
                    (df['hour'] >= time_range[0]) & 
                    (df['hour'] <= time_range[1])]
    
    # KPI Cards
    st.subheader("📈 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_detections = len(filtered_df)
        st.markdown(f"""
        <div class="metric-card">
            <h3>Total Detections</h3>
            <h2>{total_detections:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        helmet_compliance = filtered_df['helmet_detected'].mean() * 100
        trend = "↑" if helmet_compliance > 50 else "↓"
        st.markdown(f"""
        <div class="metric-card">
            <h3>Helmet Compliance</h3>
            <h2>{helmet_compliance:.1f}% {trend}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_vehicles = filtered_df['vehicle_count'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <h3>Avg Vehicles</h3>
            <h2>{avg_vehicles:.1f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        violations = len(filtered_df[filtered_df['helmet_detected'] == 0])
        st.markdown(f"""
        <div class="metric-card">
            <h3>Safety Violations</h3>
            <h2>{violations:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts Row 1
    st.markdown('<div class="plot-container">', unsafe_allow_html=True)
    st.subheader("🚦 Safety Trends Over Time")
    
    # Time period selector
    time_period = st.radio("Time Period", ["Daily", "Weekly", "Monthly"], horizontal=True)
    
    if time_period == "Daily":
        time_data = filtered_df.groupby(['date', 'helmet_status']).size().unstack().fillna(0)
    elif time_period == "Weekly":
        time_data = filtered_df.groupby(['week', 'helmet_status']).size().unstack().fillna(0)
    else:  # Monthly
        time_data = filtered_df.groupby(['month', 'helmet_status']).size().unstack().fillna(0)
        # Order months chronologically
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        time_data = time_data.reindex(month_order)
    
    time_data['Compliance Rate'] = time_data['With Helmet'] / (time_data['With Helmet'] + time_data['No Helmet']) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_data.index, 
        y=time_data['Compliance Rate'],
        name='Compliance Rate',
        line=dict(color='#00c6ff', width=3),
        yaxis='y2'
    ))
    fig.add_trace(go.Bar(
        x=time_data.index,
        y=time_data['With Helmet'],
        name='With Helmet',
        marker_color='#00b894'
    ))
    fig.add_trace(go.Bar(
        x=time_data.index,
        y=time_data['No Helmet'],
        name='No Helmet',
        marker_color='#ff7675'
    ))
    
    fig.update_layout(
        barmode='stack',
        yaxis=dict(title='Count'),
        yaxis2=dict(
            title='Compliance Rate (%)',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.subheader("🕒 Hourly Patterns")
        
        # Heatmap of violations by hour and day
        heatmap_data = filtered_df.groupby(['day_of_week', 'hour'])['helmet_detected'].mean().unstack().fillna(0)
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = heatmap_data.reindex(days_order)
        
        fig = px.imshow(
            heatmap_data,
            labels=dict(x="Hour of Day", y="Day of Week", color="Compliance Rate"),
            color_continuous_scale='Viridis',
            aspect="auto"
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="plot-container">', unsafe_allow_html=True)
        st.subheader("🚗 Vehicle Detection Analysis")
        
        # Interactive selection for vehicle analysis
        analysis_type = st.radio(
            "Analysis Type",
            ["By Hour", "By Day", "By Helmet Status"],
            horizontal=True
        )
        
        if analysis_type == "By Hour":
            vehicle_data = filtered_df.groupby('hour')['vehicle_count'].mean().reset_index()
            x_col = 'hour'
            x_title = "Hour of Day"
        elif analysis_type == "By Day":
            vehicle_data = filtered_df.groupby('day_of_week')['vehicle_count'].mean().reset_index()
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            vehicle_data['day_of_week'] = pd.Categorical(vehicle_data['day_of_week'], categories=days_order, ordered=True)
            vehicle_data = vehicle_data.sort_values('day_of_week')
            x_col = 'day_of_week'
            x_title = "Day of Week"
        else:
            vehicle_data = filtered_df.groupby('helmet_status')['vehicle_count'].mean().reset_index()
            x_col = 'helmet_status'
            x_title = "Helmet Status"
        
        fig = px.bar(
            vehicle_data,
            x=x_col,
            y='vehicle_count',
            title=f"Average Vehicles Detected by {x_title}",
            color=x_col,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            xaxis_title=x_title,
            yaxis_title="Average Vehicles Detected",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Charts Row 3 - Additional visualizations
    st.markdown('<div class="plot-container">', unsafe_allow_html=True)
    st.subheader("📊 Additional Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart of helmet compliance
        compliance_data = filtered_df['helmet_status'].value_counts().reset_index()
        fig = px.pie(
            compliance_data,
            names='helmet_status',
            values='count',
            title="Helmet Compliance Distribution",
            hole=0.4,
            color='helmet_status',
            color_discrete_map={'With Helmet': '#00b894', 'No Helmet': '#ff7675'}
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Scatter plot of vehicles vs persons with helmet status
        fig = px.scatter(
            filtered_df.sample(min(500, len(filtered_df))),
            x='vehicle_count',
            y='person_count',
            color='helmet_status',
            title="Vehicles vs Persons with Helmet Status",
            color_discrete_map={'With Helmet': '#00b894', 'No Helmet': '#ff7675'},
            opacity=0.7
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)