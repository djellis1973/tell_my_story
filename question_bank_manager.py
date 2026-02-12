# question_bank_manager.py - FIXED VERSION
"""
Question Bank Manager - Unified system for managing multiple question banks
Allows loading default QBs, creating custom QBs, and managing sessions/topics
"""
import streamlit as st
import pandas as pd
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

class QuestionBankManager:
    """
    Manages multiple question banks (both default and custom)
    Provides CRUD operations for sessions and topics within banks
    """
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.base_path = "question_banks"
        self.default_banks_path = f"{self.base_path}/default"
        self.user_banks_path = f"{self.base_path}/users"
        
        # Default banks catalog
        self.default_banks_catalog_file = f"{self.base_path}/default_banks_catalog.json"
        
        # Current active bank for this session
        self.current_bank = None
        self.current_bank_name = None
        self.current_bank_type = None  # 'default' or 'custom'
        
        self._ensure_directories()
        self._load_catalog()
        
    def _ensure_directories(self):
        """Create necessary directory structure"""
        os.makedirs(self.default_banks_path, exist_ok=True)
        if self.user_id:
            os.makedirs(f"{self.user_banks_path}/{self.user_id}", exist_ok=True)
        os.makedirs(self.base_path, exist_ok=True)
    
    def _load_catalog(self):
        """Load or create catalog of default banks"""
        if os.path.exists(self.default_banks_catalog_file):
            with open(self.default_banks_catalog_file, 'r') as f:
                self.default_catalog = json.load(f)
        else:
            # Initialize with default banks
            self.default_catalog = {
                "banks": [
                    {
                        "id": "life_story_comprehensive",
                        "name": "📖 Life Story - Comprehensive",
                        "filename": "life_story_comprehensive.csv",
                        "description": "Complete life story journey through 13 sessions",
                        "sessions": 13,
                        "topics": 71,
                        "created": "2026-01-01",
                        "is_default": True
                    },
                    {
                        "id": "quick_memories",
                        "name": "✨ Quick Memories - 5 Sessions",
                        "filename": "quick_memories.csv",
                        "description": "Shorter version focusing on key life moments",
                        "sessions": 5,
                        "topics": 25,
                        "created": "2026-01-01",
                        "is_default": True
                    },
                    {
                        "id": "family_heritage",
                        "name": "🏠 Family Heritage Focus",
                        "filename": "family_heritage.csv",
                        "description": "Deep dive into family history and traditions",
                        "sessions": 8,
                        "topics": 40,
                        "created": "2026-01-01",
                        "is_default": True
                    }
                ]
            }
            self._save_catalog()
            
            # Create default bank files if they don't exist
            self._create_default_bank_files()
    
    def _save_catalog(self):
        """Save the default banks catalog"""
        with open(self.default_banks_catalog_file, 'w') as f:
            json.dump(self.default_catalog, f, indent=2)
    
    def _create_default_bank_files(self):
        """Create the actual CSV files for default banks"""
        # Check if we have the main sessions.csv file
        if os.path.exists("sessions/sessions.csv"):
            dest_path = f"{self.default_banks_path}/life_story_comprehensive.csv"
            if not os.path.exists(dest_path):
                shutil.copy("sessions/sessions.csv", dest_path)
        
        # Create quick_memories.csv if it doesn't exist
        quick_path = f"{self.default_banks_path}/quick_memories.csv"
        if not os.path.exists(quick_path):
            quick_data = self._create_quick_memories_bank()
            df = pd.DataFrame(quick_data)
            df.to_csv(quick_path, index=False)
        
        # Create family_heritage.csv if it doesn't exist
        family_path = f"{self.default_banks_path}/family_heritage.csv"
        if not os.path.exists(family_path):
            family_data = self._create_family_heritage_bank()
            df = pd.DataFrame(family_data)
            df.to_csv(family_path, index=False)
    
    def _create_quick_memories_bank(self):
        """Create a shorter 5-session bank"""
        return [
            {"session_id": 1, "title": "Childhood Memories", "guidance": "Share your earliest memories...", 
             "question": "What is your happiest childhood memory?", "word_target": 600},
            {"session_id": 1, "title": "Childhood Memories", "guidance": "", 
             "question": "Who was your childhood hero?", "word_target": 600},
            {"session_id": 2, "title": "Family Traditions", "guidance": "Tell us about your family...", 
             "question": "What family tradition means most to you?", "word_target": 600},
            {"session_id": 2, "title": "Family Traditions", "guidance": "", 
             "question": "What lesson did your parents teach you?", "word_target": 600},
            {"session_id": 3, "title": "Career Journey", "guidance": "Your professional journey...", 
             "question": "What was your dream job as a child?", "word_target": 600},
            {"session_id": 3, "title": "Career Journey", "guidance": "", 
             "question": "What's your proudest work achievement?", "word_target": 600},
            {"session_id": 4, "title": "Love & Relationships", "guidance": "Share your story of connection...", 
             "question": "How did you meet your partner?", "word_target": 600},
            {"session_id": 4, "title": "Love & Relationships", "guidance": "", 
             "question": "What advice would you give about love?", "word_target": 600},
            {"session_id": 5, "title": "Life Wisdom", "guidance": "What life has taught you...", 
             "question": "What's the best advice you ever received?", "word_target": 600},
            {"session_id": 5, "title": "Life Wisdom", "guidance": "", 
             "question": "What do you hope your legacy will be?", "word_target": 600},
        ]
    
    def _create_family_heritage_bank(self):
        """Create a family-focused bank"""
        return [
            {"session_id": 1, "title": "Family Origins", "guidance": "Explore your roots...", 
             "question": "What do you know about your grandparents?", "word_target": 700},
            {"session_id": 1, "title": "Family Origins", "guidance": "", 
             "question": "Are there any family legends or stories passed down?", "word_target": 700},
            {"session_id": 2, "title": "Family Traditions", "guidance": "Celebrations and rituals...", 
             "question": "What holiday traditions did your family observe?", "word_target": 700},
            {"session_id": 2, "title": "Family Traditions", "guidance": "", 
             "question": "How did your family celebrate special occasions?", "word_target": 700},
            {"session_id": 3, "title": "Family Values", "guidance": "The principles that shaped you...", 
             "question": "What values did your family instill in you?", "word_target": 700},
            {"session_id": 3, "title": "Family Values", "guidance": "", 
             "question": "How have you passed these values to the next generation?", "word_target": 700},
            {"session_id": 4, "title": "Family Challenges", "guidance": "Overcoming together...", 
             "question": "What challenges did your family face together?", "word_target": 700},
            {"session_id": 4, "title": "Family Challenges", "guidance": "", 
             "question": "How did your family support each other during difficult times?", "word_target": 700},
            {"session_id": 5, "title": "Family Legacy", "guidance": "What you carry forward...", 
             "question": "What family heirlooms or stories are important to you?", "word_target": 700},
            {"session_id": 5, "title": "Family Legacy", "guidance": "", 
             "question": "How do you want your family to remember you?", "word_target": 700},
        ]
    
    def get_available_default_banks(self) -> List[Dict]:
        """Get list of all available default question banks"""
        return self.default_catalog["banks"]
    
    def load_default_bank(self, bank_id: str) -> List[Dict]:
        """Load a specific default bank by ID"""
        for bank in self.default_catalog["banks"]:
            if bank["id"] == bank_id:
                filepath = f"{self.default_banks_path}/{bank['filename']}"
                if os.path.exists(filepath):
                    sessions = self._load_sessions_from_csv(filepath)
                    self.current_bank = sessions
                    self.current_bank_name = bank["name"]
                    self.current_bank_type = "default"
                    self.current_bank_id = bank_id
                    return sessions
        return []
    
    def _load_sessions_from_csv(self, csv_path: str) -> List[Dict]:
        """Load sessions from a CSV file"""
        try:
            df = pd.read_csv(csv_path)
            sessions_dict = {}
            
            for session_id, group in df.groupby('session_id'):
                session_id_int = int(session_id)
                group = group.reset_index(drop=True)
                
                title = f"Session {session_id_int}"
                if 'title' in group.columns and not group.empty:
                    first_title = group.iloc[0]['title']
                    if pd.notna(first_title) and str(first_title).strip():
                        title = str(first_title).strip()
                
                guidance = ""
                if 'guidance' in group.columns and not group.empty:
                    first_guidance = group.iloc[0]['guidance']
                    if pd.notna(first_guidance) and str(first_guidance).strip():
                        guidance = str(first_guidance).strip()
                
                word_target = 500
                if 'word_target' in group.columns and not group.empty:
                    first_target = group.iloc[0]['word_target']
                    if pd.notna(first_target):
                        try:
                            word_target = int(float(first_target))
                        except:
                            word_target = 500
                
                questions = []
                for _, row in group.iterrows():
                    if 'question' in row and pd.notna(row['question']) and str(row['question']).strip():
                        questions.append(str(row['question']).strip())
                
                if questions:
                    sessions_dict[session_id_int] = {
                        "id": session_id_int,
                        "title": title,
                        "guidance": guidance,
                        "questions": questions,
                        "completed": False,
                        "word_target": word_target
                    }
            
            sessions_list = list(sessions_dict.values())
            sessions_list.sort(key=lambda x: x['id'])
            return sessions_list
            
        except Exception as e:
            st.error(f"Error loading sessions from {csv_path}: {e}")
            return []
    
    # ============ CUSTOM USER BANKS ============
    
    def get_user_banks(self) -> List[Dict]:
        """Get all custom banks created by the user"""
        if not self.user_id:
            return []
        
        user_banks_file = f"{self.user_banks_path}/{self.user_id}/banks_catalog.json"
        if os.path.exists(user_banks_file):
            with open(user_banks_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_user_banks(self, banks: List[Dict]):
        """Save user's custom banks catalog"""
        if not self.user_id:
            return
        
        user_banks_file = f"{self.user_banks_path}/{self.user_id}/banks_catalog.json"
        with open(user_banks_file, 'w') as f:
            json.dump(banks, f, indent=2)
    
    def create_custom_bank(self, name: str, description: str = "", copy_from_default: str = None) -> Dict:
        """Create a new custom question bank"""
        if not self.user_id:
            st.error("You must be logged in to create custom banks")
            return None
        
        bank_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        # Initialize sessions list
        sessions = []
        
        # If copying from default bank
        if copy_from_default:
            default_sessions = self.load_default_bank(copy_from_default)
            if default_sessions:
                sessions = default_sessions.copy()
        
        new_bank = {
            "id": bank_id,
            "name": name,
            "description": description,
            "created_at": timestamp,
            "updated_at": timestamp,
            "session_count": len(sessions),
            "topic_count": sum(len(s.get("questions", [])) for s in sessions),
            "is_custom": True
        }
        
        # Save the bank data
        bank_file = f"{self.user_banks_path}/{self.user_id}/{bank_id}.json"
        with open(bank_file, 'w') as f:
            json.dump({"sessions": sessions}, f, indent=2)
        
        # Update catalog
        user_banks = self.get_user_banks()
        user_banks.append(new_bank)
        self._save_user_banks(user_banks)
        
        return new_bank
    
    def load_user_bank(self, bank_id: str) -> List[Dict]:
        """Load a custom user bank"""
        if not self.user_id:
            return []
        
        bank_file = f"{self.user_banks_path}/{self.user_id}/{bank_id}.json"
        if os.path.exists(bank_file):
            with open(bank_file, 'r') as f:
                data = json.load(f)
                sessions = data.get("sessions", [])
                
                # Find bank info
                user_banks = self.get_user_banks()
                bank_info = next((b for b in user_banks if b["id"] == bank_id), {})
                
                self.current_bank = sessions
                self.current_bank_name = bank_info.get("name", "Custom Bank")
                self.current_bank_type = "custom"
                self.current_bank_id = bank_id
                
                return sessions
        return []
    
    def save_custom_bank(self, bank_id: str, sessions: List[Dict]):
        """Save changes to a custom bank"""
        if not self.user_id:
            return False
        
        bank_file = f"{self.user_banks_path}/{self.user_id}/{bank_id}.json"
        
        # Update timestamps and counts in catalog
        user_banks = self.get_user_banks()
        for bank in user_banks:
            if bank["id"] == bank_id:
                bank["updated_at"] = datetime.now().isoformat()
                bank["session_count"] = len(sessions)
                bank["topic_count"] = sum(len(s.get("questions", [])) for s in sessions)
                break
        self._save_user_banks(user_banks)
        
        # Save sessions
        with open(bank_file, 'w') as f:
            json.dump({"sessions": sessions}, f, indent=2)
        
        return True
    
    def delete_custom_bank(self, bank_id: str) -> bool:
        """Delete a custom bank"""
        if not self.user_id:
            return False
        
        # Delete bank file
        bank_file = f"{self.user_banks_path}/{self.user_id}/{bank_id}.json"
        if os.path.exists(bank_file):
            os.remove(bank_file)
        
        # Remove from catalog
        user_banks = self.get_user_banks()
        user_banks = [b for b in user_banks if b["id"] != bank_id]
        self._save_user_banks(user_banks)
        
        return True
    
    # ============ SESSION/TOPIC MANAGEMENT ============
    
    def add_session(self, sessions: List[Dict], title: str, 
                   guidance: str = "", word_target: int = 500) -> List[Dict]:
        """Add a new session to the current bank"""
        # Find max session ID
        max_id = 0
        for session in sessions:
            if session["id"] > max_id:
                max_id = session["id"]
        
        new_session = {
            "id": max_id + 1,
            "title": title,
            "guidance": guidance,
            "questions": [],
            "completed": False,
            "word_target": word_target
        }
        
        sessions.append(new_session)
        return sessions
    
    def update_session(self, sessions: List[Dict], session_id: int, 
                      updates: Dict) -> List[Dict]:
        """Update a session's properties"""
        for session in sessions:
            if session["id"] == session_id:
                session.update(updates)
                break
        return sessions
    
    def delete_session(self, sessions: List[Dict], session_id: int) -> List[Dict]:
        """Delete a session and renumber remaining sessions"""
        sessions = [s for s in sessions if s["id"] != session_id]
        
        # Renumber sessions sequentially
        for i, session in enumerate(sessions):
            session["id"] = i + 1
        
        return sessions
    
    def reorder_sessions(self, sessions: List[Dict], old_index: int, 
                        new_index: int) -> List[Dict]:
        """Reorder sessions in the bank"""
        if 0 <= old_index < len(sessions) and 0 <= new_index < len(sessions):
            session = sessions.pop(old_index)
            sessions.insert(new_index, session)
            
            # Renumber sessions
            for i, s in enumerate(sessions):
                s["id"] = i + 1
        
        return sessions
    
    def add_topic(self, sessions: List[Dict], session_id: int, 
                 question_text: str) -> List[Dict]:
        """Add a new topic/question to a session"""
        for session in sessions:
            if session["id"] == session_id:
                session["questions"].append(question_text)
                break
        return sessions
    
    def update_topic(self, sessions: List[Dict], session_id: int, 
                    topic_index: int, new_text: str) -> List[Dict]:
        """Update a topic/question"""
        for session in sessions:
            if session["id"] == session_id:
                if 0 <= topic_index < len(session["questions"]):
                    session["questions"][topic_index] = new_text
                break
        return sessions
    
    def delete_topic(self, sessions: List[Dict], session_id: int, 
                    topic_index: int) -> List[Dict]:
        """Delete a topic/question"""
        for session in sessions:
            if session["id"] == session_id:
                if 0 <= topic_index < len(session["questions"]):
                    session["questions"].pop(topic_index)
                break
        return sessions
    
    def reorder_topics(self, sessions: List[Dict], session_id: int,
                      old_index: int, new_index: int) -> List[Dict]:
        """Reorder topics within a session"""
        for session in sessions:
            if session["id"] == session_id:
                if 0 <= old_index < len(session["questions"]) and 0 <= new_index < len(session["questions"]):
                    topic = session["questions"].pop(old_index)
                    session["questions"].insert(new_index, topic)
                break
        return sessions
    
    # ============ UI COMPONENTS ============
    
    def display_bank_selector(self):
        """Display UI for selecting/creating question banks"""
        st.subheader("📚 Question Bank Manager")
        
        # Check login status
        is_logged_in = self.user_id is not None
        
        # Tabs for different bank sources
        tab1, tab2, tab3 = st.tabs(["📖 Default Banks", "✨ My Custom Banks", "➕ Create New"])
        
        with tab1:
            self._display_default_banks_ui()
        
        with tab2:
            if is_logged_in:
                self._display_custom_banks_ui()
            else:
                st.info("🔐 Please log in to manage custom question banks")
        
        with tab3:
            if is_logged_in:
                self._display_create_bank_ui()
            else:
                st.info("🔐 Please log in to create custom question banks")
    
    def _display_default_banks_ui(self):
        """Display default banks with load buttons"""
        default_banks = self.get_available_default_banks()
        
        cols = st.columns(2)
        for i, bank in enumerate(default_banks):
            with cols[i % 2]:
                with st.container():
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; border-radius:10px; padding:1rem; margin-bottom:1rem;">
                        <h4>{bank['name']}</h4>
                        <p style="color:#666;">{bank['description']}</p>
                        <p style="color:#666;">📋 {bank['sessions']} sessions • 💬 {bank['topics']} topics</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Create a unique key for each button
                    button_key = f"load_default_{bank['id']}_{datetime.now().timestamp()}"
                    
                    if st.button(f"📂 Load Bank", key=button_key, 
                               use_container_width=True, type="primary"):
                        sessions = self.load_default_bank(bank['id'])
                        if sessions:
                            # Store in session state for the main app
                            st.session_state.current_question_bank = sessions
                            st.session_state.current_bank_name = bank['name']
                            st.session_state.current_bank_type = "default"
                            st.session_state.current_bank_id = bank['id']
                            
                            # Initialize responses for all sessions
                            for session in sessions:
                                session_id = session["id"]
                                if session_id not in st.session_state.responses:
                                    st.session_state.responses[session_id] = {
                                        "title": session["title"],
                                        "questions": {},
                                        "summary": "",
                                        "completed": False,
                                        "word_target": session.get("word_target", 500)
                                    }
                            
                            st.success(f"✅ Successfully loaded '{bank['name']}'")
                            st.info("👉 Click 'Back' and go to the main screen to start writing!")
    
    def _display_custom_banks_ui(self):
        """Display user's custom banks with management options"""
        user_banks = self.get_user_banks()
        
        if not user_banks:
            st.info("✨ You haven't created any custom question banks yet. Go to the 'Create New' tab to get started!")
            return
        
        for bank in user_banks:
            with st.expander(f"📚 {bank['name']}", expanded=False):
                st.write(f"**Description:** {bank.get('description', 'No description')}")
                
                # Show stats
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Sessions", bank.get('session_count', 0))
                with col2:
                    st.metric("Topics", bank.get('topic_count', 0))
                
                st.caption(f"Created: {bank['created_at'][:10]} • Updated: {bank.get('updated_at', bank['created_at'])[:10]}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("📂 Load", key=f"load_custom_{bank['id']}", 
                               use_container_width=True, type="primary"):
                        sessions = self.load_user_bank(bank['id'])
                        if sessions:
                            # Store in session state for the main app
                            st.session_state.current_question_bank = sessions
                            st.session_state.current_bank_name = bank['name']
                            st.session_state.current_bank_type = "custom"
                            st.session_state.current_bank_id = bank['id']
                            
                            # Initialize responses for all sessions
                            for session in sessions:
                                session_id = session["id"]
                                if session_id not in st.session_state.responses:
                                    st.session_state.responses[session_id] = {
                                        "title": session["title"],
                                        "questions": {},
                                        "summary": "",
                                        "completed": False,
                                        "word_target": session.get("word_target", 500)
                                    }
                            
                            st.success(f"✅ Loaded '{bank['name']}'")
                            st.info("👉 Click 'Back' and go to the main screen to start writing!")
                
                with col2:
                    if st.button("✏️ Edit", key=f"edit_custom_{bank['id']}", 
                               use_container_width=True):
                        st.session_state.editing_bank_id = bank['id']
                        st.session_state.editing_bank_name = bank['name']
                        st.session_state.show_bank_editor = True
                        st.rerun()
                
                with col3:
                    if st.button("📋 Export", key=f"export_custom_{bank['id']}", 
                               use_container_width=True):
                        self._export_bank_to_csv(bank['id'])
                
                with col4:
                    if st.button("🗑️ Delete", key=f"delete_custom_{bank['id']}", 
                               use_container_width=True, type="secondary"):
                        if self.delete_custom_bank(bank['id']):
                            st.success(f"✅ Deleted {bank['name']}")
                            st.rerun()
    
    def _display_create_bank_ui(self):
        """Display form to create new custom bank"""
        st.markdown("### Create New Question Bank")
        
        with st.form("create_bank_form"):
            bank_name = st.text_input("Bank Name *", 
                                     placeholder="e.g., 'My Family Stories' or 'Career Reflections'")
            bank_description = st.text_area("Description (optional)",
                                          placeholder="What kind of stories will this bank focus on?",
                                          height=100)
            
            # Option to start from default bank
            st.markdown("#### Start from template (optional)")
            default_banks = self.get_available_default_banks()
            bank_options = {bank['name']: bank['id'] for bank in default_banks}
            bank_options["-- Start from scratch (empty bank) --"] = None
            
            selected_bank_name = st.selectbox(
                "Copy questions from:",
                list(bank_options.keys()),
                index=len(bank_options)-1  # Default to "Start from scratch"
            )
            copy_from_id = bank_options[selected_bank_name]
            
            submitted = st.form_submit_button("✅ Create Bank", type="primary", use_container_width=True)
            
            if submitted:
                if bank_name.strip():
                    # Create the bank
                    new_bank = self.create_custom_bank(bank_name, bank_description, copy_from_id)
                    
                    if new_bank:
                        st.success(f"✅ Bank '{bank_name}' created successfully!")
                        
                        # If we copied from a default, show how many sessions/topics
                        if copy_from_id:
                            bank_info = next((b for b in default_banks if b['id'] == copy_from_id), None)
                            if bank_info:
                                st.info(f"📋 Copied {bank_info['sessions']} sessions with {bank_info['topics']} topics")
                        
                        st.info("👉 You can now edit this bank or load it to start writing")
                        st.rerun()
                else:
                    st.error("❌ Please enter a bank name")
    
    def _export_bank_to_csv(self, bank_id: str):
        """Export a custom bank to CSV"""
        sessions = self.load_user_bank(bank_id)
        
        rows = []
        for session in sessions:
            for i, question in enumerate(session.get("questions", [])):
                guidance = session.get("guidance", "") if i == 0 else ""
                rows.append({
                    "session_id": session["id"],
                    "title": session["title"],
                    "guidance": guidance,
                    "question": question,
                    "word_target": session.get("word_target", 500)
                })
        
        df = pd.DataFrame(rows)
        csv = df.to_csv(index=False)
        
        bank_info = None
        user_banks = self.get_user_banks()
        for b in user_banks:
            if b["id"] == bank_id:
                bank_info = b
                break
        
        filename = f"{bank_info['name'].replace(' ', '_')}.csv" if bank_info else f"bank_{bank_id}.csv"
        
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv",
            key=f"download_{bank_id}_{datetime.now().timestamp()}"
        )

    def display_bank_editor(self, bank_id: str):
        """Display comprehensive bank editor for sessions and topics"""
        if not self.user_id:
            st.error("You must be logged in to edit banks")
            return
        
        sessions = self.load_user_bank(bank_id)
        
        st.title("✏️ Edit Question Bank")
        
        # Get bank info
        user_banks = self.get_user_banks()
        bank_info = next((b for b in user_banks if b["id"] == bank_id), {})
        
        # Edit bank metadata
        with st.expander("Bank Settings", expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_name = st.text_input("Bank Name", value=bank_info.get("name", ""))
                new_desc = st.text_area("Description", value=bank_info.get("description", ""), height=100)
            with col2:
                if st.button("💾 Save Settings", use_container_width=True, type="primary"):
                    for bank in user_banks:
                        if bank["id"] == bank_id:
                            bank["name"] = new_name
                            bank["description"] = new_desc
                            bank["updated_at"] = datetime.now().isoformat()
                    self._save_user_banks(user_banks)
                    st.success("✅ Bank settings updated")
                    st.rerun()
        
        st.divider()
        
        # Session management
        st.subheader("📋 Sessions")
        
        # Add new session button
        if st.button("➕ Add New Session", use_container_width=True, type="primary"):
            sessions = self.add_session(sessions, "New Session", "", 500)
            self.save_custom_bank(bank_id, sessions)
            st.rerun()
        
        # Display sessions with reordering
        for i, session in enumerate(sessions):
            with st.expander(f"📁 Session {session['id']}: {session['title']}", expanded=False):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    # Edit session title and word target
                    new_title = st.text_input("Title", value=session['title'], 
                                            key=f"title_{session['id']}")
                    new_guidance = st.text_area("Guidance", value=session.get('guidance', ''),
                                              key=f"guidance_{session['id']}", height=100)
                    new_target = st.number_input("Word Target", 
                                               value=session.get('word_target', 500),
                                               min_value=100, max_value=5000, step=100,
                                               key=f"target_{session['id']}")
                
                with col2:
                    st.write("**Reorder**")
                    if i > 0:
                        if st.button("⬆️ Move Up", key=f"up_{session['id']}", 
                                   use_container_width=True):
                            sessions = self.reorder_sessions(sessions, i, i-1)
                            self.save_custom_bank(bank_id, sessions)
                            st.rerun()
                    if i < len(sessions) - 1:
                        if st.button("⬇️ Move Down", key=f"down_{session['id']}", 
                                   use_container_width=True):
                            sessions = self.reorder_sessions(sessions, i, i+1)
                            self.save_custom_bank(bank_id, sessions)
                            st.rerun()
                
                with col3:
                    st.write("**Update**")
                    if st.button("💾 Save Session", key=f"save_session_{session['id']}", 
                               use_container_width=True, type="primary"):
                        updates = {
                            "title": new_title,
                            "guidance": new_guidance,
                            "word_target": new_target
                        }
                        sessions = self.update_session(sessions, session['id'], updates)
                        self.save_custom_bank(bank_id, sessions)
                        st.success("✅ Session updated")
                        st.rerun()
                
                with col4:
                    st.write("**Delete**")
                    if st.button("🗑️ Delete Session", key=f"delete_session_{session['id']}", 
                               use_container_width=True, type="secondary"):
                        sessions = self.delete_session(sessions, session['id'])
                        self.save_custom_bank(bank_id, sessions)
                        st.rerun()
                
                st.divider()
                
                # Topic management within session
                st.write("**Topics/Questions:**")
                
                # Add new topic
                new_topic = st.text_input("Add new topic", 
                                        placeholder="Enter a new question...",
                                        key=f"new_topic_{session['id']}")
                col1, col2 = st.columns([3, 1])
                with col1:
                    if new_topic:
                        if st.button("➕ Add Topic", key=f"add_topic_{session['id']}", 
                                   use_container_width=True, type="primary"):
                            sessions = self.add_topic(sessions, session['id'], new_topic)
                            self.save_custom_bank(bank_id, sessions)
                            st.rerun()
                
                st.markdown("---")
                
                # List topics with reorder and delete
                for j, topic in enumerate(session.get("questions", [])):
                    col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                    
                    with col1:
                        edited_topic = st.text_area(f"Topic {j+1}", value=topic,
                                                  key=f"topic_{session['id']}_{j}",
                                                  height=80)
                    
                    with col2:
                        st.write("**Reorder**")
                        if j > 0:
                            if st.button("⬆️", key=f"topic_up_{session['id']}_{j}"):
                                sessions = self.reorder_topics(sessions, session['id'], j, j-1)
                                self.save_custom_bank(bank_id, sessions)
                                st.rerun()
                        if j < len(session["questions"]) - 1:
                            if st.button("⬇️", key=f"topic_down_{session['id']}_{j}"):
                                sessions = self.reorder_topics(sessions, session['id'], j, j+1)
                                self.save_custom_bank(bank_id, sessions)
                                st.rerun()
                    
                    with col3:
                        st.write("**Update**")
                        if st.button("💾 Save", key=f"save_topic_{session['id']}_{j}"):
                            sessions = self.update_topic(sessions, session['id'], j, edited_topic)
                            self.save_custom_bank(bank_id, sessions)
                            st.rerun()
                    
                    with col4:
                        st.write("**Delete**")
                        if st.button("🗑️", key=f"del_topic_{session['id']}_{j}"):
                            sessions = self.delete_topic(sessions, session['id'], j)
                            self.save_custom_bank(bank_id, sessions)
                            st.rerun()
                    
                    st.divider()
        
        # Export and Back buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export to CSV", use_container_width=True):
                self._export_bank_to_csv(bank_id)
        with col2:
            if st.button("🔙 Back to Banks", use_container_width=True):
                st.session_state.show_bank_editor = False
                st.rerun()
