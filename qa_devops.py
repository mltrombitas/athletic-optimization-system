import anthropic
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# QA/DevOps Instructions
system_prompt = """You are an expert QA Engineer and DevOps specialist.

Your job:
- Design comprehensive testing strategies
- Create CI/CD pipelines
- Implement security best practices
- Define monitoring and alerting
- Specify deployment automation
- Document quality assurance processes

Focus on production-ready, automated solutions."""

# The question
user_question = """Design the QA and deployment strategy for the athletic optimization system:

**TESTING REQUIREMENTS:**

1. **Unit Tests:**
   - API client authentication
   - Data transformation functions (especially km→miles conversion)
   - Database operations
   - Recommendation engine logic
   - Error handling

2. **Integration Tests:**
   - End-to-end OAuth flows
   - API data fetching and storage
   - Multi-device data synchronization
   - Alert generation

3. **Data Validation Tests:**
   - Range checks (HR 40-220 bpm, pace 4-20 min/mile)
   - Format validation (timestamps, coordinates)
   - Deduplication logic
   - Missing data handling

**SECURITY REQUIREMENTS:**
- API key rotation strategy
- Secure credential storage
- Rate limiting protection
- Data encryption (at rest and in transit)
- Privacy compliance (GDPR considerations)

**DEPLOYMENT PIPELINE:**
- GitHub Actions CI/CD workflow
- Automated testing on every commit
- Staging environment testing
- Production deployment process
- Rollback procedures

**MONITORING:**
- API health checks
- Data pipeline success/failure tracking
- Performance metrics
- Error logging and alerting
- Usage analytics

**PROVIDE:**
- pytest test examples
- GitHub Actions workflow YAML
- Security checklist
- Monitoring dashboard specifications
- Deployment runbook"""

# Make the API call
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    system=system_prompt,
    messages=[
        {"role": "user", "content": user_question}
    ]
)

# Print and save
output = message.content[0].text

print(output)

# Save to file
with open("QA_DEVOPS_GUIDE.md", "w") as f:
    f.write("# QA and DevOps Guide\n\n")
    f.write("**Athletic Optimization System - Testing & Deployment**\n\n")
    f.write(output)

print("\n✅ QA/DevOps guide saved to QA_DEVOPS_GUIDE.md")