# Your6 Demo Video Script (< 3 minutes)

## Opening (0:00-0:15)
**Visual**: Your6 logo with tagline "I've got your six"
**Script**: "Your6 transforms how we support veterans in crisis. Using AWS Lambda and AI, we've built a system that doesn't just monitor—it mobilizes."

## Problem Statement (0:15-0:30)
**Visual**: Statistics on veteran mental health
**Script**: "22 veterans die by suicide every day. Many won't ask for help directly. Your6 bridges this gap by automatically activating support networks when veterans need it most."

## Architecture Overview (0:30-0:50)
**Visual**: Architecture diagram showing Lambda → EventBridge → SNS flow
**Script**: "Built entirely on AWS serverless, Your6 uses Lambda as its core. Veterans check in via text or voice. Lambda orchestrates sentiment analysis through Comprehend, generates supportive responses with Bedrock AI, and triggers alerts when sentiment drops below -0.6."

## Live Demo (0:50-2:00)

### 1. Positive Check-in (0:50-1:10)
**Visual**: Postman/curl sending request
```bash
curl -X POST https://your-api.com/check-in \
  -d '{"userId": "veteran123", "text": "Good day today. Connected with old squad."}'
```
**Show**: Positive response, no alert triggered

### 2. Concerning Check-in (1:10-1:40)
**Visual**: Send low sentiment check-in
```bash
curl -X POST https://your-api.com/check-in \
  -d '{"userId": "veteran123", "text": "Struggling today. Nightmares are back. Feel so alone."}'
```
**Show**: 
- AI response: "I hear you're struggling. That takes strength to share..."
- CloudWatch showing EventBridge trigger
- SMS alert to trusted contact

### 3. Show DynamoDB & S3 (1:40-2:00)
**Visual**: AWS Console showing:
- DynamoDB with user record and sentiment history
- S3 bucket with archived check-ins
- Step Functions visualization (if deployed)

## Key Differentiators (2:00-2:30)
**Visual**: Split screen showing features
**Script**: 
- "Lambda enables instant scaling—from 1 to 10,000 veterans"
- "Dead Letter Queues ensure no cry for help goes unheard"  
- "11 AWS services working in harmony"
- "Privacy-first: No PII required"

## Impact & Close (2:30-2:50)
**Visual**: Your6 logo with API endpoint
**Script**: "Your6 proves technology can enable human connection when it matters most. This isn't just code—it's a lifeline. Built with AWS Lambda. Built to save lives."

**End screen**: 
- GitHub: AltivumInc-Admin/your6
- API: https://3il8ifyfr7.execute-api.us-east-1.amazonaws.com/prod/check-in
- "AWS Lambda Hackathon 2025"

---

## Technical Recording Tips:
1. Use OBS or QuickTime for screen recording
2. Have terminals and browser tabs pre-opened
3. Use larger fonts for visibility
4. Keep AWS Console logged in to correct region
5. Pre-populate Postman/curl commands
6. Test SMS delivery before recording