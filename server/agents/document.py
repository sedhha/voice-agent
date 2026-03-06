"""Document specialist agent — manages compliance documents."""

from google.adk.agents import Agent

from server.config import settings
from server.tools.document_tools import (
    get_document_content,
    get_product_details,
    get_products,
    list_documents,
    list_organisations,
    list_products,
)

document_agent = Agent(
    name="document_agent",
    model=settings.gemini_model,
    instruction="""You help users manage compliance documents and discover their products.

You can:
- Fetch the user's products (use get_products — no arguments needed)
- Get details on a specific product (use get_product_details with the product ID)
- List and read documents within a product
- Explain what documents are needed for specific frameworks

When a user doesn't know their product ID or is unsure what they have set up,
call get_products first to show them their options, then let them pick.

When discussing documents, explain their relevance to compliance controls.
Guide users on what types of documents they should prepare (privacy policies,
security procedures, incident response plans, etc.).

Keep voice responses concise — users are listening, not reading.""",
    tools=[list_documents, get_document_content, list_products, list_organisations, get_products, get_product_details],
)
