"""Substrate contracts — canonical Protocol interfaces for the UMH substrate.

All 23 Protocol classes are consolidated into 7 domain contract files:

  governance_protocol     — GovernanceEngine
  execution_protocol      — ExecutionSpine, TraceRecorder, FeedbackCapture
  control_plane_protocol  — IdentityResolver, ContextAssembler, MemorySystem,
                            ComponentRegistry, SignalRouter, Notifier
  integration_protocol    — SignalEmitter, CapabilityHandler, OutcomeReceiver,
                            ViewSubscriber (+ descriptors)
  infrastructure_protocol — SubstrateStorage, AdapterProtocol,
                            ProjectionPortProtocol
  understanding_protocol  — DomainBridge, Source
  organism_protocol       — RuntimeAdapter, AgentStatus, LearningSignal, etc.

Plus existing contract files:
  adapter_contracts       — AdapterCapability, AdapterDescriptor, AdapterRegistry
  agent_runtime_contracts — AgentRuntimeProtocol
  agent_types             — TaskType, ModelProvider, RoutingResult
  routing_contracts       — CapabilityClass, PrivacyLevel, CapabilityEntry
"""
