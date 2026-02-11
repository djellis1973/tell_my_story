# auth_manager.py
import hashlib
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import json

class AuthManager:
    def __init__(self, email_config=None):
        self.email_config = email_config or {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "use_tls": True
        }
    
    def generate_password(self, length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def hash_password(self, password):
        """Hash a password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, stored_hash, password):
        """Verify a password against its hash"""
        return stored_hash == self.hash_password(password)
    
    def send_welcome_email(self, user_data, credentials):
        """Send welcome email with account credentials"""
        try:
            if not self.email_config['sender_email'] or not self.email_config['sender_password']:
                print("Email not configured - skipping welcome email")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = user_data['email']
            msg['Subject'] = "Welcome to Tell My Story"
            
            body = f"""
            <html>
            <body style="font-family: Arial; line-height: 1.6;">
            <h2>Welcome to Tell My Story, {user_data['first_name']}!</h2>
            <p>Thank you for creating your account.</p>
            <div style="background: #f0f8ff; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db;">
                <h3>Your Account Details:</h3>
                <p><strong>Account ID:</strong> {credentials['user_id']}</p>
                <p><strong>Email:</strong> {user_data['email']}</p>
                <p><strong>Password:</strong> {credentials['password']}</p>
            </div>
            <p>Start building your timeline from your birthdate: {user_data.get('birthdate', 'Not specified')}</p>
            <p>If you didn't create this account, please ignore this email.</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                if self.email_config['use_tls']:
                    server.starttls()
                server.login(self.email_config['sender_email'], self.email_config['sender_password'])
                server.send_message(msg)
            
            print(f"Welcome email sent to {user_data['email']}")
            return True
            
        except Exception as e:
            print(f"Error sending welcome email: {e}")
            return False
    
    def create_user_account(self, user_data, password=None):
        """Create a new user account"""
        try:
            user_id = hashlib.sha256(f"{user_data['email']}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            if not password:
                password = self.generate_password()
            
            user_record = {
                "user_id": user_id,
                "email": user_data["email"].lower().strip(),
                "password_hash": self.hash_password(password),
                "account_type": user_data.get("account_for", "self"),
                "created_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "profile": {
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "email": user_data["email"],
                    "gender": user_data.get("gender", ""),
                    "birthdate": user_data.get("birthdate", ""),
                    "timeline_start": user_data.get("birthdate", "")
                },
                "settings": {
                    "email_notifications": True,
                    "auto_save": True,
                    "privacy_level": "private",
                    "theme": "light",
                    "email_verified": False
                },
                "stats": {
                    "total_sessions": 0,
                    "total_words": 0,
                    "current_streak": 0,
                    "longest_streak": 0,
                    "account_age_days": 0,
                    "last_active": datetime.now().isoformat()
                }
            }
            
            return {"success": True, "user_id": user_id, "password": password, "user_record": user_record}
            
        except Exception as e:
            print(f"Error creating account: {e}")
            return {"success": False, "error": str(e)}
    
    def authenticate_user(self, email, password, get_account_data_func):
        """Authenticate a user"""
        try:
            account = get_account_data_func(email=email)
            if account and self.verify_password(account['password_hash'], password):
                account['last_login'] = datetime.now().isoformat()
                return {"success": True, "user_id": account['user_id'], "user_record": account}
            return {"success": False, "error": "Invalid email or password"}
        except Exception as e:
            return {"success": False, "error": str(e)}
