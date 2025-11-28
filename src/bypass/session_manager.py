"""
Session Manager - Persistent Session and Cookie Management

Manages session persistence, cookie storage, and authentication state
across multiple requests to maintain bypass effectiveness.
"""

import json
import pickle
import time
import os
import base64
import hashlib
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger
import threading

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    Fernet = None
    HAS_CRYPTO = False


@dataclass
class SessionData:
    """Session data container"""
    cookies: Dict[str, str]
    headers: Dict[str, str]
    fingerprint: Dict[str, Any]
    created_at: float
    last_used: float
    success_count: int = 0
    failure_count: int = 0
    domain: str = ""
    cf_clearance: Optional[str] = None
    user_agent: str = ""


class SessionManager:
    """Manages persistent sessions and cookies for Cloudflare bypass"""
    
    def __init__(
        self,
        session_dir: str = "sessions",
        max_age_hours: int = 24,
        encryption_key: Optional[str] = None
    ):
        """
        Initialize session manager
        
        Args:
            session_dir: Directory to store session files
            max_age_hours: Maximum age of sessions in hours
            encryption_key: Optional key (or env fallback) for encrypting session blobs
        """
        self.session_dir = session_dir
        self.max_age = max_age_hours * 3600  # Convert to seconds
        self.sessions: Dict[str, SessionData] = {}
        self.lock = threading.Lock()
        self.encryption_key = encryption_key or os.getenv("CD_SESSION_KEY")
        self.fernet = self._build_cipher(self.encryption_key)
        self.encryption_enabled = self.fernet is not None
        
        # Create session directory
        os.makedirs(session_dir, exist_ok=True)
        
        # Load existing sessions
        self._load_sessions()
        
        enc_state = "enabled" if self.encryption_enabled else "disabled"
        logger.info(
            f"Session manager initialized with {len(self.sessions)} sessions "
            f"(encryption {enc_state})"
        )
    
    def get_session(self, domain: str) -> Optional[SessionData]:
        """
        Get valid session for domain
        
        Args:
            domain: Target domain
            
        Returns:
            SessionData if valid session exists, None otherwise
        """
        with self.lock:
            session_key = self._get_session_key(domain)
            
            if session_key not in self.sessions:
                return None
            
            session = self.sessions[session_key]
            
            # Check if session is expired
            if self._is_session_expired(session):
                logger.info(f"Session expired for {domain}")
                del self.sessions[session_key]
                self._delete_session_file(session_key)
                return None
            
            # Update last used time
            session.last_used = time.time()
            self._save_session(session_key, session)
            
            logger.debug(f"Retrieved session for {domain}")
            return session
    
    def create_session(
        self, 
        domain: str, 
        cookies: Dict[str, str],
        headers: Dict[str, str],
        fingerprint: Dict[str, Any]
    ) -> SessionData:
        """
        Create new session for domain
        
        Args:
            domain: Target domain
            cookies: Session cookies
            headers: Session headers
            fingerprint: Browser fingerprint used
            
        Returns:
            Created SessionData
        """
        with self.lock:
            current_time = time.time()
            
            session = SessionData(
                cookies=cookies,
                headers=headers,
                fingerprint=fingerprint,
                created_at=current_time,
                last_used=current_time,
                domain=domain,
                cf_clearance=cookies.get('cf_clearance'),
                user_agent=headers.get('User-Agent', '')
            )
            
            session_key = self._get_session_key(domain)
            self.sessions[session_key] = session
            
            # Save to disk
            self._save_session(session_key, session)
            
            logger.success(f"Created new session for {domain}")
            return session
    
    def update_session(
        self, 
        domain: str, 
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        success: bool = True
    ):
        """
        Update existing session
        
        Args:
            domain: Target domain
            cookies: Updated cookies (optional)
            headers: Updated headers (optional)
            success: Whether the session was used successfully
        """
        with self.lock:
            session_key = self._get_session_key(domain)
            
            if session_key not in self.sessions:
                logger.warning(f"No session found to update for {domain}")
                return
            
            session = self.sessions[session_key]
            
            # Update cookies and headers if provided
            if cookies:
                session.cookies.update(cookies)
                session.cf_clearance = cookies.get('cf_clearance', session.cf_clearance)
            
            if headers:
                session.headers.update(headers)
                session.user_agent = headers.get('User-Agent', session.user_agent)
            
            # Update usage statistics
            session.last_used = time.time()
            if success:
                session.success_count += 1
            else:
                session.failure_count += 1
            
            # Save updated session
            self._save_session(session_key, session)
            
            logger.debug(f"Updated session for {domain} (success: {success})")
    
    def delete_session(self, domain: str):
        """Delete session for domain"""
        with self.lock:
            session_key = self._get_session_key(domain)
            
            if session_key in self.sessions:
                del self.sessions[session_key]
                self._delete_session_file(session_key)
                logger.info(f"Deleted session for {domain}")
    
    def get_valid_sessions(self) -> List[SessionData]:
        """Get all valid (non-expired) sessions"""
        with self.lock:
            valid_sessions = []
            expired_keys = []
            
            for key, session in self.sessions.items():
                if self._is_session_expired(session):
                    expired_keys.append(key)
                else:
                    valid_sessions.append(session)
            
            # Clean up expired sessions
            for key in expired_keys:
                del self.sessions[key]
                self._delete_session_file(key)
            
            return valid_sessions
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        with self.lock:
            expired_keys = []
            
            for key, session in self.sessions.items():
                if self._is_session_expired(session):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.sessions[key]
                self._delete_session_file(key)
            
            logger.info(f"Cleaned up {len(expired_keys)} expired sessions")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        with self.lock:
            valid_sessions = self.get_valid_sessions()
            
            total_sessions = len(valid_sessions)
            total_successes = sum(s.success_count for s in valid_sessions)
            total_failures = sum(s.failure_count for s in valid_sessions)
            
            stats = {
                "total_sessions": total_sessions,
                "total_successes": total_successes,
                "total_failures": total_failures,
                "success_rate": total_successes / (total_successes + total_failures) if (total_successes + total_failures) > 0 else 0,
                "sessions_with_clearance": sum(1 for s in valid_sessions if s.cf_clearance),
                "average_age_hours": sum((time.time() - s.created_at) / 3600 for s in valid_sessions) / total_sessions if total_sessions > 0 else 0
            }
            
            return stats
    
    def export_cookies_for_requests(self, domain: str) -> Dict[str, str]:
        """
        Export cookies in format suitable for requests library
        
        Args:
            domain: Target domain
            
        Returns:
            Cookies dictionary
        """
        session = self.get_session(domain)
        if session:
            return session.cookies.copy()
        return {}
    
    def export_session_for_selenium(self, domain: str) -> List[Dict]:
        """
        Export session cookies in format suitable for Selenium
        
        Args:
            domain: Target domain
            
        Returns:
            List of cookie dictionaries for Selenium
        """
        session = self.get_session(domain)
        if not session:
            return []
        
        selenium_cookies = []
        for name, value in session.cookies.items():
            cookie_dict = {
                'name': name,
                'value': value,
                'domain': domain,
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            selenium_cookies.append(cookie_dict)
        
        return selenium_cookies
    
    def _get_session_key(self, domain: str) -> str:
        """Generate session key for domain"""
        # Remove protocol and www
        clean_domain = domain.replace('https://', '').replace('http://', '').replace('www.', '')
        return clean_domain.split('/')[0]  # Remove path
    
    def _build_cipher(self, key_str: Optional[str]):
        """Initialize Fernet cipher if possible."""
        if not key_str:
            return None
        
        if not HAS_CRYPTO or Fernet is None:
            logger.warning("Session encryption key provided but cryptography is unavailable.")
            return None
        
        try:
            normalized = self._normalize_key(key_str)
            return Fernet(normalized)
        except Exception as exc:
            logger.error(f"Failed to initialize session encryption: {exc}")
            return None
    
    @staticmethod
    def _normalize_key(key_str: str) -> bytes:
        """Normalize human-friendly key into Fernet-compatible bytes."""
        key_str = key_str.strip()
        try:
            decoded = base64.urlsafe_b64decode(key_str)
            if len(decoded) == 32:
                return base64.urlsafe_b64encode(decoded)
        except Exception:
            pass
        
        digest = hashlib.sha256(key_str.encode()).digest()
        return base64.urlsafe_b64encode(digest)
    
    def _is_session_expired(self, session: SessionData) -> bool:
        """Check if session is expired"""
        return (time.time() - session.created_at) > self.max_age
    
    def _save_session(self, session_key: str, session: SessionData):
        """Save session to disk"""
        try:
            filename = os.path.join(self.session_dir, f"{session_key}.pkl")
            payload = pickle.dumps(session)
            if self.fernet:
                payload = self.fernet.encrypt(payload)
            with open(filename, 'wb') as f:
                f.write(payload)
        except Exception as e:
            logger.error(f"Failed to save session {session_key}: {e}")
    
    def _load_sessions(self):
        """Load sessions from disk"""
        try:
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.pkl'):
                    session_key = filename[:-4]  # Remove .pkl extension
                    filepath = os.path.join(self.session_dir, filename)
                    
                    try:
                        with open(filepath, 'rb') as f:
                            payload = f.read()
                        
                        if self.fernet:
                            try:
                                payload = self.fernet.decrypt(payload)
                            except Exception as decrypt_exc:
                                logger.warning(
                                    f"Failed to decrypt session {session_key}: {decrypt_exc}"
                                )
                                os.remove(filepath)
                                continue
                        
                        session = pickle.loads(payload)
                        
                        # Validate session data
                        if isinstance(session, SessionData):
                            if not self._is_session_expired(session):
                                self.sessions[session_key] = session
                            else:
                                # Delete expired session file
                                os.remove(filepath)
                        else:
                            # Invalid session data, delete file
                            os.remove(filepath)
                            
                    except Exception as e:
                        logger.warning(f"Failed to load session {session_key}: {e}")
                        # Delete corrupted session file
                        try:
                            os.remove(filepath)
                        except:
                            pass
                        
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
    
    def _delete_session_file(self, session_key: str):
        """Delete session file from disk"""
        try:
            filename = os.path.join(self.session_dir, f"{session_key}.pkl")
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            logger.debug(f"Failed to delete session file {session_key}: {e}")
    
    def backup_sessions(self, backup_path: str):
        """Backup all sessions to a file"""
        try:
            backup_data = {
                "sessions": {k: asdict(v) for k, v in self.sessions.items()},
                "backup_time": time.time(),
                "version": "1.0"
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Sessions backed up to {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to backup sessions: {e}")
    
    def restore_sessions(self, backup_path: str):
        """Restore sessions from backup file"""
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            sessions_data = backup_data.get("sessions", {})
            
            with self.lock:
                for key, session_dict in sessions_data.items():
                    session = SessionData(**session_dict)
                    if not self._is_session_expired(session):
                        self.sessions[key] = session
                        self._save_session(key, session)
            
            logger.success(f"Sessions restored from {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore sessions: {e}")
    
    def clear_all_sessions(self):
        """Clear all sessions"""
        with self.lock:
            for session_key in list(self.sessions.keys()):
                self._delete_session_file(session_key)
            
            self.sessions.clear()
            logger.info("All sessions cleared")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Save all sessions on exit
        with self.lock:
            for key, session in self.sessions.items():
                self._save_session(key, session)