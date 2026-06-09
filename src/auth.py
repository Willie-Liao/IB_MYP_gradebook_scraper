"""Authentication module for ManageBac Gradebook Scraper."""

import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import Dict, Optional
from urllib.parse import urljoin

from .exceptions import AuthenticationError, SessionExpiredError


class RequestConfig:
    """Centralized configuration for HTTP requests."""
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    }
    
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3


class HTMLParser:
    """Utility class for HTML parsing operations."""
    
    @staticmethod
    def extract_csrf_token(html: str) -> Optional[str]:
        """Extract CSRF token from HTML."""
        soup = BeautifulSoup(html, "lxml")
        meta_tag = soup.find("meta", attrs={"name": "csrf-token"})
        if meta_tag and (content := meta_tag.get("content")):
            return str(content)
        return None
    
    @staticmethod
    def extract_error_message(html: str) -> Optional[str]:
        """Extract error message from HTML."""
        soup = BeautifulSoup(html, "lxml")
        
        # Define error class patterns to check
        error_classes = ["alert-danger", "error", "alert-error", "flash-error"]
        
        for error_class in error_classes:
            error_div = soup.find("div", class_=error_class)
            if error_div:
                return error_div.get_text(strip=True)
        
        return None
    
    @staticmethod
    def find_form_action(html: str, base_url: str) -> str:
        """Find form action URL from HTML."""
        soup = BeautifulSoup(html, "lxml")
        form = soup.find("form")
        
        if not form or not form.get("action"):
            return f"{base_url}/session"
        
        form_action = form.get("action", "")
        
        if form_action.startswith("/"):
            return f"{base_url}{form_action}"
        elif form_action.startswith("http"):
            return form_action
        else:
            return f"{base_url}/{form_action}"
    
    @staticmethod
    def extract_form_fields(html: str, email: str, password: str) -> Dict[str, str]:
        """Extract all form fields from login form."""
        soup = BeautifulSoup(html, "lxml")
        form = soup.find("form")
        payload = {}
        
        if form:
            for input_field in form.find_all("input"):
                name = input_field.get("name")
                if not name:
                    continue
                    
                if name == "authenticity_token":
                    continue
                
                # Map email/password fields
                if any(keyword in name.lower() for keyword in ["email", "login", "user[email]", "session[email]"]):
                    payload[name] = email
                elif any(keyword in name.lower() for keyword in ["password", "user[password]", "session[password]"]):
                    payload[name] = password
                elif (value := input_field.get("value")):
                    payload[name] = value
        
        return payload


