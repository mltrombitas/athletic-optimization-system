import anthropic
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# System Architect Instructions
system_prompt = """You are an expert System Architect specializing in athletic performance optimization systems.

Your job:
- Design data flow architecture for multi-device integration (Oura, Garmin, Polar, Stryd)
- Specify API integration requirements
- Define database schema for training/recovery data
- Create system diagrams and technical specifications
- Identify potential bottlenecks and solutions

Be specific, technical, and actionable."""

# The question we're asking
user_question = """Design the system architecture for an athletic optimization platform that:

1. Integrates data from:
   - Oura Ring (sleep, HRV, RHR, body temp, SPO2)
   - Garmin Connect API (workouts, HR, pace, cadence, power from Stryd)
   
2. Analyzes patterns across:
   - Training load
   - Recovery metrics
   - Sleep quality
   - Performance trends

3. Generates recommendations for:
   - When to train hard vs easy
   - Optimal sleep timing
   - Recovery interventions needed
   - Performance predictions

Provide:
- High-level architecture diagram (text description)
- API integration approach
- Database schema recommendations
- Processing pipeline design"""

# Make the API call
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    system=system_prompt,
    messages=[
        {"role": "user", "content": user_question}
    ]
)

# Print the response
print(message.content[0].text)
# Save to file
with open("ARCHITECTURE.md", "w") as f:
    f.write("# Athletic Optimization System Architecture\n\n")
    f.write(message.content[0].text)

print("\n✅ Architecture saved to ARCHITECTURE.md")