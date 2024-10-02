import json
from typing import Callable

import requests

from openhands.core.config import AppConfig
from openhands.events.action.commands import CmdRunAction, IPythonRunCellAction
from openhands.events.observation import (
    Observation,
)
from openhands.events.observation.commands import (
    CmdOutputObservation,
    IPythonRunCellObservation,
)
from openhands.events.stream import EventStream
from openhands.runtime.plugins import PluginRequirement
from openhands.runtime.runtime import Runtime


class EC2Runtime(Runtime):
    def __init__(
        self,
        config: AppConfig,
        event_stream: EventStream,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_message_callback: Callable | None = None,
    ):
        super().__init__(
            config, event_stream, sid, plugins, env_vars, status_message_callback
        )
        self.url = 'http://127.0.0.1:5000/execute'

    def run(self, action: CmdRunAction) -> Observation:
        command = action.command
        # http://127.0.0.1:5000/execute
        headers = {'Content-Type': 'application/json'}
        data = {'command': command}
        response = requests.post(self.url, headers=headers, data=json.dumps(data))
        content = response.json()['output']
        obs = CmdOutputObservation(
            command_id=action.id, command=command, content=content
        )
        return obs

    def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        return IPythonRunCellObservation(
            'Not implemented. Please execute bash only for now.', action.code
        )

    def list_files(self, path: str | None = None) -> list[str]:
        return []

    def copy_to(self, action):
        pass
