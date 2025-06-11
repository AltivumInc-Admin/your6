import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda.alert_dispatcher import lambda_handler

class TestAlertDispatcher(unittest.TestCase):
    """Unit tests for the alert dispatcher Lambda"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_event = {
            'detail': {
                'userId': 'veteran123',
                'sentimentScore': -0.85,
                'textPreview': 'Feeling really isolated and struggling...',
                'timestamp': '2024-06-10T15:30:00Z',
                'alertType': 'LOW_SENTIMENT'
            }
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
    
    @patch('lambda.alert_dispatcher.get_user_data')
    @patch('lambda.alert_dispatcher.format_alert_message')
    @patch('lambda.alert_dispatcher.sns')
    def test_successful_sms_alert(self, mock_sns, mock_format, mock_user):
        """Test successful SMS alert to trusted contact"""
        # Arrange
        mock_user.return_value = self.mock_user_data
        mock_format.return_value = {
            'message': 'Alert message',
            'subject': 'Your6 Alert',
            'contact_name': 'John Smith',
            'contact_method': 'SMS'
        }
        mock_sns.publish.return_value = {'MessageId': '12345'}
        
        # Act
        response = lambda_handler(self.valid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['notificationSent'])
        self.assertEqual(body['contactMethod'], 'SMS')
        
        # Verify SNS was called with correct parameters
        mock_sns.publish.assert_called_once()
        call_args = mock_sns.publish.call_args[1]
        self.assertEqual(call_args['PhoneNumber'], '+15555551234')
    
    @patch('lambda.alert_dispatcher.get_user_data')
    @patch('lambda.alert_dispatcher.format_alert_message')
    @patch('lambda.alert_dispatcher.sns')
    @patch('lambda.alert_dispatcher.os.environ.get')
    def test_successful_email_alert(self, mock_env, mock_sns, mock_format, mock_user):
        """Test successful email alert to trusted contact"""
        # Arrange
        email_user = self.mock_user_data.copy()
        email_user['trustedContact']['preferredMethod'] = 'EMAIL'
        mock_user.return_value = email_user
        mock_env.return_value = 'arn:aws:sns:us-east-1:123456789:topic'
        mock_format.return_value = {
            'message': 'Alert message',
            'subject': 'Your6 Alert: veteran123 needs support',
            'contact_name': 'John Smith',
            'contact_method': 'EMAIL'
        }
        
        # Act
        response = lambda_handler(self.valid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['notificationSent'])
        self.assertEqual(body['contactMethod'], 'EMAIL')
    
    @patch('lambda.alert_dispatcher.get_user_data')
    def test_user_not_found(self, mock_user):
        """Test handling when user is not found"""
        # Arrange
        mock_user.return_value = None
        
        # Act
        response = lambda_handler(self.valid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('User not found', body['error'])
    
    @patch('lambda.alert_dispatcher.get_user_data')
    def test_no_trusted_contact(self, mock_user):
        """Test handling when user has no trusted contact"""
        # Arrange
        user_no_contact = {'userId': 'veteran123'}
        mock_user.return_value = user_no_contact
        
        # Act
        response = lambda_handler(self.valid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('No trusted contact configured', body['message'])
    
    def test_missing_userid_in_event(self):
        """Test handling of missing userId in event"""
        # Arrange
        invalid_event = {'detail': {'sentimentScore': -0.85}}
        
        # Act
        response = lambda_handler(invalid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('userId is required', body['error'])
    
    @patch('lambda.alert_dispatcher.get_user_data')
    @patch('lambda.alert_dispatcher.format_alert_message')
    @patch('lambda.alert_dispatcher.sns')
    def test_sns_publish_failure(self, mock_sns, mock_format, mock_user):
        """Test handling of SNS publish failure"""
        # Arrange
        mock_user.return_value = self.mock_user_data
        mock_format.return_value = {
            'message': 'Alert message',
            'subject': 'Your6 Alert',
            'contact_name': 'John Smith',
            'contact_method': 'SMS'
        }
        mock_sns.publish.side_effect = Exception('SNS error')
        
        # Act
        response = lambda_handler(self.valid_event, None)
        
        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertFalse(body['notificationSent'])

if __name__ == '__main__':
    unittest.main()