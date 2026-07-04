#!/usr/bin/env bash
# Install UMH pre-commit hooks into the repository.
# Run once after clone: bash scripts/install_hooks.sh
#
# The installed hook runs the canonical 11-gate set (see scripts/pre-commit for
# the same list). All gates run in fail-accumulate mode so the developer sees
# EVERY violation at once. Keep this list in sync with scripts/pre-commit.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$(git rev-parse --git-common-dir)/hooks"

cat > "$HOOK_DIR/pre-commit" << 'HOOK'
#!/usr/bin/env bash
# UMH Pre-Commit Gate — runs all coherence gates before allowing a commit.
# All gates run (fail-accumulate) so the developer sees ALL violations at once.

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
FAILED=0

run_gate() {
    local label="$1" script="$2"
    if [ -f "$REPO_ROOT/scripts/$script" ]; then
        echo "── $label ──"
        if ! python3 "$REPO_ROOT/scripts/$script"; then
            FAILED=1
        fi
    fi
}

run_gate "Gate 1: Type Coherence"          check_type_divergence.py
run_gate "Gate 2: Instance Context"        check_instance_leak.py
run_gate "Gate 3: Projection Boundary"     check_projection_leak.py
run_gate "Gate 4: Dependency Direction"    check_dependency_direction.py
run_gate "Gate 5: CPU Gate"                check_cpu_gate.py
run_gate "Gate 6: Ungoverned Mutations"    check_ungoverned_mutations.py
run_gate "Gate 7: Credential Injection"    check_credential_injection.py
run_gate "Gate 8: Secret Patterns"         check_secret_patterns.py
run_gate "Gate 9: Mesh Relay Firewall"     check_mesh_relay_firewall.py
run_gate "Gate 10: Pytest Collection"      check_pytest_collection.py
run_gate "Gate 11: Ontology Layers"        check_ontology_layers.py

exit $FAILED
HOOK

chmod +x "$HOOK_DIR/pre-commit"
echo "Pre-commit hook installed at $HOOK_DIR/pre-commit"
echo "Gates: type, instance, projection, dependency, cpu, ungoverned,"
echo "       credential, secret, mesh, pytest, ontology (11 total)"
