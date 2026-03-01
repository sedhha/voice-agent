"""Document specialist agent — manages compliance documents."""

from google.adk.agents import Agent

from server.config import settings
from server.tools.document_tools import (
    get_document_content,
    list_documents,
    list_organisations,
    list_products,
)

document_agent = Agent(
    name="document_agent",
    model=settings.gemini_model,
    instruction="""You help users manage compliance documents. You can list existing
documents, read their content, and explain what documents are needed for specific
frameworks.

When discussing documents, explain their relevance to compliance controls.
Guide users on what types of documents they should prepare (privacy policies,
security procedures, incident response plans, etc.).

Keep voice responses concise — users are listening, not reading.""",
    tools=[list_documents, get_document_content, list_products, list_organisations],
)
