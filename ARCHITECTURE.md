# Athletic Optimization System Architecture

# Athletic Optimization Platform Architecture

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  Web App    │  Mobile App  │  API Dashboard  │  Webhook Endpoints│
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                    API GATEWAY LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  Rate Limiting  │  Authentication  │  Request Routing  │  Logging│
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                   APPLICATION LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│ Data Ingestion │ Analysis Engine │ ML Pipeline │ Recommendation │
│   Service      │                 │             │    Engine      │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                   DATA PROCESSING LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│ Stream Processor│ Batch Processor │ Feature Store │ Cache Layer  │
│   (Kafka)       │   (Airflow)     │  (Redis/DDB)  │   (Redis)    │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                    STORAGE LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│ Time Series DB  │ Relational DB   │ Document Store│ Blob Storage │
│ (InfluxDB)      │ (PostgreSQL)    │  (MongoDB)    │   (S3)       │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                EXTERNAL INTEGRATIONS                           │
├─────────────────────────────────────────────────────────────────┤
│ Oura API v2     │ Garmin Connect │ Stryd API     │ Other Devices │
└─────────────────────────────────────────────────────────────────┘
```

## API Integration Architecture

### 1. Data Source Integration Patterns

#### Oura Ring Integration
```python
# OAuth 2.0 + Webhook Pattern
class OuraIntegration:
    endpoints = {
        'personal_info': '/v2/usercollection/personal_info',
        'daily_activity': '/v2/usercollection/daily_activity',
        'daily_readiness': '/v2/usercollection/daily_readiness',
        'daily_sleep': '/v2/usercollection/daily_sleep',
        'sessions': '/v2/usercollection/session',
        'tags': '/v2/usercollection/tag',
        'workouts': '/v2/usercollection/workout'
    }
    
    sync_strategy = 'webhook_primary_polling_fallback'
    rate_limits = {
        'requests_per_day': 5000,
        'requests_per_minute': 300
    }
```

#### Garmin Connect Integration
```python
# OAuth 1.0a + REST API
class GarminIntegration:
    endpoints = {
        'activities': '/activities',
        'activity_details': '/activities/{activityId}',
        'daily_summary': '/dailySummaries',
        'user_profile': '/userProfile',
        'device_info': '/devices'
    }
    
    sync_strategy = 'polling_with_incremental_sync'
    rate_limits = {
        'requests_per_minute': 100,
        'concurrent_connections': 3
    }
```

### 2. Integration Service Design

```python
class DataIngestionService:
    def __init__(self):
        self.kafka_producer = KafkaProducer()
        self.integrations = {
            'oura': OuraIntegration(),
            'garmin': GarminIntegration()
        }
    
    async def sync_user_data(self, user_id: str, source: str):
        """Orchestrates data sync from external APIs"""
        
        # Get incremental sync timestamp
        last_sync = await self.get_last_sync_time(user_id, source)
        
        # Fetch data with error handling & rate limiting
        raw_data = await self.fetch_with_retry(
            source, user_id, since=last_sync
        )
        
        # Validate and normalize data
        normalized_data = self.normalize_data(raw_data, source)
        
        # Stream to processing pipeline
        await self.kafka_producer.send(
            topic=f'{source}_raw_data',
            value=normalized_data
        )
        
        # Update sync timestamp
        await self.update_sync_time(user_id, source)
```

## Database Schema Design

### 1. Core Tables (PostgreSQL)

```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    timezone VARCHAR(50) DEFAULT 'UTC',
    athlete_profile JSONB
);

-- Device Integrations
CREATE TABLE user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    integration_type VARCHAR(50) NOT NULL, -- 'oura', 'garmin', 'stryd'
    external_user_id VARCHAR(255),
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,
    UNIQUE(user_id, integration_type)
);

-- Training Sessions
CREATE TABLE training_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    source VARCHAR(50) NOT NULL,
    session_type VARCHAR(100), -- 'running', 'cycling', 'strength', etc.
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds INTEGER,
    distance_meters REAL,
    
    -- Performance metrics
    avg_heart_rate INTEGER,
    max_heart_rate INTEGER,
    avg_pace_per_km INTEGER, -- seconds
    normalized_power REAL,
    training_stress_score REAL,
    
    -- Stryd metrics
    avg_power REAL,
    avg_cadence INTEGER,
    ground_contact_time REAL,
    vertical_oscillation REAL,
    
    -- Raw data reference
    raw_data_url TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX (user_id, start_time),
    INDEX (user_id, session_type, start_time)
);
```

### 2. Time Series Tables (InfluxDB Schema)

```python
# InfluxDB Measurement Schemas
measurements = {
    'sleep_metrics': {
        'tags': ['user_id', 'source'],
        'fields': [
            'sleep_score',
            'total_sleep_duration',
            'deep_sleep_duration', 
            'rem_sleep_duration',
            'sleep_efficiency',
            'sleep_latency',
            'wake_count',
            'lowest_heart_rate',
            'average_hrv',
            'body_temperature_delta'
        ]
    },
    
    'daily_readiness': {
        'tags': ['user_id', 'source'],
        'fields': [
            'readiness_score',
            'recovery_index',
            'hrv_balance',
            'body_temperature',
            'resting_heart_rate',
            'activity_balance',
            'previous_day_activity'
        ]
    },
    
    'workout_metrics': {
        'tags': ['user_id', 'session_id', 'workout_type'],
        'fields': [
            'heart_rate',
            'power',
            'pace',
            'cadence',
            'elevation',
            'ground_contact_time',
            'vertical_oscillation',
            'form_power',
            'leg_spring_stiffness'
        ]
    }
}
```

### 3. Aggregated Analytics Tables

```sql
-- Daily Performance Summary
CREATE TABLE daily_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    date DATE NOT NULL,
    
    -- Sleep metrics
    sleep_score INTEGER,
    total_sleep_duration INTEGER,
    sleep_efficiency REAL,
    
    -- Readiness metrics  
    readiness_score INTEGER,
    hrv_score REAL,
    resting_hr INTEGER,
    
    -- Training load
    total_training_time INTEGER,
    acute_training_load REAL,
    chronic_training_load REAL,
    training_stress_balance REAL,
    
    -- Calculated metrics
    fatigue_index REAL,
    form_index REAL,
    fitness_index REAL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);
