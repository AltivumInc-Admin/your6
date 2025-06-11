import json
import logging
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import boto3
from crisis_failsafe import apply_crisis_failsafe

logger = logging.getLogger()

class AdvancedSentimentAnalyzer:
    """Enhanced sentiment analysis with entity detection and risk scoring"""
    
    # High-risk indicators with weights
    RISK_INDICATORS = {
        # Critical phrases
        r'\b(end\s+it|ending\s+it|done\s+with\s+life|no\s+point)\b': 10.0,
        r'\b(kill\s+myself|suicide|suicidal)\b': 10.0,
        r'\b(better\s+off\s+dead|world\s+better\s+without)\b': 9.0,
        
        # Weapon/method mentions
        r'\b(gun|weapon|pills|rope|bridge)\b': 8.0,
        r'\b(overdose|OD|cut\s+myself|cutting)\b': 8.0,
        
        # Isolation indicators
        r'\b(alone|nobody\s+cares|no\s+one\s+understands)\b': 6.0,
        r'\b(burden|worthless|hopeless|trapped)\b': 7.0,
        r'\b(given\s+up|cant\s+go\s+on|exhausted)\b': 7.0,
        
        # Substance abuse
        r'\b(drinking\s+heavily|drunk\s+again|blackout)\b': 5.0,
        r'\b(using\s+again|relapsed|high)\b': 5.0,
        
        # Sleep/nightmare patterns
        r'\b(nightmares?\s+every\s+night|no\s+sleep|insomnia)\b': 4.0,
        r'\b(flashbacks?|PTSD|panic\s+attacks?)\b': 5.0,
        
        # Goodbye indicators
        r'\b(goodbye|farewell|this\s+is\s+it|final\s+message)\b': 9.0,
        r'\b(sorry\s+for\s+everything|forgive\s+me)\b': 8.0
    }
    
    # Positive indicators (reduce risk score)
    PROTECTIVE_FACTORS = {
        r'\b(reaching\s+out|getting\s+help|therapy)\b': -3.0,
        r'\b(family|friends|support\s+group)\b': -2.0,
        r'\b(improving|better\s+today|progress)\b': -2.0,
        r'\b(hope|future|goals|plans)\b': -3.0,
        r'\b(grateful|thankful|blessed)\b': -2.0
    }
    
    # Time-based risk multipliers
    TEMPORAL_RISK_FACTORS = {
        'late_night': 1.2,      # 11 PM - 4 AM
        'anniversary': 1.5,     # Death anniversaries, deployment dates
        'holiday': 1.3,         # Holidays often trigger isolation
        'weekend': 1.1         # Weekends can be isolating
    }
    
    def __init__(self, comprehend_client, dynamodb_table):
        self.comprehend = comprehend_client
        self.user_table = dynamodb_table
    
    def analyze_with_context(self, text: str, user_id: str) -> Dict:
        """
        Perform advanced sentiment analysis with entity detection and risk scoring
        """
        # Get user history for baseline
        user_profile = self._get_user_profile(user_id) or {}
        baseline_sentiment = user_profile.get('baseline_sentiment', -0.2)
        
        # Standard sentiment analysis
        sentiment_result = self.comprehend.detect_sentiment(
            Text=text,
            LanguageCode='en'
        )
        
        # Entity detection
        entities_result = self.comprehend.detect_entities(
            Text=text,
            LanguageCode='en'
        )
        
        # Syntax analysis for deeper understanding
        try:
            syntax_result = self.comprehend.detect_syntax(
                Text=text,
                LanguageCode='en'
            )
        except Exception as e:
            logger.warning(f"Syntax analysis failed: {str(e)}, continuing without it")
            syntax_result = {'SyntaxTokens': []}
        
        # Calculate risk score
        risk_score, risk_factors = self._calculate_risk_score(text)
        logger.info(f"Raw risk score calculated: {risk_score}, factors: {risk_factors}")
        
        # Adjust for temporal factors
        temporal_multiplier = self._get_temporal_multiplier()
        adjusted_risk_score = risk_score * temporal_multiplier
        logger.info(f"Adjusted risk score: {adjusted_risk_score} (multiplier: {temporal_multiplier})")
        
        # Apply crisis detection failsafe
        final_risk_score, failsafe_triggered, failsafe_reason = apply_crisis_failsafe(
            text, adjusted_risk_score, sentiment_score
        )
        if failsafe_triggered:
            logger.critical(f"Crisis failsafe applied: {failsafe_reason}")
            adjusted_risk_score = final_risk_score
        
        # Extract meaningful entities
        entities = self._extract_relevant_entities(entities_result, syntax_result)
        
        # Compare to baseline
        sentiment_score = sentiment_result['SentimentScore'][sentiment_result['Sentiment'].capitalize()]
        if sentiment_result['Sentiment'] == 'NEGATIVE':
            sentiment_score = -sentiment_score
        
        deviation_from_baseline = abs(sentiment_score - baseline_sentiment)
        
        # Build comprehensive analysis
        analysis = {
            'sentiment': sentiment_result['Sentiment'],
            'sentiment_score': sentiment_score,
            'baseline_deviation': deviation_from_baseline,
            'risk_score': adjusted_risk_score,
            'risk_factors': risk_factors,
            'entities': entities,
            'temporal_context': {
                'time_of_day': datetime.now().strftime('%H:%M'),
                'day_of_week': datetime.now().strftime('%A'),
                'temporal_multiplier': temporal_multiplier
            },
            'requires_immediate_attention': adjusted_risk_score > 50,
            'confidence_scores': sentiment_result['SentimentScore']
        }
        
        # Update user profile with new data point
        self._update_user_profile(user_id, analysis)
        
        logger.info(f"Advanced analysis complete for {user_id}: risk_score={adjusted_risk_score}, sentiment={sentiment_result['Sentiment']}")
        return analysis
    
    def _calculate_risk_score(self, text: str) -> Tuple[float, List[str]]:
        """Calculate risk score based on content indicators"""
        risk_score = 0.0
        risk_factors = []
        text_lower = text.lower()
        
        # Check risk indicators
        for pattern, weight in self.RISK_INDICATORS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                risk_score += weight
                risk_factors.append(pattern.strip('\\b()'))
        
        # Check protective factors
        for pattern, weight in self.PROTECTIVE_FACTORS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                risk_score += weight  # Note: weights are negative
                cleaned_pattern = pattern.strip('\\b()')
                risk_factors.append(f"protective: {cleaned_pattern}")
        
        # Ensure score is non-negative
        risk_score = max(0, risk_score)
        
        # Normalize to 0-100 scale
        risk_score = min(100, risk_score * 5)
        
        return risk_score, risk_factors
    
    def _get_temporal_multiplier(self) -> float:
        """Calculate temporal risk multiplier based on time/date"""
        now = datetime.now()
        hour = now.hour
        multiplier = 1.0
        
        # Late night hours
        if hour >= 23 or hour <= 4:
            multiplier *= self.TEMPORAL_RISK_FACTORS['late_night']
        
        # Weekend
        if now.weekday() >= 5:
            multiplier *= self.TEMPORAL_RISK_FACTORS['weekend']
        
        # Holiday check (simplified - would need holiday calendar)
        # Anniversary check (would need user-specific dates)
        
        return multiplier
    
    def _extract_relevant_entities(self, entities_result: Dict, syntax_result: Dict) -> List[Dict]:
        """Extract and categorize relevant entities"""
        relevant_entities = []
        
        for entity in entities_result.get('Entities', []):
            if entity['Score'] > 0.8:
                entity_info = {
                    'text': entity['Text'],
                    'type': entity['Type'],
                    'score': entity['Score']
                }
                
                # Special handling for PERSON entities (potential support network)
                if entity['Type'] == 'PERSON':
                    entity_info['potential_support'] = True
                
                # Location entities (potential risk if isolated)
                elif entity['Type'] == 'LOCATION':
                    entity_info['isolation_indicator'] = 'alone' in entity['Text'].lower()
                
                relevant_entities.append(entity_info)
        
        # Extract action verbs from syntax
        verbs = [token['Text'] for token in syntax_result.get('SyntaxTokens', []) 
                 if token.get('PartOfSpeech', {}).get('Tag') == 'VERB']
        
        if verbs:
            relevant_entities.append({
                'type': 'ACTIONS',
                'verbs': verbs[:5],  # Top 5 verbs
                'sentiment_indicator': True
            })
        
        return relevant_entities
    
    def _get_user_profile(self, user_id: str) -> Dict:
        """Get user's historical profile"""
        try:
            response = self.user_table.get_item(Key={'userId': user_id})
            return response.get('Item', {})
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return {}
    
    def _update_user_profile(self, user_id: str, analysis: Dict):
        """Update user profile with new analysis data"""
        try:
            # Calculate running average sentiment
            self.user_table.update_item(
                Key={'userId': user_id},
                UpdateExpression="""
                    SET last_analysis = :analysis,
                        analysis_history = list_append(if_not_exists(analysis_history, :empty_list), :new_analysis),
                        check_in_count = if_not_exists(check_in_count, :zero) + :one
                """,
                ExpressionAttributeValues={
                    ':analysis': analysis,
                    ':new_analysis': [{
                        'timestamp': datetime.now().isoformat(),
                        'sentiment_score': analysis['sentiment_score'],
                        'risk_score': analysis['risk_score']
                    }],
                    ':empty_list': [],
                    ':zero': 0,
                    ':one': 1
                }
            )
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")

