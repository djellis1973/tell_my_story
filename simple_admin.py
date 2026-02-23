import streamlit as st
import json
from pathlib import Path
import hashlib

st.set_page_config(page_title="Simple User Admin", page_icon="👤")

# Use secrets for admin login
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == st.secrets["ADMIN_USERNAME"] and password == st.secrets["ADMIN_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong username or password")
    st.stop()

st.title("👤 User Management")

# Load all users
accounts_dir = Path("accounts")
if not accounts_dir.exists():
    st.error("No accounts folder found")
    st.stop()

users = []
for account_file in accounts_dir.glob("*_account.json"):
    with open(account_file) as f:
        account = json.load(f)
    
    users.append({
        "file": account_file,
        "email": account.get("email", "unknown"),
        "name": f"{account.get('profile', {}).get('first_name', '')} {account.get('profile', {}).get('last_name', '')}",
        "created": account.get("created_at", "unknown")[:10],
        "last_login": account.get("last_login", "never")[:10] if account.get("last_login") else "never",
        "id": account.get("user_id", "")
    })

# Show users
for user in users:
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
    with col1:
        st.write(f"**{user['email']}**")
    with col2:
        st.write(user['name'])
    with col3:
        st.write(f"📅 {user['created']}")
    with col4:
        st.write(f"🔑 {user['last_login']}")
    with col5:
        if st.button("🗑️ Delete", key=user['id']):
            # Delete account file
            user['file'].unlink()
            # Also delete their data file
            data_file = Path(f"user_data_{hashlib.md5(user['id'].encode()).hexdigest()[:8]}.json")
            if data_file.exists():
                data_file.unlink()
            st.success(f"Deleted {user['email']}")
            st.rerun()
    st.divider()

st.write(f"**Total users: {len(users)}**")
