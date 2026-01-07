import anthropic
import os
from dotenv import load_dotenv
import base64

load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

def encode_image(image_path):
    """Convert image to base64 for Claude API"""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")

def generate_briefing(oura_screenshot_path, training_log_path):
    """Generate morning briefing from screenshots"""
    
    # Encode images
    oura_image = encode_image(oura_screenshot_path)
    training_image = encode_image(training_log_path)
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system="""You are Michael's Performance Optimization Analyst.

Generate his daily training briefing in this EXACT format:

==============================================
TRAINING BRIEFING - [Date]
==============================================

RECOVERY STATUS: [✅ READY / ⚠️ ELEVATED / 🔴 REST NEEDED]
- RHR: [X] bpm ([comparison to 49 baseline])
- HRV: [X] ms ([status])
- Sleep: [X] hrs, [X]% efficiency, [X] hrs deep
- Readiness: [X]/100

TRAINING PROGRESS:
- Total miles: [X] (Week [X] complete)
- Improvement since Oct 15:
  • RHR: [start] → [current] bpm ([change])
  • Threshold: [start] → [current]/mile ([change])
  • Mt Ryan: [start] → [current] ([change])

CURRENT PHASE: [Phase] (Week [X] of 24)
- Next tempo: [Day] ([X] days)
- Next Mt Ryan: [Date] ([X] days)
- Next long run: [Date] ([X] days)
- Race day: March 29 ([X] days, [X] weeks)

THIS WEEK:
- Target: [X]-[X] miles
- Current: [X] miles
- Remaining: [X]-[X] miles

TODAY'S WORKOUT: [Workout Type]
- Target pace: [X]:[X]/mile
- Target HR: [X]-[X] bpm (Zone [X])
- Distance: [X] miles
- Focus: [Primary focus]

FUEL PLAN:
- Pre-run: [Specific foods and amounts]
- During: [Fuel strategy]
- Post-run: [Recovery nutrition]

FOCUS AREAS:
[3-4 specific tactical items]

WHY THIS MATTERS:
[1-2 sentence physiological reasoning]

SYSTEM INSIGHT:
[Current trajectory, predictions, confidence levels]
==============================================

Extract ALL data from the screenshots. Be specific with numbers. Reference his training plan.""",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": oura_image
                        }
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": training_image
                        }
                    },
                    {
                        "type": "text",
                        "text": "Generate my morning training briefing from these screenshots. Today is Tuesday, January 07, 2026. Week 12 training cycle."
                    }
                ]
            }
        ]
    )
    
    return message.content[0].text

# Usage
if __name__ == "__main__":
    # You'll upload screenshots, this script processes them
    briefing = generate_briefing(
        "oura_morning.png",
        "training_log.png"
    )
    
    print(briefing)
    
    # Save to file
    with open("DAILY_BRIEFING.txt", "w") as f:
        f.write(briefing)
    
    print("\n✅ Briefing saved to DAILY_BRIEFING.txt")