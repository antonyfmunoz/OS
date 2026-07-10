# Secret Reference Manifest — umh-mesh.service (least-privilege).
# The host node-mesh relay only needs the mesh secrets, not the full
# services/.env.tpl set. Injected at runtime via scripts/op_run.sh
# (op run); this file holds op:// references only, never values.
UMH_MESH_RELAY_SECRET=op://${UMH_OP_VAULT}/Mesh-Relay-Secret/password
UMH_MESH_VERDICT_SECRET=op://${UMH_OP_VAULT}/Mesh-Verdict-Secret/password
