import streamlit as st
import json
from datetime import datetime
import pandas as pd
from pathlib import Path
import re
import hashlib

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Tell My Story - Admin Dashboard",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SIMPLE ADMIN AUTH - Use secrets in Streamlit Cloud
# ============================================================================
# Add these to your Streamlit Community Cloud secrets:
# ADMIN_USERNAME = admin
# ADMIN_PASSWORD = your-secure-password
# ADMIN_SECRET_KEY = your-secret-key

def check_admin_password():
    """Simple password check for admin access"""
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("👑 Admin Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login", type="primary", use_container_width=True):
                # Check against secrets
                if (username == st.secrets.get("ADMIN_USERNAME") and 
                    password == st.secrets.get("ADMIN_PASSWORD")):
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return False
    return True

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================
def load_all_users():
    """Load all user accounts from the accounts folder"""
    accounts_dir = Path("accounts")
    if not accounts_dir.exists():
        return []
    
    users = []
    for account_file in accounts_dir.glob("*_account.json"):
        try:
            with open(account_file, 'r') as f:
                account = json.load(f)
            
            # Load user data file for stats
            user_id = account['user_id']
            data_file = Path(f"user_data_{hashlib.md5(user_id.encode()).hexdigest()[:8]}.json")
            
            stats = {
                'total_words': 0,
                'total_answers': 0,
                'total_sessions': 0,
                'last_active': None
            }
            
            if data_file.exists():
                with open(data_file, 'r') as f:
                    user_data = json.load(f)
                    
                # Calculate stats
                for session_id, session_data in user_data.get('responses', {}).items():
                    answers = session_data.get('questions', {})
                    stats['total_answers'] += len(answers)
                    for q_data in answers.values():
                        if q_data.get('answer'):
                            text_only = re.sub(r'<[^>]+>', '', q_data['answer'])
                            stats['total_words'] += len(re.findall(r'\w+', text_only))
                    
                    # Get last active
                    timestamps = [q.get('timestamp') for q in answers.values() if q.get('timestamp')]
                    if timestamps:
                        latest = max(timestamps)
                        if not stats['last_active'] or latest > stats['last_active']:
                            stats['last_active'] = latest
            
            # Combine account and stats
            users.append({
                'user_id': user_id,
                'email': account.get('email', ''),
                'first_name': account.get('profile', {}).get('first_name', ''),
                'last_name': account.get('profile', {}).get('last_name', ''),
                'created_at': account.get('created_at', ''),
                'last_login': account.get('last_login', ''),
                'subscription': account.get('subscription', {'status': 'free'}),
                'total_words': stats['total_words'],
                'total_answers': stats['total_answers'],
                'last_active': stats['last_active'],
                'account_data': account
            })
        except Exception as e:
            st.error(f"Error loading {account_file}: {e}")
    
    # Sort by creation date
    users.sort(key=lambda x: x['created_at'], reverse=True)
    return users

def save_user_subscription(user_id, subscription_data):
    """Update a user's subscription status"""
    try:
        account_file = Path(f"accounts/{user_id}_account.json")
        if account_file.exists():
            with open(account_file, 'r') as f:
                account = json.load(f)
            
            account['subscription'] = subscription_data
            account['subscription']['last_updated'] = datetime.now().isoformat()
            
            with open(account_file, 'w') as f:
                json.dump(account, f, indent=2)
            
            return True
    except Exception as e:
        st.error(f"Error saving: {e}")
    return False

# ============================================================================
# MAIN ADMIN INTERFACE
# ============================================================================
if not check_admin_password():
    st.stop()

# Custom CSS
st.markdown("""
<style>
    .admin-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    .user-row {
        background: white;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .active-badge {
        background: #27ae60;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .free-badge {
        background: #95a5a6;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .expired-badge {
        background: #e74c3c;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="admin-header">
    <h1>👑 Tell My Story - Admin Dashboard</h1>
    <p>Manage users, subscriptions, and monitor usage</p>
</div>
""", unsafe_allow_html=True)

# Load all users
with st.spinner("Loading user data..."):
    users = load_all_users()

# Sidebar stats
with st.sidebar:
    st.title("📊 Quick Stats")
    
    total_users = len(users)
    active_subs = sum(1 for u in users if u['subscription'].get('status') == 'active')
    total_words = sum(u['total_words'] for u in users)
    
    st.metric("Total Users", total_users)
    st.metric("Active Subscriptions", active_subs)
    st.metric("Total Words", f"{total_words:,}")
    
    st.divider()
    
    st.markdown("### 🔍 Quick Filters")
    show_active = st.checkbox("Show only active subscriptions")
    show_free = st.checkbox("Show only free users")
    
    st.divider()
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.rerun()

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 User Management", 
    "📈 Analytics", 
    "➕ Add/Edit User",
    "⚙️ Settings"
])

