import json
import logging
import asyncio
import concurrent.futures
from typing import Dict, List, Tuple, Optional
import boto3
from dataclasses import dataclass
from ai_validator import ResponseValidator
from ai_logger import AIServiceLogger, MetricsCollector, AIServiceTimer

logger = logging.getLogger()

@dataclass
class ModelResponse:
    """Response from a single model"""
    model_id: str
    response: str
    confidence: float
    latency_ms: float
    tokens_used: int
    validation_score: float
    metadata: Dict

class MultiModelEnsemble:
    """Ensemble approach using multiple AI models for robust responses"""
    
    # Model configurations
    MODELS = {
        'claude-3.5-sonnet': {
            'id': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'weight': 0.6,
            'strengths': ['empathy', 'nuance', 'context'],
            'max_tokens': 300,
            'temperature': 0.7
        },
        'claude-3-haiku': {
            'id': 'anthropic.claude-3-haiku-20240307-v1:0',
            'weight': 0.3,
            'strengths': ['speed', 'clarity', 'directness'],
            'max_tokens': 200,
            'temperature': 0.5
        },
        'claude-instant': {
            'id': 'anthropic.claude-instant-v1',
            'weight': 0.1,
            'strengths': ['availability', 'consistency'],
            'max_tokens': 150,
            'temperature': 0.6
        }
    }
    
    # Response cache for common patterns
    RESPONSE_CACHE_TTL = 3600  # 1 hour
    
    def __init__(self, bedrock_client, validator: ResponseValidator, metrics: MetricsCollector):
        self.bedrock = bedrock_client
        self.validator = validator
        self.metrics = metrics
        self.response_cache = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
    
    def generate_ensemble_response(self,
                                 text: str,
                                 sentiment_data: Dict,
                                 user_id: str,
                                 context: Dict) -> Dict:
        """
        Generate response using multiple models and select/blend the best
        """
        request_id = AIServiceLogger.log_request(
            service="bedrock_ensemble",
            operation="multi_model_generation",
            user_id=user_id,
            input_data={"text": text, "models": list(self.MODELS.keys())}
        )
        
        with AIServiceTimer() as ensemble_timer:
            try:
                # Check cache first
                cache_key = self._generate_cache_key(text, sentiment_data)
                cached_response = self._check_cache(cache_key)
                if cached_response:
                    logger.info(f"Using cached response for {cache_key}")
                    return cached_response
                
                # Generate prompt
                prompt = self._create_enhanced_prompt(text, sentiment_data, context)
                
                # Invoke models in parallel
                model_responses = self._invoke_models_parallel(
                    prompt, 
                    sentiment_data,
                    user_id
                )
                
                # Select best response or blend
                final_response = self._select_or_blend_responses(
                    model_responses,
                    sentiment_data,
                    context
                )
                
                # Cache the result
                self._cache_response(cache_key, final_response)
                
                # Log ensemble metrics
                AIServiceLogger.log_response(
                    service="bedrock_ensemble",
                    request_id=request_id,
                    success=True,
                    output_data={
                        "models_used": len(model_responses),
                        "selection_method": final_response['metadata'].get('selection_method'),
                        "ensemble_confidence": final_response['metadata'].get('ensemble_confidence')
                    },
                    latency_ms=ensemble_timer.elapsed_ms
                )
                
                return final_response
                
            except Exception as e:
                logger.error(f"Ensemble generation failed: {str(e)}")
                # Fall back to single model
                return self._fallback_single_model(text, sentiment_data, user_id)
    
    def _create_enhanced_prompt(self, text: str, sentiment_data: Dict, context: Dict) -> str:
        """Create an enhanced prompt with additional context"""
        base_prompt = f"""You are a supportive AI assistant for veterans. 
        
User Context:
- Sentiment: {sentiment_data.get('sentiment')} (score: {sentiment_data.get('sentiment_score', 0):.2f})
- Risk Level: {sentiment_data.get('risk_score', 0)}/100
- Entities: {', '.join([e.get('text', '') for e in context.get('entities', [])[:3]])}

User Message: "{text}"

Provide a supportive response that:
1. Acknowledges their specific concerns
2. Offers practical support
3. Includes Veterans Crisis Line (1-800-273-8255) if risk > 50
4. Is warm but not overly emotional
5. Respects military culture"""
        
        return base_prompt
    
    def _invoke_models_parallel(self, 
                               prompt: str, 
                               sentiment_data: Dict,
                               user_id: str) -> List[ModelResponse]:
        """Invoke multiple models in parallel"""
        futures = []
        
        for model_name, config in self.MODELS.items():
            future = self.executor.submit(
                self._invoke_single_model,
                model_name,
                config,
                prompt,
                sentiment_data,
                user_id
            )
            futures.append((model_name, future))
        
        # Collect results
        responses = []
        for model_name, future in futures:
            try:
                response = future.result(timeout=10)  # 10 second timeout
                if response:
                    responses.append(response)
            except Exception as e:
                logger.error(f"Model {model_name} failed: {str(e)}")
        
        return responses
    
    def _invoke_single_model(self,
                           model_name: str,
                           config: Dict,
                           prompt: str,
                           sentiment_data: Dict,
                           user_id: str) -> Optional[ModelResponse]:
        """Invoke a single model"""
        with AIServiceTimer() as timer:
            try:
                response = self.bedrock.invoke_model(
                    modelId=config['id'],
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps({
                        'anthropic_version': 'bedrock-2023-05-31',
                        'max_tokens': config['max_tokens'],
                        'temperature': config['temperature'],
                        'messages': [{
                            'role': 'user',
                            'content': prompt
                        }]
                    })
                )
                
                response_body = json.loads(response['body'].read())
                ai_text = response_body['content'][0]['text']
                usage = response_body.get('usage', {})
                
                # Validate response
                validation_result = self.validator.validate_response(ai_text, sentiment_data)
                
                # Calculate confidence based on validation and model weight
                confidence = validation_result.score * config['weight']
                
                return ModelResponse(
                    model_id=model_name,
                    response=ai_text,
                    confidence=confidence,
                    latency_ms=timer.elapsed_ms,
                    tokens_used=usage.get('total_tokens', 0),
                    validation_score=validation_result.score,
                    metadata={'validation_details': validation_result.failed_checks}
                )
                
            except Exception as e:
                logger.error(f"Error invoking {model_name}: {str(e)}")
                return None
    
    def _select_or_blend_responses(self,
                                  responses: List[ModelResponse],
                                  sentiment_data: Dict,
                                  context: Dict) -> Dict:
        """Select best response or blend multiple responses"""
        if not responses:
            raise Exception("No model responses available")
        
        # Sort by confidence
        responses.sort(key=lambda x: x.confidence, reverse=True)
        
        # High-risk situations: use most validated response
        if sentiment_data.get('risk_score', 0) > 70:
            best_response = max(responses, key=lambda x: x.validation_score)
            selection_method = 'highest_validation'
        
        # Normal situations: consider blending
        elif len(responses) >= 2 and responses[0].confidence > 0.7:
            # Check if top responses are similar
            similarity = self._calculate_similarity(
                responses[0].response, 
                responses[1].response
            )
            
            if similarity > 0.8:
                # Responses are similar, use the best one
                best_response = responses[0]
                selection_method = 'highest_confidence'
            else:
                # Blend responses
                best_response = self._blend_responses(responses[:2], sentiment_data)
                selection_method = 'blended'
        else:
            # Use single best response
            best_response = responses[0]
            selection_method = 'single_best'
        
        # Calculate ensemble confidence
        ensemble_confidence = sum(r.confidence for r in responses) / len(responses)
        
        return {
            'response': best_response.response,
            'metadata': {
                'primary_model': best_response.model_id,
                'selection_method': selection_method,
                'ensemble_confidence': ensemble_confidence,
                'models_consulted': len(responses),
                'latency_ms': best_response.latency_ms,
                'validation_score': best_response.validation_score,
                'all_models': [
                    {
                        'model': r.model_id,
                        'confidence': r.confidence,
                        'validation': r.validation_score
                    } for r in responses
                ]
            }
        }
    
    def _blend_responses(self, 
                        responses: List[ModelResponse],
                        sentiment_data: Dict) -> ModelResponse:
        """Blend two responses intelligently"""
        r1, r2 = responses[0], responses[1]
        
        # Extract key elements from each
        r1_sentences = r1.response.split('. ')
        r2_sentences = r2.response.split('. ')
        
        blended_sentences = []
        
        # Take best opening
        if 'hear you' in r1_sentences[0].lower() or 'understand' in r1_sentences[0].lower():
            blended_sentences.append(r1_sentences[0])
        else:
            blended_sentences.append(r2_sentences[0])
        
        # Combine middle content
        combined_middle = r1_sentences[1:-1] + r2_sentences[1:-1]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_middle = []
        for sent in combined_middle:
            sent_lower = sent.lower().strip()
            if sent_lower not in seen and len(sent_lower) > 10:
                seen.add(sent_lower)
                unique_middle.append(sent)
        
        # Add up to 2 middle sentences
        blended_sentences.extend(unique_middle[:2])
        
        # Ensure crisis resources if needed
        crisis_line = "Veterans Crisis Line: 1-800-273-8255 (press 1)"
        has_crisis = any(crisis_line in sent for sent in blended_sentences)
        
        if sentiment_data.get('sentiment') == 'NEGATIVE' and not has_crisis:
            blended_sentences.append(f"Remember, support is available 24/7: {crisis_line}")
        
        blended_response = '. '.join(blended_sentences)
        if not blended_response.endswith('.'):
            blended_response += '.'
        
        # Create blended model response
        return ModelResponse(
            model_id=f"{r1.model_id}+{r2.model_id}",
            response=blended_response,
            confidence=(r1.confidence + r2.confidence) / 2,
            latency_ms=max(r1.latency_ms, r2.latency_ms),
            tokens_used=r1.tokens_used + r2.tokens_used,
            validation_score=(r1.validation_score + r2.validation_score) / 2,
            metadata={'blend_method': 'sentence_combination'}
        )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two responses"""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0
    
    def _generate_cache_key(self, text: str, sentiment_data: Dict) -> str:
        """Generate cache key for response"""
        # Use first 50 chars of text + sentiment for key
        text_key = text[:50].lower().replace(' ', '_')
        sentiment_key = sentiment_data.get('sentiment', 'unknown')
        risk_key = int(sentiment_data.get('risk_score', 0) / 20) * 20  # Round to nearest 20
        
        return f"{text_key}_{sentiment_key}_{risk_key}"
    
    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check response cache"""
        cached = self.response_cache.get(cache_key)
        if cached:
            # Check if still valid
            if cached['timestamp'] + self.RESPONSE_CACHE_TTL > datetime.now().timestamp():
                return cached['response']
        return None
    
    def _cache_response(self, cache_key: str, response: Dict):
        """Cache response for reuse"""
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now().timestamp()
        }
        
        # Limit cache size
        if len(self.response_cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(
                self.response_cache.items(), 
                key=lambda x: x[1]['timestamp']
            )
            self.response_cache = dict(sorted_cache[-50:])
    
    def _fallback_single_model(self, text: str, sentiment_data: Dict, user_id: str) -> Dict:
        """Fallback to single model if ensemble fails"""
        # Try Claude 3.5 Sonnet as primary
        config = self.MODELS['claude-3.5-sonnet']
        
        try:
            response = self._invoke_single_model(
                'claude-3.5-sonnet',
                config,
                self._create_enhanced_prompt(text, sentiment_data, {}),
                sentiment_data,
                user_id
            )
            
            if response:
                return {
                    'response': response.response,
                    'metadata': {
                        'primary_model': response.model_id,
                        'selection_method': 'fallback_single',
                        'ensemble_confidence': response.confidence,
                        'models_consulted': 1
                    }
                }
        except Exception as e:
            logger.error(f"Fallback model also failed: {str(e)}")
        
        # Ultimate fallback
        return {
            'response': "I hear you and I'm here to support you. While I'm having technical difficulties generating a personalized response, please know that your check-in has been received. If you're struggling, please reach out to the Veterans Crisis Line: 1-800-273-8255 (press 1). You're not alone.",
            'metadata': {
                'fallback': True,
                'error': 'all_models_failed'
            }
        }