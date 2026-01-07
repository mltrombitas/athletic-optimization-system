import anthropic
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# Data Engineer Instructions
system_prompt = """You are an expert Data Engineer specializing in wearable device API integration.

Your job:
- Design OAuth authentication flows for APIs
- Specify data extraction endpoints and methods
- Define data transformation pipelines (including unit conversions)
- Create data validation and error handling strategies
- Design database schema for raw and processed data

Be specific, include code examples, and provide actionable implementation steps."""

# The question
user_question = """Design the data integration pipeline for:

**SOURCE 1: Oura Ring API**
- Sleep data (stages, efficiency, timing)
- Readiness score
- HRV, RHR, body temperature
- SPO2
- Activity data

**SOURCE 2: Garmin Connect API**
- Workout data (GPS, HR, pace, elevation)
- Stryd power data (flows through Garmin)
- Daily activity summary
- Training load metrics

**REQUIREMENTS:**
1. OAuth 2.0 authentication for both APIs
2. Automated daily data pulls
3. **ALL DISTANCE CONVERSIONS: km → miles** (critical!)
4. Data validation and error handling
5. Storage in structured format for analysis
6. Deduplication logic

**PROVIDE:**
- API endpoint specifications
- Authentication flow diagrams
- Data transformation pipeline (with km→miles conversion)
- Database schema recommendations
- Python code examples for key functions"""

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
with open("DATA_INTEGRATION_GUIDE.md", "w") as f:
    f.write("# Data Integration Guide\n\n")
    f.write("**Athletic Optimization System - API Integration Specifications**\n\n")
    f.write(output)

print("\n✅ Data integration guide saved to DATA_INTEGRATION_GUIDE.md")