# Recommendation Engine Design

**Athletic Optimization System - Analysis & Decision Logic**

# Athletic Performance Optimization Recommendation Engine

## 1. Core Algorithm Architecture

### 1.1 Weighted Scoring System

```python
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from scipy import stats

class AthleteRecommendationEngine:
    def __init__(self):
        # Weight factors for different metrics (sum = 1.0)
        self.weights = {
            'hrv_score': 0.25,
            'rhr_score': 0.20,
            'sleep_score': 0.20,
            'recovery_score': 0.15,
            'training_load_score': 0.10,
            'spo2_score': 0.05,
            'temp_score': 0.05
        }
        
        # Baseline tracking
        self.baselines = {}
        self.trend_windows = {'short': 3, 'medium': 7, 'long': 28}
    
    def calculate_baselines(self, historical_data, days=28):
        """Calculate rolling baselines for each metric"""
        metrics = ['rhr', 'hrv', 'sleep_efficiency', 'body_temp', 'spo2']
        
        for metric in metrics:
            self.baselines[metric] = {
                'mean': historical_data[metric].rolling(days).mean().iloc[-1],
                'std': historical_data[metric].rolling(days).std().iloc[-1],
                'percentile_10': historical_data[metric].rolling(days).quantile(0.1).iloc[-1],
                'percentile_90': historical_data[metric].rolling(days).quantile(0.9).iloc[-1]
            }
```

### 1.2 Individual Metric Scoring Functions

```python
def calculate_hrv_score(self, current_hrv, trend_days=7):
    """HRV Score: Higher = Better Recovery"""
    baseline = self.baselines['hrv']['mean']
    std = self.baselines['hrv']['std']
    
    # Z-score calculation
    z_score = (current_hrv - baseline) / std if std > 0 else 0
    
    # Convert to 0-100 scale
    if z_score >= 1.0:  # >1 SD above baseline
        return 100
    elif z_score >= 0.5:  # 0.5-1 SD above
        return 85
    elif z_score >= -0.5:  # Within 0.5 SD
        return 70
    elif z_score >= -1.0:  # 0.5-1 SD below
        return 40
    else:  # >1 SD below baseline
        return 10

def calculate_rhr_score(self, current_rhr):
    """RHR Score: Lower = Better Recovery"""
    baseline = self.baselines['rhr']['mean']
    
    deviation = current_rhr - baseline
    
    if deviation <= -3:  # 3+ bpm below baseline
        return 100
    elif deviation <= -1:  # 1-3 bpm below
        return 85
    elif deviation <= 1:  # Within 1 bpm
        return 70
    elif deviation <= 3:  # 1-3 bpm above (YELLOW FLAG)
        return 40
    elif deviation <= 5:  # 3-5 bpm above (RED FLAG)
        return 20
    else:  # >5 bpm above (CRITICAL)
        return 0

def calculate_sleep_score(self, sleep_efficiency, duration, deep_sleep_pct):
    """Composite sleep score"""
    # Sleep efficiency score (target: >85%)
    eff_score = min(100, (sleep_efficiency / 85) * 100) if sleep_efficiency > 0 else 0
    
    # Duration score (target: 7-9 hours for athletes)
    if 7 <= duration <= 9:
        dur_score = 100
    elif 6.5 <= duration < 7 or 9 < duration <= 9.5:
        dur_score = 80
    elif 6 <= duration < 6.5 or 9.5 < duration <= 10:
        dur_score = 60
    else:
        dur_score = 30
    
    # Deep sleep score (target: >20%)
    deep_score = min(100, (deep_sleep_pct / 20) * 100) if deep_sleep_pct > 0 else 0
    
    # Weighted composite (40% efficiency, 35% duration, 25% deep sleep)
    return (eff_score * 0.4 + dur_score * 0.35 + deep_score * 0.25)

def calculate_training_load_score(self, current_load, historical_loads):
    """Training load vs recovery balance"""
    # Calculate acute:chronic load ratio
    acute_load = np.mean(historical_loads[-7:])  # 7-day average
    chronic_load = np.mean(historical_loads[-28:])  # 28-day average
    
    ac_ratio = acute_load / chronic_load if chronic_load > 0 else 1.0
    
    # Optimal ratio: 0.8-1.3
    if 0.8 <= ac_ratio <= 1.3:
        return 100
    elif 0.7 <= ac_ratio < 0.8 or 1.3 < ac_ratio <= 1.5:
        return 70  # Slight concern
    elif ac_ratio < 0.7 or ac_ratio > 1.5:
        return 30  # High concern
    else:
        return 0
```

