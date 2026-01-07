# Data Integration Guide

**Athletic Optimization System - API Integration Specifications**

# Wearable Device Data Integration Pipeline

## 1. OAuth 2.0 Authentication Flows

### Oura Ring OAuth Flow
```python
import requests
from datetime import datetime, timedelta
import os
from typing import Dict, Optional

class OuraAuth:
    def __init__(self):
        self.client_id = os.getenv('OURA_CLIENT_ID')
        self.client_secret = os.getenv('OURA_CLIENT_SECRET')
        self.redirect_uri = os.getenv('OURA_REDIRECT_URI')
        self.base_url = "https://api.ouraring.com"
        
    def get_authorization_url(self) -> str:
        """Generate authorization URL for user consent"""
        auth_url = f"https://cloud.ouraring.com/oauth/authorize"
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'email personal daily'
        }
        return f"{auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
    
    def exchange_code_for_token(self, authorization_code: str) -> Dict:
        """Exchange authorization code for access token"""
        token_url = "https://api.ouraring.com/oauth/token"
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token exchange failed: {response.text}")
    
    def refresh_token(self, refresh_token: str) -> Dict:
        """Refresh expired access token"""
        token_url = "https://api.ouraring.com/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token refresh failed: {response.text}")
```

### Garmin Connect OAuth Flow
```python
import requests
from requests_oauthlib import OAuth1Session

class GarminAuth:
    def __init__(self):
        self.consumer_key = os.getenv('GARMIN_CONSUMER_KEY')
        self.consumer_secret = os.getenv('GARMIN_CONSUMER_SECRET')
        self.request_token_url = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
        self.authorization_url = "https://connect.garmin.com/oauthConfirm"
        self.access_token_url = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
        
    def get_request_token(self) -> OAuth1Session:
        """Step 1: Get request token"""
        oauth = OAuth1Session(self.consumer_key, client_secret=self.consumer_secret)
        fetch_response = oauth.fetch_request_token(self.request_token_url)
        return oauth, fetch_response
    
    def get_authorization_url(self, oauth_session: OAuth1Session) -> str:
        """Step 2: Get authorization URL"""
        return oauth_session.authorization_url(self.authorization_url)
    
    def get_access_token(self, oauth_session: OAuth1Session, oauth_verifier: str) -> Dict:
        """Step 3: Get access token"""
        oauth_session.token['oauth_verifier'] = oauth_verifier
        oauth_tokens = oauth_session.fetch_access_token(self.access_token_url)
        return oauth_tokens
```

## 2. API Endpoint Specifications

### Oura Ring API Endpoints
```python
class OuraClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.ouraring.com/v2/usercollection"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_sleep_data(self, start_date: str, end_date: str) -> Dict:
        """Get sleep data including stages, efficiency, timing"""
        url = f"{self.base_url}/sleep"
        params = {'start_date': start_date, 'end_date': end_date}
        return self._make_request(url, params)
    
    def get_readiness_data(self, start_date: str, end_date: str) -> Dict:
        """Get readiness score data"""
        url = f"{self.base_url}/daily_readiness"
        params = {'start_date': start_date, 'end_date': end_date}
        return self._make_request(url, params)
    
    def get_heart_rate_data(self, start_date: str, end_date: str) -> Dict:
        """Get HRV, RHR data"""
        url = f"{self.base_url}/heartrate"
        params = {'start_date': start_date, 'end_date': end_date}
        return self._make_request(url, params)
    
    def get_spo2_data(self, start_date: str, end_date: str) -> Dict:
        """Get SpO2 data"""
        url = f"{self.base_url}/spo2"
        params = {'start_date': start_date, 'end_date': end_date}
        return self._make_request(url, params)
    
    def get_temperature_data(self, start_date: str, end_date: str) -> Dict:
        """Get body temperature data"""
        url = f"{self.base_url}/temperature_skin"
        params = {'start_date': start_date, 'end_date': end_date}
        return self._make_request(url, params)
    
    def get_activity_data(self, start_date: str, end_date: str) -> Dict:
        """Get daily activity data"""
        url = f"{self.base_url}/daily_activity"
        params = {'start_date': start_date, 'end_date': end_date}
        return self._make_request(url, params)
    
    def _make_request(self, url: str, params: Dict) -> Dict:
        """Make authenticated API request with error handling"""
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Oura API request failed: {e}")
```

### Garmin Connect API Endpoints
```python
class GarminClient:
    def __init__(self, oauth_tokens: Dict):
        self.oauth_tokens = oauth_tokens
        self.base_url = "https://connectapi.garmin.com"
        
    def get_activities(self, start_date: str, limit: int = 20) -> Dict:
        """Get workout/activity data"""
        url = f"{self.base_url}/activities-service/activities"
        params = {'start': start_date, 'limit': limit}
        return self._make_authenticated_request(url, params)
    
    def get_activity_details(self, activity_id: str) -> Dict:
        """Get detailed activity data including GPS, HR, pace, elevation"""
        url = f"{self.base_url}/activities-service/activities/{activity_id}"
        return self._make_authenticated_request(url)
    
    def get_daily_summary(self, date: str) -> Dict:
        """Get daily activity summary"""
        url = f"{self.base_url}/userstats-service/stats/{date}"
        return self._make_authenticated_request(url)
    
    def get_training_status(self, date: str) -> Dict:
        """Get training load metrics"""
        url = f"{self.base_url}/metrics-service/metrics/trainingStatus/{date}"
        return self._make_authenticated_request(url)
    
    def get_power_data(self, activity_id: str) -> Dict:
        """Get Stryd power data for specific activity"""
        url = f"{self.base_url}/activities-service/activities/{activity_id}/power"
        return self._make_authenticated_request(url)
    
    def _make_authenticated_request(self, url: str, params: Dict = None) -> Dict:
        """Make OAuth1 authenticated request"""
        from requests_oauthlib import OAuth1
        
        auth = OAuth1(
            os.getenv('GARMIN_CONSUMER_KEY'),
            client_secret=os.getenv('GARMIN_CONSUMER_SECRET'),
            resource_owner_key=self.oauth_tokens['oauth_token'],
            resource_owner_secret=self.oauth_tokens['oauth_token_secret']
        )
        
        try:
            response = requests.get(url, auth=auth, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Garmin API request failed: {e}")
```

