"""
Crisis Detection Failsafe Module
Ensures critical situations are never missed
"""
import re
import logging

logger = logging.getLogger()

# Critical patterns that MUST trigger high risk
CRISIS_PATTERNS = [
    (r'\b(gun|weapon|firearm|pistol|rifle)\b.*\b(use|pull|trigger|shoot|end)\b', 95),
    (r'\b(kill\s+myself|suicide|suicidal|take\s+my\s+life)\b', 95),
    (r'\b(pills|medication|overdose|OD)\b.*\b(all|bottle|take)\b', 90),
    (r'\b(jump|bridge|building|cliff)\b.*\b(off|from)\b', 90),
    (r'\b(cut|blade|knife|razor)\b.*\b(myself|wrist|vein)\b', 85),
    (r'\b(noose|rope|hang|hanging)\s*\b(myself)?\b', 90),
    (r'\bgoodbye\b.*\b(final|last|forever)\b', 85),
    (r'\b(note|letter)\b.*\b(suicide|goodbye|final)\b', 85)
]

def apply_crisis_failsafe(text: str, current_risk_score: float, sentiment_score: float) -> tuple:
    """
    Apply failsafe rules to ensure crisis situations are detected
    
    Returns: (adjusted_risk_score, failsafe_triggered, matched_pattern)
    """
    text_lower = text.lower()
    
    # Check critical patterns
    for pattern, min_score in CRISIS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            if current_risk_score < min_score:
                logger.critical(f"CRISIS FAILSAFE TRIGGERED: Pattern '{pattern}' matched, overriding risk score from {current_risk_score} to {min_score}")
                return min_score, True, pattern
    
    # Check extreme negative sentiment
    if sentiment_score < -0.9 and current_risk_score < 50:
        logger.warning(f"Extreme negative sentiment ({sentiment_score}) with low risk score ({current_risk_score}), applying failsafe")
        return max(current_risk_score, 60), True, "extreme_negative_sentiment"
    
    # Check combination of moderate risk factors
    risk_word_count = 0
    risk_words = ['hopeless', 'worthless', 'alone', 'pain', 'can\'t', 'tired', 'done', 'give up']
    for word in risk_words:
        if word in text_lower:
            risk_word_count += 1
    
    if risk_word_count >= 4 and current_risk_score < 40:
        logger.warning(f"Multiple risk words detected ({risk_word_count}), applying moderate failsafe")
        return max(current_risk_score, 45), True, "multiple_risk_words"
    
    return current_risk_score, False, None

def validate_risk_assessment(analysis_result: dict) -> dict:
    """
    Validate and enhance risk assessment results
    """
    text = analysis_result.get('_original_text', '')
    current_risk = analysis_result.get('risk_score', 0)
    sentiment_score = analysis_result.get('sentiment_score', 0)
    
    # Apply failsafe
    adjusted_risk, failsafe_triggered, pattern = apply_crisis_failsafe(
        text, current_risk, sentiment_score
    )
    
    if failsafe_triggered:
        analysis_result['risk_score'] = adjusted_risk
        analysis_result['failsafe_applied'] = True
        analysis_result['failsafe_reason'] = pattern
        
        # Update immediate attention flag
        analysis_result['requires_immediate_attention'] = adjusted_risk > 50
        
        # Add to risk factors if not present
        if 'risk_factors' not in analysis_result:
            analysis_result['risk_factors'] = []
        analysis_result['risk_factors'].append(f"FAILSAFE: {pattern}")
    
    return analysis_result