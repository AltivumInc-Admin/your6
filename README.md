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
- ✅ AI-generated supportive feedback using Amazon Bedrock (Claude 3.5 Sonnet)
- ✅ **Automated trusted contact alerts when sentiment < -0.6 threshold**
- ✅ **Dual notification system (SMS + Email) via SNS**
- ✅ **Direct VA Crisis Line integration (1-800-273-8255, press 1)**
- ✅ Longitudinal tracking in DynamoDB with trusted contact info
- ✅ S3 archival for check-in history
- ✅ Step Functions workflow orchestration
- ✅ Dead Letter Queues for reliability
- ✅ Comprehensive AI logging with request tracking
- ✅ CloudWatch dashboard for AI monitoring
- ✅ Fallback responses with clear system indicators

---

## 🧱 Architecture

### Event Flow

```
     [User Check-In]
          ↓
    [API Gateway]
          ↓
  [Step Functions] ──────┐
          ↓              │
 [Lambda: handler.py]    │ (DLQ for failures)
├── Transcribe (voice)   │
├── Comprehend (sentiment)│
├── Bedrock (AI response)│
├── DynamoDB (user data) │
├── S3 (archival)        │
└── ↓ if score < -0.6    │
   [EventBridge Rule]    │
         ↓               │
[Lambda: alert_dispatcher.py]
         ↓
    [SNS Topic]
    ├── 📱 SMS
    └── 📧 Email
         
Alert Contents:
- Timestamp & user ID
- Support suggestions
- VA Crisis Line: 1-800-273-8255
```

---

## 🧰 AWS Services Used

| Service                  | Purpose                                                                 |
|--------------------------|-------------------------------------------------------------------------|
| **Amazon API Gateway**   | RESTful endpoint for user check-ins                                     |
| **AWS Lambda**           | Core orchestration logic (input → process → feedback → store)           |
| **AWS Step Functions**   | Visual workflow orchestration with retry logic                          |
| **Amazon Transcribe**    | Converts voice memos to text                                            |
| **Amazon Comprehend**    | Sentiment and entity analysis                                           |
| **Amazon Bedrock**       | Claude 3.5 Sonnet – generates tailored responses                        |
| **Amazon DynamoDB**      | Tracks user data, trusted contacts, and sentiment history               |
| **Amazon S3**            | Archives check-ins with lifecycle policies                              |
| **Amazon EventBridge**   | Triggers alerts when sentiment < -0.6                                   |
| **Amazon SNS**           | Dual-channel notifications (SMS + Email)                                |
| **Amazon SQS**           | Dead Letter Queues for error handling                                   |
| **CloudWatch**           | Comprehensive logging, metrics, and dashboards                          |
| **Amazon SES**           | Email delivery (required for SNS email subscriptions)                   |

---

## 📦 Folder Structure

```
your6/
├── lambda/
│   ├── handler.py              # Main check-in processor
│   ├── handler_stepfunctions.py # Step Functions handler
│   ├── alert_dispatcher.py     # Trusted contact alerting
│   ├── utils.py               # Shared AWS service helpers
│   └── ai_logger.py           # AI service logging & metrics
├── prompts/
│   └── bedrock_system_prompt.txt
├── events/
│   ├── text_checkin.json      # Sample text input
│   ├── voice_checkin.json     # Sample voice input
│   └── alert_event.json       # Sample alert trigger
├── api-docs/
│   └── openapi.yaml           # API documentation
├── terraform/                  # Alternative IaC deployment
│   ├── main.tf
│   ├── variables.tf
│   └── README.md
├── tests/                      # Unit tests
│   ├── test_handler.py
│   └── test_alert_dispatcher.py
├── cloudformation-fixed.yaml   # Enhanced CloudFormation
├── cloudwatch-dashboard.json   # AI monitoring dashboard
├── sns-policy-fixed.json      # SNS topic policy
├── SYSTEM-REVIEW.md           # System documentation
├── demo-video-script.md       # Demo instructions
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
  "response": "Thanks for checking in. It sounds like you're feeling low today. You're not alone—take a few minutes to breathe. Remember, reaching out is a sign of strength.",
  "sentiment": "NEGATIVE",
  "score": -0.72,
  "entities": ["feeling low", "unsure"],
  "alertTriggered": true,
  "aiMetadata": {
    "model": "claude-3.5-sonnet",
    "fallback": false,
    "latency_ms": 245.3,
    "request_id": "abc123..."
  }
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

## 🔧 Recent Enhancements

### Phase 1: AI Monitoring & Logging (Complete)
- ✅ Structured JSON logging for all AI service calls
- ✅ CloudWatch metrics tracking (latency, errors, tokens)
- ✅ Unique request IDs for end-to-end tracing
- ✅ Fallback responses with system indicators
- ✅ Real-time monitoring dashboard
- ✅ DynamoDB Decimal conversion fix

### Phase 2: Coming Soon
- Retry logic with exponential backoff
- AI response validation & quality checks
- Advanced sentiment analysis with entity detection

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

### Option 1: CloudFormation
```bash
aws cloudformation deploy \
  --template-file cloudformation-fixed.yaml \
  --stack-name your6-stack \
  --capabilities CAPABILITY_IAM
```

### Option 2: Terraform
```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

### Option 3: SAM
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

# In Memory

For Dave Troutman, Andrew Manelski, and Moses Shin.

DOL.

And for all those who served and struggled in silence.
You are not forgotten.
