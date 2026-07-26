"""LFPOOP — the Manual as data, in Python and Prolog. Stdlib core; uco for chains."""
from .ontology import (THE_QUESTION, LADDER, ARCHITECTURE, COOLING, LOOP,
                       CONDITIONAL_VERBS, PIPELINE, AGENT_RITES, NODE_FIELDS,
                       Node, next_level, admissible_transition, run_loop)
from . import domain
from . import prolog
# chains imports uco; kept lazy so the stdlib core stays zero-dep:
#   from lfpoop import chains
