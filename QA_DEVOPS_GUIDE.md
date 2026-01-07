# QA and DevOps Guide

**Athletic Optimization System - Testing & Deployment**

# Athletic Optimization System - QA & Deployment Strategy

## 1. Testing Strategy & Implementation

### Unit Tests (pytest examples)

```python
# tests/unit/test_auth.py
import pytest
from unittest.mock import Mock, patch
from src.auth.oauth_manager import OAuthManager
from src.exceptions import AuthenticationError

class TestOAuthManager:
    
    @pytest.fixture
    def oauth_manager(self):
        return OAuthManager(
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback"
        )
    
    def test_token_validation_success(self, oauth_manager):
        """Test valid token passes validation"""
        valid_token = {
            'access_token': 'valid_token',
            'expires_at': 9999999999,  # Future timestamp
            'refresh_token': 'refresh_token'
        }
        assert oauth_manager.is_token_valid(valid_token) == True
    
    def test_token_validation_expired(self, oauth_manager):
        """Test expired token fails validation"""
        expired_token = {
            'access_token': 'expired_token',
            'expires_at': 1000000000,  # Past timestamp
            'refresh_token': 'refresh_token'
        }
        assert oauth_manager.is_token_valid(expired_token) == False
    
    @patch('src.auth.oauth_manager.requests.post')
    def test_refresh_token_success(self, mock_post, oauth_manager):
        """Test successful token refresh"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'expires_in': 3600,
            'refresh_token': 'new_refresh_token'
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = oauth_manager.refresh_access_token('old_refresh_token')
        assert result['access_token'] == 'new_token'
```

```python
# tests/unit/test_conversions.py
import pytest
from src.utils.conversions import DataConverter
from decimal import Decimal

class TestDataConverter:
    
    def test_km_to_miles_conversion(self):
        """Test kilometer to mile conversion accuracy"""
        converter = DataConverter()
        
        # Test cases with expected precision
        test_cases = [
            (5.0, 3.10686),  # 5K race
            (10.0, 6.21371),  # 10K race
            (21.0975, 13.1069),  # Half marathon
            (42.195, 26.2188),  # Full marathon
            (0, 0)  # Edge case
        ]
        
        for km, expected_miles in test_cases:
            result = converter.km_to_miles(km)
            assert abs(result - expected_miles) < 0.0001
    
    def test_pace_conversion_km_to_mile(self):
        """Test pace conversion from min/km to min/mile"""
        converter = DataConverter()
        
        # 4:00 min/km should equal ~6:26 min/mile
        pace_per_km = 240  # 4 minutes in seconds
        expected_pace_per_mile = 386.24  # ~6:26 in seconds
        
        result = converter.pace_km_to_mile(pace_per_km)
        assert abs(result - expected_pace_per_mile) < 1  # Within 1 second
    
    @pytest.mark.parametrize("invalid_input", [None, -1, "invalid", float('inf')])
    def test_conversion_invalid_input(self, invalid_input):
        """Test conversion handles invalid inputs gracefully"""
        converter = DataConverter()
        
        with pytest.raises(ValueError):
            converter.km_to_miles(invalid_input)
```

```python
# tests/unit/test_database.py
import pytest
from unittest.mock import Mock, patch
from src.database.activity_repository import ActivityRepository
from src.models.activity import Activity
import psycopg2

class TestActivityRepository:
    
    @pytest.fixture
    def mock_connection(self):
        return Mock()
    
    @pytest.fixture
    def repository(self, mock_connection):
        return ActivityRepository(mock_connection)
    
    def test_save_activity_success(self, repository, mock_connection):
        """Test successful activity save"""
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        activity = Activity(
            user_id="user123",
            activity_id="act456",
            distance_miles=5.0,
            duration_seconds=1800,
            avg_heart_rate=150
        )
        
        repository.save_activity(activity)
        
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
    
    def test_save_activity_duplicate_handling(self, repository, mock_connection):
        """Test duplicate activity handling"""
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("Duplicate key")
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        activity = Activity(user_id="user123", activity_id="duplicate")
        
        # Should not raise exception, should handle gracefully
        result = repository.save_activity(activity)
        assert result is False
        mock_connection.rollback.assert_called_once()
```

### Integration Tests

```python
# tests/integration/test_oauth_flow.py
import pytest
from src.auth.oauth_manager import OAuthManager
from src.database.user_repository import UserRepository
import os

@pytest.mark.integration
class TestOAuthIntegration:
    
    @pytest.fixture
    def oauth_manager(self):
        return OAuthManager(
            client_id=os.getenv('TEST_CLIENT_ID'),
            client_secret=os.getenv('TEST_CLIENT_SECRET'),
            redirect_uri="http://localhost:8000/callback"
        )
    
    @pytest.mark.skipif(not os.getenv('INTEGRATION_TESTS'), reason="Integration tests disabled")
    async def test_complete_oauth_flow(self, oauth_manager):
        """Test complete OAuth flow with test credentials"""
        # This would use sandbox/test API credentials
        auth_url = oauth_manager.get_authorization_url()
        assert "oauth/authorize" in auth_url
        assert oauth_manager.client_id in auth_url
        
        # Simulate callback with test authorization code
        test_auth_code = os.getenv('TEST_AUTH_CODE')
        if test_auth_code:
            token_data = await oauth_manager.exchange_code_for_token(test_auth_code)
            assert 'access_token' in token_data
            assert 'refresh_token' in token_data
```