with tab1:
    st.header("User Management")
    
    # Search
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search by email or name", placeholder="Type to filter...")
    with col2:
        sort_by = st.selectbox("Sort by", ["Newest", "Oldest", "Most Active", "Most Words"])
    
    # Filter users
    filtered_users = users.copy()
    
    if search:
        search_lower = search.lower()
        filtered_users = [
            u for u in filtered_users 
            if search_lower in u['email'].lower() or 
               search_lower in f"{u['first_name']} {u['last_name']}".lower()
        ]
    
    if show_active:
        filtered_users = [u for u in filtered_users if u['subscription'].get('status') == 'active']
    
    if show_free:
        filtered_users = [u for u in filtered_users if u['subscription'].get('status') == 'free']
    
    # Sort
    if sort_by == "Newest":
        filtered_users.sort(key=lambda x: x['created_at'], reverse=True)
    elif sort_by == "Oldest":
        filtered_users.sort(key=lambda x: x['created_at'])
    elif sort_by == "Most Active":
        filtered_users.sort(key=lambda x: x['last_active'] or '', reverse=True)
    elif sort_by == "Most Words":
        filtered_users.sort(key=lambda x: x['total_words'], reverse=True)
    
    st.info(f"Showing {len(filtered_users)} users")
    
    # User list
    for user in filtered_users:
        status = user['subscription'].get('status', 'free')
        
        # Status badge
        if status == 'active':
            badge = '<span class="active-badge">✅ ACTIVE</span>'
        elif status == 'free':
            badge = '<span class="free-badge">🆓 FREE</span>'
        else:
            badge = f'<span class="expired-badge">❌ {status.upper()}</span>'
        
        # Created date
        created = datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d') if user['created_at'] else 'Unknown'
        
        # Last active
        last_active = "Never"
        if user['last_active']:
            try:
                last_active = datetime.fromisoformat(user['last_active']).strftime('%Y-%m-%d %H:%M')
            except:
                last_active = user['last_active'][:16]
        
        with st.container():
            st.markdown(f"""
            <div class="user-row">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{user['email']}</strong> - {user['first_name']} {user['last_name']}
                        <br>
                        <small>📅 Joined: {created} | 🕐 Last: {last_active} | 📝 {user['total_words']:,} words</small>
                    </div>
                    <div>
                        {badge}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
            with col1:
                if st.button("✏️ Edit", key=f"edit_{user['user_id']}"):
                    st.session_state['editing_user'] = user
                    st.rerun()
            with col2:
                if st.button("📊 Stats", key=f"stats_{user['user_id']}"):
                    st.session_state['viewing_stats'] = user
                    st.rerun()
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{user['user_id']}"):
                    st.session_state['deleting_user'] = user
                    st.rerun()
            
            st.markdown("---")
    
    # Edit user modal
    if 'editing_user' in st.session_state:
        user = st.session_state['editing_user']
        
        st.divider()
        st.subheader(f"✏️ Edit Subscription: {user['email']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_status = user['subscription'].get('status', 'free')
            new_status = st.selectbox(
                "Subscription Status",
                ["free", "active", "expired", "cancelled"],
                index=["free", "active", "expired", "cancelled"].index(current_status) 
                    if current_status in ["free", "active", "expired", "cancelled"] else 0,
                key=f"edit_status_{user['user_id']}"
            )
            
            if new_status == "active":
                expires = st.date_input(
                    "Expiration Date (optional)",
                    value=None,
                    key=f"edit_expires_{user['user_id']}"
                )
            else:
                expires = None
            
            tier = st.selectbox(
                "Tier",
                ["free", "premium", "lifetime"],
                index=["free", "premium", "lifetime"].index(user['subscription'].get('tier', 'free')),
                key=f"edit_tier_{user['user_id']}"
            )
            
            notes = st.text_area(
                "Notes",
                value=user['subscription'].get('notes', ''),
                key=f"edit_notes_{user['user_id']}"
            )
            
            if st.button("💾 Save Changes", key=f"save_edit_{user['user_id']}", type="primary"):
                subscription_data = {
                    "status": new_status,
                    "tier": tier,
                    "expires_at": expires.isoformat() if expires else None,
                    "notes": notes,
                    "last_updated": datetime.now().isoformat()
                }
                
                if save_user_subscription(user['user_id'], subscription_data):
                    st.success(f"✅ Updated subscription for {user['email']}")
                    del st.session_state['editing_user']
                    st.rerun()
        
        with col2:
            st.write("**Current Stats:**")
            st.write(f"Words: {user['total_words']:,}")
            st.write(f"Answers: {user['total_answers']}")
            st.write(f"Last Login: {user['last_login'][:16] if user['last_login'] else 'Never'}")
        
        if st.button("← Cancel", key=f"cancel_edit_{user['user_id']}"):
            del st.session_state['editing_user']
            st.rerun()
    
    # View stats modal
    if 'viewing_stats' in st.session_state:
        user = st.session_state['viewing_stats']
        
        st.divider()
        st.subheader(f"📊 Detailed Stats: {user['email']}")
        
        # Load full user data
        data_file = Path(f"user_data_{hashlib.md5(user['user_id'].encode()).hexdigest()[:8]}.json")
        if data_file.exists():
            with open(data_file, 'r') as f:
                user_data = json.load(f)
            
            # Session breakdown
            sessions_data = []
            for session_id, session in user_data.get('responses', {}).items():
                sessions_data.append({
                    'Session': session.get('title', f'Session {session_id}'),
                    'Answers': len(session.get('questions', {})),
                    'Words': sum(len(re.sub(r'<[^>]+>', '', q.get('answer', '')).split()) 
                                for q in session.get('questions', {}).values())
                })
            
            if sessions_data:
                df = pd.DataFrame(sessions_data)
                st.bar_chart(df.set_index('Session'))
        
        if st.button("← Back", key="back_from_stats"):
            del st.session_state['viewing_stats']
            st.rerun()
    
    # Delete confirmation
    if 'deleting_user' in st.session_state:
        user = st.session_state['deleting_user']
        
        st.warning(f"⚠️ Are you sure you want to delete {user['email']}? This cannot be undone!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete", key=f"confirm_delete_{user['user_id']}"):
                # Delete account file
                account_file = Path(f"accounts/{user['user_id']}_account.json")
                data_file = Path(f"user_data_{hashlib.md5(user['user_id'].encode()).hexdigest()[:8]}.json")
                
                if account_file.exists():
                    account_file.unlink()
                if data_file.exists():
                    data_file.unlink()
                
                st.success(f"User {user['email']} deleted")
                del st.session_state['deleting_user']
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel", key=f"cancel_delete_{user['user_id']}"):
                del st.session_state['deleting_user']
                st.rerun()

with tab2:
    st.header("Analytics Dashboard")
    
    if users:
        # Convert to DataFrame
        df = pd.DataFrame(users)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", len(df))
        with col2:
            active_count = len(df[df['subscription'].apply(lambda x: x.get('status') == 'active')])
            st.metric("Active Subscriptions", active_count)
        with col3:
            st.metric("Total Words", f"{df['total_words'].sum():,}")
        with col4:
            avg_words = df['total_words'].mean()
            st.metric("Avg Words/User", f"{avg_words:.0f}")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Subscription Status")
            status_counts = df['subscription'].apply(lambda x: x.get('status', 'free')).value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index, title="User Distribution")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("User Growth")
            df['created_date'] = pd.to_datetime(df['created_at']).dt.date
            growth = df.groupby('created_date').size().cumsum()
            st.line_chart(growth)
        
        # Top users
        st.subheader("Top Users by Words")
        top_users = df.nlargest(10, 'total_words')[['email', 'total_words', 'total_answers']]
        st.dataframe(top_users, use_container_width=True)
        
    else:
        st.info("No user data available")

with tab3:
    st.header("Add/Edit User")
    
    # Simple form to add a user manually
    with st.form("add_user_form"):
        st.subheader("Add New User")
        
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
            email = st.text_input("Email")
        with col2:
            last_name = st.text_input("Last Name")
            password = st.text_input("Password", type="password")
        
        st.subheader("Subscription Settings")
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Status", ["free", "active", "expired"])
        with col2:
            tier = st.selectbox("Tier", ["free", "premium", "lifetime"])
        
        notes = st.text_area("Notes")
        
        if st.form_submit_button("Create User", type="primary"):
            # Create user ID
            user_id = hashlib.sha256(f"{email}{datetime.now()}".encode()).hexdigest()[:12]
            
            # Create account data
            account = {
                "user_id": user_id,
                "email": email.lower(),
                "password_hash": hashlib.sha256(password.encode()).hexdigest(),
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "profile": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email
                },
                "subscription": {
                    "status": status,
                    "tier": tier,
                    "notes": notes,
                    "last_updated": datetime.now().isoformat()
                }
            }
            
            # Save account
            account_file = Path(f"accounts/{user_id}_account.json")
            account_file.parent.mkdir(exist_ok=True)
            with open(account_file, 'w') as f:
                json.dump(account, f, indent=2)
            
            # Create empty data file
            data_file = Path(f"user_data_{hashlib.md5(user_id.encode()).hexdigest()[:8]}.json")
            with open(data_file, 'w') as f:
                json.dump({"responses": {}}, f)
            
            st.success(f"✅ User created! User ID: {user_id}")
            st.balloons()

with tab4:
    st.header("Settings")
    
    st.subheader("Admin Settings")
    st.info("Configure these in your Streamlit Community Cloud secrets")
    
    st.code("""
    # .streamlit/secrets.toml
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "your-secure-password"
    ADMIN_SECRET_KEY = "your-secret-key"
    """)
    
    st.subheader("Email Configuration (Optional)")
    if st.button("Test Email Settings"):
        st.info("Email feature coming soon")
    
    st.subheader("Export Data")
    if st.button("Export All Users to CSV"):
        if users:
            df = pd.DataFrame(users)
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "users_export.csv",
                "text/csv"
            )
