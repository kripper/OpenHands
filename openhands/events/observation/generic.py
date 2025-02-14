import json

from dataclasses import dataclass

from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation

@dataclass
class GenericObservation(Observation):
    """This data class represents a generic observation.
    It contains a dictionary with information that will be passed to the model.
    Use this for observations that don't require special processing.
    """

    observation: str = ObservationType.GENERIC
    extras: dict = None

    def __init__(self, content: str, extras: dict):
        self.content = ""
        self.extras = extras

    @property
    def message(self) -> str:
        return json.dumps(self.extras)