## 2. Decision Tree Logic

### 2.1 Daily Training Recommendation Algorithm

```python
def generate_training_recommendation(self, scores, trend_analysis):
    """
    Decision tree for daily training recommendations
    """
    # Calculate composite readiness score
    readiness = sum(scores[metric] * self.weights[metric] for metric in scores)
    
    # Get trend information
    hrv_trend = trend_analysis['hrv']['slope_7d']
    rhr_trend = trend_analysis['rhr']['slope_7d']
    sleep_trend = trend_analysis['sleep']['avg_7d']
    
    # Critical flags
    critical_flags = self._check_critical_flags(scores)
    
    if critical_flags['count'] >= 2:
        return {
            'recommendation': 'REST_DAY',
            'intensity': 0,
            'confidence': 0.95,
            'reasoning': f"Multiple critical flags detected: {critical_flags['flags']}"
        }
    
    # Main decision logic
    if readiness >= 80:
        if hrv_trend > 0 and scores['rhr_score'] >= 70:
            return {
                'recommendation': 'GO_HARD',
                'intensity': 0.85,
                'confidence': 0.90,
                'reasoning': 'High readiness, positive HRV trend, stable RHR'
            }
        else:
            return {
                'recommendation': 'GO_MODERATE',
                'intensity': 0.70,
                'confidence': 0.80,
                'reasoning': 'Good readiness but mixed recovery signals'
            }
    
    elif readiness >= 60:
        if trend_analysis['overall_trend'] == 'improving':
            return {
                'recommendation': 'GO_MODERATE',
                'intensity': 0.65,
                'confidence': 0.75,
                'reasoning': 'Moderate readiness with improving trend'
            }
        else:
            return {
                'recommendation': 'GO_EASY',
                'intensity': 0.50,
                'confidence': 0.80,
                'reasoning': 'Moderate readiness, prioritize recovery'
            }
    
    elif readiness >= 40:
        return {
            'recommendation': 'GO_EASY',
            'intensity': 0.45,
            'confidence': 0.85,
            'reasoning': 'Low readiness, active recovery recommended'
        }
    
    else:
        return {
            'recommendation': 'REST_DAY',
            'intensity': 0,
            'confidence': 0.90,
            'reasoning': 'Very low readiness, full rest required'
        }

def _check_critical_flags(self, scores):
    """Check for critical warning flags"""
    flags = []
    
    if scores['rhr_score'] <= 20:  # RHR >3 bpm above baseline
        flags.append('ELEVATED_RHR')
    
    if scores['hrv_score'] <= 20:  # HRV >1 SD below baseline
        flags.append('LOW_HRV')
    
    if scores['sleep_score'] <= 30:  # Poor sleep
        flags.append('POOR_SLEEP')
    
    if scores['spo2_score'] <= 30:  # Low oxygen saturation
        flags.append('LOW_SPO2')
    
    return {'flags': flags, 'count': len(flags)}
```

### 2.2 Alert Threshold Specifications

