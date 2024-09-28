"""
This is the main file for the runtime client.
It is responsible for executing actions received from OpenHands backend and producing observations.

NOTE: this will be executed inside the docker sandbox.
"""

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pexpect
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pexpect import EOF, TIMEOUT, ExceptionPexpect
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn import run

from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
)
from openhands.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)
from openhands.events.serialization import event_from_dict, event_to_dict
from openhands.runtime.browser import browse
from openhands.runtime.browser.browser_env import BrowserEnv
from openhands.runtime.plugins import (
    ALL_PLUGINS,
    JupyterPlugin,
    Plugin,
)
from openhands.runtime.utils import split_bash_commands
from openhands.runtime.utils.files import insert_lines, read_lines


class ActionRequest(BaseModel):
    action: dict


ROOT_GID = 0
INIT_COMMANDS = [
    'git config --global user.name "openhands" && git config --global user.email "openhands@all-hands.dev" && alias git="git --no-pager"',
    'export TERM=xterm-256color',
    "export PATH=/openhands/poetry/$(ls /openhands/poetry | sed -n '2p')/bin:$PATH",
]
SOFT_TIMEOUT_SECONDS = 5


class RuntimeClient:
    """RuntimeClient is running inside docker sandbox.
    It is responsible for executing actions received from OpenHands backend and producing observations.
    """

    def __init__(
        self,
        plugins_to_load: list[Plugin],
        work_dir: str,
        username: str,
        user_id: int,
        browsergym_eval_env: str | None,
    ) -> None:
        self.plugins_to_load = plugins_to_load
        self.username = username
        self.user_id = user_id
        self.pwd = work_dir  # current PWD
        self._initial_pwd = work_dir
        self._init_user(self.username, self.user_id)
        self._init_bash_shell(self.pwd, self.username)
        self.lock = asyncio.Lock()
        self.plugins: dict[str, Plugin] = {}
        self.browser = BrowserEnv(browsergym_eval_env)
        self.last_command = ''
        self.last_code = ''
        self.is_last_code_error = False
        self.start_time = time.time()
        self.last_execution_time = self.start_time

    @property
    def initial_pwd(self):
        return self._initial_pwd

    async def ainit(self):
        for plugin in self.plugins_to_load:
            await plugin.initialize(self.username)
            self.plugins[plugin.name] = plugin
            logger.info(f'Initializing plugin: {plugin.name}')

            if isinstance(plugin, JupyterPlugin):
                await self.run_ipython(
                    IPythonRunCellAction(code=f'import os; os.chdir("{self.pwd}")')
                )

        # This is a temporary workaround
        # TODO: refactor AgentSkills to be part of JupyterPlugin
        # AFTER ServerRuntime is deprecated
        if 'agent_skills' in self.plugins and 'jupyter' in self.plugins:
            self.kernel_init_code = (
                'from openhands.runtime.plugins.agent_skills.agentskills import *'
            )
            obs = await self.run_ipython(
                IPythonRunCellAction(code=self.kernel_init_code)
            )
            logger.info(f'AgentSkills initialized: {obs}')

        await self._init_bash_commands()
        logger.info('Runtime client initialized.')

    def _init_user(self, username: str, user_id: int) -> None:
        """Create working directory and user if not exists.
        It performs the following steps effectively:
        * Creates the Working Directory:
            - Uses mkdir -p to create the directory.
            - Sets ownership to username:root.
            - Adjusts permissions to be readable and writable by group and others.
        * User Verification and Creation:
            - Checks if the user exists using id -u.
            - If the user exists with the correct UID, it skips creation.
            - If the UID differs, it logs a warning and updates self.user_id.
            - If the user doesn't exist, it proceeds to create the user.
        * Sudo Configuration:
            - Appends %sudo ALL=(ALL) NOPASSWD:ALL to /etc/sudoers to grant
              passwordless sudo access to the sudo group.
            - Adds the user to the sudo group with the useradd command, handling
              UID conflicts by incrementing the UID if necessary.
        """

        # First create the working directory, independent of the user
        logger.info(f'Client working directory: {self.initial_pwd}')
        command = f'umask 002; mkdir -p {self.initial_pwd}'
        output = subprocess.run(command, shell=True, capture_output=True)
        out_str = output.stdout.decode()

        command = f'chown -R {username}:root {self.initial_pwd}'
        output = subprocess.run(command, shell=True, capture_output=True)
        out_str += output.stdout.decode()

        command = f'chmod g+rw {self.initial_pwd}'
        output = subprocess.run(command, shell=True, capture_output=True)
        out_str += output.stdout.decode()
        logger.debug(f'Created working directory. Output: [{out_str}]')

        # Skip root since it is already created
        if username == 'root':
            return

        # Check if the username already exists
        existing_user_id = -1
        try:
            result = subprocess.run(
                f'id -u {username}', shell=True, check=True, capture_output=True
            )
            existing_user_id = int(result.stdout.decode().strip())

            # The user ID already exists, skip setup
            if existing_user_id == user_id:
                logger.debug(
                    f'User `{username}` already has the provided UID {user_id}. Skipping user setup.'
                )
            else:
                logger.warning(
                    f'User `{username}` already exists with UID {existing_user_id}. Skipping user setup.'
                )
                self.user_id = existing_user_id
            return
        except subprocess.CalledProcessError as e:
            # Returncode 1 indicates, that the user does not exist yet
            if e.returncode == 1:
                logger.debug(
                    f'User `{username}` does not exist. Proceeding with user creation.'
                )
            else:
                logger.error(
                    f'Error checking user `{username}`, skipping setup:\n{e}\n'
                )
                raise

        # Add sudoer
        sudoer_line = r"echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"
        output = subprocess.run(sudoer_line, shell=True, capture_output=True)
        if output.returncode != 0:
            raise RuntimeError(f'Failed to add sudoer: {output.stderr.decode()}')
        logger.debug(f'Added sudoer successfully. Output: [{output.stdout.decode()}]')

        # Add user and change ownership of the initial working directory if it doesn't exist
        command = (
            f'useradd -rm -d /home/{username} -s /bin/bash '
            f'-g root -G sudo -o -u {user_id} {username}'
        )

        if not os.path.exists(self.initial_pwd):
            command += f' && mkdir -p {self.initial_pwd}'
            command += f' && chown -R {username}:root {self.initial_pwd}'
            command += f' && chmod g+s {self.initial_pwd}'

        output = subprocess.run(
            command,
            shell=True,
            capture_output=True,
        )
        if output.returncode != 0:
            raise RuntimeError(
                f'Failed to create user {username}: {output.stderr.decode()}'
            )

        command = 'deluser pn'
        output = subprocess.run(command, shell=True, capture_output=True)
        logger.debug(f'Output: {output.stdout.decode()}')

    def _init_bash_shell(self, work_dir: str, username: str) -> None:
        self.shell = pexpect.spawn(
            f'su {username}',
            encoding='utf-8',
            echo=False,
        )
        self.__bash_PS1 = (
            r'[PEXPECT_BEGIN]\n'
            # r'$(which python >/dev/null 2>&1 && echo "[Python Interpreter: $(which python)]\n")'
            r'\u@\h:\w\n'
            r'[PEXPECT_END]'
        )

        # This should NOT match "PS1=\u@\h:\w [PEXPECT]$" when `env` is executed
        self.__bash_expect_regex = r'\[PEXPECT_BEGIN\]\s*(.*?)\s*([a-z0-9_-]*)@([a-zA-Z0-9.-]*):(.+)\s*\[PEXPECT_END\]'
        # Set umask to allow group write permissions
        self.shell.sendline(f'umask 002; export PS1="{self.__bash_PS1}"; export PS2=""')
        self.shell.expect(self.__bash_expect_regex)

        self.shell.sendline(
            f'if [ ! -d "{work_dir}" ]; then mkdir -p "{work_dir}"; fi && cd "{work_dir}"'
        )
        self.shell.expect(self.__bash_expect_regex)
        logger.debug(
            f'Bash initialized. Working directory: {work_dir}. Output: [{self.shell.before}]'
        )
        # Ensure the group has write permissions on the working directory
        self.shell.sendline(f'chmod g+rw "{work_dir}"')
        self.shell.expect(self.__bash_expect_regex)

    async def _init_bash_commands(self):
        logger.info(f'Initializing by running {len(INIT_COMMANDS)} bash commands...')
        # if root user, skip last command
        if self.username == 'root':
            INIT_COMMANDS.pop()
        for command in INIT_COMMANDS:
            action = CmdRunAction(command=command)
            action.timeout = 300
            logger.debug(f'Executing init command: {command}')
            obs: CmdOutputObservation = await self.run(action)
            logger.debug(
                f'Init command outputs (exit code: {obs.exit_code}): {obs.content}'
            )
            assert obs.exit_code == 0

        logger.info('Bash init commands completed')

    def _get_bash_prompt_and_update_pwd(self):
        ps1 = self.shell.after
        if ps1 == pexpect.EOF:
            logger.error(f'Bash shell EOF! {self.shell.after=}, {self.shell.before=}')
            raise RuntimeError('Bash shell EOF')
        if ps1 == pexpect.TIMEOUT:
            logger.warning('Bash shell timeout')
            return ''

        # begin at the last occurrence of '[PEXPECT_BEGIN]'.
        # In multi-line bash commands, the prompt will be repeated
        # and the matched regex captures all of them
        # - we only want the last one (newest prompt)
        try:
            _begin_pos = ps1.rfind('[PEXPECT_BEGIN]')
        except AttributeError:
            # the above check is not working.
            # AttributeError: type object 'EOF' has no attribute 'rfind'
            return ''

        if _begin_pos != -1:
            ps1 = ps1[_begin_pos:]

        # parse the ps1 to get username, hostname, and working directory
        matched = re.match(self.__bash_expect_regex, ps1)
        assert (
            matched is not None
        ), f'Failed to parse bash prompt: {ps1}. This should not happen.'
        other_info, username, hostname, working_dir = matched.groups()
        working_dir = working_dir.rstrip()
        self.pwd = os.path.expanduser(working_dir)

        # re-assemble the prompt
        other_info = other_info.strip()
        if other_info:
            other_info += '\n'
        prompt = f'{other_info.strip()}{username}@{hostname}:{working_dir} '
        if username == 'root':
            prompt += '#'
        else:
            prompt += '$'
        return prompt + ' '

    def _execute_bash(
        self,
        command: str,
        timeout: int | None,
        keep_prompt: bool = True,
        kill_on_timeout: bool = True,
    ) -> tuple[str, int]:
        logger.debug(f'Executing command: {command}')
        self.shell.sendline(command)
        return self._continue_bash(
            command=command,
            timeout=timeout,
            keep_prompt=keep_prompt,
            kill_on_timeout=kill_on_timeout,
        )

    def _interrupt_bash(
        self,
        timeout: int | None,
    ) -> tuple[str, int]:
        # send a SIGINT to the process
        self.shell.sendintr()
        self.shell.expect(self.__bash_expect_regex, timeout=timeout)
        command_output = self.shell.before
        return (
            f'Command timed out. Sent SIGINT to the process: {command_output}\nPlease run in background if you want to continue.\n',
            130,
        )

    def _continue_bash(
        self,
        command: str,
        timeout: int | None,
        keep_prompt: bool = True,
        kill_on_timeout: bool = True,
    ) -> tuple[str, int]:
        prompts = [
            self.__bash_expect_regex,
            EOF,
            TIMEOUT,
            r'Do you want to continue\? \[Y/n\]',
            r'Proceed \(Y/n\)\? ',
            r'Enter .*:\s*$',
        ]
        full_output = ''
        timeout_counter = 0
        timeout = 15
        last_output = ''
        seeking_input = False
        while True:
            try:
                # Wait for one of the prompts
                index = self.shell.expect(prompts, timeout=1)
                output = self.shell.before
                if output:
                    logger.info(output)
                if index == 0:
                    logger.debug('Prompt matched')
                    break
                elif index == 1:
                    logger.debug('End of file')
                    break
                elif index == 2:
                    if output:
                        last_line = output.splitlines()[-1]
                    else:
                        last_line = ''
                    if output == last_output and not re.search(
                        r'Installing|Building|Downloading', last_line
                    ):
                        timeout_counter += 1
                        if timeout_counter > timeout:
                            logger.debug('Timeout reached.')
                            return self._interrupt_bash(timeout=timeout)
                elif index in [3, 4]:
                    self.shell.sendline('Y')
                    full_output += output + self.shell.match.group(1)
                elif index == 5:
                    full_output += self.shell.match.group(0)
                    logger.debug('Seems like asking for input.')
                    seeking_input = True
                    break

                last_output = output
            except ExceptionPexpect as e:
                logger.exception(f'Unexpected exception: {e}')
                break
        full_output += output

        if not seeking_input:
            if not output.strip():
                if 'grep' in command:
                    output = '[No matching lines were found. Why did you search this term?]\r\n'
                else:
                    output = '[Command executed successfully with no output]\r\n'
            bash_prompt = self._get_bash_prompt_and_update_pwd()
            if keep_prompt:
                output += '\r\n' + bash_prompt

            # Get exit code
            self.shell.sendline('echo $?')
            logger.debug('Requesting exit code...')
            self.shell.expect(self.__bash_expect_regex, timeout=timeout)
            _exit_code_output = self.shell.before
            try:
                exit_code = int(_exit_code_output.strip().split()[0])
            except Exception as e:
                logger.error(
                    f'{e} getting exit code from bash script {_exit_code_output} '
                )
                # If we try to run an invalid shell script the output sometimes includes error text
                # rather than the error code - we assume this is an error
                exit_code = 2
        else:
            exit_code = 1  # command is asking for input

        logger.debug(f'Command output: {output}')
        return output, exit_code

    async def run_action(self, action) -> Observation:
        action_type = action.action
        logger.debug(f'Running action:\n{action}')
        observation = await getattr(self, action_type)(action)
        logger.debug(f'Action output:\n{observation}')
        return observation

    async def run(self, action: CmdRunAction) -> CmdOutputObservation:
        try:
            assert (
                action.timeout is not None
            ), f'Timeout argument is required for CmdRunAction: {action}'
            commands = split_bash_commands(action.command)
            all_output = ''
            for command in commands:
                output = None
                exit_code = 0
                if command == self.last_command and command in ['ls -l', 'ls -la']:
                    output = "[Why are you executing the same command twice? What's wrong with you? Please focus 🙏]"
                elif command.startswith('cd'):
                    path = command[3:].strip()
                    if self.pwd == path:
                        output = '[You are already in this directory.]'
                if output is not None:
                    pass
                elif re.search(r'cd [^;]*\.py$', command, re.IGNORECASE):
                    output = (
                        '[Invalid usage of cd command. Use open_file skill instead.]'
                    )
                elif re.search(r'^(vim?|nano)\s', command, re.IGNORECASE):
                    output = (
                        'vim/nano are not prohibited in the sandbox. '
                        'Please use agentskills for file operations.'
                    )
                elif ' -m unittest' in command:
                    output = '[Please run the tests using pytest.]'
                elif command.lower() == 'ctrl+c':
                    output, exit_code = self._interrupt_bash(
                        timeout=SOFT_TIMEOUT_SECONDS
                    )
                else:
                    output, exit_code = self._execute_bash(
                        command,
                        timeout=SOFT_TIMEOUT_SECONDS
                        if not action.blocking
                        else action.timeout,
                        keep_prompt=action.keep_prompt,
                        kill_on_timeout=False if not action.blocking else True,
                    )
                self.last_command = command
                if command.startswith('pip install'):
                    output = await self.parse_pip_output(command, output)
                if all_output:
                    # previous output already exists with prompt "user@hostname:working_dir #""
                    # we need to add the command to the previous output,
                    # so model knows the following is the output of another action)
                    all_output = all_output.rstrip() + ' ' + command + '\r\n'

                all_output += str(output) + '\r\n'
                if exit_code != 0:
                    break

            # strip last line break only
            all_output = '\r\n'.join(all_output.split('\r\n')[:-1])
            return CmdOutputObservation(
                command_id=-1,
                content=all_output,
                command=action.command,
                exit_code=exit_code,
            )
        except UnicodeDecodeError:
            raise RuntimeError('Command output could not be decoded as utf-8')

    async def chdir(self):
        if 'jupyter' not in self.plugins:
            return
        _jupyter_plugin: JupyterPlugin = self.plugins['jupyter']  # type: ignore
        logger.debug(
            f"{self.pwd} != {getattr(self, '_jupyter_pwd', None)} -> reset Jupyter PWD"
        )
        reset_jupyter_pwd_code = f'import os; os.chdir("{self.pwd}")'
        _aux_action = IPythonRunCellAction(code=reset_jupyter_pwd_code)
        _reset_obs = await _jupyter_plugin.run(_aux_action)
        logger.debug(
            f'Changed working directory in IPython to: {self.pwd}. Output: {_reset_obs}'
        )
        self._jupyter_pwd = self.pwd

    async def restart_kernel(self) -> str:
        if 'agent_skills' not in self.plugins:
            return ''

        jupyter_plugin: JupyterPlugin = self.plugins['jupyter']  # type: ignore
        restart_kernel_code = (
            'import IPython\nIPython.Application.instance().kernel.do_shutdown(True)'
        )
        act = IPythonRunCellAction(code=restart_kernel_code)
        obs = await jupyter_plugin.run(act)
        output = obs.content
        if "{'status': 'ok', 'restart': True}" != output.strip():
            print(output)
            output = '\n[Failed to restart the kernel]'
        else:
            output = '\n[Kernel restarted successfully]'

        await self.chdir()
        # re-init the kernel after restart
        logger.info(f'Re-initializing the kernel with {self.kernel_init_code}')
        # act = IPythonRunCellAction(code=self.kernel_init_code)
        # obs = await jupyter_plugin.run(act)
        # logger.info(f'Kernel re-initialized. Output: {obs}')
        return output

    async def parse_pip_output(self, code, output) -> str:
        print(output)
        package_names = code.split(' ', 2)[-1]
        parsed_output = output
        if 'Successfully installed' in output:
            parsed_output = '[Package installed successfully]'
            if (
                'Note: you may need to restart the kernel to use updated packages.'
                in output
            ):
                parsed_output += await self.restart_kernel()
            else:
                # restart kernel if installed via bash too
                await self.restart_kernel()
        else:
            package_names = package_names.split()
            if all(
                f'Requirement already satisfied: {package_name}' in output
                for package_name in package_names
            ):
                plural = 's' if len(package_names) > 1 else ''
                parsed_output = f'[Package{plural} already installed]'

        prompt_output = self._get_bash_prompt_and_update_pwd()
        return parsed_output + '\r\n' + prompt_output

    async def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        if 'jupyter' in self.plugins:
            _jupyter_plugin: JupyterPlugin = self.plugins['jupyter']  # type: ignore
            # This is used to make AgentSkills in Jupyter aware of the
            # current working directory in Bash
            if self.pwd != getattr(self, '_jupyter_pwd', None):
                await self.chdir()
            if action.code == self.last_code and self.is_last_code_error:
                obs: Observation = ErrorObservation(
                    '[You are trying to run the same code twice. Please focus and run the correct code.]'
                )
            else:
                action.code = action.code.replace('!pip', '%pip')
                obs = await _jupyter_plugin.run(action)
                if 'pip install' in action.code:
                    obs.content = await self.parse_pip_output(action.code, obs.content)
                obs.content = obs.content.rstrip()
                self.last_code = action.code
                self.is_last_code_error = 'error' in obs.content
            # obs.content += f'\n[Jupyter current working directory: {self.pwd}]'
            # obs.content += f'\n[Jupyter Python interpreter: {_jupyter_plugin.python_interpreter_path}]'
            return obs
        else:
            raise RuntimeError(
                'JupyterRequirement not found. Unable to run IPython action.'
            )

    def _get_working_directory(self):
        # NOTE: this is part of initialization, so we hard code the timeout
        result, exit_code = self._execute_bash('pwd', timeout=60, keep_prompt=False)
        if exit_code != 0:
            raise RuntimeError('Failed to get working directory')
        return result.strip()

    def _resolve_path(self, path: str, working_dir: str) -> str:
        filepath = Path(path)
        if not filepath.is_absolute():
            return str(Path(working_dir) / filepath)
        return str(filepath)

    async def read(self, action: FileReadAction) -> Observation:
        # NOTE: the client code is running inside the sandbox,
        # so there's no need to check permission
        working_dir = self._get_working_directory()
        filepath = self._resolve_path(action.path, working_dir)
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                lines = read_lines(file.readlines(), action.start, action.end)
        except FileNotFoundError:
            return ErrorObservation(
                f'File not found: {filepath}. Your current working directory is {working_dir}.'
            )
        except UnicodeDecodeError:
            return ErrorObservation(f'File could not be decoded as utf-8: {filepath}.')
        except IsADirectoryError:
            return ErrorObservation(
                f'Path is a directory: {filepath}. You can only read files'
            )

        code_view = ''.join(lines)
        return FileReadObservation(path=filepath, content=code_view)

    async def write(self, action: FileWriteAction) -> Observation:
        working_dir = self._get_working_directory()
        filepath = self._resolve_path(action.path, working_dir)

        insert = action.content.split('\n')
        try:
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))

            file_exists = os.path.exists(filepath)
            if file_exists:
                file_stat = os.stat(filepath)
            else:
                file_stat = None

            mode = 'w' if not file_exists else 'r+'
            try:
                with open(filepath, mode, encoding='utf-8') as file:
                    if mode != 'w':
                        all_lines = file.readlines()
                        new_file = insert_lines(
                            insert, all_lines, action.start, action.end
                        )
                    else:
                        new_file = [i + '\n' for i in insert]

                    file.seek(0)
                    file.writelines(new_file)
                    file.truncate()

                # Handle file permissions
                if sys.platform != 'win32':
                    if file_exists:
                        assert file_stat is not None
                        # restore the original file permissions if the file already exists
                        os.chmod(filepath, file_stat.st_mode)
                        os.chown(filepath, file_stat.st_uid, file_stat.st_gid)
                    else:
                        # set the new file permissions if the file is new
                        os.chmod(filepath, 0o644)
                        os.chown(filepath, self.user_id, self.user_id)

            except FileNotFoundError:
                return ErrorObservation(f'File not found: {filepath}')
            except IsADirectoryError:
                return ErrorObservation(
                    f'Path is a directory: {filepath}. You can only write to files'
                )
            except UnicodeDecodeError:
                return ErrorObservation(
                    f'File could not be decoded as utf-8: {filepath}'
                )
        except PermissionError:
            return ErrorObservation(f'Malformed paths not permitted: {filepath}')
        return FileWriteObservation(content='', path=filepath)

    async def browse(self, action: BrowseURLAction) -> Observation:
        return await browse(action, self.browser)

    async def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        return await browse(action, self.browser)

    def close(self):
        self.shell.close()
        self.browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, help='Port to listen on')
    parser.add_argument('--working-dir', type=str, help='Working directory')
    parser.add_argument('--plugins', type=str, help='Plugins to initialize', nargs='+')
    parser.add_argument(
        '--username', type=str, help='User to run as', default='openhands'
    )
    parser.add_argument('--user-id', type=int, help='User ID to run as', default=1000)
    parser.add_argument(
        '--browsergym-eval-env',
        type=str,
        help='BrowserGym environment used for browser evaluation',
        default=None,
    )
    # example: python client.py 8000 --working-dir /workspace --plugins JupyterRequirement
    args = parser.parse_args()

    plugins_to_load: list[Plugin] = []
    if args.plugins:
        for plugin in args.plugins:
            if plugin not in ALL_PLUGINS:
                raise ValueError(f'Plugin {plugin} not found')
            plugins_to_load.append(ALL_PLUGINS[plugin]())  # type: ignore

    client: RuntimeClient | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global client
        client = RuntimeClient(
            plugins_to_load,
            work_dir=args.working_dir,
            username=args.username,
            user_id=args.user_id,
            browsergym_eval_env=args.browsergym_eval_env,
        )
        await client.ainit()
        yield
        # Clean up & release the resources
        client.close()

    app = FastAPI(lifespan=lifespan)

    # TODO below 3 exception handlers were recommended by Sonnet.
    # Are these something we should keep?
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception('Unhandled exception occurred:')
        return JSONResponse(
            status_code=500,
            content={
                'message': 'An unexpected error occurred. Please try again later.'
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f'HTTP exception occurred: {exc.detail}')
        return JSONResponse(
            status_code=exc.status_code, content={'message': exc.detail}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.error(f'Validation error occurred: {exc}')
        return JSONResponse(
            status_code=422,
            content={'message': 'Invalid request parameters', 'details': exc.errors()},
        )

    @app.middleware('http')
    async def one_request_at_a_time(request: Request, call_next):
        assert client is not None
        async with client.lock:
            response = await call_next(request)
        return response

    @app.get('/server_info')
    async def get_server_info():
        assert client is not None
        current_time = time.time()
        uptime = current_time - client.start_time
        idle_time = current_time - client.last_execution_time
        return {'uptime': uptime, 'idle_time': idle_time}

    @app.post('/execute_action')
    async def execute_action(action_request: ActionRequest):
        assert client is not None
        try:
            action = event_from_dict(action_request.action)
            if not isinstance(action, Action):
                raise HTTPException(status_code=400, detail='Invalid action type')
            client.last_execution_time = time.time()
            observation = await client.run_action(action)
            return event_to_dict(observation)
        except Exception as e:
            logger.error(
                f'Error processing command: {str(e)}', exc_info=True, stack_info=True
            )
            raise HTTPException(status_code=500, detail=str(e))

    @app.post('/upload_file')
    async def upload_file(
        file: UploadFile, destination: str = '/', recursive: bool = False
    ):
        assert client is not None

        try:
            # Ensure the destination directory exists
            if not os.path.isabs(destination):
                raise HTTPException(
                    status_code=400, detail='Destination must be an absolute path'
                )

            full_dest_path = destination
            if not os.path.exists(full_dest_path):
                os.makedirs(full_dest_path, exist_ok=True)

            if recursive:
                # For recursive uploads, we expect a zip file
                if not file.filename.endswith('.zip'):
                    raise HTTPException(
                        status_code=400, detail='Recursive uploads must be zip files'
                    )

                zip_path = os.path.join(full_dest_path, file.filename)
                with open(zip_path, 'wb') as buffer:
                    shutil.copyfileobj(file.file, buffer)

                # Extract the zip file
                shutil.unpack_archive(zip_path, full_dest_path)
                os.remove(zip_path)  # Remove the zip file after extraction

                logger.info(
                    f'Uploaded file {file.filename} and extracted to {destination}'
                )
            else:
                # For single file uploads
                file_path = os.path.join(full_dest_path, file.filename)
                with open(file_path, 'wb') as buffer:
                    shutil.copyfileobj(file.file, buffer)
                logger.info(f'Uploaded file {file.filename} to {destination}')

            return JSONResponse(
                content={
                    'filename': file.filename,
                    'destination': destination,
                    'recursive': recursive,
                },
                status_code=200,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get('/alive')
    async def alive():
        return {'status': 'ok'}

    # ================================
    # File-specific operations for UI
    # ================================

    @app.post('/list_files')
    async def list_files(request: Request):
        """List files in the specified path.

        This function retrieves a list of files from the agent's runtime file store,
        excluding certain system and hidden files/directories.

        To list files:
        ```sh
        curl http://localhost:3000/api/list-files
        ```

        Args:
            request (Request): The incoming request object.
            path (str, optional): The path to list files from. Defaults to '/'.

        Returns:
            list: A list of file names in the specified path.

        Raises:
            HTTPException: If there's an error listing the files.
        """
        assert client is not None

        # get request as dict
        request_dict = await request.json()
        path = request_dict.get('path', None)

        # Get the full path of the requested directory
        if path is None:
            full_path = client.initial_pwd
        elif os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.join(client.initial_pwd, path)

        if not os.path.exists(full_path):
            # if user just removed a folder, prevent server error 500 in UI
            return []

        try:
            # Check if the directory exists
            if not os.path.exists(full_path) or not os.path.isdir(full_path):
                return []

            entries = os.listdir(full_path)

            # Separate directories and files
            directories = []
            files = []
            for entry in entries:
                # Remove leading slash and any parent directory components
                entry_relative = entry.lstrip('/').split('/')[-1]

                # Construct the full path by joining the base path with the relative entry path
                full_entry_path = os.path.join(full_path, entry_relative)
                if os.path.exists(full_entry_path):
                    is_dir = os.path.isdir(full_entry_path)
                    if is_dir:
                        # add trailing slash to directories
                        # required by FE to differentiate directories and files
                        entry = entry.rstrip('/') + '/'
                        directories.append(entry)
                    else:
                        files.append(entry)

            # Sort directories and files separately
            directories.sort(key=lambda s: s.lower())
            files.sort(key=lambda s: s.lower())

            # Combine sorted directories and files
            sorted_entries = directories + files
            return sorted_entries

        except Exception as e:
            logger.error(f'Error listing files: {e}', exc_info=True)
            return []

    logger.info('Runtime client initialized.')

    logger.info(f'Starting action execution API on port {args.port}')
    run(app, host='0.0.0.0', port=args.port)
