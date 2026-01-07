import anthropic
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# Backend Developer Instructions
system_prompt = """You are an expert Backend Developer specializing in Python API integrations and data pipelines.

Your job:
- Write production-ready Python code
- Implement OAuth authentication flows
- Create robust API client classes
- Build data transformation pipelines
- Include comprehensive error handling
- Write clean, well-documented code

Provide actual working code, not pseudocode."""

# The question
user_question = """Based on the system architecture and data integration specs, write the core Python modules for:

**MODULE 1: Oura API Client**
- OAuth 2.0 authentication
- Methods to fetch: sleep data, readiness, HRV, RHR, activity
- Rate limiting and error handling
- Data validation

**MODULE 2: Garmin API Client**
- OAuth 2.0 authentication
- Methods to fetch: workouts, activities, training metrics
- Parse Stryd data from Garmin activities
- Rate limiting and error handling

**MODULE 3: Data Transformer**
- **Convert ALL distances from km to miles**
- Standardize timestamps (UTC)
- Validate data ranges (HR, pace, etc.)
- Handle missing data
- Format for database storage

**MODULE 4: Database Manager**
- SQLite schema (can upgrade to PostgreSQL later)
- Insert/update operations
- Deduplication logic
- Query helpers for analysis

**REQUIREMENTS:**
- Production-ready code
- Type hints
- Docstrings
- Error handling
- Unit conversion constants (KM_TO_MILES = 0.621371)

Provide complete, working Python code for all 4 modules."""

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
with open("IMPLEMENTATION_CODE.md", "w") as f:
    f.write("# Implementation Code\n\n")
    f.write("**Athletic Optimization System - Core Python Modules**\n\n")
    f.write(output)

print("\n✅ Implementation code saved to IMPLEMENTATION_CODE.md")