class Authenticator:
    """Handles ManageBac authentication and CSRF token extraction."""
    
    def __init__(
        self,
        school_code: str,
        email: str,
        password: str,
        domain: str = "managebac.cn",
    ):
        self.school_code = school_code
        self.email = email
        self.password = password
        self.domain = domain
        self.base_url = f"https://{school_code}.{domain}"
        self._session: Optional[requests.Session] = None
        self._parser = HTMLParser()
    
    def create_session(self) -> requests.Session:
        """Create and configure a new requests session."""
        session = requests.Session()
        session.headers.update(RequestConfig.DEFAULT_HEADERS)
        return session
    
    def login(self) -> requests.Session:
        """Authenticate with ManageBac and return authenticated session."""
        tqdm.write(f"Logging in to {self.base_url}...")
        
        try:
            session = self.create_session()
            login_url = f"{self.base_url}/login"
            
            # Get login page
            response = self._make_request(session.get, login_url)
            
            # Extract CSRF token
            csrf_token = self._parser.extract_csrf_token(response.text)
            if not csrf_token:
                raise AuthenticationError("Failed to extract CSRF token from login page")
            
            # Prepare login payload
            form_action = self._parser.find_form_action(response.text, self.base_url)
            form_fields = self._parser.extract_form_fields(response.text, self.email, self.password)
            
            payload = {"authenticity_token": csrf_token, **form_fields}
            self._add_fallback_credentials(payload)
            
            # Submit login
            login_response = self._submit_login(session, form_action, login_url, payload)
            
            # Check login result
            if self._is_login_successful(login_response):
                tqdm.write(f"Login successful! Got {len(session.cookies)} cookies")
                self._session = session
                return session
            
            raise AuthenticationError(self._get_login_error(login_response))
            
        except requests.RequestException as e:
            raise AuthenticationError(f"Network error during authentication: {str(e)}") from e
    
    def _make_request(self, request_method, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with default timeout."""
        kwargs.setdefault("timeout", RequestConfig.DEFAULT_TIMEOUT)
        tqdm.write(f"Requesting: {url}")
        response = request_method(url, **kwargs)
        tqdm.write(f"Response status: {response.status_code}")
        response.raise_for_status()
        return response
    
    def _add_fallback_credentials(self, payload: Dict[str, str]) -> None:
        """Add fallback email/password fields if not found in form."""
        if not any(k for k in payload.keys() if "email" in k.lower() or k == "login"):
            payload["login"] = self.email
        if not any(k for k in payload.keys() if "password" in k.lower()):
            payload["password"] = self.password
    
    def _submit_login(self, session: requests.Session, form_action: str, 
                     referer: str, payload: Dict[str, str]) -> requests.Response:
        """Submit login form."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": referer,
            "Origin": self.base_url,
        }
        
        tqdm.write(f"Submitting credentials to: {form_action}")
        return session.post(
            form_action,
            data=payload,
            headers=headers,
            allow_redirects=True,
            timeout=RequestConfig.DEFAULT_TIMEOUT
        )
    
    def _is_login_successful(self, response: requests.Response) -> bool:
        """Check if login was successful."""
        if response.status_code == 404:
            raise AuthenticationError(f"Login endpoint not found (404)")
        
        # Successful if not redirected to login page
        return "/login" not in response.url and response.status_code < 400
    
    def _get_login_error(self, response: requests.Response) -> str:
        """Extract error message from failed login response."""
        error_msg = self._parser.extract_error_message(response.text)
        return error_msg or "Invalid credentials or unexpected response"


class SessionManager:
    """Manages authenticated sessions with retry logic."""
    
    def __init__(self, session: requests.Session, authenticator: Authenticator):
        self.session: requests.Session = session
        self.authenticator: Authenticator = authenticator
    
    def get(self, url: str, retry_count: int = RequestConfig.MAX_RETRIES) -> requests.Response:
        """Make authenticated GET request with retry logic."""
        last_exception = None
        
        for attempt in range(retry_count):
            try:
                response = self._make_authenticated_request(url)
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                last_exception = e
                if attempt < retry_count - 1:
                    self._wait_and_retry(attempt, retry_count)
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        raise requests.RequestException("All retry attempts failed")
    
    def _make_authenticated_request(self, url: str) -> requests.Response:
        """Make a single authenticated request with session check."""
        tqdm.write(f"Requesting: {url}")
        tqdm.write(f"Session cookies: {list(self.session.cookies.keys())}")
        
        response = self.session.get(url, timeout=RequestConfig.DEFAULT_TIMEOUT)
        tqdm.write(f"Response status: {response.status_code}")
        
        if self._is_session_expired(response):
            self._reauthenticate()
            # Retry with new session
            response = self.session.get(url, timeout=RequestConfig.DEFAULT_TIMEOUT)
        
        return response
    
    def _is_session_expired(self, response: requests.Response) -> bool:
        """Check if session has expired."""
        if response.status_code == 200:
            return response.url.rstrip('/').endswith('/login')
        
        # Check redirect history
        if response.history:
            for r in response.history:
                location = r.headers.get("Location", "")
                if location.rstrip('/').endswith('/login'):
                    return True
        
        return response.url.rstrip('/').endswith('/login')
    
    def _reauthenticate(self) -> None:
        """Re-authenticate when session expires."""
        tqdm.write("Session expired, re-authenticating...")
        try:
            self.session = self.authenticator.login()
        except AuthenticationError as e:
            raise SessionExpiredError(f"Failed to re-authenticate: {str(e)}") from e
    
    @staticmethod
    def _wait_and_retry(attempt: int, max_retries: int) -> None:
        """Implement exponential backoff for retries."""
        wait_time = 2 ** attempt
        tqdm.write(f"Request failed, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
        time.sleep(wait_time)
