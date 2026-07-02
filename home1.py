import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def home_tab(conn=None):
    """Interactive Home Page with Overview, System Info, and Traffic Map"""
    st.title("🚦 Safety Vision AI Dashboard")
    
    # Custom CSS styling
    st.markdown("""
    <style>
        .hero {
            background: linear-gradient(135deg, #0078ff 0%, #00c6ff 100%);
            padding: 2rem;
            border-radius: 10px;
            color: white;
            margin-bottom: 2rem;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .plot-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .tab-content {
            padding: 1rem 0;
        }
        .stButton>button {
            background: linear-gradient(135deg, #0078ff 0%, #00c6ff 100%);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero">
        <h2>Intelligent Traffic Safety Monitoring System</h2>
        <p>Real-time helmet detection, traffic monitoring, and violation analytics powered by AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["🏠 Overview", "📊 System Analytics", "🌍 Traffic Map"])
    
    with tab1:
        # Features Section
        st.subheader("✨ Key Features")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="card">
                <h4>🚦 Real-time Detection</h4>
                <p>Instant identification of helmets, number plates, and vehicles using advanced AI</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="card">
                <h4>📊 Comprehensive Analytics</h4>
                <p>Detailed dashboards with trends, patterns, and compliance metrics</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="card">
                <h4>🌍 Live Traffic Monitoring</h4>
                <p>Interactive map showing real-time traffic conditions and hotspots</p>
            </div>
            """, unsafe_allow_html=True)
        
        # How It Works Section
        st.subheader("⚙️ How It Works")
        st.markdown("""
        <div class="plot-container">
            <div style="display: flex; justify-content: center;">
                <img src="https://via.placeholder.com/800x300?text=System+Architecture+Diagram" 
                     style="border-radius: 8px; max-width: 100%;">
            </div>
            <ol style="margin-top: 1rem; padding-left: 1.5rem;">
                <li>AI models process live camera feeds to detect vehicles and safety equipment</li>
                <li>Detection data is analyzed for compliance with safety regulations</li>
                <li>Real-time alerts are generated for violations</li>
                <li>All data is stored for historical analysis and reporting</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    with tab2:
        if conn is not None:
            # System Status
            st.subheader("🖥️ System Status")
            
            try:
                record_count = pd.read_sql("SELECT COUNT(*) FROM detection_records", conn).iloc[0,0]
                last_record = pd.read_sql("SELECT MAX(timestamp) FROM detection_records", conn).iloc[0,0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div class="card">
                        <h4>Database Records</h4>
                        <p style="font-size: 24px; font-weight: bold; color: #00c6ff;">{record_count:,}</p>
                        <p>Total detection events stored</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="card">
                        <h4>Last Detection</h4>
                        <p style="font-size: 24px; font-weight: bold; color: #00c6ff;">{last_record or 'Never'}</p>
                        <p>Most recent detection timestamp</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Sample data visualization
                if record_count > 0:
                    st.subheader("📈 Recent Activity")
                    st.markdown('<div class="plot-container">', unsafe_allow_html=True)
                    
                    # Get last 30 days of data
                    query = """
                    SELECT 
                        date(timestamp) as date,
                        COUNT(*) as detections,
                        SUM(CASE WHEN helmet_detected = 1 THEN 1 ELSE 0 END) as compliant_detections,
                        SUM(CASE WHEN helmet_detected = 0 THEN 1 ELSE 0 END) as violations,
                        AVG(vehicle_count) as avg_vehicles,
                        AVG(helmet_detected) * 100 as compliance_rate
                    FROM detection_records
                    WHERE date(timestamp) >= date('now', '-30 days')
                    GROUP BY date(timestamp)
                    ORDER BY date(timestamp)
                    """
                    
                    df = pd.read_sql(query, conn)
                    
                    if not df.empty:
                        # Convert date column to datetime
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # Create tabs for different visualizations
                        subtab1, subtab2, subtab3 = st.tabs(["Detection Trends", "Compliance Analysis", "Vehicle Statistics"])
                        
                        with subtab1:
                            # Detection trends chart
                            fig = px.area(
                                df,
                                x='date',
                                y='detections',
                                title='Daily Detections (Last 30 Days)',
                                labels={'date': 'Date', 'detections': 'Number of Detections'},
                                color_discrete_sequence=['#00c6ff']
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                                yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with subtab2:
                            # Compliance chart
                            fig = px.bar(
                                df,
                                x='date',
                                y=['compliant_detections', 'violations'],
                                title='Helmet Compliance (Last 30 Days)',
                                labels={'date': 'Date', 'value': 'Count'},
                                color_discrete_sequence=['#00b894', '#ff7675']
                            )
                            fig.update_layout(
                                barmode='stack',
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'),
                                legend_title_text='Detection Type',
                                xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                                yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with subtab3:
                            # Vehicle statistics
                            col1, col2 = st.columns(2)
                            with col1:
                                fig = px.bar(
                                    df,
                                    x='date',
                                    y='avg_vehicles',
                                    title='Average Vehicles per Detection',
                                    labels={'date': 'Date', 'avg_vehicles': 'Average Vehicles'},
                                    color_discrete_sequence=['#0078ff']
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'),
                                    xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                                    yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with col2:
                                fig = px.line(
                                    df,
                                    x='date',
                                    y='compliance_rate',
                                    title='Helmet Compliance Rate (%)',
                                    labels={'date': 'Date', 'compliance_rate': 'Compliance Rate'},
                                    color_discrete_sequence=['#00c6ff']
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'),
                                    xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                                    yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
                                )
                                st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error loading database information: {str(e)}")
        else:
            st.warning("Database connection not available. System analytics disabled.")
    
    with tab3:
        st.subheader("🌍 Real-Time Traffic Map")
        
        # Map configuration
        default_lat = 18.5204  # Pune coordinates as default
        default_lng = 73.8567
        default_zoom = 12
        
        # User inputs for map customization
        col1, col2, col3 = st.columns(3)
        with col1:
            lat = st.number_input("Latitude", value=default_lat, format="%.6f")
        with col2:
            lng = st.number_input("Longitude", value=default_lng, format="%.6f")
        with col3:
            zoom = st.slider("Zoom Level", 1, 20, default_zoom)
        
        # Traffic layer toggle
        show_traffic = st.checkbox("Show Traffic Layer", value=True)
        show_bikelanes = st.checkbox("Highlight Bike Lanes", value=False)
        
        # Define the HTML & JavaScript for Google Maps with Traffic Layer
        GOOGLE_MAPS_API_KEY = "AIzaSyCbtZPl3LCWSldzcZT7UykJ_nDhf4SjQ6w"
        
        map_html = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap" async defer></script>
            <script>
              function initMap() {{
                var map = new google.maps.Map(document.getElementById('map'), {{
                  center: {{ lat: {lat}, lng: {lng} }},
                  zoom: {zoom}
                }});
                
                {f"var trafficLayer = new google.maps.TrafficLayer(); trafficLayer.setMap(map);" if show_traffic else ""}
                
                {f"""
                var bikeLayer = new google.maps.BicyclingLayer();
                bikeLayer.setMap(map);
                """ if show_bikelanes else ""}
              }}
            </script>
            <style>
              #map {{
                height: 600px;
                width: 100%;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
              }}
            </style>
          </head>
          <body onload="initMap()">
            <div id="map"></div>
          </body>
        </html>
        """
        
        # Display the map
        st.components.v1.html(map_html, height=620)
        
        # Map controls info
        st.markdown("""
        <div class="card">
            <h4>Map Controls</h4>
            <ul>
                <li><strong>Drag</strong> to pan the map</li>
                <li><strong>Scroll</strong> to zoom in/out</li>
                <li><strong>Click</strong> on any location to center the map</li>
                <li>Use the controls above to customize the view</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    home_tab()