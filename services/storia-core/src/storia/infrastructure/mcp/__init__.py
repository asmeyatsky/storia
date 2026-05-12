"""
Module: storia.infrastructure.mcp
Layer: infrastructure (Rules §2 — MCP servers live in infrastructure)
Ports: depends on application use cases
MCP integration: this package IS the MCP server registry. One server per bounded context
                 (Rules §3.5). Tools = writes. Resources = reads.
Stack: stdlib + storia.application

Bounded contexts in v1:
  - guest_signal_server   (ingest, identity resolution)
  - action_engine_server  (playbook evaluation, action queueing)
  - operator_console_server (shift view, approvals, audit access)
"""