## 3. Data Transformation Pipeline with Unit Conversions

```python
from typing import List, Dict, Any
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

class DataTransformer:
    
    @staticmethod
    def km_to_miles(km_value: float) -> float:
        """Convert kilometers to miles with high precision"""
        if km_value is None:
            return None
        # Using Decimal for precise conversion
        km_decimal = Decimal(str(km_value))
        miles_decimal = km_decimal * Decimal('0.621371192')
        return float(miles_decimal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
    
    @staticmethod
    def meters_to_miles(meters_value: float) -> float:
        """Convert meters to miles"""
        if meters_value is None:
            return None
        km_value = meters_value / 1000
        return DataTransformer.km_to_miles(km_value)
    
    def transform_oura_sleep(self, raw_data: Dict) -> List[Dict]:
        """Transform Oura sleep data"""
        transformed_records = []
        
        for record in raw_data.get('data', []):
            transformed = {
                'source': 'oura',
                'data_type': 'sleep',
                'date': record.get('day'),
                'bedtime_start': record.get('bedtime_start'),
                'bedtime_end': record.get('bedtime_end'),
                'total_sleep_duration_seconds': record.get('total_sleep_duration'),
                'sleep_efficiency_percent': record.get('efficiency'),
                'rem_sleep_duration_seconds': record.get('rem_sleep_duration'),
                'deep_sleep_duration_seconds': record.get('deep_sleep_duration'),
                'light_sleep_duration_seconds': record.get('light_sleep_duration'),
                'awake_time_seconds': record.get('awake_time'),
                'sleep_score': record.get('score'),
                'raw_data': record
            }
            transformed_records.append(transformed)
            
        return transformed_records
    
    def transform_oura_activity(self, raw_data: Dict) -> List[Dict]:
        """Transform Oura activity data with distance conversions"""
        transformed_records = []
        
        for record in raw_data.get('data', []):
            # CRITICAL: Convert all distances from km to miles
            equivalent_walking_distance_miles = None
            if record.get('equivalent_walking_distance'):
                equivalent_walking_distance_miles = self.km_to_miles(
                    record.get('equivalent_walking_distance') / 1000  # Convert meters to km first
                )
            
            transformed = {
                'source': 'oura',
                'data_type': 'daily_activity',
                'date': record.get('day'),
                'active_calories': record.get('active_calories'),
                'total_calories': record.get('total_calories'),
                'steps': record.get('steps'),
                'equivalent_walking_distance_miles': equivalent_walking_distance_miles,
                'high_activity_minutes': record.get('high_activity_met_minutes'),
                'medium_activity_minutes': record.get('medium_activity_met_minutes'),
                'low_activity_minutes': record.get('low_activity_met_minutes'),
                'activity_score': record.get('score'),
                'raw_data': record
            }
            transformed_records.append(transformed)
            
        return transformed_records
    
    def transform_garmin_activity(self, raw_data: Dict) -> List[Dict]:
        """Transform Garmin activity data with distance conversions"""
        transformed_records = []
        
        for activity in raw_data:
            # CRITICAL: Convert distances from km to miles
            distance_miles = None
            if activity.get('distance'):
                distance_miles = self.km_to_miles(activity.get('distance') / 1000)
            
            avg_pace_per_mile = None
            if activity.get('averageMovingSpeed') and activity.get('averageMovingSpeed') > 0:
                # Convert pace from min/km to min/mile
                pace_per_km = 1000 / (activity.get('averageMovingSpeed') * 60)  # min/km
                avg_pace_per_mile = pace_per_km / 0.621371192  # Convert to min/mile
            
            transformed = {
                'source': 'garmin',
                'data_type': 'activity',
                'activity_id': str(activity.get('activityId')),
                'activity_name': activity.get('activityName'),
                'activity_type': activity.get('activityType', {}).get('typeKey'),
                'start_time': activity.get('startTimeLocal'),
                'duration_seconds': activity.get('duration'),
                'distance_miles': distance_miles,
                'elevation_gain_feet': activity.get('elevationGain') * 3.28084 if activity.get('elevationGain') else None,  # Convert m to ft
                'avg_heart_rate': activity.get('averageHR'),
                'max_heart_rate': activity.get('maxHR'),
                'avg_pace_per_mile_seconds': avg_pace_per_mile * 60 if avg_pace_per_mile else None,
                'calories': activity.get('calories'),
                'avg_power_watts': activity.get('avgPower'),  # Stryd power data
                'normalized_power_watts': activity.get('normalizedPower'),
                'training_stress_score': activity.get('trainingStressScore'),
                'raw_data': activity
            }
            transformed_records.append(transformed)
            
        return transformed_records
    
    def transform_garmin_daily_summary(self, raw_data: Dict, date: str) -> Dict:
        """Transform Garmin daily summary with distance conversions"""
        # CRITICAL: Convert distances from km to miles
        total_distance_miles = None
        if raw_data.get('totalDistance'):
            total_distance_miles = self.km_to_miles(raw_data.get('totalDistance') / 1000)
        
        return {
            'source': 'garmin