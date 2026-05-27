Check primitive validity for current stage.

python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
# evolution_engine: dormant — pending substrate migration
# primitives: dormant — pending substrate migration
from substrate.state.context.context import load_context_from_env
from substrate.state.business.business_instance import BusinessInstanceManager
ctx = load_context_from_env()
bim = BusinessInstanceManager(ctx)
venture_id = bim.get_primary_venture_id() or 'lyfe_institute'
ee = EvolutionEngine(ctx)
stage = ee.get_current_stage(venture_id)
print(f'Venture: {venture_id} | Stage {stage}')
for pid in PRIMITIVE_LIBRARY:
  result = ee.is_primitive_unlocked(pid)
  status = 'OK' if result['applies'] else '--'
  print(f'{status} {pid}')
  if not result['applies']:
    print(f'   -> {result.get(\"what_applies_instead\",\"\")[:60]}')
"
