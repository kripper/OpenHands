"""
This runtime runs the action_execution_server directly on the local machine without Docker.
"""

import os
import subprocess
import threading
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

import requests
import tenacity
from requests import Response

from openhands.core.config import AppConfig
from openhands.core.logger import openhands_logger as logger
from openhands.events import EventStream
from openhands.events.action import Action
from openhands.events.observation import ErrorObservation, Observation
from openhands.events.serialization import event_to_dict, observation_from_dict
from openhands.runtime.base import Runtime, RuntimeDisconnectedError
from openhands.runtime.plugins import PluginRequirement
from openhands.runtime.utils import find_available_tcp_port
from openhands.runtime.utils.request import send_request
from openhands.utils.async_utils import call_sync_from_async
from openhands.utils.tenacity_stop import stop_if_should_exit


class LocalRuntime(Runtime):
    """This runtime will run the action_execution_server directly on the local machine.
    When receiving an event, it will send the event to the server via HTTP.

    Args:
        config (AppConfig): The application configuration.
        event_stream (EventStream): The event stream to subscribe to.
        sid (str, optional): The session ID. Defaults to 'default'.
        plugins (list[PluginRequirement] | None, optional): List of plugin requirements. Defaults to None.
        env_vars (dict[str, str] | None, optional): Environment variables to set. Defaults to None.
    """

    def __init__(
        self,
        config: AppConfig,
        event_stream: EventStream,
        sid: str = "default",
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
    ):
        self.config = config
        self._host_port = 30000  # initial dummy value
        self._runtime_initialized: bool = False
        self.api_url = f"{self.config.sandbox.local_runtime_url}:{self._host_port}"
        self.session = requests.Session()
        self.status_callback = status_callback
        self.server_process: Optional[subprocess.Popen[str]] = None
        self.action_semaphore = threading.Semaphore(1)  # Ensure one action at a time

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

    async def connect(self):
        """Start the action_execution_server on the local machine."""
        self.send_status_message("STATUS$STARTING_RUNTIME")

        self._host_port = self._find_available_port()
        self.api_url = f"{self.config.sandbox.local_runtime_url}:{self._host_port}"

        plugin_arg = ""
        if self.plugins is not None and len(self.plugins) > 0:
            plugin_arg = f"--plugins {' '.join([plugin.name for plugin in self.plugins])} "

        if self.config.sandbox.browsergym_eval_env is not None:
            browsergym_arg = f"--browsergym-eval-env {self.config.sandbox.browsergym_eval_env}"
        else:
            browsergym_arg = ""

        # Start the server process
        cmd = (
            f"python -u -m openhands.runtime.action_execution_server {self._host_port} "
            f"--working-dir {self.config.workspace_mount_path_in_sandbox} "
            f"{plugin_arg}"
            f"--username {'openhands' if self.config.run_as_openhands else 'root'} "
            f"--user-id {self.config.sandbox.user_id} "
            f"{browsergym_arg}"
        )

        self.log("debug", f"Starting server with command: {cmd}")
        self.server_process = subprocess.Popen(
            cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Start a thread to read and log server output
        def log_output():
            if self.server_process and self.server_process.stdout:
                while True:
                    line = self.server_process.stdout.readline()
                    if not line:
                        break
                    self.log("debug", f"Server: {line.strip()}")

        log_thread = threading.Thread(target=log_output, daemon=True)
        log_thread.start()

        self.log("info", f"Waiting for server to become ready at {self.api_url}...")
        self.send_status_message("STATUS$WAITING_FOR_CLIENT")

        await call_sync_from_async(self._wait_until_alive)

        if not self.attach_to_existing:
            await call_sync_from_async(self.setup_initial_env)

        self.log(
            "debug",
            f"Server initialized with plugins: {[plugin.name for plugin in self.plugins]}",
        )
        if not self.attach_to_existing:
            self.send_status_message(" ")
        self._runtime_initialized = True

    def _find_available_port(self) -> int:
        """Find an available port to use for the server."""
        return find_available_tcp_port()

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=0.1, min=0.1, max=1),
        stop=stop_if_should_exit,
        before_sleep=lambda retry_state: logger.debug(
            f"Waiting for server to be ready... (attempt {retry_state.attempt_number})"
        ),
    )
    def _wait_until_alive(self):
        """Wait until the server is ready to accept requests."""
        if self.server_process and self.server_process.poll() is not None:
            raise RuntimeError("Server process died")

        try:
            response = self.session.get(f"{self.api_url}/health")
            response.raise_for_status()
            return True
        except Exception as e:
            self.log("debug", f"Server not ready yet: {e}")
            raise

    async def execute_action(self, action: Action) -> Observation:
        """Execute an action by sending it to the server."""
        if not self._runtime_initialized:
            return ErrorObservation("Runtime not initialized")

        if self.server_process is None or self.server_process.poll() is not None:
            return ErrorObservation("Server process died")

        with self.action_semaphore:
            try:
                response = await call_sync_from_async(
                    lambda: self.session.post(
                        f"{self.api_url}/action",
                        json={"action": event_to_dict(action)},
                    )
                )
                return observation_from_dict(response.json())
            except requests.exceptions.ConnectionError:
                raise RuntimeDisconnectedError("Server connection lost")
            except requests.exceptions.RequestException as e:
                return ErrorObservation(f"Failed to execute action: {e}")

    def close(self):
        """Stop the server process."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None

        super().close()