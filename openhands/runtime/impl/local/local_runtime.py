import os
import subprocess
import threading
from pathlib import Path
from typing import Callable

import docker

from openhands.core.config import AppConfig
from openhands.events import EventStream
from openhands.events.action import (
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
)
from openhands.events.action.action import Action
from openhands.events.observation import (
    Observation,
)
from openhands.events.observation.commands import (
    CmdOutputObservation,
    IPythonRunCellObservation,
)
from openhands.events.observation.empty import NullObservation
from openhands.runtime.base import (
    Runtime,
)
from openhands.runtime.plugins import PluginRequirement


class LogBuffer:
    """Synchronous buffer for Docker container logs.

    This class provides a thread-safe way to collect, store, and retrieve logs
    from a Docker container. It uses a list to store log lines and provides methods
    for appending, retrieving, and clearing logs.
    """

    def __init__(self, container: docker.models.containers.Container, logFn: Callable):
        self.init_msg = 'Runtime client initialized.'

        self.buffer: list[str] = []
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self.log_generator = container.logs(stream=True, follow=True)
        self.log_stream_thread = threading.Thread(target=self.stream_logs)
        self.log_stream_thread.daemon = True
        self.log_stream_thread.start()
        self.log = logFn

    def append(self, log_line: str):
        with self.lock:
            self.buffer.append(log_line)

    def get_and_clear(self) -> list[str]:
        with self.lock:
            logs = list(self.buffer)
            self.buffer.clear()
            return logs

    def stream_logs(self):
        """Stream logs from the Docker container in a separate thread.

        This method runs in its own thread to handle the blocking
        operation of reading log lines from the Docker SDK's synchronous generator.
        """
        try:
            for log_line in self.log_generator:
                if self._stop_event.is_set():
                    break
                if log_line:
                    decoded_line = log_line.decode('utf-8').rstrip()
                    self.append(decoded_line)
        except Exception as e:
            self.log('error', f'Error streaming docker logs: {e}')

    def __del__(self):
        pass
        # if self.log_stream_thread.is_alive():
        #     self.log(
        #         'warn',
        #         "LogBuffer was not properly closed. Use 'log_buffer.close()' for clean shutdown.",
        #     )
        #     self.close(timeout=5)

    def close(self, timeout: float = 5.0):
        self._stop_event.set()
        self.log_stream_thread.join(timeout)
        # Close the log generator to release the file descriptor
        if hasattr(self.log_generator, 'close'):
            self.log_generator.close()


class LocalRuntime(Runtime):
    """This runtime will subscribe the event stream.
    When receive an event, it will send the event to runtime-client which run inside the docker environment.

    Args:
        config (AppConfig): The application configuration.
        event_stream (EventStream): The event stream to subscribe to.
        sid (str, optional): The session ID. Defaults to 'default'.
        plugins (list[PluginRequirement] | None, optional): List of plugin requirements. Defaults to None.
        env_vars (dict[str, str] | None, optional): Environment variables to set. Defaults to None.
    """

    # Need to provide this method to allow inheritors to init the Runtime
    # without initting the EventStreamRuntime.
    def init_base_runtime(
        self,
        config: AppConfig,
        event_stream: EventStream,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
    ):
        super().__init__(
            config,
            event_stream,
            sid,
            plugins,
            env_vars,
            status_callback,
            attach_to_existing,
            headless_mode,
        )

    def __init__(
        self,
        config: AppConfig,
        event_stream: EventStream,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
    ):
        self.init_base_runtime(
            config,
            event_stream,
            sid,
            plugins,
            env_vars,
            status_callback,
            attach_to_existing,
            headless_mode,
        )

    async def connect(self):
        pass

    def run(self, action: CmdRunAction) -> Observation:
        command = action.command
        for editor in ['nano', 'vi', 'vim', 'pico', 'joe', 'emacs']:
            if f'{editor} ' in command:
                content = 'Use non interactive command to edit files'
                break
        else:
            if os.getenv('ENABLE_THIS', '1'):
                os.chdir('/testbed')
                content = os.popen(command).read()
            else:
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    cwd='/testbed',
                )
                output, error = proc.communicate(timeout=10)
                content = '\n'.join([output, error])
            if not content.strip():
                content = '[Command executed successfully with no output]'
        obs = CmdOutputObservation(
            command_id=action.id, command=command, content=content
        )
        return obs

    def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        code = action.code
        imports = 'from openhands.runtime.plugins.agent_skills.agentskills import *'
        cwd_code = 'import os; os.chdir("/testbed")'
        with open('/tmp/code.py', 'w') as f:
            codes = code.strip().splitlines()
            # wrap the code with print() if it doesn't end with print()
            last_line = codes[-1]
            # have only ) bracket
            l_count = last_line.count('(')
            r_count = last_line.count(')')
            if not last_line.startswith('print') and l_count == r_count:
                codes[-1] = 'print(' + codes[-1] + ')'
            f.write(imports + '\n' + cwd_code + '\n' + '\n'.join(codes))
        proc = subprocess.run(
            ['poetry', 'run', 'python', '/tmp/code.py'],
            capture_output=True,
            text=True,
        )
        content = '\n'.join([proc.stdout, proc.stderr])
        if not content.strip():
            content = '[Code executed successfully with no output]'

        return IPythonRunCellObservation(
            content,
            action.code,
        )

    def run_action(self, action: Action) -> Observation:
        if isinstance(action, CmdRunAction):
            return self.run(action)
        elif isinstance(action, IPythonRunCellAction):
            return self.run_ipython(action)
        else:
            return super().run_action(action)

    def read(self, action: FileReadAction) -> Observation:
        return NullObservation('')

    def write(self, action: FileWriteAction) -> Observation:
        return NullObservation('')

    def browse(self, action: BrowseURLAction) -> Observation:
        return NullObservation('')

    def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        return NullObservation('')

    # ====================================================================
    # Implement these methods (for file operations) in the subclass
    # ====================================================================

    def copy_to(
        self, host_src: str, sandbox_dest: str, recursive: bool = False
    ) -> None:
        pass

    def list_files(self, path: str | None = None) -> list[str]:
        """List files in the sandbox.

        If path is None, list files in the sandbox's initial working directory (e.g., /workspace).
        """
        return []

    def copy_from(self, path: str) -> Path:
        """Zip all files in the sandbox and return as a stream of bytes."""
        return Path('')
