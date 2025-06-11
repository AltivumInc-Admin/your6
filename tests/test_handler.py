import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda.handler import lambda_handler

class TestCheckinHandler(unittest.TestCase):
    """Unit tests for the main check-in handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_text_event = {
            'body': json.dumps({
                'userId': 'veteran123',
                'text': 'Feeling okay today, but had some rough dreams last night.'
            })
        }
        
        self.valid_voice_event = {
            'body': json.dumps({
                'userId': 'veteran456',
                'voiceS3Uri': 's3://bucket/voice.wav'
            })
        }
        
        self.mock_user_data = {
            'userId': 'veteran123',
            'trustedContact': {
                'name': 'John Smith',
                'phone': '+15555551234',
                'email': 'john@example.com',
                'preferredMethod': 'SMS'
            }
        }
    
    @patch('lambda.handler.get_user_data')
    @patch('lambda.handler.analyze_sentiment')
    @patch('lambda.handler.generate_ai_response')
    @patch('lambda.handler.store_checkin')
    @patch('lambda.handler.trigger_alert')
    def test_successful_text_checkin(self, mock_trigger, mock_store, mock_ai, mock_sentiment, mock_user):
        """Test successful text check-in processing"""
        # Arrange
        mock_user.return_value = self.mock_user_data
        mock_sentiment.return_value = ('NEUTRAL', 0.2, ['okay', 'rough dreams'])
        mock_ai.return_value = 'I hear you had some rough dreams. That\'s not uncommon. How are you coping today?'
        mock_store.return_value = True
        
        # Act
        response = lambda_handler(self.valid_text_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['sentiment'], 'NEUTRAL')
        self.assertEqual(body['score'], 0.2)
        self.assertIn('rough dreams', body['entities'])
        mock_trigger.assert_not_called()  # Sentiment not below threshold
    
    @patch('lambda.handler.get_user_data')
    @patch('lambda.handler.analyze_sentiment')
    @patch('lambda.handler.generate_ai_response')
    @patch('lambda.handler.store_checkin')
    @patch('lambda.handler.trigger_alert')
    def test_low_sentiment_triggers_alert(self, mock_trigger, mock_store, mock_ai, mock_sentiment, mock_user):
        """Test that low sentiment triggers alert"""
        # Arrange
        mock_user.return_value = self.mock_user_data
        mock_sentiment.return_value = ('NEGATIVE', -0.85, ['struggling', 'isolated'])
        mock_ai.return_value = 'It sounds like you\'re going through a tough time. You\'re not alone.'
        mock_store.return_value = True
        mock_trigger.return_value = True
        
        # Act
        response = lambda_handler(self.valid_text_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 200)
        mock_trigger.assert_called_once()
        args = mock_trigger.call_args[1]
        self.assertEqual(args['sentiment_score'], -0.85)
    
    def test_missing_userid(self):
        """Test handling of missing userId"""
        # Arrange
        invalid_event = {
            'body': json.dumps({
                'text': 'Some text without userId'
            })
        }
        
        # Act
        response = lambda_handler(invalid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('userId is required', body['error'])
    
    def test_missing_content(self):
        """Test handling of missing text and voice"""
        # Arrange
        invalid_event = {
            'body': json.dumps({
                'userId': 'veteran123'
            })
        }
        
        # Act
        response = lambda_handler(invalid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('text or voiceS3Uri is required', body['error'])
    
    @patch('lambda.handler.get_user_data')
    @patch('lambda.handler.transcribe_audio')
    def test_voice_transcription_failure(self, mock_transcribe, mock_user):
        """Test handling of voice transcription failure"""
        # Arrange
        mock_user.return_value = self.mock_user_data
        mock_transcribe.return_value = None
        
        # Act
        response = lambda_handler(self.valid_voice_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertIn('Failed to transcribe audio', body['error'])
    
    def test_invalid_json_body(self):
        """Test handling of invalid JSON in request body"""
        # Arrange
        invalid_event = {
            'body': 'invalid json{{'
        }
        
        # Act
        response = lambda_handler(invalid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('Invalid JSON', body['error'])

if __name__ == '__main__':
    unittest.main()