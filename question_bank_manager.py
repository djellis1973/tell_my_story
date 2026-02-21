# question_bank_manager.py - THE WORKING VERSION
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import uuid

class QuestionBankManager:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.base_path = "question_banks"
        self.default_banks_path = f"{self.base_path}/default"
        self.user_banks_path = f"{self.base_path}/users"
        
        # Create directories
        os.makedirs(self.default_banks_path, exist_ok=True)
        os.makedirs(self.user_banks_path, exist_ok=True)
        if self.user_id:
            os.makedirs(f"{self.user_banks_path}/{self.user_id}", exist_ok=True)
    
    def load_sessions_from_csv(self, csv_path):
        try:
            df = pd.read_csv(csv_path)
            sessions = []
            
            for _, row in df.iterrows():
                session_id = int(row['session_id'])
                
                session = next((s for s in sessions if s['id'] == session_id), None)
                if not session:
                    session = {
                        'id': session_id,
                        'title': str(row.get('title', f'Session {session_id}')),
                        'guidance': str(row.get('guidance', '')) if pd.notna(row.get('guidance', '')) else '',
                        'questions': [],
                        'word_target': int(row.get('word_target', 500)) if pd.notna(row.get('word_target', 500)) else 500
                    }
                    sessions.append(session)
                
                if pd.notna(row['question']):
                    session['questions'].append(str(row['question']).strip())
            
            return sorted(sessions, key=lambda x: x['id'])
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
            return []
    
    def get_default_banks(self):
        banks = []
        if os.path.exists(self.default_banks_path):
            for filename in os.listdir(self.default_banks_path):
                if filename.endswith('.csv'):
                    bank_id = filename.replace('.csv', '')
                    name_parts = bank_id.replace('_', ' ').title()
                    
                    try:
                        df = pd.read_csv(f"{self.default_banks_path}/{filename}")
                        sessions = df['session_id'].nunique()
                        topics = len(df)
                        
                        banks.append({
                            "id": bank_id,
                            "name": f"📖 {name_parts}",
                            "description": f"{sessions} sessions • {topics} topics",
                            "sessions": sessions,
                            "topics": topics,
                            "filename": filename
                        })
                    except Exception as e:
                        st.error(f"Error reading {filename}: {e}")
        return banks
    
    def load_default_bank(self, bank_id):
        filename = f"{self.default_banks_path}/{bank_id}.csv"
        if os.path.exists(filename):
            return self.load_sessions_from_csv(filename)
        return []
    
    def get_user_banks(self):
        if not self.user_id:
            return []
        
        catalog_file = f"{self.user_banks_path}/{self.user_id}/catalog.json"
        if os.path.exists(catalog_file):
            with open(catalog_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_user_banks(self, banks):
        if not self.user_id:
            return
        catalog_file = f"{self.user_banks_path}/{self.user_id}/catalog.json"
        with open(catalog_file, 'w') as f:
            json.dump(banks, f, indent=2)
    
    def create_custom_bank(self, name, description="", copy_from=None):
        if not self.user_id:
            st.error("You must be logged in")
            return None
        
        user_dir = f"{self.user_banks_path}/{self.user_id}"
        os.makedirs(user_dir, exist_ok=True)
        
        bank_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        sessions = []
        if copy_from:
            sessions = self.load_default_bank(copy_from)
        
        bank_file = f"{user_dir}/{bank_id}.json"
        with open(bank_file, 'w') as f:
            json.dump({
                'id': bank_id,
                'name': name,
                'description': description,
                'created_at': now,
                'updated_at': now,
                'sessions': sessions
            }, f, indent=2)
        
        banks = self.get_user_banks()
        banks.append({
            'id': bank_id,
            'name': name,
            'description': description,
            'created_at': now,
            'updated_at': now,
            'session_count': len(sessions),
            'topic_count': sum(len(s.get('questions', [])) for s in sessions)
        })
        self._save_user_banks(banks)
        
        st.success(f"✅ Bank '{name}' created!")
        st.session_state.editing_bank_id = bank_id
        st.session_state.editing_bank_name = name
        st.session_state.show_bank_editor = True
        st.rerun()
        
        return bank_id
    
    def load_user_bank(self, bank_id):
        if not self.user_id:
            return []
        
        bank_file = f"{self.user_banks_path}/{self.user_id}/{bank_id}.json"
        if os.path.exists(bank_file):
            with open(bank_file, 'r') as f:
                data = json.load(f)
                return data.get('sessions', [])
        return []
    
    def delete_user_bank(self, bank_id):
        if not self.user_id:
            return False
        
        bank_file = f"{self.user_banks_path}/{self.user_id}/{bank_id}.json"
        if os.path.exists(bank_file):
            os.remove(bank_file)
        
        banks = self.get_user_banks()
        banks = [b for b in banks if b['id'] != bank_id]
        self._save_user_banks(banks)
        return True
    
    def export_user_bank_to_csv(self, bank_id):
        sessions = self.load_user_bank(bank_id)
        rows = []
        for session in sessions:
            for i, q in enumerate(session.get('questions', [])):
                rows.append({
                    'session_id': session['id'],
                    'title': session['title'],
                    'guidance': session.get('guidance', '') if i == 0 else '',
                    'question': q,
                    'word_target': session.get('word_target', 500)
                })
        if rows:
            df = pd.DataFrame(rows)
            return df.to_csv(index=False)
        return None
    
    def save_user_bank(self, bank_id, sessions):
        if not self.user_id:
            return False
        
        bank_file = f"{self.user_banks_path}/{self.user_id}/{bank_id}.json"
        if os.path.exists(bank_file):
            with open(bank_file, 'r') as f:
                data = json.load(f)
            data['sessions'] = sessions
            data['updated_at'] = datetime.now().isoformat()
            with open(bank_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            banks = self.get_user_banks()
            for bank in banks:
                if bank['id'] == bank_id:
                    bank['updated_at'] = datetime.now().isoformat()
                    bank['session_count'] = len(sessions)
                    bank['topic_count'] = sum(len(s.get('questions', [])) for s in sessions)
                    break
            self._save_user_banks(banks)
            return True
        return False
    
    def display_bank_selector(self):
        st.title("📚 Question Bank Manager")
        
        tab1, tab2, tab3 = st.tabs(["📖 Default Banks", "✨ My Custom Banks", "➕ Create New"])
        
        with tab1:
            self._display_default_banks()
        
        with tab2:
            if self.user_id:
                self._display_my_banks()
            else:
                st.info("🔐 Please log in")
        
        with tab3:
            if self.user_id:
                self._display_create_bank_form()
            else:
                st.info("🔐 Please log in")
    
    def _display_default_banks(self):
        banks = self.get_default_banks()
        if not banks:
            st.info("No default banks found")
            return
        
        for bank in banks:
            with st.container():
                st.markdown(f"**{bank['name']}**")
                st.caption(bank['description'])
                if st.button("📂 Load", key=f"load_default_{bank['id']}"):
                    sessions = self.load_default_bank(bank['id'])
                    if sessions:
                        st.session_state.current_question_bank = sessions
                        st.session_state.current_bank_name = bank['name']
                        st.session_state.current_bank_id = bank['id']
                        st.success(f"✅ Loaded '{bank['name']}'")
                        st.rerun()
                st.divider()
    
    def _display_my_banks(self):
        banks = self.get_user_banks()
        if not banks:
            st.info("✨ No custom banks yet. Create one in the 'Create New' tab!")
            return
        
        for bank in banks:
            with st.expander(f"📚 {bank['name']}", expanded=False):
                st.write(f"**Description:** {bank.get('description', 'No description')}")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Sessions", bank.get('session_count', 0))
                with col2:
                    st.metric("Topics", bank.get('topic_count', 0))
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("📂 Load", key=f"load_user_{bank['id']}"):
                        sessions = self.load_user_bank(bank['id'])
                        if sessions:
                            st.session_state.current_question_bank = sessions
                            st.session_state.current_bank_name = bank['name']
                            st.session_state.current_bank_id = bank['id']
                            st.success(f"✅ Loaded '{bank['name']}'")
                            st.rerun()
                
                with col2:
                    if st.button("✏️ Edit", key=f"edit_user_{bank['id']}"):
                        st.session_state.editing_bank_id = bank['id']
                        st.session_state.editing_bank_name = bank['name']
                        st.session_state.show_bank_editor = True
                        st.rerun()
                
                with col3:
                    csv_data = self.export_user_bank_to_csv(bank['id'])
                    if csv_data:
                        st.download_button("📥 CSV", data=csv_data, 
                                         file_name=f"{bank['name']}.csv", 
                                         mime="text/csv", key=f"csv_{bank['id']}")
                    else:
                        st.button("📥 No Data", disabled=True, key=f"nodata_{bank['id']}")
                
                with col4:
                    if st.button("🗑️ Delete", key=f"del_user_{bank['id']}"):
                        if self.delete_user_bank(bank['id']):
                            st.success(f"✅ Deleted '{bank['name']}'")
                            st.rerun()
    
    def _display_create_bank_form(self):
        with st.form("create_bank_form"):
            name = st.text_input("Bank Name *")
            description = st.text_area("Description")
            
            default_banks = self.get_default_banks()
            options = ["-- Start from scratch --"] + [b['name'] for b in default_banks]
            selected = st.selectbox("Copy from template:", options)
            
            if st.form_submit_button("✅ Create Bank", type="primary"):
                if name.strip():
                    copy_from = None
                    if selected != "-- Start from scratch --":
                        for bank in default_banks:
                            if bank['name'] == selected:
                                copy_from = bank['id']
                                break
                    self.create_custom_bank(name, description, copy_from)
                else:
                    st.error("Please enter a bank name")
    
    def display_bank_editor(self, bank_id):
        st.title(f"✏️ Edit Bank")
        
        sessions = self.load_user_bank(bank_id)
        bank_info = next((b for b in self.get_user_banks() if b['id'] == bank_id), {})
        
        with st.expander("Bank Settings", expanded=True):
            new_name = st.text_input("Bank Name", value=bank_info.get('name', ''))
            new_desc = st.text_area("Description", value=bank_info.get('description', ''))
            if st.button("💾 Save Settings"):
                banks = self.get_user_banks()
                for bank in banks:
                    if bank['id'] == bank_id:
                        bank['name'] = new_name
                        bank['description'] = new_desc
                self._save_user_banks(banks)
                st.success("✅ Settings saved")
                st.rerun()
        
        st.divider()
        st.subheader("📋 Sessions")
        
        if not sessions:
            st.info("👋 No sessions yet. Click below to add your first session!")
        
        if st.button("➕ Add New Session", type="primary"):
            max_id = max([s['id'] for s in sessions], default=0)
            sessions.append({
                'id': max_id + 1,
                'title': 'New Session',
                'guidance': '',
                'questions': [],
                'word_target': 500
            })
            self.save_user_bank(bank_id, sessions)
            st.rerun()
        
        for i, session in enumerate(sessions):
            with st.expander(f"📁 Session {session['id']}: {session['title']}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    new_title = st.text_input("Title", session['title'], key=f"title_{session['id']}")
                    new_guidance = st.text_area("Guidance", session.get('guidance', ''), 
                                               key=f"guidance_{session['id']}", height=100)
                    new_target = st.number_input("Word Target", value=session.get('word_target', 500),
                                               min_value=100, max_value=5000, step=100,
                                               key=f"target_{session['id']}")
                
                with col2:
                    st.write("**Actions**")
                    if i > 0:
                        if st.button("⬆️", key=f"up_{session['id']}"):
                            sessions[i], sessions[i-1] = sessions[i-1], sessions[i]
                            for idx, s in enumerate(sessions):
                                s['id'] = idx + 1
                            self.save_user_bank(bank_id, sessions)
                            st.rerun()
                    if i < len(sessions)-1:
                        if st.button("⬇️", key=f"down_{session['id']}"):
                            sessions[i], sessions[i+1] = sessions[i+1], sessions[i]
                            for idx, s in enumerate(sessions):
                                s['id'] = idx + 1
                            self.save_user_bank(bank_id, sessions)
                            st.rerun()
                    if st.button("💾 Save", key=f"save_{session['id']}"):
                        session['title'] = new_title
                        session['guidance'] = new_guidance
                        session['word_target'] = new_target
                        self.save_user_bank(bank_id, sessions)
                        st.success("✅ Saved")
                        st.rerun()
                    if st.button("🗑️", key=f"del_{session['id']}"):
                        sessions.pop(i)
                        for idx, s in enumerate(sessions):
                            s['id'] = idx + 1
                        self.save_user_bank(bank_id, sessions)
                        st.rerun()
                
                st.divider()
                st.write("**Topics/Questions:**")
                
                new_topic = st.text_input("Add new topic", key=f"new_topic_{session['id']}")
                if new_topic:
                    if st.button("➕ Add", key=f"add_topic_{session['id']}"):
                        session['questions'].append(new_topic)
                        self.save_user_bank(bank_id, sessions)
                        st.rerun()
                
                for j, topic in enumerate(session.get('questions', [])):
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.text(f"{j+1}. {topic}")
                    with col2:
                        if st.button("🗑️", key=f"del_q_{session['id']}_{j}"):
                            session['questions'].pop(j)
                            self.save_user_bank(bank_id, sessions)
                            st.rerun()
        
        if st.button("🔙 Back to Bank Manager"):
            st.session_state.show_bank_editor = False
            st.rerun()
