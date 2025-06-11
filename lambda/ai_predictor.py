import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
from collections import defaultdict
import boto3

logger = logging.getLogger()

class PredictiveRiskAnalytics:
    """Predictive analytics for proactive intervention"""
    
    # Risk patterns and their weights
    RISK_PATTERNS = {
        'declining_sentiment': {
            'weight': 8.0,
            'threshold': -0.2,  # 0.2 point decline
            'window_days': 7
        },
        'increased_frequency': {
            'weight': 5.0,
            'threshold': 2.0,   # 2x normal frequency
            'window_days': 3
        },
        'time_silence': {
            'weight': 6.0,
            'threshold': 72,    # 72 hours silence
            'window_days': 7
        },
        'language_intensity': {
            'weight': 7.0,
            'threshold': 1.5,   # 1.5x increase in negative words
            'window_days': 5
        },
        'crisis_keywords': {
            'weight': 9.0,
            'threshold': 2,     # 2+ crisis keywords
            'window_days': 3
        },
        'isolation_indicators': {
            'weight': 6.0,
            'threshold': 3,     # 3+ isolation mentions
            'window_days': 7
        }
    }
    
    # Intervention thresholds
    INTERVENTION_LEVELS = {
        'monitor': 30,
        'check_in': 50,
        'alert_single': 70,
        'alert_multiple': 85,
        'crisis': 95
    }
    
    def __init__(self, dynamodb_table, sns_client, events_client):
        self.user_table = dynamodb_table
        self.sns = sns_client
        self.events = events_client
        self.pattern_cache = {}
    
    def analyze_user_risk(self, user_id: str) -> Dict:
        """
        Comprehensive risk analysis for a user
        """
        # Get user history
        user_data = self._get_user_history(user_id)
        if not user_data or not user_data.get('analysis_history'):
            return {
                'risk_score': 0,
                'risk_level': 'unknown',
                'patterns_detected': [],
                'recommended_action': 'continue_monitoring'
            }
        
        # Analyze patterns
        patterns_detected = []
        total_risk_score = 0
        
        # Check each risk pattern
        for pattern_name, config in self.RISK_PATTERNS.items():
            pattern_score = self._check_pattern(
                pattern_name,
                config,
                user_data
            )
            
            if pattern_score > 0:
                patterns_detected.append({
                    'pattern': pattern_name,
                    'score': pattern_score,
                    'severity': self._get_severity(pattern_score)
                })
                total_risk_score += pattern_score
        
        # Normalize risk score to 0-100
        risk_score = min(100, total_risk_score)
        
        # Determine risk level and action
        risk_level, recommended_action = self._determine_intervention(
            risk_score,
            patterns_detected,
            user_data
        )
        
        # Calculate trajectory
        trajectory = self._calculate_trajectory(user_data)
        
        # Build comprehensive analysis
        analysis = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'patterns_detected': patterns_detected,
            'trajectory': trajectory,
            'recommended_action': recommended_action,
            'last_check_in': user_data.get('last_check_in'),
            'check_in_count': len(user_data.get('analysis_history', [])),
            'baseline_deviation': self._calculate_baseline_deviation(user_data)
        }
        
        # Store analysis
        self._store_risk_analysis(user_id, analysis)
        
        # Trigger interventions if needed
        if risk_score >= self.INTERVENTION_LEVELS['check_in']:
            self._trigger_intervention(user_id, analysis)
        
        return analysis
    
    def _check_pattern(self, pattern_name: str, config: Dict, user_data: Dict) -> float:
        """Check for specific risk pattern"""
        history = user_data.get('analysis_history', [])
        if not history:
            return 0
        
        # Get relevant time window
        cutoff_date = datetime.now() - timedelta(days=config['window_days'])
        recent_history = [
            h for h in history 
            if datetime.fromisoformat(h.get('timestamp', '')) > cutoff_date
        ]
        
        if not recent_history:
            return 0
        
        score = 0
        
        if pattern_name == 'declining_sentiment':
            score = self._check_declining_sentiment(recent_history, config)
        elif pattern_name == 'increased_frequency':
            score = self._check_increased_frequency(recent_history, user_data, config)
        elif pattern_name == 'time_silence':
            score = self._check_silence_period(user_data, config)
        elif pattern_name == 'language_intensity':
            score = self._check_language_intensity(recent_history, config)
        elif pattern_name == 'crisis_keywords':
            score = self._check_crisis_keywords(recent_history, config)
        elif pattern_name == 'isolation_indicators':
            score = self._check_isolation(recent_history, config)
        
        return score * config['weight']
    
    def _check_declining_sentiment(self, history: List[Dict], config: Dict) -> float:
        """Check for declining sentiment trend"""
        if len(history) < 2:
            return 0
        
        sentiments = [h.get('sentiment_score', 0) for h in history]
        
        # Calculate trend
        if len(sentiments) >= 3:
            # Linear regression for trend
            x = np.arange(len(sentiments))
            slope, _ = np.polyfit(x, sentiments, 1)
            
            if slope < -config['threshold']:
                return abs(slope) / config['threshold']
        
        # Simple comparison for short history
        decline = sentiments[0] - sentiments[-1]
        if decline > config['threshold']:
            return decline / config['threshold']
        
        return 0
    
    def _check_increased_frequency(self, history: List[Dict], user_data: Dict, config: Dict) -> float:
        """Check for increased check-in frequency"""
        # Calculate current frequency
        timestamps = [
            datetime.fromisoformat(h.get('timestamp', ''))
            for h in history
        ]
        
        if len(timestamps) < 2:
            return 0
        
        # Average time between check-ins
        deltas = []
        for i in range(1, len(timestamps)):
            delta = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # hours
            deltas.append(delta)
        
        current_avg_hours = sum(deltas) / len(deltas)
        
        # Get baseline frequency
        baseline_frequency = user_data.get('baseline_check_in_hours', 48)
        
        if current_avg_hours < baseline_frequency / config['threshold']:
            return baseline_frequency / current_avg_hours
        
        return 0
    
    def _check_silence_period(self, user_data: Dict, config: Dict) -> float:
        """Check for concerning silence periods"""
        last_check_in = user_data.get('last_check_in')
        if not last_check_in:
            return 0
        
        last_time = datetime.fromisoformat(last_check_in)
        hours_silent = (datetime.now() - last_time).total_seconds() / 3600
        
        if hours_silent > config['threshold']:
            return hours_silent / config['threshold']
        
        return 0
    
    def _check_language_intensity(self, history: List[Dict], config: Dict) -> float:
        """Check for intensifying negative language"""
        negative_word_counts = []
        
        for h in history:
            risk_factors = h.get('risk_factors', [])
            negative_count = len([f for f in risk_factors if 'protective' not in str(f)])
            negative_word_counts.append(negative_count)
        
        if len(negative_word_counts) >= 2:
            recent_avg = sum(negative_word_counts[-2:]) / 2
            older_avg = sum(negative_word_counts[:-2]) / max(1, len(negative_word_counts[:-2]))
            
            if older_avg > 0 and recent_avg / older_avg > config['threshold']:
                return recent_avg / older_avg
        
        return 0
    
    def _check_crisis_keywords(self, history: List[Dict], config: Dict) -> float:
        """Check for crisis-related keywords"""
        crisis_count = 0
        
        for h in history:
            risk_factors = h.get('risk_factors', [])
            crisis_indicators = [
                'end it', 'suicide', 'kill myself', 'gun', 'pills',
                'goodbye', 'sorry for everything'
            ]
            
            for factor in risk_factors:
                if any(crisis in str(factor).lower() for crisis in crisis_indicators):
                    crisis_count += 1
        
        if crisis_count >= config['threshold']:
            return crisis_count / config['threshold']
        
        return 0
    
    def _check_isolation(self, history: List[Dict], config: Dict) -> float:
        """Check for isolation indicators"""
        isolation_count = 0
        
        for h in history:
            entities = h.get('entities', [])
            risk_factors = h.get('risk_factors', [])
            
            # Check for lack of people mentions
            people_mentioned = len([e for e in entities if e.get('type') == 'PERSON'])
            if people_mentioned == 0:
                isolation_count += 1
            
            # Check for isolation keywords
            isolation_keywords = ['alone', 'nobody', 'isolated', 'no one']
            for factor in risk_factors:
                if any(keyword in str(factor).lower() for keyword in isolation_keywords):
                    isolation_count += 1
        
        if isolation_count >= config['threshold']:
            return isolation_count / config['threshold']
        
        return 0
    
    def _calculate_trajectory(self, user_data: Dict) -> str:
        """Calculate overall trajectory (improving, stable, declining)"""
        history = user_data.get('analysis_history', [])
        if len(history) < 3:
            return 'insufficient_data'
        
        recent = history[-3:]
        sentiments = [h.get('sentiment_score', 0) for h in recent]
        risks = [h.get('risk_score', 0) for h in recent]
        
        # Check sentiment trend
        sentiment_trend = sentiments[-1] - sentiments[0]
        risk_trend = risks[-1] - risks[0]
        
        if sentiment_trend > 0.2 and risk_trend < -10:
            return 'improving'
        elif sentiment_trend < -0.2 or risk_trend > 10:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_baseline_deviation(self, user_data: Dict) -> float:
        """Calculate deviation from user's baseline"""
        baseline = user_data.get('baseline_sentiment', -0.2)
        recent_sentiment = user_data.get('last_sentiment_score', baseline)
        
        return abs(recent_sentiment - baseline)
    
    def _determine_intervention(self, 
                               risk_score: float,
                               patterns: List[Dict],
                               user_data: Dict) -> Tuple[str, str]:
        """Determine risk level and recommended intervention"""
        # Risk level
        if risk_score >= self.INTERVENTION_LEVELS['crisis']:
            risk_level = 'critical'
        elif risk_score >= self.INTERVENTION_LEVELS['alert_multiple']:
            risk_level = 'high'
        elif risk_score >= self.INTERVENTION_LEVELS['alert_single']:
            risk_level = 'elevated'
        elif risk_score >= self.INTERVENTION_LEVELS['check_in']:
            risk_level = 'moderate'
        else:
            risk_level = 'low'
        
        # Recommended action based on patterns and level
        if risk_level == 'critical':
            action = 'immediate_crisis_intervention'
        elif risk_level == 'high':
            action = 'alert_multiple_contacts'
        elif risk_level == 'elevated':
            action = 'alert_trusted_contact'
        elif risk_level == 'moderate':
            action = 'proactive_check_in'
        else:
            action = 'continue_monitoring'
        
        # Adjust based on specific patterns
        if any(p['pattern'] == 'time_silence' for p in patterns) and risk_score > 40:
            action = 'welfare_check'
        
        return risk_level, action
    
    def _trigger_intervention(self, user_id: str, analysis: Dict):
        """Trigger appropriate intervention based on analysis"""
        action = analysis['recommended_action']
        
        logger.info(f"Triggering intervention for {user_id}: {action}")
        
        if action == 'proactive_check_in':
            self._send_check_in_reminder(user_id)
        
        elif action in ['alert_trusted_contact', 'alert_multiple_contacts']:
            self._trigger_alert_event(user_id, analysis)
        
        elif action == 'immediate_crisis_intervention':
            self._trigger_crisis_protocol(user_id, analysis)
        
        elif action == 'welfare_check':
            self._request_welfare_check(user_id, analysis)
    
    def _send_check_in_reminder(self, user_id: str):
        """Send proactive check-in reminder"""
        # This would integrate with notification system
        logger.info(f"Sending check-in reminder to {user_id}")
    
    def _trigger_alert_event(self, user_id: str, analysis: Dict):
        """Trigger EventBridge event for alerts"""
        self.events.put_events(
            Entries=[{
                'Source': 'your6.analytics',
                'DetailType': 'Predictive Risk Alert',
                'Detail': json.dumps({
                    'userId': user_id,
                    'riskScore': analysis['risk_score'],
                    'riskLevel': analysis['risk_level'],
                    'patterns': analysis['patterns_detected'],
                    'action': analysis['recommended_action']
                })
            }]
        )
    
    def _trigger_crisis_protocol(self, user_id: str, analysis: Dict):
        """Trigger immediate crisis intervention"""
        # Alert all contacts and crisis services
        logger.critical(f"CRISIS PROTOCOL TRIGGERED for {user_id}")
        self._trigger_alert_event(user_id, analysis)
        
        # Additional crisis-specific actions
        # This would integrate with emergency services if configured
    
    def _request_welfare_check(self, user_id: str, analysis: Dict):
        """Request welfare check for silent user"""
        logger.warning(f"Welfare check requested for {user_id} - silent for {analysis.get('last_check_in')}")
        self._trigger_alert_event(user_id, analysis)
    
    def _store_risk_analysis(self, user_id: str, analysis: Dict):
        """Store risk analysis for future reference"""
        try:
            self.user_table.update_item(
                Key={'userId': user_id},
                UpdateExpression='SET last_risk_analysis = :analysis',
                ExpressionAttributeValues={
                    ':analysis': analysis
                }
            )
        except Exception as e:
            logger.error(f"Error storing risk analysis: {str(e)}")
    
    def _get_severity(self, score: float) -> str:
        """Convert score to severity level"""
        if score > 8:
            return 'critical'
        elif score > 5:
            return 'high'
        elif score > 3:
            return 'moderate'
        else:
            return 'low'