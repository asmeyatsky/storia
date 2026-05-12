"""
Module: storia.infrastructure
Layer: infrastructure
Ports: implements domain.ports
MCP integration: storia.infrastructure.mcp.* — one server per bounded context
Stack: Python 3.12 + psycopg, google-cloud-pubsub, anthropic, httpx

Adapters for every domain port. Tests substitute the in_memory adapters here.
"""
