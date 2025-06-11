# Your6 Test Interface

A simple HTML interface for testing the Your6 API without building a full application.

## Usage

1. **Open the file**
   ```bash
   open test-ui/index.html
   ```
   Or just double-click `index.html` in Finder

2. **Test different scenarios**
   - Click the test buttons to pre-fill positive/neutral/negative messages
   - Or write your own message
   - Submit and see the AI response + sentiment analysis

3. **What to expect**
   - **Positive sentiment**: Encouraging response, no alert
   - **Neutral sentiment**: Supportive response, no alert  
   - **Negative sentiment** (< -0.6): Supportive response + alert to trusted contact

## Features

- No server needed - runs in browser
- Pre-configured test messages
- Shows full API response
- Visual sentiment indicators
- Alert notification display

## Note

This is for testing only. A production UI would include:
- User authentication
- Trusted contact management
- Check-in history
- Voice recording
- Mobile app version