# Implementation Code

**Athletic Optimization System - Core Python Modules**

I'll provide complete, production-ready Python modules for your fitness data integration system. Here are all four modules:

## MODULE 1: Oura API Client

```python
"""
Oura Ring API Client with OAuth 2.0 authentication and comprehensive data fetching.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import httpx
import time
from urllib.parse import urlencode, parse_qs, urlparse

logger = logging.getLogger(__name__)

@dataclass
class RateLimiter:
    """Rate limiter for API requests."""
    max_requests: int
    time_window: int  # seconds
    requests: List[float] = None
    
    def __post_init__(self):
        if self.requests is None:
            self.requests = []
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                logger.info(f"Rate limit hit, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                await self.acquire()  # Retry after sleeping
        
        self.requests.append(now)

class OuraAPIError(Exception):
    """Custom exception for Oura API errors."""
    pass

class OuraClient:
    """
    Oura Ring API client with OAuth 2.0 authentication and comprehensive data fetching.
    
    Supports fetching sleep data, readiness scores, HRV, RHR, and activity data
    with proper rate limiting and error handling.
    """
    
    BASE_URL = "https://api.ouraring.com"
    AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
    TOKEN_URL = "https://api.ouraring.com/oauth/token"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        rate_limit_requests: int = 300,  # Oura allows 5000 requests/day
        rate_limit_window: int = 3600    # 1 hour window
    ):
        """
        Initialize Oura API client.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
            access_token: Existing access token (optional)
            refresh_token: Existing refresh token (optional)
            rate_limit_requests: Max requests per time window
            rate_limit_window: Time window in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        self.refresh_token = refresh_token
        
        self.rate_limiter = RateLimiter(rate_limit_requests, rate_limit_window)
        self._http_client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http_client.aclose()
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'email personal daily'
        }
        
        if state:
            params['state'] = state
            
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: OAuth authorization code
            
        Returns:
            Token response dictionary
            
        Raises:
            OuraAPIError: If token exchange fails
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        try:
            response = await self._http_client.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            return token_data
            
        except httpx.HTTPError as e:
            raise OuraAPIError(f"Token exchange failed: {e}")
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Returns:
            New token data
            
        Raises:
            OuraAPIError: If token refresh fails
        """
        if not self.refresh_token:
            raise OuraAPIError("No refresh token available")
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = await self._http_client.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            if 'refresh_token' in token_data:
                self.refresh_token = token_data['refresh_token']
            
            return token_data
            
        except httpx.HTTPError as e:
            raise OuraAPIError(f"Token refresh failed: {e}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_on_auth_error: bool = True
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with rate limiting.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            retry_on_auth_error: Whether to retry on auth errors
            
        Returns:
            API response data
            
        Raises:
            OuraAPIError: If request fails
        """
        if not self.access_token:
            raise OuraAPIError("No access token available")
        
        await self.rate_limiter.acquire()
        
        headers = {'Authorization': f'Bearer {self.access_token}'}
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = await self._http_client.request(
                method, url, headers=headers, params=params
            )
            
            if response.status_code == 401 and retry_on_auth_error and self.refresh_token:
                # Try to refresh token and retry
                logger.info("Access token expired, refreshing...")
                await self.refresh_access_token()
                return await self._make_request(method, endpoint, params, False)
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            raise OuraAPIError(f"API request failed: {e}")
    
    def _validate_date_range(self, start_date: str, end_date: str) -> None:
        """Validate date range parameters."""
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            if start > end:
                raise ValueError("Start date must be before end date")
            
            if end > datetime.now():
                raise ValueError("End date cannot be in the future")
                
        except ValueError as e:
            raise OuraAPIError(f"Invalid date range: {e}")
    
    async def get_sleep_data(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch sleep data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of sleep data records
        """
        self._validate_date_range(start_date, end_date)
        
        params = {'start_date': start_date, 'end_date': end_date}
        response = await self._make_request('GET', '/v2/usercollection/sleep', params)
        
        return response.get('data', [])
    
    async def get_readiness_data(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch readiness data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of readiness data records
        """
        self._validate_date_range(start_date, end_date)
        
        params = {'start_date': start_date, 'end_date': end_date}
        response = await self._make_request('GET', '/v2/usercollection/daily_readiness', params)
        
        return response.get('data', [])
    
    async def get_hrv_data(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch HRV data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of HRV data records
        """
        self._validate_date_range(start_date, end_date)
        
        params = {'start_date': start_date, 'end_date': end_date}
        response = await self._make_request('GET', '/v2/usercollection/heartrate', params)
        
        return response.get('data', [])
    
    async def get_resting_heart_rate_data(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch resting heart rate data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of RHR data records
        """
        # RHR is typically included in daily readiness data
        return await self.get_readiness_data(start_date, end_date)
    
    async def get_activity_data(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch activity data for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of activity data records
        """
        self._validate_date_range(start_date, end_date)
        
        params = {'start_date': start_date, 'end_date': end_date}
        response = await self._make_request('GET', '/v2/usercollection/daily_activity', params)
        
        return response.get('data', [])
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Fetch user profile information.
        
        Returns:
            User profile data
        """
        response = await self._make_request('GET', '/v2/usercollection/personal_info')
        return response
```

## MODULE 2: Garmin API Client

```python
"""
Garmin Connect IQ API Client with OAuth 2.0 authentication and Stryd data parsing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import httpx
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class GarminAPIError(Exception):
    """Custom exception for Garmin API errors."""
    pass

@dataclass
class StrydMetrics:
    """Stryd running power metrics."""
    power: Optional[float] = None
    ground_contact_time: Optional[float] = None
    vertical_oscillation: Optional[float] = None
    cadence: Optional[int] = None
    form_power: Optional[float] = None
    leg_spring_stiffness: Optional[float] = None

class GarminClient:
    """
    Garmin Connect IQ API client with OAuth 2.0 authentication.
    
    Supports fetching workouts, activities, training metrics, and parsing
    Stryd running power data with proper rate limiting and error handling.
    """
    
    BASE_URL = "https://connectapi.garmin.com"
    AUTH_URL = "https://connect.garmin.com/oauthConfirm"
    TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        rate_limit_requests: int = 200,  # Conservative rate limiting
        rate_limit_window: int = 3600    # 1 hour window
    ):
        """
        Initialize Garmin API client.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
            access_token: Existing access token (optional)
            refresh_token: Existing refresh token (optional)
            rate_limit_requests: Max requests per time window
            rate_limit_window: Time window in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        self.refresh_token = refresh_token
        
        self.rate_limiter = RateLimiter(rate_limit_requests, rate_limit_window)
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._http_client.aclose()
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            'oauth_consumer