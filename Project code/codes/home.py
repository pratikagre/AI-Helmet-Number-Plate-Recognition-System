import streamlit as st

def home_tab():
    st.title("🚦 Real-Time Traffic Map 🌍")

    # Define the HTML for Waze Live Traffic Map
    map_html = """
    <iframe src="https://embed.waze.com/iframe?zoom=13&lat=18.5204&lon=73.8567&ct=livemap" 
            width="100%" 
            height="600" 
            style="border:0;" 
            allowfullscreen>
    </iframe>
    """

    # Button to show map
    if st.button("📍 Show Real-Time Traffic Map"):
        st.components.v1.html(map_html, height=620)
