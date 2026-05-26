---
name: new-primitive
description: Use when adding a new business primitive to PRIMITIVE_LIBRARY — knowledge truth with validity matrix.
allowed-tools: Bash, Read, Edit
---

# How to Add a Business Primitive

## Steps

### 1. Add to PRIMITIVE_LIBRARY in primitives.py

  'primitive_id': KnowledgePrimitive(
    id='primitive_id',
    principle='The timeless truth',
    domain='sales|marketing|hiring|finance|growth',
    evidence=['Source'],
    application='How to use it',
    exception='When it does not apply',
    source='offer_theory|influence_theory|general',
    stage_applicability={1: False, 2: True, 3: True},
    validity_conditions=[{
      'context': 'bootstrapped_pre_revenue',
      'applies': False,
      'warning': 'Why not',
      'what_applies_instead': 'Alternative',
      'when_it_applies': 'Milestone',
    }],
    common_misapplication='Most common mistake',
  ),

### 2. Add prerequisites if needed
PRIMITIVE_PREREQUISITES['id'] = ['prereq_1']

### 3. Test
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from substrate.state.context.context import load_context_from_env
# NOTE: EvolutionEngine was removed during convergence.
# Primitive validation now lives in substrate.ontology.primitives
from substrate.understanding.ontology.primitives import PRIMITIVE_LIBRARY
print('primitive_id' in PRIMITIVE_LIBRARY)
"

## Validity matrix checklist
- [ ] stage_applicability 1-3 set
- [ ] validity_conditions for bootstrapped
- [ ] common_misapplication documented
- [ ] prerequisites added if dependent
- [ ] what_applies_instead specified
