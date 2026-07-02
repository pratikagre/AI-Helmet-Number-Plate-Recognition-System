import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

def dashboard_tab():
    """Enhanced Dashboard Page for Safety Analytics"""
    st.title("🚦 Safety Compliance Dashboard")
    st.markdown(
        "<h3 style='text-align: center; color: white;'>Real-time Safety Monitoring & Performance Analytics</h3>", 
        unsafe_allow_html=True
    )
    
    # Generate more comprehensive sample data
    def generate_sample_data():
        dates = pd.date_range(start="2025-12-01", end="2026-03-15")
        zones = ['Zone A', 'Zone B', 'Zone C', 'Zone D']
        
        data = {
            "Date": np.random.choice(dates, 500),
            "Zone": np.random.choice(zones, 500),
            "Violation_Type": np.random.choice(["No Helmet", "Triple Seat", "Speeding", "Wrong Lane"], 500, p=[0.4, 0.3, 0.2, 0.1]),
            "Vehicle_Type": np.random.choice(["Motorcycle", "Car", "Truck", "Bicycle"], 500),
            "Severity": np.random.choice(["Low", "Medium", "High"], 500, p=[0.6, 0.3, 0.1])
        }
        
        df = pd.DataFrame(data)
        df['Count'] = 1
        df['Week'] = df['Date'].dt.isocalendar().week
        return df
    
    df = generate_sample_data()
    
    # Add date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", 
                                  value=datetime(2025, 12, 1), 
                                  min_value=datetime(2025, 12, 1), 
                                  max_value=datetime(2026, 3, 15))
    with col2:
        end_date = st.date_input("End Date", 
                                value=datetime(2026, 3, 15), 
                                min_value=datetime(2025, 12, 1), 
                                max_value=datetime(2026, 3, 15))
    
    # Filter data based on date selection
    filtered_df = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]
    
    # Add statistics with more meaningful metrics
    st.subheader("📊 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_detections = len(filtered_df)
        weekly_avg = len(df) / 12  # Approx 12 weeks in sample data
        change = ((total_detections / (weekly_avg * ((end_date - start_date).days / 7))) - 1) * 100
        st.metric("Total Detections", f"{total_detections:,}", f"{change:.1f}%")
    
    with col2:
        helmet_violations = len(filtered_df[filtered_df['Violation_Type'] == "No Helmet"])
        prev_period = len(df[(df['Date'].dt.date >= start_date - timedelta(days=30)) & 
                           (df['Date'].dt.date <= end_date - timedelta(days=30)) & 
                           (df['Violation_Type'] == "No Helmet")])
        change = ((helmet_violations / prev_period) - 1) * 100 if prev_period > 0 else 0
        st.metric("Helmet Violations", f"{helmet_violations:,}", f"{change:.1f}%")
    
    with col3:
        vehicles_detected = filtered_df['Vehicle_Type'].nunique()
        st.metric("Vehicle Types Detected", vehicles_detected)
    
    with col4:
        high_severity = len(filtered_df[filtered_df['Severity'] == "High"])
        st.metric("High Severity Incidents", high_severity, help="Potentially dangerous violations")
    
    # First row of charts
    st.subheader("📈 Trend Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Weekly violations trend
        weekly_data = filtered_df.groupby(['Week', 'Violation_Type']).size().unstack().fillna(0)
        fig = px.area(weekly_data, 
                     title="Weekly Violations Trend",
                     labels={'value': 'Count', 'Week': 'Week Number'},
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=True, legend_title_text='Violation Type')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Violation by zone
        zone_data = filtered_df.groupby(['Zone', 'Violation_Type']).size().unstack().fillna(0)
        fig = px.bar(zone_data, 
                    title="Violations by Zone",
                    barmode='stack',
                    labels={'value': 'Count', 'Zone': 'Monitoring Zone'},
                    color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=True, legend_title_text='Violation Type')
        st.plotly_chart(fig, use_container_width=True)
    
    # Second row of charts
    st.subheader("🔍 Detailed Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Severity distribution
        severity_data = filtered_df.groupby(['Severity', 'Violation_Type']).size().reset_index(name='Count')
        fig = px.sunburst(severity_data, 
                         path=['Severity', 'Violation_Type'], 
                         values='Count',
                         title="Violation Severity Distribution",
                         color_discrete_sequence=px.colors.sequential.Plasma)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Vehicle type analysis
        vehicle_data = filtered_df.groupby(['Vehicle_Type', 'Violation_Type']).size().unstack().fillna(0)
        fig = px.pie(vehicle_data, 
                    values=vehicle_data.sum(axis=1), 
                    names=vehicle_data.index,
                    title="Violations by Vehicle Type",
                    hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    
    # Add a heatmap of violations by day of week and hour
    st.subheader("🕒 Temporal Patterns")
    filtered_df['DayOfWeek'] = filtered_df['Date'].dt.day_name()
    filtered_df['Hour'] = filtered_df['Date'].dt.hour
    heatmap_data = filtered_df.groupby(['DayOfWeek', 'Hour']).size().unstack().fillna(0)
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex(days_order)
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='Viridis',
        colorbar_title="Violations Count"
    ))
    
    fig.update_layout(
        title="Violations by Day of Week and Hour",
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add raw data table with filters
    st.subheader("🔎 Detailed Records")
    violation_filter = st.multiselect(
        "Filter by Violation Type",
        options=df['Violation_Type'].unique(),
        default=df['Violation_Type'].unique()
    )
    
    severity_filter = st.multiselect(
        "Filter by Severity",
        options=df['Severity'].unique(),
        default=df['Severity'].unique()
    )
    
    filtered_table = filtered_df[
        (filtered_df['Violation_Type'].isin(violation_filter)) &
        (filtered_df['Severity'].isin(severity_filter))
    ]
    
    st.dataframe(filtered_table.sort_values('Date', ascending=False).head(100))

# Run the dashboard
if __name__ == "__main__":
    dashboard_tab()