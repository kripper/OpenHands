import os
import re

import bashlex
import pexpect

from openhands.core.logger import openhands_logger as logger
from openhands.events.action import CmdRunAction
from openhands.events.observation import (
    CmdOutputObservation,
    FatalErrorObservation,
)

SOFT_TIMEOUT_SECONDS = 5


def split_bash_commands(commands):
    if not commands.strip():
        return ['']
    try:
        parsed = bashlex.parse(commands)
    except bashlex.errors.ParsingError as e:
        logger.debug(
            f'Failed to parse bash commands\n'
            f'[input]: {commands}\n'
            f'[warning]: {e}\n'
            f'The original command will be returned as is.'
        )
        # If parsing fails, return the original commands
        return [commands]

    result: list[str] = []
    last_end = 0

    for node in parsed:
        start, end = node.pos

        # Include any text between the last command and this one
        if start > last_end:
            between = commands[last_end:start]
            logger.debug(f'BASH PARSING between: {between}')
            if result:
                result[-1] += between.rstrip()
            elif between.strip():
                # THIS SHOULD NOT HAPPEN
                result.append(between.rstrip())

        # Extract the command, preserving original formatting
        command = commands[start:end].rstrip()
        logger.debug(f'BASH PARSING command: {command}')
        result.append(command)

        last_end = end

    # Add any remaining text after the last command to the last command
    remaining = commands[last_end:].rstrip()
    logger.debug(f'BASH PARSING: {remaining = }')
    if last_end < len(commands) and result:
        result[-1] += remaining
        logger.debug(f'BASH PARSING result[-1] += remaining: {result[-1]}')
    elif last_end < len(commands):
        if remaining:
            result.append(remaining)
            logger.debug(f'BASH PARSING result.append(remaining): {result[-1]}')
    return result


