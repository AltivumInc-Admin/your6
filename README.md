# Your6: AI-Powered Veteran Support Mobilization System

**Your6** is a serverless, AI-driven support activation platform that mobilizes help when veterans need it most. The name refers to the military phrase "I've got your six"—a promise of having someone's back. Your6 isn't just a mental health tracker—it's a silent recon system that activates when a veteran can't or won't ask for help directly. Using AWS-native services, it analyzes check-ins and automatically alerts trusted contacts when intervention may be needed.

---

## 🧠 Project Purpose

Veterans often face unique emotional and psychological challenges, many of which go unspoken. Your6 transforms passive monitoring into active mobilization:

- **Silent Support Activation**: When sentiment drops below threshold, trusted contacts are automatically notified
- **Human Connection First**: Technology enables, not replaces, human intervention
- **Non-Clinical Language**: Respects veteran culture with action-oriented messaging
- **Privacy-Preserving**: Pseudonymous check-ins with opt-in contact sharing
- **Crisis Resource Integration**: Direct links to VA Crisis Line and support resources

Your6 bridges the gap between a veteran in distress and the people who care about them—activating support networks when it matters most.

---

## 🚀 Features

- ✅ Voice or text check-in via secure API
- ✅ Sentiment and key phrase extraction using Amazon Comprehend
- ✅ AI-generated supportive feedback using Amazon Bedrock
- ✅ **Automated trusted contact alerts when sentiment < -0.6 threshold**
- ✅ **Human-friendly SNS messages with actionable guidance**
- ✅ **Direct VA Crisis Line integration (1-800-273-8255, press 1)**
- ✅ Longitudinal tracking in DynamoDB with trusted contact info
- ✅ S3 archival for check-in history
- ✅ JSON-based API for future UI/mobile integration

---

## 🧱 Architecture

### Event Flow

```
          [User Check-In]
               ↓
         [API Gateway]
               ↓
      [Lambda: handler.py]
    ├── Transcribe (voice → text)
    ├── Comprehend (sentiment analysis)
    ├── Bedrock (support message)
    ├── S3 + DynamoDB (storage)
    └── ↓ if sentiment < -0.6
       [EventBridge Rule]
              ↓
    [Lambda: alert_dispatcher.py]
              ↓
         [SNS → Trusted Contact]
              ↓
       📱 SMS/Email with:
         - Alert timestamp
         - Support suggestion
         - VA Crisis Line info
```

---

## 🧰 AWS Services Used

| Service                  | Purpose                                                                 |
|--------------------------|-------------------------------------------------------------------------|
| **Amazon API Gateway**   | RESTful endpoint for user check-ins                                     |
| **AWS Lambda**           | Core orchestration logic (input → process → feedback → store)           |
| **Amazon Transcribe**    | Converts voice memos to text                                            |
| **Amazon Comprehend**    | Sentiment and entity analysis                                           |
| **Amazon Bedrock**       | Claude or Titan – generates tailored responses                          |
| **Amazon DynamoDB**      | Tracks user sentiment scores over time                                  |
| **Amazon S3**            | Archives raw user submissions                                           |
| **Amazon EventBridge**   | Detects sentiment dips triggering downstream events                     |
| **Amazon SNS**           | Sends alerts (e.g. to user, support team, future integration)           |

---

## 📦 Folder Structure

```
your6/
├── lambda/
│   ├── handler.py              # Main check-in processor
│   ├── alert_dispatcher.py     # Trusted contact alerting
│   └── utils.py               # Shared AWS service helpers
├── prompts/
│   └── bedrock_system_prompt.txt
├── events/
│   ├── text_checkin.json      # Sample text input
│   ├── voice_checkin.json     # Sample voice input
│   └── alert_event.json       # Sample alert trigger
├── template.yaml              # SAM/CloudFormation
├── README.md
└── requirements.txt
```

---

## 📝 API Usage

### Endpoint

`POST /check-in`

### Payload

**Text Check-in**
```json
{
  "userId": "veteran123",
  "text": "Feeling kind of low today. Not sure why."
}
```

**Voice Check-in**
```json
{
  "userId": "veteran123",
  "voiceS3Uri": "s3://your6-inputs/veteran123/voice-10JUN.wav"
}
```

### Response

```json
{
  "response": "Thanks for checking in. It sounds like you're feeling low today. You're not alone—take a few minutes to breathe. Here's one small thing you can do now...",
  "sentiment": "NEGATIVE",
  "score": 0.87,
  "entities": ["feeling low", "unsure"]
}
```

---

## 🔔 Trusted Contact System

### DynamoDB User Schema
```json
{
  "userId": "veteran123",
  "trustedContact": {
    "name": "Marcus Alvarez",
    "email": "marcus.alvarez@gmail.com",
    "phone": "+15555555555",
    "preferredMethod": "SMS"
  },
  "alertThreshold": -0.6,
  "lastCheckIn": "2024-06-10T07:43:00Z"
}
```

### Sample Alert Message (SMS)
```
📡 Your6 Check-In Alert

[veteran123] checked in at 07:43 AM.
The AI detected signs of emotional distress.

✅ You are their trusted contact.

Please consider reaching out today.

Resources:
☎️ Veterans Crisis Line: 1-800-273-8255, press 1
💬 Suggested: "Hey, saw you weren't doing great. Let's talk."
```

---

## 🔐 Security & Privacy

- No PII required beyond opt-in trusted contact info
- All check-ins are pseudonymous (`userId`)
- Trusted contacts must be explicitly configured by veteran
- Bedrock prompts include responsible AI guidelines
- SNS alerts are auditable via CloudWatch
- All data encrypted at rest and in transit

---

## 📈 Future Enhancements

- Add Cognito for secure veteran authentication
- Mobile app with push notifications for check-in reminders
- Twilio integration for two-way SMS conversations
- Multiple trusted contacts with escalation logic
- Integration with VA appointment scheduling API
- Sentiment trend visualization in QuickSight
- Peer support network matching based on shared experiences

---

## 🧪 Local Testing

To simulate the Lambda locally with `sam local`:

```bash
sam build
sam local invoke --event events/sample_input.json
```

---

## 🛠️ Deployment

```bash
sam deploy --guided
```

---

## 👥 Contributors

- **Christian Perez** – Founder, Altivum Inc. (Project Lead)

---

## 📄 License

MIT License

---

For questions or collaboration inquiries, reach out via GitHub Issues or christian.perez@altivum.io.