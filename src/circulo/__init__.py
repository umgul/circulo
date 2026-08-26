# -*- coding: utf-8 -*-
"""circulo — skill trees an agent has to earn, and can lose.

    from circulo import Circulo, KIND_STUDY, KIND_CREATION

    c = Circulo()
    c.add_ring("rust", KIND_STUDY, "read the ownership chapter",
               {"projects": 0.7, "contributes": 0.6, "fulfils": 0.5})
    c.mastery_of("rust")     # -> level READ from evidence, never granted
    c.can("rust")            # -> False until it has actually been earned

Levels are read from two continuous quantities, not unlocked. Evidence kinds
weigh differently. Hollow work records nothing. Repetition consolidates but
does not teach. Unused mastery decays.

Holds no I/O: serialise with ``to_dict`` / ``from_dict`` into whatever your
architecture already persists.
"""

from .core import (  # noqa: F401
    DORMANCY_DAYS,
    FELT_WEIGHTS,
    KIND_CREATION,
    KIND_DISTILL,
    KIND_PRACTICE,
    KIND_STUDY,
    LEVEL_NAMES,
    RING_FELT_FLOOR,
    Circulo,
    MasteryLevel,
    MasteryTree,
    Ring,
    read_level,
)

__version__ = "0.1.0"

__all__ = [
    "Circulo", "MasteryTree", "Ring", "MasteryLevel", "LEVEL_NAMES",
    "KIND_STUDY", "KIND_PRACTICE", "KIND_CREATION", "KIND_DISTILL",
    "read_level", "RING_FELT_FLOOR", "DORMANCY_DAYS", "FELT_WEIGHTS",
    "__version__",
]