```python
# tests/integration/test_data_pipeline.py
import pytest
from src.pipeline.data_fetcher import DataFetcher
from src.database.activity_repository import ActivityRepository
from src.transformers.activity_transformer import ActivityTransformer

@pytest.mark.integration
class TestDataPipeline:
    
    @pytest.fixture
    def test_database(self):
        # Set up test database connection
        pass
    
    async def test_end_to_end_data_flow(self, test_database):
        """Test complete data flow from API to database"""
        # Mock API response with real data structure
        mock_api_data = {
            "activities": [{
                "id": "test_activity_123",
                "name": "Morning Run",
                "distance": 5000,  # meters
                "moving_time": 1800,  # seconds
                "average_heartrate": 150,
                "start_date": "2024-01-15T08:00:00Z"
            }]
        }
        
        # Transform data
        transformer = ActivityTransformer()
        transformed_data = transformer.transform_api_response(mock_api_data)
        
        # Verify transformations
        activity = transformed_data[0]
        assert activity.distance_miles == pytest.approx(3.10686, rel=1e-4)
        assert activity.duration_seconds == 1800
        assert activity.avg_heart_rate == 150
        
        # Save to database
        repository = ActivityRepository(test_database)
        success = repository.save_activity(activity)
        assert success is True
        
        # Verify data was saved correctly
        retrieved = repository.get_activity_by_id("test_activity_123")
        assert retrieved.distance_miles == activity.distance_miles
```

### Data Validation Tests

```python
# tests/validation/test_data_validation.py
import pytest
from src.validation.data_validator import DataValidator, ValidationError
from datetime import datetime

class TestDataValidator:
    
    def test_heart_rate_validation(self):
        """Test heart rate range validation"""
        validator = DataValidator()
        
        # Valid heart rates
        assert validator.validate_heart_rate(60) == True
        assert validator.validate_heart_rate(180) == True
        
        # Invalid heart rates
        with pytest.raises(ValidationError):
            validator.validate_heart_rate(39)  # Too low
        
        with pytest.raises(ValidationError):
            validator.validate_heart_rate(221)  # Too high
        
        with pytest.raises(ValidationError):
            validator.validate_heart_rate(None)
    
    def test_pace_validation(self):
        """Test pace validation (4-20 min/mile)"""
        validator = DataValidator()
        
        # Valid paces (in seconds per mile)
        assert validator.validate_pace(240) == True  # 4:00 min/mile
        assert validator.validate_pace(1200) == True  # 20:00 min/mile
        
        # Invalid paces
        with pytest.raises(ValidationError):
            validator.validate_pace(180)  # Too fast (3:00 min/mile)
        
        with pytest.raises(ValidationError):
            validator.validate_pace(1300)  # Too slow (21:40 min/mile)
    
    def test_coordinate_validation(self):
        """Test GPS coordinate validation"""
        validator = DataValidator()
        
        # Valid coordinates
        assert validator.validate_coordinates(40.7128, -74.0060) == True  # NYC
        
        # Invalid coordinates
        with pytest.raises(ValidationError):
            validator.validate_coordinates(91.0, 0.0)  # Invalid latitude
        
        with pytest.raises(ValidationError):
            validator.validate_coordinates(0.0, 181.0)  # Invalid longitude
    
    def test_deduplication_logic(self):
        """Test activity deduplication"""
        validator = DataValidator()
        
        activities = [
            {"id": "1", "start_time": "2024-01-01T10:00:00Z", "distance": 5.0},
            {"id": "2", "start_time": "2024-01-01T10:01:00Z", "distance": 5.0},  # Duplicate
            {"id": "3", "start_time": "2024-01-01T14:00:00Z", "distance": 3.0}   # Different
        ]
        
        unique_activities = validator.deduplicate_activities(activities)
        assert len(unique_activities) == 2
        assert unique_activities[0]["id"] == "1"  # Keeps first occurrence
        assert unique_activities[1]["id"] == "3"
```

## 2. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci-cd.yml
name: Athletic Optimization System CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: athletic_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Cache Python dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Set up test environment
      run: |
        cp .env.test .env
        python -m src.database.migrate
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/athletic_test
        REDIS_URL: redis://localhost:6379/0
    
    - name: Run linting
      run: |
        black --check src/ tests/
        isort --check-only src/ tests/
        flake8 src/ tests/
        mypy src/
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src --cov-report=xml --cov-report=term
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/athletic_test
        REDIS_URL: redis://localhost:6379/0
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --cov-append --cov=src --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/athletic_test
        REDIS_URL: redis://localhost:6379/0
        INTEGRATION_TESTS: true
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Bandit security scan
      run: |
        pip install bandit[toml]
        bandit -r src/ -f json -o security-report.json
    
    - name: Run Safety check
      run: |
        pip install safety
        safety check --json --output safety-report.json
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          security-report.json
          safety-report.json

  build-and-push:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: $