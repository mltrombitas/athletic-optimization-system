# Recommendation Engine Design

**Athletic Optimization System - Analysis & Decision Logic**

# Athletic Performance Recommendation Engine

## 1. CORE ANALYTICAL FRAMEWORK

### Data Preprocessing & Feature Engineering

```python
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import warnings

class AthleteDataProcessor:
    def __init__(self):
        self.baseline_window = 28  # days for baseline calculation
        self.trend_windows = [3, 7, 14, 28]  # multi-timeframe analysis
        
    def calculate_baselines(self, df):
        """Calculate rolling baselines for key metrics"""
        baselines = {}
        
        # RHR baseline (28-day rolling median to reduce noise)
        baselines['rhr_baseline'] = df['rhr'].rolling(
            window=self.baseline_window, min_periods=14
        ).median()
        
        # HRV baseline (28-day rolling mean with IQR filtering)
        hrv_filtered = df['hrv'].clip(
            lower=df['hrv'].quantile(0.1),
            upper=df['hrv'].quantile(0.9)
        )
        baselines['hrv_baseline'] = hrv_filtered.rolling(
            window=self.baseline_window, min_periods=14
        ).mean()
        
        # Sleep efficiency baseline
        baselines['sleep_eff_baseline'] = df['sleep_efficiency'].rolling(
            window=self.baseline_window, min_periods=14
        ).mean()
        
        return baselines
    
    def calculate_deviations(self, df, baselines):
        """Calculate percentage deviations from baseline"""
        deviations = {}
        
        # RHR deviation (higher = worse)
        deviations['rhr_dev'] = (
            (df['rhr'] - baselines['rhr_baseline']) / baselines['rhr_baseline'] * 100
        )
        
        # HRV deviation (higher = better)
        deviations['hrv_dev'] = (
            (df['hrv'] - baselines['hrv_baseline']) / baselines['hrv_baseline'] * 100
        )
        
        # Sleep efficiency deviation
        deviations['sleep_dev'] = (
            (df['sleep_efficiency'] - baselines['sleep_eff_baseline']) / 
            baselines['sleep_eff_baseline'] * 100
        )
        
        return deviations
    
    def calculate_training_load_metrics(self, df):
        """Advanced training load calculations"""
        # Acute:Chronic Workload Ratio (ACWR)
        acute_load = df['training_load'].rolling(window=7, min_periods=5).mean()
        chronic_load = df['training_load'].rolling(window=28, min_periods=20).mean()
        acwr = acute_load / chronic_load
        
        # Training Stress Balance (TSB)
        ctl = df['training_load'].ewm(span=42).mean()  # Chronic Training Load
        atl = df['training_load'].ewm(span=7).mean()   # Acute Training Load
        tsb = ctl - atl
        
        # Load progression rate
        load_7d = df['training_load'].rolling(window=7).mean()
        load_28d = df['training_load'].rolling(window=28).mean()
        load_progression = (load_7d - load_28d) / load_28d * 100
        
        return {
            'acwr': acwr,
            'tsb': tsb,
            'load_progression': load_progression,
            'ctl': ctl,
            'atl': atl
        }
```

## 2. DECISION TREE LOGIC & THRESHOLDS

### Recovery Status Assessment

