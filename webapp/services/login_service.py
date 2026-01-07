import os
import hashlib
import secrets
from datetime import datetime, timedelta
from pymongo import MongoClient
from urllib.parse import quote_plus


class LoginService:
    
    def __init__(self):
        user = os.environ.get('MONGO_USER', '')
        password = os.environ.get('MONGO_PASSWORD', '')
        
        if not user or not password:
            raise ValueError("MongoDB credentials not configured")
        
        user_escaped = quote_plus(user)
        password_escaped = quote_plus(password)
        
        uri = f'mongodb://{user_escaped}:{password_escaped}@atlas-sql-6858308155a50c4c1cab0c84-zvdtc0.a.query.mongodb.net/promptchess?ssl=true&authSource=admin'
        
        self.client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        self.db = self.client['promptchess']
        self.users = self.db['users']
        self.sessions_collection = self.db['sessions']
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hashed.hex(), salt
    
    def register_user(self, username: str, password: str, email: str = None) -> dict:
        if self.users.find_one({'username': username}):
            return {'success': False, 'error': 'Username already exists'}
        
        if email and self.users.find_one({'email': email}):
            return {'success': False, 'error': 'Email already registered'}
        
        hashed_password, salt = self._hash_password(password)
        
        user_doc = {
            'username': username,
            'password_hash': hashed_password,
            'salt': salt,
            'email': email,
            'created_at': datetime.utcnow(),
            'last_login': None,
            'profile': {
                'display_name': username,
                'games_played': 0,
                'games_won': 0,
                'games_lost': 0,
                'elo_rating': 1200
            }
        }
        
        result = self.users.insert_one(user_doc)
        
        return {
            'success': True,
            'user_id': str(result.inserted_id),
            'username': username
        }
    
    def authenticate(self, username: str, password: str) -> dict:
        user = self.users.find_one({'username': username})
        
        if not user:
            return {'success': False, 'error': 'Invalid username or password'}
        
        hashed_password, _ = self._hash_password(password, user['salt'])
        
        if hashed_password != user['password_hash']:
            return {'success': False, 'error': 'Invalid username or password'}
        
        self.users.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        session_token = secrets.token_urlsafe(32)
        
        self.sessions_collection.insert_one({
            'token': session_token,
            'user_id': str(user['_id']),
            'username': username,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=24)
        })
        
        return {
            'success': True,
            'user_id': str(user['_id']),
            'username': username,
            'session_token': session_token,
            'profile': user.get('profile', {})
        }
    
    def validate_session(self, session_token: str) -> dict:
        session = self.sessions_collection.find_one({
            'token': session_token,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        
        if not session:
            return {'valid': False}
        
        return {
            'valid': True,
            'user_id': session['user_id'],
            'username': session['username']
        }
    
    def logout(self, session_token: str) -> bool:
        result = self.sessions_collection.delete_one({'token': session_token})
        return result.deleted_count > 0
    
    def get_user_profile(self, username: str) -> dict:
        user = self.users.find_one({'username': username})
        
        if not user:
            return None
        
        return {
            'username': user['username'],
            'email': user.get('email'),
            'display_name': user.get('profile', {}).get('display_name', username),
            'games_played': user.get('profile', {}).get('games_played', 0),
            'games_won': user.get('profile', {}).get('games_won', 0),
            'games_lost': user.get('profile', {}).get('games_lost', 0),
            'elo_rating': user.get('profile', {}).get('elo_rating', 1200),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login')
        }
    
    def update_profile(self, username: str, updates: dict) -> bool:
        allowed_fields = ['display_name', 'email']
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if 'display_name' in filtered_updates:
            filtered_updates = {'profile.display_name': filtered_updates['display_name']}
        
        if not filtered_updates:
            return False
        
        result = self.users.update_one(
            {'username': username},
            {'$set': filtered_updates}
        )
        
        return result.modified_count > 0
    
    def update_game_stats(self, username: str, won: bool) -> bool:
        update_ops = {
            '$inc': {
                'profile.games_played': 1,
                'profile.games_won': 1 if won else 0,
                'profile.games_lost': 0 if won else 1,
                'profile.elo_rating': 15 if won else -10
            }
        }
        
        result = self.users.update_one({'username': username}, update_ops)
        return result.modified_count > 0
    
    def close(self):
        self.client.close()