class BashSession:
    """A class that maintains a pexpect process and provides a simple interface for running commands and interacting with the shell."""

    def __init__(self, work_dir: str, username: str):
        self._pwd = work_dir
        self.last_command = ''

        self.shell = pexpect.spawn(
            f'su {username}',
            encoding='utf-8',
            codec_errors='replace',
            echo=False,
        )
        self._init_bash_shell(work_dir)

    def close(self):
        self.shell.close()

    @property
    def pwd(self):
        return self._pwd

    @property
    def workdir(self):
        return self._get_working_directory()

    def _get_working_directory(self):
        # NOTE: this is part of initialization, so we hard code the timeout
        result, exit_code = self._execute_bash('pwd', timeout=60, keep_prompt=False)
        if exit_code != 0:
            raise RuntimeError(
                f'Failed to get working directory (exit code: {exit_code}): {result}'
            )
        return result.strip()

    def _init_bash_shell(self, work_dir: str):
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
        other_info = other_info.strip()
        if other_info:
            other_info += '\n'
        working_dir = working_dir.rstrip()
        self._pwd = os.path.expanduser(working_dir)

        # re-assemble the prompt
        # ignore the hostname AND use 'openhands-workspace'
        prompt = f'{other_info}{username}@openhands-workspace:{working_dir} '
        if username == 'root':
            prompt += '#'
        else:
            prompt += '$'
        return prompt + ' '

    def _execute_bash(
        self,
        command: str,
        timeout: int,
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
        action_timeout: int | None,
        interrupt_timeout: int | None = None,
        max_retries: int = 2,
    ) -> tuple[str, int]:
        interrupt_timeout = interrupt_timeout or 1  # default timeout for SIGINT
        # try to interrupt the bash shell use SIGINT
        while max_retries > 0:
            self.shell.sendintr()  # send SIGINT to the shell
            logger.debug('Sent SIGINT to bash. Waiting for output...')
            try:
                self.shell.expect(self.__bash_expect_regex, timeout=interrupt_timeout)
                output = self.shell.before
                logger.debug(f'Received output after SIGINT: {output}')
                exit_code = 130  # SIGINT

                _additional_msg = ''
                if action_timeout is not None:
                    _additional_msg = (
                        f'Command timed out after {action_timeout} seconds. '
                    )
                output += (
                    '\r\n\r\n'
                    + f'[{_additional_msg}SIGINT was sent to interrupt the command.]'
                )
                return output, exit_code
            except pexpect.TIMEOUT as e:
                logger.warning(f'Bash pexpect.TIMEOUT while waiting for SIGINT: {e}')
                max_retries -= 1

        # fall back to send control-z
        logger.error(
            'Failed to get output after SIGINT. Max retries reached. Sending control-z...'
        )
        self.shell.sendcontrol('z')
        self.shell.expect(self.__bash_expect_regex)
        output = self.shell.before
        logger.debug(f'Received output after control-z: {output}')
        # Try to kill the job
        self.shell.sendline('kill -9 %1')
        self.shell.expect(self.__bash_expect_regex)
        logger.debug(f'Received output after killing job %1: {self.shell.before}')
        output += self.shell.before

        _additional_msg = ''
        if action_timeout is not None:
            _additional_msg = f'Command timed out after {action_timeout} seconds. '
        output += (
            '\r\n\r\n'
            + f'[{_additional_msg}SIGINT was sent to interrupt the command, but failed. The command was killed.]'
        )

        # Try to get the exit code again
        self.shell.sendline('echo $?')
        self.shell.expect(self.__bash_expect_regex)
        _exit_code_output = self.shell.before
        exit_code = self._parse_exit_code(_exit_code_output)

        return output, exit_code

    def _parse_exit_code(self, output: str) -> int:
        try:
            exit_code = int(output.strip().split()[0])
        except Exception:
            logger.error('Error getting exit code from bash script')
            # If we try to run an invalid shell script the output sometimes includes error text
            # rather than the error code - we assume this is an error
            exit_code = 2
        return exit_code

    def _continue_bash(
        self,
        command: str,
        timeout: int,
        keep_prompt: bool = True,
        kill_on_timeout: bool = True,
    ) -> tuple[str, int]:
        prompts = [
            self.__bash_expect_regex,
            pexpect.EOF,
            pexpect.TIMEOUT,
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
                            return self._interrupt_bash(action_timeout=timeout)
                elif index in [3, 4]:
                    self.shell.sendline('Y')
                    full_output += output + self.shell.match.group(1)
                elif index == 5:
                    full_output += self.shell.match.group(0)
                    logger.debug('Seems like asking for input.')
                    seeking_input = True
                    break

                last_output = output
            except pexpect.ExceptionPexpect as e:
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
            exit_code = self._parse_exit_code(_exit_code_output)
        else:
            exit_code = 1  # command is asking for input

        logger.debug(f'Command output: {output}')
        return output, exit_code

    def parse_pip_output(self, code, output) -> str:
        print(output)
        package_names = code.split(' ', 2)[-1]
        parsed_output = output
        if 'Successfully installed' in output:
            parsed_output = '[Package installed successfully]'
            if (
                'Note: you may need to restart the kernel to use updated packages.'
                in output
            ):
                # parsed_output += await self.restart_kernel()
                pass
            else:
                # restart kernel if installed via bash too
                # await self.restart_kernel()
                pass
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

    def run(self, action: CmdRunAction) -> CmdOutputObservation | FatalErrorObservation:
        try:
            assert (
                action.timeout is not None
            ), f'Timeout argument is required for CmdRunAction: {action}'
            commands = split_bash_commands(action.command)
            all_output = ''
            python_interpreter = ''
            for command in commands:
                output = None
                exit_code = 0
                if command == self.last_command and command in ['ls -l', 'ls -la']:
                    output = "[Why are you executing the same command twice? What's wrong with you? Please focus 🙏]"
                elif command.startswith('cd'):
                    path = command[3:].strip()
                    if self.pwd == path:
                        output = '[You are already in this directory.]'
                elif os.getenv('SWE_BENCH') == '1' or 1:  # TODO
                    if command.startswith('git blame'):
                        output = (
                            "[Don't use git commands. Just directly give the solution.]"
                        )
                    elif 'pip install' in command:
                        output = '[Use the current packages only.]'

                    elif (
                        '/tmp/test_task.py' in command
                        and 'cat' not in command
                        and 'python3' not in command
                        and 'pytest' not in command
                    ):
                        output = "[The content in this file is absolutely correct. Also, you can't modify this test file. You must pass this test case. You should correct the codebase instead.]"
                    elif command.startswith('pytest') and '.py' not in command:
                        output = '[Please run specific test cases instead of running all test cases.]'
                # logger.debug('magic')
                # logger.debug(output)
                # logger.debug(os.getenv('SWE_BENCH'))
                if output:
                    pass
                elif command == '':
                    output, exit_code = self._continue_bash(
                        command=command,
                        timeout=SOFT_TIMEOUT_SECONDS,
                        keep_prompt=action.keep_prompt,
                        kill_on_timeout=False,
                    )
                elif '-m venv' in command:
                    output = '[venv is not needed in the sandbox because it is already isolated]'
                elif re.search(r'cd [^;&]*\.py$', command, re.IGNORECASE):
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
                        action_timeout=None,  # intentionally None
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
                    output = self.parse_pip_output(command, output)
                # if all_output:
                #     # previous output already exists so we add a newline
                #     all_output += '\r\n'

                # If the command originated with the agent, append the command that was run...
                # if action.source == EventSource.AGENT:
                #     all_output += command + '\r\n'

                all_output += str(output)
                if exit_code != 0:
                    break

            return CmdOutputObservation(
                command_id=-1,
                content=all_output.rstrip('\r\n'),
                command=action.command,
                hidden=action.hidden,
                exit_code=exit_code,
                interpreter_details=python_interpreter,
            )
        except UnicodeDecodeError:
            raise RuntimeError('Command output could not be decoded as utf-8')
