import streamlit as st
import random

# ---- Page Config ----
st.set_page_config(page_title="Emoji Popups", layout="wide")

# ---- Generate Falling Emojis ----
emojis = ["❄️", "🎈", "🎊", "🎉", "💖", "🍂"]  # Customize the emojis

emoji_styles = ""
for i in range(20):  # Adjust the number of falling emojis
    emoji = random.choice(emojis)
    left_position = random.randint(0, 100)  # Random horizontal position
    duration = round(random.uniform(3, 8), 2)  # Random falling speed
    emoji_styles += f"""
    <div class="emoji" style="left: {left_position}vw; animation-duration: {duration}s;">
        {emoji}
    </div>
    """

# ---- Custom CSS for Falling Emojis ----
custom_css = f"""
<style>
@keyframes fall {{
    0% {{ transform: translateY(-100vh); opacity: 1; }}
    100% {{ transform: translateY(100vh); opacity: 0; }}
}}

.emoji {{
    position: fixed;
    top: -10vh;
    font-size: 2.5rem;
    opacity: 0.8;
    animation: fall linear infinite;
}}

{emoji_styles}
</style>
"""

# ---- Display Effect on Website ----
st.markdown(custom_css, unsafe_allow_html=True)

# ---- Main Content ----
st.title("🎈 Falling Emojis Effect in Streamlit 🎊")
st.write("Enjoy the floating emojis effect with snow, balloons, confetti, and more!")

# Toast messages for additional effect
st.toast("❄️ Snowfall effect activated!", icon="🌨️")
st.toast("🎈 Balloons floating up!", icon="🎉")
st.toast("💖 Love and confetti dropping!", icon="💖")
