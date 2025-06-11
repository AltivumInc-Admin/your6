import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger()

@dataclass
class ValidationResult:
    """Result of AI response validation"""
    is_valid: bool
    score: float
    failed_checks: List[str]
    warnings: List[str]
    suggestions: Dict[str, str]

class ResponseValidator:
    """Validates AI responses for quality and appropriateness"""
    
    # Medical terms to avoid
    MEDICAL_TERMS = [
        r'\b(diagnos\w+|prescri\w+|medicat\w+|dosage|treatment plan)\b',
        r'\b(disorder|syndrome|patholog\w+|clinical|therapeutic)\b',
        r'\b(antidepress\w+|antipsychotic|anxiolytic|benzodiazepine)\b'
    ]
    
    # Diagnostic language patterns
    DIAGNOSTIC_PATTERNS = [
        r'you (have|appear to have|seem to have|are showing signs of)',
        r'this (indicates|suggests|points to|is consistent with)',
        r'symptoms of\s+\w+',
        r'(suffering from|afflicted with|dealing with)\s+\w+'
    ]
    
    # Crisis resources
    CRISIS_RESOURCES = [
        'Veterans Crisis Line',
        '1-800-273-8255',
        'press 1',
        'veteranscrisisline.net'
    ]
    
    # Supportive language indicators
    SUPPORTIVE_PHRASES = [
        r'\b(strength|courage|brave|resilient)\b',
        r'\b(support|help|resource|reach out)\b',
        r'\b(not alone|here for you|people care)\b',
        r'\b(thank\w* for sharing|appreciate|hear you)\b'
    ]
    
    def __init__(self):
        self.min_length = 50
        self.max_length = 500
        self.high_risk_threshold = -0.8
    
    def validate_response(self, response: str, sentiment_data: Dict) -> ValidationResult:
        """
        Comprehensive validation of AI response
        """
        checks = {}
        warnings = []
        suggestions = {}
        
        # Length checks
        checks['length_min'] = len(response) >= self.min_length
        checks['length_max'] = len(response) <= self.max_length
        
        if not checks['length_min']:
            suggestions['length'] = f"Response too short ({len(response)} chars). Add more supportive content."
        elif not checks['length_max']:
            suggestions['length'] = f"Response too long ({len(response)} chars). Be more concise."
        
        # Medical advice check
        checks['no_medical_terms'] = not self._contains_medical_terms(response)
        if not checks['no_medical_terms']:
            suggestions['medical'] = "Remove medical terminology and clinical language."
        
        # Diagnostic language check
        checks['no_diagnosis'] = not self._contains_diagnostic_language(response)
        if not checks['no_diagnosis']:
            suggestions['diagnosis'] = "Avoid diagnostic or prescriptive language."
        
        # Supportive tone check
        supportive_count = self._count_supportive_phrases(response)
        checks['supportive_tone'] = supportive_count >= 2
        if not checks['supportive_tone']:
            suggestions['tone'] = "Add more supportive and encouraging language."
        
        # Crisis resource check (for negative sentiment)
        if sentiment_data.get('dominant') == 'NEGATIVE':
            checks['has_resources'] = self._has_crisis_resources(response)
            if not checks['has_resources']:
                suggestions['resources'] = "Include Veterans Crisis Line information."
        else:
            checks['has_resources'] = True
        
        # Severity matching
        checks['appropriate_severity'] = self._matches_severity(
            response, 
            sentiment_data.get('sentiment_score', 0)
        )
        if not checks['appropriate_severity']:
            suggestions['severity'] = "Adjust response tone to match sentiment severity."
        
        # Personal acknowledgment
        checks['acknowledges_user'] = self._acknowledges_user_content(
            response,
            sentiment_data.get('key_phrases', [])
        )
        if not checks['acknowledges_user']:
            warnings.append("Response may feel generic - consider referencing user's specific concerns.")
        
        # Calculate overall score
        passed_checks = sum(1 for v in checks.values() if v)
        total_checks = len(checks)
        score = passed_checks / total_checks
        
        # Additional quality metrics
        if score == 1.0 and supportive_count >= 3:
            score = 1.1  # Bonus for exceptional quality
        
        failed_checks = [k for k, v in checks.items() if not v]
        
        return ValidationResult(
            is_valid=len(failed_checks) == 0,
            score=score,
            failed_checks=failed_checks,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _contains_medical_terms(self, text: str) -> bool:
        """Check if text contains medical terminology"""
        text_lower = text.lower()
        for pattern in self.MEDICAL_TERMS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def _contains_diagnostic_language(self, text: str) -> bool:
        """Check if text contains diagnostic language"""
        text_lower = text.lower()
        for pattern in self.DIAGNOSTIC_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def _count_supportive_phrases(self, text: str) -> int:
        """Count supportive language indicators"""
        count = 0
        text_lower = text.lower()
        for pattern in self.SUPPORTIVE_PHRASES:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            count += len(matches)
        return count
    
    def _has_crisis_resources(self, text: str) -> bool:
        """Check if crisis resources are mentioned"""
        text_lower = text.lower()
        # Must have at least the phone number
        return '1-800-273-8255' in text or 'veterans crisis line' in text_lower
    
    def _matches_severity(self, response: str, sentiment_score: float) -> bool:
        """Check if response tone matches sentiment severity"""
        response_lower = response.lower()
        
        if sentiment_score < self.high_risk_threshold:
            # High risk - should have urgent/immediate language
            urgent_terms = ['immediate', 'right now', 'today', 'reach out', 'please call']
            return any(term in response_lower for term in urgent_terms)
        elif sentiment_score < -0.4:
            # Moderate risk - should acknowledge difficulty
            acknowledging_terms = ['difficult', 'tough', 'hard', 'struggle', 'challenging']
            return any(term in response_lower for term in acknowledging_terms)
        else:
            # Low risk - general support is fine
            return True
    
    def _acknowledges_user_content(self, response: str, key_phrases: List[str]) -> bool:
        """Check if response acknowledges user's specific content"""
        if not key_phrases:
            return True
        
        response_lower = response.lower()
        # Check if at least one key phrase is referenced
        for phrase in key_phrases[:3]:  # Check top 3 key phrases
            if phrase.lower() in response_lower or \
               any(word in response_lower for word in phrase.lower().split() if len(word) > 4):
                return True
        
        return False

def generate_validation_feedback(validation_result: ValidationResult) -> str:
    """
    Generate feedback for improving the response
    """
    if validation_result.is_valid:
        return "Response validated successfully."
    
    feedback_parts = ["Response validation failed:"]
    
    for check in validation_result.failed_checks:
        suggestion = validation_result.suggestions.get(check.replace('_', ' '))
        if suggestion:
            feedback_parts.append(f"- {suggestion}")
    
    if validation_result.warnings:
        feedback_parts.append("\nWarnings:")
        feedback_parts.extend(f"- {warning}" for warning in validation_result.warnings)
    
    return "\n".join(feedback_parts)