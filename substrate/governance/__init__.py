"""UMH Governance — risk classification, authority, and policy enforcement.

Public entry point: substrate.control_plane.governance.ConcreteGovernanceEngine

Internal engines (not for direct external use):
  - AuthorityEngine  — business-action governance (send_dm, execute_payment)
  - PolicyEngine     — capability-level governance (READ_ONLY, FINANCIAL)
  - ActionRiskCategory — semantic side-effect classification
"""
