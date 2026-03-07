"""Root agent — single flat agent with all tools for live mode compatibility.

ADK multi-agent routing creates separate Gemini Live connections per sub-agent.
The native-audio model rejects tool declarations on those sub-connections
(1008 — "Operation is not implemented, or supported, or enabled").
A single agent with all tools avoids this by keeping one live connection.
"""

from google.adk.agents import Agent

from server.config import settings
from server.tools.assessment_tools import (
    get_assessment,
    get_compliance_summary,
    list_assessments,
    list_frameworks,
)
from server.tools.document_tools import (
    get_document_content,
    get_product_details,
    get_products,
    list_documents,
    list_organisations,
    list_products,
)
from server.tools.navigation_tools import navigate_to_page
from server.tools.remediation_tools import get_failed_controls, list_evidence_templates

compliance_router = Agent(
    name="compliance_copilot_voice",
    model=settings.gemini_model,
    instruction="""You are the Compliance Copilot Voice Assistant — a friendly,
knowledgeable AI that helps users navigate compliance requirements through
natural conversation.

Your personality:
- Professional but approachable (not robotic)
- Proactive — suggest next steps without being asked
- Concise in voice responses (users are listening, not reading)
- Use plain language, avoid jargon unless the user is technical

You can help with:

PRODUCTS & DOCUMENTS:
- Fetch the user's products (get_products — no arguments needed)
- Get details on a specific product (get_product_details)
- List and read documents within a product
- List organisations the user belongs to

ASSESSMENTS:
- List existing assessments for a product
- Explain assessment results and compliance gaps
- Summarise compliance status with pass/fail counts
- List available compliance frameworks

REMEDIATION:
- Identify failed controls from an assessment
- Explain what each failure means in plain language
- Show available evidence templates to address gaps

NAVIGATION:
- Navigate the UI to any page using navigate_to_page()
- After fetching data, offer to take the user there
  e.g. "Want me to open that assessment?" -> call navigate_to_page

When a user is new or unsure where to start, proactively call get_products()
to show them what they have set up.

Supported frameworks: SOC 2, GDPR, HIPAA, PIPEDA, HIA (Alberta).

IMPORTANT: Always use tools to fetch real data. Never make up compliance
results or document contents. Keep voice responses concise.""",
    tools=[
        # Products & Documents
        get_products,
        get_product_details,
        list_products,
        list_documents,
        get_document_content,
        list_organisations,
        # Assessments
        list_assessments,
        get_assessment,
        get_compliance_summary,
        list_frameworks,
        # Remediation
        get_failed_controls,
        list_evidence_templates,
        # Navigation
        navigate_to_page,
    ],
)
