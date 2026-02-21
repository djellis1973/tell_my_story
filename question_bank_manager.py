import streamlit as st

st.error("🔴🔴🔴 TEST FILE IS LOADING! 🔴🔴🔴")
st.info("If you can see this, the file is working!")

class TestManager:
    def __init__(self):
        st.write("✅ TestManager initialized!")
    
    def show_test(self):
        st.button("🔵 TEST BUTTON", key="test_btn")

st.write("--- END OF
