"""Reference agents: a deliberately naive document agent and its guarded twin.

The naive agent is the measuring instrument for the attack-validity gate; the guarded agent
provides the naive-vs-guardrailed delta for the demo. Neither is the product.
"""

from .guarded_agent import GuardedInvoiceAgent
from .llm import LLMClient, MockLLM, OpenAIClient, live_client_available
from .naive_agent import AgentRun, NaiveInvoiceAgent

__all__ = [
    "AgentRun",
    "GuardedInvoiceAgent",
    "LLMClient",
    "MockLLM",
    "NaiveInvoiceAgent",
    "OpenAIClient",
    "live_client_available",
]
