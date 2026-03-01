"""Assessment specialist agent — runs and explains compliance assessments."""

from google.adk.agents import Agent

from server.config import settings
from server.tools.assessment_tools import (
    get_assessment,
    get_compliance_summary,
    list_assessments,
    list_frameworks,
)

assessment_agent = Agent(
    name="assessment_agent",
    model=settings.gemini_model,
    instruction="""You help users run and understand compliance assessments.
You can list existing assessments, explain results, and summarise compliance gaps.

When a user asks about their compliance status, use the available tools to fetch
real data and explain it clearly in plain language. Always mention specific control
IDs and their pass/fail status when discussing results.

Keep voice responses concise — users are listening, not reading.

Supported frameworks: SOC 2, GDPR, HIPAA, PIPEDA, HIA (Alberta).""",
    tools=[list_assessments, get_assessment, get_compliance_summary, list_frameworks],
)
