import anthropic
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# Data Analyst Instructions
system_prompt = """You are an expert Data Analyst and Sports Scientist specializing in athletic performance optimization.

Your job:
- Design analytical models for training optimization
- Create recommendation algorithms based on recovery metrics
- Build predictive models for performance
- Define alert thresholds for overtraining/injury risk
- Specify data visualization strategies

Combine data science with sports science expertise."""

# The question
user_question = """Design the recommendation engine for athletic optimization:

**INPUT DATA:**
- Resting Heart Rate (RHR) trends
- Heart Rate Variability (HRV)
- Sleep quality metrics (efficiency, duration, deep sleep %)
- Training load (weekly mileage, intensity distribution)
- Recovery scores (Oura readiness)
- Performance metrics (pace at threshold HR, running power)
- Body temperature trends
- SPO2 readings

**OUTPUTS NEEDED:**
1. **Daily Training Recommendations:**
   - Go hard (quality workout)
   - Go moderate (tempo/steady)
   - Go easy (recovery run)
   - Rest day (full recovery needed)

2. **Recovery Interventions:**
   - Sleep optimization suggestions
   - Active recovery protocols
   - When to take extra rest

3. **Performance Predictions:**
   - Fitness trend analysis
   - Race readiness assessment
   - Optimal taper timing

4. **Risk Alerts:**
   - Overtraining warning signs
   - Injury risk indicators
   - Illness/burnout flags

**SPECIFIC REQUIREMENTS:**
- Define RHR threshold logic (e.g., >3 bpm above baseline = yellow flag)
- HRV interpretation (% deviation from norm)
- Sleep debt calculation
- Training load vs recovery balance
- Trend analysis (3-day, 7-day, 4-week windows)

**PROVIDE:**
- Decision tree logic for recommendations
- Alert threshold specifications
- Python implementation examples
- Visualization recommendations"""

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
with open("RECOMMENDATION_ENGINE.md", "w") as f:
    f.write("# Recommendation Engine Design\n\n")
    f.write("**Athletic Optimization System - Analysis & Decision Logic**\n\n")
    f.write(output)

print("\n✅ Recommendation engine design saved to RECOMMENDATION_ENGINE.md")