```python
class RecoveryAssessment:
    def __init__(self):
        self.thresholds = {
            # RHR thresholds (% above baseline)
            'rhr_green': 2,      # <2% = good
            'rhr_yellow': 5,     # 2-5% = moderate concern
            'rhr_red': 8,        # >5% = high concern
            
            # HRV thresholds (% below baseline)
            'hrv_green': -10,    # >-10% = good
            'hrv_yellow': -20,   # -10 to -20% = moderate concern
            'hrv_red': -30,      # <-20% = high concern
            
            # Sleep thresholds
            'sleep_duration_min': 6.5,   # hours
            'sleep_efficiency_min': 85,  # %
            'deep_sleep_min': 15,        # % of total sleep
            
            # Recovery score thresholds
            'recovery_good': 75,
            'recovery_moderate': 60,
            'recovery_poor': 45,
            
            # Training load thresholds
            'acwr_optimal_low': 0.8,
            'acwr_optimal_high': 1.3,
            'acwr_injury_risk': 1.5,
            
            # Body temperature (deviation from baseline)
            'temp_fever': 1.0,    # °C above baseline
            'temp_concern': 0.5,  # °C above baseline
        }
    
    def assess_recovery_status(self, metrics):
        """
        Multi-dimensional recovery assessment
        Returns: score (0-100), status, and component breakdown
        """
        scores = {}
        weights = {
            'rhr': 0.25,
            'hrv': 0.30,
            'sleep': 0.25,
            'recovery_score': 0.15,
            'body_temp': 0.05
        }
        
        # RHR component (inverted - higher deviation = lower score)
        if metrics['rhr_dev'] < self.thresholds['rhr_green']:
            scores['rhr'] = 100
        elif metrics['rhr_dev'] < self.thresholds['rhr_yellow']:
            scores['rhr'] = 70
        elif metrics['rhr_dev'] < self.thresholds['rhr_red']:
            scores['rhr'] = 40
        else:
            scores['rhr'] = 20
            
        # HRV component
        if metrics['hrv_dev'] > self.thresholds['hrv_green']:
            scores['hrv'] = 100
        elif metrics['hrv_dev'] > self.thresholds['hrv_yellow']:
            scores['hrv'] = 70
        elif metrics['hrv_dev'] > self.thresholds['hrv_red']:
            scores['hrv'] = 40
        else:
            scores['hrv'] = 20
            
        # Sleep component (composite of duration, efficiency, deep sleep)
        sleep_components = [
            min(100, metrics['sleep_duration'] / 8 * 100),
            metrics['sleep_efficiency'],
            min(100, metrics['deep_sleep_pct'] / 20 * 100)
        ]
        scores['sleep'] = np.mean(sleep_components)
        
        # Recovery score (direct mapping)
        scores['recovery_score'] = metrics['oura_readiness']
        
        # Body temperature
        if metrics['temp_dev'] < self.thresholds['temp_concern']:
            scores['body_temp'] = 100
        elif metrics['temp_dev'] < self.thresholds['temp_fever']:
            scores['body_temp'] = 60
        else:
            scores['body_temp'] = 20
            
        # Calculate weighted final score
        final_score = sum(scores[k] * weights[k] for k in scores.keys())
        
        # Determine status
        if final_score >= 80:
            status = 'OPTIMAL'
        elif final_score >= 65:
            status = 'GOOD'
        elif final_score >= 50:
            status = 'MODERATE'
        else:
            status = 'POOR'
            
        return final_score, status, scores
```

### Training Recommendation Engine

