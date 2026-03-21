"""Onboarding tools — help new users understand and explore the product."""

from typing import Any

from google.adk.tools import ToolContext

JsonDict = dict[str, Any]


async def get_product_overview(
    tool_context: ToolContext,
) -> JsonDict:
    """Return an overview of Krep for new or curious users.

    Call this when a user asks "what is this?", "what can you do?",
    "how does this work?", "give me a tour", or seems unfamiliar with
    the platform. Also call it on first interaction if the user has no
    products set up yet.

    Returns:
        A dict with product description, key features, supported frameworks,
        and a getting-started workflow that the agent should speak aloud.
    """
    _ = tool_context  # required by ADK but unused here
    return {
        "product_name": "Krep",
        "tagline": "AI-powered compliance assessments — upload your docs, get a verdict in minutes, and fix what's missing.",
        "description": (
            "Krep is a compliance assessment platform that uses AI to analyze "
            "your policies, procedures, and security documents against industry "
            "frameworks like SOC 2, GDPR, and HIPAA. Instead of spending weeks "
            "on manual audits, you upload your documents, run an assessment, and "
            "Krep tells you exactly which controls pass, which fail, and why — "
            "with citations back to your actual document text."
        ),
        "key_features": [
            "Upload PDFs or write policies directly in the app — Krep reads and understands them all",
            "Run AI assessments against SOC 2, GDPR, HIPAA, PIPEDA, or HIA in minutes, not weeks",
            "See a clear pass-or-fail verdict for every control, with evidence citations from your documents",
            "Use the remediation wizard to fix compliance gaps — it guides you step by step like a GPS",
            "Generate missing policy documents with AI — just pick a template and Krep drafts it for you",
            "Talk to me like your compliance assistant, and I'll help you navigate the app hands-free and get answers fast",
        ],
        "supported_frameworks": [
            {"name": "SOC 2", "description": "Service Organization Control 2 — trust services criteria for SaaS and cloud services"},
            {"name": "GDPR", "description": "EU General Data Protection Regulation — data privacy for European users"},
            {"name": "HIPAA", "description": "US Health Insurance Portability and Accountability Act — healthcare data protection"},
            {"name": "PIPEDA", "description": "Canadian Personal Information Protection and Electronic Documents Act"},
            {"name": "HIA", "description": "Alberta Health Information Act — provincial health data rules"},
        ],
        "getting_started_steps": [
            "First, create a product — that's the app or service you want to assess, like your SaaS platform or mobile app",
            "Next, upload your compliance documents — things like security policies, privacy policies, or access control procedures",
            "Then, pick a framework and run an assessment — Krep will analyze all your documents and tell you where you stand",
            "Finally, check your results and use the remediation wizard to close any gaps — it'll guide you on exactly what to fix or generate",
        ],
    }