class EntityContextualizer:
    """Contextualizes entities for better understanding"""
    
    MILITARY_TERMS = {
        'MOS', 'CO', 'XO', 'FOB', 'IED', 'PTSD', 'TBI', 
        'deployment', 'tour', 'unit', 'squad', 'platoon'
    }
    
    SUPPORT_INDICATORS = {
        'buddy', 'battle buddy', 'therapist', 'counselor', 
        'VA', 'support group', 'meeting', 'appointment'
    }
    
    @classmethod
    def contextualize(cls, entities: List[Dict], text: str) -> Dict:
        """Add context to extracted entities"""
        context = {
            'has_military_references': False,
            'has_support_references': False,
            'people_mentioned': [],
            'locations_mentioned': [],
            'temporal_references': []
        }
        
        text_lower = text.lower()
        
        # Check for military context
        for term in cls.MILITARY_TERMS:
            if term.lower() in text_lower:
                context['has_military_references'] = True
                break
        
        # Check for support system references
        for term in cls.SUPPORT_INDICATORS:
            if term.lower() in text_lower:
                context['has_support_references'] = True
                break
        
        # Process entities
        for entity in entities:
            if entity.get('type') == 'PERSON':
                context['people_mentioned'].append(entity['text'])
            elif entity.get('type') == 'LOCATION':
                context['locations_mentioned'].append(entity['text'])
            elif entity.get('type') == 'DATE':
                context['temporal_references'].append(entity['text'])
        
        return context