```python
class AlertSystem:
    def __init__(self):
        self.thresholds = {
            # Overtraining Risk
            'overtraining': {
                'rhr_elevation': {'yellow': 3, 'red': 5, 'critical': 7},  # bpm above baseline
                'hrv_depression': {'yellow': -15, 'red': -25, 'critical': -35},  # % below baseline
                'sleep_debt': {'yellow': 2, 'red': 4, 'critical': 7},  # hours cumulative deficit
                'training_load_ratio': {'yellow': 1.3, 'red': 1.5, 'critical': 1.8},  # acute:chronic
                'consecutive_hard_days': {'yellow': 3, 'red': 4, 'critical': 5}
            },
            
            # Injury Risk
            'injury_risk': {
                'load_spike': {'yellow': 1.3, 'red': 1.5},  # week-over-week increase
                'readiness_training_mismatch': {'yellow': 30, 'red': 50},  # high load + low readiness
                'pain_inflammation_markers': {'yellow': 0.5, 'red': 1.0}  # elevated temp/RHR combo
            },
            
            # Illness Risk
            'illness': {
                'rhr_hrv_combo': {'trigger': True},  # Both elevated RHR AND depressed HRV
                'temperature_elevation': {'yellow': 0.3, 'red': 0.5},  # °C above baseline
                'spo2_depression': {'yellow': -2, 'red': -4}  # % below baseline
            }
        }
    
    def evaluate_alerts(self, current_metrics, baselines, trends):
        """Generate alerts based on current metrics and trends"""
        alerts = {'overtraining': [], 'injury_risk': [], 'illness': []}
        
        # Overtraining evaluation
        rhr_deviation = current_metrics['rhr'] - baselines['rhr']['mean']
        hrv_deviation = ((current_metrics['hrv'] - baselines['hrv']['mean']) / 
                        baselines['hrv']['mean']) * 100
        
        # RHR Alert
        if rhr_deviation >= self.thresholds['overtraining']['rhr_elevation']['critical']:
            alerts['overtraining'].append({
                'type': 'CRITICAL_RHR_ELEVATION',
                'value': rhr_deviation,
                'message': f'RHR elevated {rhr_deviation:.1f} bpm above baseline'
            })
        elif rhr_deviation >= self.thresholds['overtraining']['rhr_elevation']['red']:
            alerts['overtraining'].append({
                'type': 'HIGH_RHR_ELEVATION',
                'value': rhr_deviation,
                'message': f'RHR elevated {rhr_deviation:.1f} bpm above baseline'
            })
        
        # HRV Alert
        if hrv_deviation <= self.thresholds['overtraining']['hrv_depression']['critical']:
            alerts['overtraining'].append({
                'type': 'CRITICAL_HRV_DEPRESSION',
                'value': hrv_deviation,
                'message': f'HRV depressed {abs(hrv_deviation):.1f}% below baseline'
            })
        
        # Illness detection (RHR + HRV combo)
        if (rhr_deviation >= 3 and hrv_deviation <= -15):
            alerts['illness'].append({
                'type': 'ILLNESS_RISK',
                'message': 'Combined RHR elevation and HRV depression detected'
            })
        
        return alerts
```

## 3. Recovery Intervention Engine

```python
class RecoveryInterventionEngine:
    def generate_interventions(self, scores, alerts, athlete_profile):
        """Generate personalized recovery interventions"""
        interventions = []
        
        # Sleep optimization
        if scores['sleep_score'] < 60:
            interventions.extend(self._sleep_interventions(scores))
        
        # Active recovery protocols
        if 30 <= scores['readiness'] < 60:
            interventions.extend(self._active_recovery_protocols())
        
        # Stress management
        if scores['hrv_score'] < 40 or len(alerts['overtraining']) > 0:
            interventions.extend(self._stress_management_protocols())
        
        return interventions
    
    def _sleep_interventions(self, scores):
        return [
            {
                'category': 'SLEEP_OPTIMIZATION',
                'priority': 'HIGH',
                'recommendations': [
                    'Target 8+ hours sleep tonight',
                    'Cool room to 65-68°F',
                    'Blue light blocking 2h before bed',
                    'Magnesium supplement 30min before bed',
                    'Progressive muscle relaxation'
                ]
            }
        ]
    
    def _active_recovery_protocols(self):
        return [
            {
                'category': 'ACTIVE_RECOVERY',
                'priority': 'MEDIUM',
                'recommendations': [
                    'Light movement: 20-30min easy walk/swim',
                    'Dynamic stretching routine',
                    'Foam rolling - focus on tight areas',
                    'Contrast shower (hot/cold therapy)',
                    'Meditation or breathing exercises'
                ]
            }
        ]
```

## 4. Performance Prediction Models

### 4.1 Fitness Trend Analysis

```python
class PerformancePredictionEngine:
    def __init__(self):
        self.fitness_model = RandomForestRegressor(n_estimators=100, random_state=42)
        
    def calculate_fitness_trend(self, historical_data, window_days=42):
        """Calculate fitness trend using multiple indicators"""
        
        # Prepare features
        features = ['rhr', 'hrv', 'training_load', 'recovery_score', 
                   'sleep_efficiency', 'performance_metrics']
        
        # Create composite fitness score
        fitness_scores = []
        dates = []
        
        for i in range(window_days, len(historical_data)):
            window_data = historical_data.iloc[i-window_days:i]
            
            # Weighted fitness calculation
            fitness_score = (
                (1 - window_data['rhr'].rolling(7).mean().iloc[-1] / 
                 window_data['rhr'].rolling(28).mean().iloc[-1]) * 0.2 +
                (window_data['hrv'].rolling(7).mean().iloc[-1] / 
                 window_data['hrv'].rolling(28).mean().iloc[-1]) * 0.