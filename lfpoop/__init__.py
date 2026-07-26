"""LFPOOP — the Manual as data, in Python and Prolog. Stdlib core; uco for chains."""
from .ontology import (THE_QUESTION, LADDER, ARCHITECTURE, COOLING, LOOP,
                       CONDITIONAL_VERBS, PIPELINE, AGENT_RITES, NODE_FIELDS,
                       Node, next_level, admissible_transition, run_loop)
from . import domain
from . import prolog
from . import onion
from . import deltas
from . import gp
from . import blocks
from . import rollup
from . import envelope
from . import alphabets
from . import classify
from .climb import kleene_climb, REQUIREMENTS
# chains imports uco; kept lazy so the stdlib core stays zero-dep:
#   from lfpoop import chains
# onion2 imports pydantic + pydantic_stack_core; kept lazy for the same law:
#   from lfpoop import onion2
