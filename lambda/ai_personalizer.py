import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import boto3

logger = logging.getLogger()

class ResponsePersonalizer:
    """Personalizes AI responses based on user profile and history"""
    
    # Communication style templates
    COMMUNICATION_STYLES = {
        'military_brief': {
            'template': "Roger. {acknowledgment} {action} {resource}",
            'tone': 'direct',
            'max_length': 150
        },
        'military_supportive': {
            'template': "Copy that, {rank_or_name}. {acknowledgment} {support} {action}",
            'tone': 'understanding',
            'max_length': 200
        },
        'civilian_empathetic': {
            'template': "{acknowledgment} {validation} {support} {action}",
            'tone': 'warm',
            'max_length': 250
        },
        'peer_casual': {
            'template': "Hey {name}, {acknowledgment} {peer_support} {action}",
            'tone': 'conversational',
            'max_length': 200
        }
    }
    
    # Response effectiveness indicators
    POSITIVE_RESPONSE_INDICATORS = [
        'thank you', 'thanks', 'helpful', 'appreciate',
        'feeling better', 'good advice', 'will try'
    ]
    
    NEGATIVE_RESPONSE_INDICATORS = [
        "doesn't help", "not helpful", "don't understand",
        "leave me alone", "stop", "whatever"
    ]
    
    def __init__(self, dynamodb_table):
        self.user_table = dynamodb_table
        self.response_cache = {}
    
    def personalize_response(self, 
                           base_response: str,
                           user_id: str,
                           sentiment_data: Dict,
                           context: Dict) -> Dict:
        """
        Personalize response based on user profile and context
        """
        # Get user profile
        profile = self._get_enhanced_profile(user_id)
        
        # Determine communication style
        comm_style = self._determine_communication_style(profile, sentiment_data)
        
        # Get personalization elements
        elements = self._get_personalization_elements(profile, context)
        
        # Adapt response
        personalized = self._adapt_response(
            base_response,
            comm_style,
            elements,
            sentiment_data
        )
        
        # Add personal touches
        if profile.get('preferences', {}).get('use_name', True):
            name = profile.get('preferred_name', user_id)
            if name and name != user_id:
                personalized = self._add_name_reference(personalized, name)
        
        # Include relevant past positive experiences
        if sentiment_data.get('sentiment_score', 0) < -0.5:
            positive_memory = self._get_positive_memory(profile)
            if positive_memory:
                personalized = self._incorporate_positive_memory(
                    personalized, 
                    positive_memory
                )
        
        # Ensure crisis resources for high risk
        if sentiment_data.get('risk_score', 0) > 50:
            personalized = self._ensure_crisis_resources(personalized, comm_style)
        
        return {
            'response': personalized,
            'personalization_metadata': {
                'style': comm_style,
                'elements_used': elements,
                'profile_completeness': self._calculate_profile_completeness(profile),
                'response_history_considered': len(profile.get('response_history', []))
            }
        }
    
    def _get_enhanced_profile(self, user_id: str) -> Dict:
        """Get comprehensive user profile with preferences"""
        try:
            response = self.user_table.get_item(Key={'userId': user_id})
            profile = response.get('Item', {})
            
            # Initialize if new user
            if not profile.get('preferences'):
                profile['preferences'] = {
                    'communication_style': 'military_supportive',
                    'use_name': True,
                    'include_memories': True,
                    'response_length': 'medium'
                }
            
            # Calculate response effectiveness
            if 'response_history' in profile:
                profile['avg_effectiveness'] = self._calculate_effectiveness(
                    profile['response_history']
                )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {'preferences': {'communication_style': 'military_supportive'}}
    
    def _determine_communication_style(self, profile: Dict, sentiment_data: Dict) -> str:
        """Determine best communication style for current situation"""
        base_style = profile.get('preferences', {}).get(
            'communication_style', 
            'military_supportive'
        )
        
        # Adjust based on severity
        if sentiment_data.get('risk_score', 0) > 70:
            # High risk - be more direct
            if 'military' in base_style:
                return 'military_brief'
            else:
                return 'civilian_empathetic'
        
        # Check response effectiveness history
        if profile.get('avg_effectiveness', 0.5) < 0.3:
            # Current style not working well, try alternative
            if base_style == 'military_brief':
                return 'military_supportive'
            elif base_style == 'civilian_empathetic':
                return 'peer_casual'
        
        return base_style
    
    def _get_personalization_elements(self, profile: Dict, context: Dict) -> Dict:
        """Extract elements for personalization"""
        elements = {
            'preferred_name': profile.get('preferred_name'),
            'rank': profile.get('rank'),
            'branch': profile.get('branch'),
            'coping_strategies': profile.get('effective_strategies', []),
            'support_network': profile.get('support_network', []),
            'interests': profile.get('interests', []),
            'time_preferences': profile.get('time_preferences', {})
        }
        
        # Add context-specific elements
        if context.get('entities', {}).get('people_mentioned'):
            elements['mentioned_people'] = context['entities']['people_mentioned']
        
        return {k: v for k, v in elements.items() if v}
    
    def _adapt_response(self, 
                       base_response: str, 
                       style: str,
                       elements: Dict,
                       sentiment_data: Dict) -> str:
        """Adapt response to communication style"""
        style_config = self.COMMUNICATION_STYLES.get(style, self.COMMUNICATION_STYLES['military_supportive'])
        
        # Shorten if needed
        if len(base_response) > style_config['max_length']:
            base_response = self._intelligently_shorten(
                base_response, 
                style_config['max_length']
            )
        
        # Apply tone adjustments
        if style_config['tone'] == 'direct':
            base_response = self._make_direct(base_response)
        elif style_config['tone'] == 'warm':
            base_response = self._add_warmth(base_response)
        
        # Add military terminology if applicable
        if 'military' in style:
            base_response = self._add_military_terminology(base_response)
        
        return base_response
    
    def _add_name_reference(self, response: str, name: str) -> str:
        """Add personalized name reference"""
        # Add name at beginning if not present
        if name.lower() not in response.lower():
            return f"{name}, {response[0].lower()}{response[1:]}"
        return response
    
    def _get_positive_memory(self, profile: Dict) -> Optional[Dict]:
        """Retrieve a relevant positive memory or achievement"""
        history = profile.get('analysis_history', [])
        positive_moments = [
            h for h in history 
            if h.get('sentiment_score', 0) > 0.5
        ]
        
        if positive_moments:
            # Return most recent positive moment
            return positive_moments[-1]
        
        # Check for stored achievements
        return profile.get('achievements', [{}])[0] if profile.get('achievements') else None
    
    def _incorporate_positive_memory(self, response: str, memory: Dict) -> str:
        """Weave positive memory into response"""
        memory_date = memory.get('timestamp', '')
        if memory_date:
            days_ago = (datetime.now() - datetime.fromisoformat(memory_date)).days
            if days_ago < 30:
                memory_text = f"Remember {days_ago} days ago when you felt more positive? You've overcome tough times before."
                response += f" {memory_text}"
        
        return response
    
    def _ensure_crisis_resources(self, response: str, style: str) -> str:
        """Ensure crisis resources are included appropriately"""
        crisis_line = "Veterans Crisis Line: 1-800-273-8255 (press 1)"
        
        if crisis_line not in response:
            if 'military' in style:
                response += f"\n\nImmediate support available: {crisis_line}"
            else:
                response += f"\n\nPlease remember, help is always available: {crisis_line}"
        
        return response
    
    def _calculate_effectiveness(self, history: List[Dict]) -> float:
        """Calculate average response effectiveness"""
        if not history:
            return 0.5
        
        recent_history = history[-10:]  # Last 10 interactions
        effectiveness_scores = []
        
        for i in range(1, len(recent_history)):
            prev = recent_history[i-1]
            curr = recent_history[i]
            
            # Check sentiment improvement
            sentiment_delta = curr.get('sentiment_score', 0) - prev.get('sentiment_score', 0)
            
            # Check for positive indicators in next response
            next_text = curr.get('text', '').lower()
            has_positive = any(ind in next_text for ind in self.POSITIVE_RESPONSE_INDICATORS)
            has_negative = any(ind in next_text for ind in self.NEGATIVE_RESPONSE_INDICATORS)
            
            if has_positive and not has_negative:
                effectiveness_scores.append(0.8)
            elif has_negative:
                effectiveness_scores.append(0.2)
            elif sentiment_delta > 0:
                effectiveness_scores.append(0.6)
            else:
                effectiveness_scores.append(0.4)
        
        return sum(effectiveness_scores) / len(effectiveness_scores) if effectiveness_scores else 0.5
    
    def _calculate_profile_completeness(self, profile: Dict) -> float:
        """Calculate how complete the user profile is"""
        important_fields = [
            'preferred_name', 'rank', 'branch', 'preferences',
            'support_network', 'effective_strategies', 'interests'
        ]
        
        present_fields = sum(1 for field in important_fields if profile.get(field))
        return present_fields / len(important_fields)
    
    def _intelligently_shorten(self, text: str, max_length: int) -> str:
        """Shorten text while preserving key information"""
        if len(text) <= max_length:
            return text
        
        # Preserve crisis resources
        crisis_line = "Veterans Crisis Line: 1-800-273-8255 (press 1)"
        has_crisis = crisis_line in text
        
        # Split into sentences
        sentences = text.split('. ')
        
        # Prioritize sentences
        prioritized = []
        for sent in sentences:
            if crisis_line in sent:
                priority = 1
            elif any(word in sent.lower() for word in ['help', 'support', 'reach out']):
                priority = 2
            else:
                priority = 3
            prioritized.append((priority, sent))
        
        # Sort by priority
        prioritized.sort(key=lambda x: x[0])
        
        # Reconstruct
        result = []
        current_length = 0
        
        for _, sent in prioritized:
            if current_length + len(sent) + 2 <= max_length:
                result.append(sent)
                current_length += len(sent) + 2
        
        return '. '.join(result) + '.'
    
    def _make_direct(self, text: str) -> str:
        """Make response more direct and action-oriented"""
        # Remove filler words
        fillers = [
            'I think', 'maybe', 'perhaps', 'it seems like',
            'you might want to', 'you could'
        ]
        
        result = text
        for filler in fillers:
            result = result.replace(filler, '')
        
        # Make suggestions more direct
        result = result.replace('You might consider', 'Consider')
        result = result.replace('It would be good to', 'Recommend:')
        
        return result.strip()
    
    def _add_warmth(self, text: str) -> str:
        """Add warmth and empathy to response"""
        if not text.startswith(('I hear you', 'I understand', 'Thank you for')):
            text = f"I hear you, and {text[0].lower()}{text[1:]}"
        
        return text
    
    def _add_military_terminology(self, text: str) -> str:
        """Add appropriate military terminology"""
        replacements = {
            'understand': 'copy',
            'okay': 'roger',
            'friend': 'battle buddy',
            'group': 'unit'
        }
        
        result = text
        for civilian, military in replacements.items():
            result = result.replace(civilian, military)
        
        return result