```

## Data Processing Pipeline Design

### 1. Stream Processing (Apache Kafka + Kafka Streams)

```python
class StreamProcessingTopology:
    """Real-time data processing pipeline"""
    
    def build_topology(self):
        builder = StreamsBuilder()
        
        # Raw data ingestion streams
        oura_stream = builder.stream('oura_raw_data')
        garmin_stream = builder.stream('garmin_raw_data')
        
        # Data validation and enrichment
        validated_oura = oura_stream.filter(
            lambda key, value: self.validate_oura_data(value)
        ).map_values(self.enrich_oura_data)
        
        validated_garmin = garmin_stream.filter(
            lambda key, value: self.validate_garmin_data(value)
        ).map_values(self.enrich_garmin_data)
        
        # Aggregate streams by user
        user_aggregates = validated_oura.join(
            validated_garmin,
            lambda oura_data, garmin_data: self.combine_metrics(oura_data, garmin_data),
            JoinWindows.of(Duration.of_hours(24))
        )
        
        # Real-time alerting
        alerts = user_aggregates.filter(
            lambda key, value: self.detect_anomalies(value)
        )
        alerts.to('user_alerts')
        
        # Store processed data
        user_aggregates.to('processed_metrics')
        
        return builder.build()
```

### 2. Batch Processing Pipeline (Apache Airflow)

```python
from airflow import DAG
from airflow.operators.python import PythonOperator

class AthleticAnalyticsPipeline:
    """Daily batch processing for complex analytics"""
    
    def create_dag(self):
        dag = DAG(
            'athletic_analytics_pipeline',
            schedule_interval='0 6 * * *',  # Daily at 6 AM
            catchup=False
        )
        
        # Data quality checks
        validate_data = PythonOperator(
            task_id='validate_daily_data',
            python_callable=self.validate_data_quality,
            dag=dag
        )
        
        # Calculate training load metrics
        calculate_training_load = PythonOperator(
            task_id='calculate_training_load',
            python_callable=self.calculate_acute_chronic_workload,
            dag=dag
        )
        
        # Sleep analysis and scoring
        analyze_sleep = PythonOperator(
            task_id='analyze_sleep_patterns',
            python_callable=self.analyze_sleep_quality,
            dag=dag
        )
        
        # ML model inference
        generate_predictions = PythonOperator(
            task_id='generate_performance_predictions',
            python_callable=self.run_ml_inference,
            dag=dag
        )
        
        # Generate recommendations
        create_recommendations = PythonOperator(
            task_id='create_daily_recommendations',
            python_callable=self.generate_recommendations,
            dag=dag
        )
        
        # Pipeline dependencies
        validate_data >> [calculate_training_load, analyze_sleep]
        [calculate_training_load, analyze_sleep] >> generate_predictions
        generate_predictions >> create_recommendations
        
        return dag
```

### 3. ML Feature Engineering Pipeline

```python
class FeatureEngineeringPipeline:
    """Creates ML-ready features from raw athletic data"""
    
    def create_features(self, user_id: str, lookback_days: int = 30):
        features = {}
        
        # Training load features
        features.update(self.calculate_training_features(user_id, lookback_days))
        
        # Recovery features  
        features.update(self.calculate_recovery_features(user_id, lookback_days))
        
        # Sleep features
        features.update(self.calculate_sleep_features(user_id, lookback_days))
        
        # Temporal features
        features.update(self.calculate_temporal_features(user_id))
        
        return features
    
    def calculate_training_features(self, user_id: str, days: int):
        """Rolling training load calculations"""
        return {
            'acute_training_load_7d': self.calculate_atl(user_id, 7),
            'chronic_training_load_28d': self.calculate_ctl(user_id, 28),
            'training_stress_balance': self.calculate_tsb(user_id),
            'training_monotony': self.calculate_monotony(user_id, days),
            'training_strain': self.calculate_strain(user_id, days),
            'power_duration_curve_fatigue': self.calculate_pdc_fatigue(user_id),
            'volume_intensity_ratio': self.calculate_vi_ratio(user_id, days)
        }
```

## Recommendation Engine Architecture

### 1. Rule-Based Recommendation System

```python
class RecommendationEngine:
    """Generates actionable recommendations based on data analysis"""
    
    def __init__(self):
        self.rules = self.load_recommendation_rules()
        self.ml_models = self.load_ml_models()
    
    def generate_daily_recommendations(self, user_id: str) -> Dict:
        # Get latest user data
        user_data = self.get_user_metrics(user_id)
        features = self.feature_pipeline.create_features(user_id)
        
        recommendations = {
            'training': self.recommend_training_intensity(features),
            'sleep': self.recommend_sleep_optimization(features),
            'recovery': self.recommend_recovery_interventions(features),
            'performance': self.predict_performance_window(features)
        }
        
        return recommendations
    
    def recommend_training_intensity(self, features: Dict) -> Dict:
        """Determines optimal training intensity for today"""
        
        