```python
class TrainingRecommendationEngine:
    def __init__(self):
        self.recovery_assessment = RecoveryAssessment()
        
    def generate_daily_recommendation(self, current_metrics, training_history):
        """
        Main decision tree for daily training recommendations
        """
        # Step 1: Assess current recovery
        recovery_score, recovery_status, recovery_breakdown = \
            self.recovery_assessment.assess_recovery_status(current_metrics)
        
        # Step 2: Check training load context
        acwr = current_metrics.get('acwr', 1.0)
        tsb = current_metrics.get('tsb', 0)
        days_since_hard = self._days_since_last_hard_session(training_history)
        weekly_load_trend = current_metrics.get('load_progression', 0)
        
        # Step 3: Apply decision tree logic
        recommendation = self._decision_tree_logic(
            recovery_score=recovery_score,
            recovery_status=recovery_status,
            acwr=acwr,
            tsb=tsb,
            days_since_hard=days_since_hard,
            weekly_load_trend=weekly_load_trend,
            recovery_breakdown=recovery_breakdown
        )
        
        return recommendation
    
    def _decision_tree_logic(self, recovery_score, recovery_status, acwr, tsb, 
                           days_since_hard, weekly_load_trend, recovery_breakdown):
        """
        Hierarchical decision tree for training recommendations
        """
        
        # CRITICAL FLAGS - Override everything
        if (recovery_breakdown['body_temp'] < 50 or 
            recovery_breakdown['rhr'] < 30 or
            recovery_breakdown['hrv'] < 30):
            return {
                'recommendation': 'REST',
                'confidence': 0.95,
                'reason': 'Critical recovery flags detected',
                'details': 'Elevated temperature, severe RHR elevation, or HRV suppression'
            }
        
        # OVERTRAINING/INJURY RISK
        if acwr > 1.5 or weekly_load_trend > 30:
            return {
                'recommendation': 'EASY_OR_REST',
                'confidence': 0.90,
                'reason': 'High injury risk from load progression',
                'details': f'ACWR: {acwr:.2f}, Load increase: {weekly_load_trend:.1f}%'
            }
        
        # RECOVERY-BASED DECISIONS
        if recovery_status == 'OPTIMAL':
            if days_since_hard >= 2 and tsb > -10:
                return {
                    'recommendation': 'HARD',
                    'confidence': 0.85,
                    'reason': 'Optimal recovery + adequate rest since last hard session',
                    'details': f'Recovery score: {recovery_score:.0f}, TSB: {tsb:.1f}'
                }
            elif days_since_hard >= 1:
                return {
                    'recommendation': 'MODERATE',
                    'confidence': 0.80,
                    'reason': 'Good recovery, moderate load appropriate',
                    'details': f'Recovery score: {recovery_score:.0f}'
                }
            else:
                return {
                    'recommendation': 'EASY',
                    'confidence': 0.75,
                    'reason': 'Good recovery but need spacing from previous hard session',
                    'details': 'Allow recovery time between hard sessions'
                }
        
        elif recovery_status == 'GOOD':
            if days_since_hard >= 3 and acwr < 1.2:
                return {
                    'recommendation': 'MODERATE',
                    'confidence': 0.75,
                    'reason': 'Good recovery allows moderate intensity',
                    'details': f'Recovery score: {recovery_score:.0f}, ACWR: {acwr:.2f}'
                }
            else:
                return {
                    'recommendation': 'EASY',
                    'confidence': 0.80,
                    'reason': 'Good recovery but conservative approach recommended',
                    'details': 'Easy training maintains fitness while supporting recovery'
                }
        
        elif recovery_status == 'MODERATE':
            if days_since_hard >= 2 and recovery_score > 55:
                return {
                    'recommendation': 'EASY',
                    'confidence': 0.85,
                    'reason': 'Moderate recovery - easy training only',
                    'details': f'Recovery score: {recovery_score:.0f}'
                }
            else:
                return {
                    'recommendation': 'REST',
                    'confidence': 0.80,
                    'reason': 'Moderate recovery with recent stress',
                    'details': 'Complete rest recommended for recovery optimization'
                }
        
        else:  # POOR recovery
            return {
                'recommendation': 'REST',
                'confidence': 0.90,
                'reason': 'Poor recovery status',
                'details': f'Recovery score: {recovery_score:.0f} - prioritize recovery'
            }
    
    def _days_since_last_hard_session(self, training_history, lookback_days=7):
        """Count days since last high-intensity session"""
        if not training_history:
            return 7  # Default to allowing hard session
        
        for i, session in enumerate(training_history[-lookback_days:]):
            if session.get('intensity', 'easy') in ['hard', 'high', 'threshold', 'vo2max']:
                return i + 1
        return lookback_days  # No hard session found in lookback period
```

## 3. RECOVERY INTERVENTIONS ENGINE

```python
class RecoveryInterventions:
    def __init__(self):
        self.sleep_optimizer = SleepOptimizer()
        self.active_recovery = ActiveRecoveryProtocols()
    
    def generate_interventions(self, metrics, recovery_breakdown):
        """Generate targeted recovery interventions"""
        interventions = []
        
        # Sleep optimization
        if recovery_breakdown['sleep'] < 70:
            sleep_interventions = self.sleep_optimizer.generate_recommendations(metrics)
            interventions.extend(sleep_interventions)
        
        # HRV-based interventions
        if recovery_breakdown['hrv'] < 60:
            interventions.extend(self._hrv_interventions(metrics))
        
        # RHR-based interventions
        if recovery_breakdown['rhr'] < 60:
            interventions.extend(self._rhr_interventions(metrics))
        
        # Active recovery protocols
        if metrics.get('days_since_easy', 0) > 2:
            interventions.extend(self.active_recovery.get_protocols(metrics))
        
        return self._prioritize_interventions(interventions)
    
    def _hrv_interventions(self, metrics):
        """HRV-specific recovery strategies"""
        interventions = []
        
        if metrics['hrv_dev'] < -20:
            interventions.extend([
                {
                    'type': 'breathing',
                    'priority': 'HIGH',
                    'intervention': 'Box breathing (4-4-4-4) for 10 minutes before bed',
                    'rationale': 'Parasympathetic nervous system activation'
                },
                {
                    'type': 'stress_management',
                    'priority': 'HIGH',
                    'intervention': 'Meditation or mindfulness practice (15+ minutes)',
                    'rationale': 'Reduce sympathetic nervous system activation'
                },
                {
                    'type': 'recovery_modality',
                    'priority': 'MEDIUM',
                    'intervention': 'Cold exposure (2-3 min cold shower/ice bath)',
                    'rationale': 'Vagal tone improvement and stress adaptation'
                }
            ])
        
        return interventions
    
    def _rhr_interventions(self,