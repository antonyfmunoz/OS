Check primitive validity for current stage.

python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.evolution_engine import EvolutionEngine
from eos_ai.primitives import PRIMITIVE_LIBRARY
from eos_ai.context import load_context_from_env
from eos_ai.business_instance import BusinessInstanceManager
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
