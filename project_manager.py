import anthropic
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# Project Manager Instructions
system_prompt = """You are an expert Project Manager specializing in technical project coordination and AI system integration.

Your job:
- Coordinate work across multiple specialists
- Create integration roadmaps
- Define milestones and deliverables
- Identify dependencies and risks
- Manage timeline and resource allocation
- Ensure all components work together

Focus on practical execution and clear accountability."""

# The question
user_question = """Create the master integration and execution plan for the athletic optimization system:

**TEAM OUTPUTS TO INTEGRATE:**
1. System Architect → Overall architecture design
2. Data Engineer → API integration specifications
3. Backend Developer → Python implementation code
4. Data Analyst → Recommendation engine logic
5. QA/DevOps → Testing and deployment strategy

**PROJECT PHASES:**

**Phase 1: Foundation (Week 1-2)**
- Set up development environment
- Implement OAuth authentication for both APIs
- Create database schema
- Build basic data fetching

**Phase 2: Data Pipeline (Week 3-4)**
- Implement data transformation (km→miles)
- Build automated daily sync
- Add data validation and error handling
- Test end-to-end data flow

**Phase 3: Analysis Engine (Week 5-6)**
- Implement recommendation algorithms
- Build alert system (RHR, HRV thresholds)
- Create trend analysis
- Test decision logic

**Phase 4: Testing & Deployment (Week 7-8)**
- Comprehensive testing (unit, integration, end-to-end)
- Security audit
- Set up monitoring
- Deploy to production
- Documentation finalization

**DELIVERABLES:**
- Detailed task breakdown for each phase
- Dependency mapping
- Risk assessment and mitigation
- Success metrics
- Timeline with milestones
- Handoff protocols between specialists
- Integration testing checklist

**PROVIDE:**
- Gantt chart (text format)
- Task assignments
- Integration sequence
- Testing gates
- Go-live checklist"""

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
with open("PROJECT_PLAN.md", "w") as f:
    f.write("# Project Integration Plan\n\n")
    f.write("**Athletic Optimization System - Master Execution Roadmap**\n\n")
    f.write(output)

print("\n✅ Project plan saved to PROJECT_PLAN.md")