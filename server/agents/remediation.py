"""Remediation specialist agent — identifies gaps and helps fix them."""

from google.adk.agents import Agent

from server.config import settings
from server.tools.remediation_tools import get_failed_controls, list_evidence_templates

remediation_agent = Agent(
    name="remediation_agent",
    model=settings.gemini_model,
    instruction="""You help users fix compliance gaps. When a user wants to remediate
a failed control, you can identify which controls failed and what evidence templates
are available to address them.

Guide users through the remediation process step by step:
1. Identify failed controls from their assessment
2. Explain what each failure means in plain language
3. Suggest which documents or policies would fix each gap
4. Help them understand the available evidence templates

Keep voice responses concise — users are listening, not reading.""",
    tools=[get_failed_controls, list_evidence_templates],
)
