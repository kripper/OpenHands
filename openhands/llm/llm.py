import copy
import os
import time
import warnings
from functools import partial
from time import sleep
from typing import Any, Union

from openhands.core.config import LLMConfig
from openhands.core.message import Message

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm
from litellm import ModelInfo
from litellm import completion as litellm_completion
from litellm import completion_cost as litellm_completion_cost
from litellm.caching import Cache
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
)
from litellm.types.utils import CostPerToken, ModelResponse, Usage

from openhands.condenser.condenser import CondenserMixin
from openhands.core.exceptions import (
    ContextWindowLimitExceededError,
)
from openhands.core.logger import LOG_DIR
from openhands.core.logger import openhands_logger as logger
from openhands.core.metrics import Metrics
from openhands.llm.debug_mixin import DebugMixin
from openhands.llm.retry_mixin import RetryMixin

__all__ = ['LLM']

# tuple of exceptions to retry on
LLM_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    APIConnectionError,
    # FIXME: APIError is useful on 502 from a proxy for example,
    # but it also retries on other errors that are permanent
    APIError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
)

# cache prompt supporting models
# remove this when we gemini and deepseek are supported
CACHE_PROMPT_SUPPORTED_MODELS = [
    'claude-3-5-sonnet-20240620',
    'claude-3-haiku-20240307',
    'claude-3-opus-20240229',
    'anthropic/claude-3-opus-20240229',
    'anthropic/claude-3-haiku-20240307',
    'anthropic/claude-3-5-sonnet-20240620',
]


class LLM(RetryMixin, DebugMixin, CondenserMixin):
    """The LLM class represents a Language Model instance.

    Attributes:
        config: an LLMConfig object specifying the configuration of the LLM.
    """

    def __init__(
        self,
        config: LLMConfig,
        metrics: Metrics | None = None,
    ):
        """Initializes the LLM. If LLMConfig is passed, its values will be the fallback.

        Passing simple parameters always overrides config.

        Args:
            config: The LLM configuration.
            metrics: The metrics to use.
        """
        self.metrics: Metrics = metrics if metrics is not None else Metrics()
        self.cost_metric_supported: bool = True
        self.config: LLMConfig = copy.deepcopy(config)
        self.log_prompt_once = True
        self.reload_counter = 0

        if self.config.enable_cache:
            litellm.cache = Cache()

        # list of LLM completions (for logging purposes). Each completion is a dict with the following keys:
        # - 'messages': list of messages
        # - 'response': response from the LLM
        self.llm_completions: list[dict[str, Any]] = []

        # litellm actually uses base Exception here for unknown model
        self.model_info: ModelInfo | None = None
        try:
            if self.config.model.startswith('openrouter'):
                self.model_info = litellm.get_model_info(self.config.model)
            else:
                self.model_info = litellm.get_model_info(
                    self.config.model.split(':')[0]
                )
        # noinspection PyBroadException
        except Exception:
            logger.warning(f'Could not get model info for {config.model}')

        # Set the max tokens in an LM-specific way if not set
        if config.max_input_tokens is None:
            if (
                self.model_info is not None
                and 'max_input_tokens' in self.model_info
                and isinstance(self.model_info['max_input_tokens'], int)
            ):
                self.config.max_input_tokens = self.model_info['max_input_tokens']
            else:
                # Safe fallback for any potentially viable model
                self.config.max_input_tokens = 4096

        if self.config.max_output_tokens is None:
            # Safe default for any potentially viable model
            self.config.max_output_tokens = 4096
            if self.model_info is not None:
                # max_output_tokens has precedence over max_tokens, if either exists.
                # litellm has models with both, one or none of these 2 parameters!
                if 'max_output_tokens' in self.model_info and isinstance(
                    self.model_info['max_output_tokens'], int
                ):
                    self.config.max_output_tokens = self.model_info['max_output_tokens']
                elif 'max_tokens' in self.model_info and isinstance(
                    self.model_info['max_tokens'], int
                ):
                    self.config.max_output_tokens = self.model_info['max_tokens']

        logger.info(f'{self.config.model=}')
        logger.info(f'{self.config.max_input_tokens=}')
        logger.info(f'{self.config.max_output_tokens=}')
        if self.config.drop_params:
            litellm.drop_params = self.config.drop_params

        if self.config.model.startswith('ollama'):
            max_input_tokens = self.config.max_input_tokens
            max_output_tokens = self.config.max_output_tokens
            if max_input_tokens and max_output_tokens:
                logger.info(f'{max_input_tokens=}, {max_output_tokens=}')
                total = max_input_tokens + max_output_tokens
                litellm.OllamaConfig.num_ctx = total
                logger.info(f'Setting OllamaConfig.num_ctx to {total}')

        self._completion = partial(
            litellm_completion,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            api_version=self.config.api_version,
            custom_llm_provider=self.config.custom_llm_provider,
            max_tokens=self.config.max_output_tokens,
            timeout=self.config.timeout,
            temperature=1
            if self.config.model.startswith('o1-')
            else self.config.temperature,
            top_p=self.config.top_p,
            caching=self.config.enable_cache,
            drop_params=self.config.drop_params,
        )

        if self.vision_is_active():
            logger.debug('LLM: model has vision enabled')
        if self.is_caching_prompt_active():
            logger.debug('LLM: caching prompt enabled')

        self.completion_unwrapped = self._completion

        def is_hallucination(text) -> bool:
            lines = text.strip().split('\n')
            if len(lines) < 2:
                return False
            line_index = -2
            while line_index >= -len(lines):
                second_last_line = lines[line_index].strip()
                if second_last_line.strip():
                    break
                line_index -= 1
            repetition_count = sum(
                1 for line in lines if line.strip() == second_last_line
            )
            return repetition_count >= 5

        @self.retry_decorator(
            num_retries=self.config.num_retries,
            retry_exceptions=LLM_RETRY_EXCEPTIONS,
            retry_min_wait=self.config.retry_min_wait,
            retry_max_wait=self.config.retry_max_wait,
            retry_multiplier=self.config.retry_multiplier,
        )
        def wrapper(*args, **kwargs):
            """Wrapper for the litellm completion function. Logs the input and output of the completion function."""
            messages: list[Message] | Message = []

            # some callers might send the model and messages directly
            # litellm allows positional args, like completion(model, messages, **kwargs)
            if len(args) > 1:
                # ignore the first argument if it's provided (it would be the model)
                # design wise: we don't allow overriding the configured values
                # implementation wise: the partial function set the model as a kwarg already
                # as well as other kwargs
                messages = args[1] if len(args) > 1 else args[0]
                kwargs['messages'] = messages

                # remove the first args, they're sent in kwargs
                args = args[2:]
            elif 'messages' in kwargs:
                messages = kwargs['messages']

            # ensure we work with a list of messages
            messages = messages if isinstance(messages, list) else [messages]

            if self.is_over_token_limit(messages):
                if kwargs['condense']:
                    summary_action = self.condense(messages=messages)
                    return summary_action
                else:
                    raise ContextWindowLimitExceededError()

            kwargs.pop('condense', None)
            if isinstance(messages[0], Message):
                messages = [message.model_dump() for message in messages]
                kwargs['messages'] = messages

            if not messages:
                raise ValueError(
                    'The messages list is empty. At least one message is required.'
                )

            # log the entire LLM prompt
            self.log_prompt(messages)

            if self.is_caching_prompt_active():
                # Anthropic-specific prompt caching
                if 'claude-3' in self.config.model:
                    kwargs['extra_headers'] = {
                        'anthropic-beta': 'prompt-caching-2024-07-31',
                    }
            source = kwargs.pop('origin', None)
            resp = {}
            if (
                continue_on_step_env := os.environ.get('CONTINUE_ON_STEP')
            ) and source == 'Agent':
                # int
                continue_on_step = int(continue_on_step_env)
                self.reload_counter += 1
                if self.reload_counter < continue_on_step:
                    model_config = os.getenv('model_config')
                    if model_config:
                        with open('evaluation/swe_bench/config.toml', 'r') as f:
                            environ = f.read()
                            import toml

                            config = toml.loads(environ)
                            selection_id = config['selected_ids'][0]
                        session = (
                            model_config.split('.')[-1]
                            + '_'
                            + selection_id.split('-')[-1]
                        )
                    else:
                        session = 'default'
                    log_directory = os.path.join(LOG_DIR, 'llm', session)
                    filename = f'{self.reload_counter:03}_response.log'
                    file_name = os.path.join(log_directory, filename)
                    if os.path.exists(file_name):
                        logger.info('Using cached response')
                        with open(file_name, 'r') as f:
                            message_back = f.read()
                        with open(file_name, 'w') as f:
                            f.write('')
                        resp = {'choices': [{'message': {'content': message_back}}]}
            if resp:
                pass
            else:
                kwargs2 = kwargs.copy()
                for _ in range(5):
                    resp = self.completion_unwrapped(*args, **kwargs)
                    message_back = resp['choices'][0]['message']['content']
                    self_analyse = int(os.environ.get('SELF_ANALYSE', '0'))
                    if self_analyse:
                        logger.info(f'{self_analyse=}')
                        kwargs2['messages'].append(
                            {'role': 'assistant', 'content': message_back}
                        )
                        self_analyse_question = (
                            'If the above approach is not wrong, just reply yes.'
                        )
                        kwargs2['messages'].append(
                            {'role': 'user', 'content': self_analyse_question}
                        )
                        self_analyse_response = self.completion_unwrapped(
                            *args, **kwargs2
                        )
                        self_analyse_response_content = self_analyse_response[
                            'choices'
                        ][0]['message']['content'].strip()
                        if self_analyse_response_content != 'yes':
                            logger.info(
                                f'Response is incorrect. {self_analyse_response_content}'
                            )
                            continue
                    if message_back and message_back != 'None':
                        if is_hallucination(message_back):
                            logger.warning(f'Hallucination detected!\n{message_back}')
                            sleep(2)
                            continue
                        break
                    else:
                        msg = 'Why are you not responding to the user?'
                        kwargs['messages'].append({'role': 'user', 'content': msg})
                        logger.warning('No completion messages!')

            # log for evals or other scripts that need the raw completion
            if self.config.log_completions:
                self.llm_completions.append(
                    {
                        'messages': messages,
                        'response': resp,
                        'timestamp': time.time(),
                        'cost': self._completion_cost(resp)
                        if not isinstance(resp, dict)
                        else 0,
                    }
                )

            # log the LLM response
            self.log_response(message_back)
            # post-process to log costs
            self._post_completion(resp)
            return resp

        self._completion = wrapper

    @property
    def completion(self):
        """Decorator for the litellm completion function.

        Check the complete documentation at https://litellm.vercel.app/docs/completion
        """
        return self._completion

    def vision_is_active(self):
        return not self.config.disable_vision and self._supports_vision()

    def _supports_vision(self):
        """Acquire from litellm if model is vision capable.

        Returns:
            bool: True if model is vision capable. If model is not supported by litellm, it will return False.
        """
        # litellm.supports_vision currently returns False for 'openai/gpt-...' or 'anthropic/claude-...' (with prefixes)
        # but model_info will have the correct value for some reason.
        # we can go with it, but we will need to keep an eye if model_info is correct for Vertex or other providers
        # remove when litellm is updated to fix https://github.com/BerriAI/litellm/issues/5608
        return litellm.supports_vision(self.config.model) or (
            self.model_info is not None
            and self.model_info.get('supports_vision', False)
        )

    def is_caching_prompt_active(self) -> bool:
        """Check if prompt caching is supported and enabled for current model.

        Returns:
            boolean: True if prompt caching is supported and enabled for the given model.
        """
        return (
            self.config.caching_prompt is True
            and self.model_info is not None
            and self.model_info.get('supports_prompt_caching', False)
            and self.config.model in CACHE_PROMPT_SUPPORTED_MODELS
        )

    def _post_completion(self, response: ModelResponse) -> None:
        """Post-process the completion response.

        Logs the cost and usage stats of the completion call.
        """
        try:
            cur_cost = self._completion_cost(response)
        except Exception:
            cur_cost = 0

        stats = ''
        if self.cost_metric_supported:
            # keep track of the cost
            stats = 'Cost: %.2f USD | Accumulated Cost: %.2f USD\n' % (
                cur_cost,
                self.metrics.accumulated_cost,
            )

        usage: Usage | None = response.get('usage')

        if usage:
            # keep track of the input and output tokens
            input_tokens = usage.get('prompt_tokens')
            output_tokens = usage.get('completion_tokens')

            if input_tokens:
                stats += 'Input tokens: ' + str(input_tokens)

            if output_tokens:
                stats += (
                    (' | ' if input_tokens else '')
                    + 'Output tokens: '
                    + str(output_tokens)
                    + '\n'
                )

            # read the prompt caching status as received from the provider
            model_extra = usage.get('model_extra', {})

            cache_creation_input_tokens = model_extra.get('cache_creation_input_tokens')
            if cache_creation_input_tokens:
                stats += (
                    'Input tokens (cache write): '
                    + str(cache_creation_input_tokens)
                    + '\n'
                )

            cache_read_input_tokens = model_extra.get('cache_read_input_tokens')
            if cache_read_input_tokens:
                stats += (
                    'Input tokens (cache read): ' + str(cache_read_input_tokens) + '\n'
                )

        # if stats:
        # logger.info(stats)

    def get_token_count(self, messages=None, text=None):
        """Get the number of tokens in a list of messages.

        Args:
            messages (list): A list of messages.

        Returns:
            int: The number of tokens.
        """
        if messages and isinstance(messages[0], Message):
            messages = [m.model_dump() for m in messages]
        try:
            return litellm.token_counter(
                model=self.config.model, messages=messages, text=text
            )
        except Exception:
            # TODO: this is to limit logspam in case token count is not supported
            return 0

    def _is_local(self):
        """Determines if the system is using a locally running LLM.

        Returns:
            boolean: True if executing a local model.
        """
        if self.config.base_url is not None:
            for substring in ['localhost', '127.0.0.1' '0.0.0.0']:
                if substring in self.config.base_url:
                    return True
        elif self.config.model is not None:
            if self.config.model.startswith('ollama'):
                return True
        return False

    def _completion_cost(self, response):
        """Calculate the cost of a completion response based on the model.  Local models are treated as free.
        Add the current cost into total cost in metrics.

        Args:
            response: A response from a model invocation.

        Returns:
            number: The cost of the response.
        """
        if os.getenv('IGNORE_COST'):
            return 0.0
        if not self.cost_metric_supported:
            return 0.0

        extra_kwargs = {}
        if (
            self.config.input_cost_per_token is not None
            and self.config.output_cost_per_token is not None
        ):
            cost_per_token = CostPerToken(
                input_cost_per_token=self.config.input_cost_per_token,
                output_cost_per_token=self.config.output_cost_per_token,
            )
            logger.info(f'Using custom cost per token: {cost_per_token}')
            extra_kwargs['custom_cost_per_token'] = cost_per_token

        if not self._is_local():
            try:
                cost = litellm_completion_cost(
                    completion_response=response, **extra_kwargs
                )
                self.metrics.add_cost(cost)
                return cost
            except Exception:
                self.cost_metric_supported = False
                logger.warning('Cost calculation not supported for this model.')
        return 0.0

    def __str__(self):
        if self.config.api_version:
            return f'LLM(model={self.config.model}, api_version={self.config.api_version}, base_url={self.config.base_url})'
        elif self.config.base_url:
            return f'LLM(model={self.config.model}, base_url={self.config.base_url})'
        return f'LLM(model={self.config.model})'

    def __repr__(self):
        return str(self)

    def reset(self):
        self.metrics = Metrics()
        self.llm_completions = []

    def is_over_token_limit(self, messages: list[Message]) -> bool:
        """
        Estimates the token count of the given events using litellm tokenizer and returns True if over the max_input_tokens value.

        Parameters:
        - messages: List of messages to estimate the token count for.

        Returns:
        - Estimated token count.
        """
        # max_input_tokens will always be set in init to some sensible default
        # 0 in config.llm disables the check
        MAX_TOKEN_COUNT_PADDING = 512
        if not self.config.max_input_tokens:
            return False
        token_count = self.get_token_count(messages=messages) + MAX_TOKEN_COUNT_PADDING
        output = token_count >= self.config.max_input_tokens
        if output:
            logger.info(f'Token count: {token_count}')
        return output

    def get_text_messages(self, messages: list[Message]) -> list[dict]:
        text_messages = []
        for message in messages:
            text_messages.append(message.model_dump())
        return text_messages

    def format_messages_for_llm(
        self, messages: Union[Message, list[Message]]
    ) -> list[dict]:
        if isinstance(messages, Message):
            messages = [messages]

        # set flags to know how to serialize the messages
        for message in messages:
            message.cache_enabled = self.is_caching_prompt_active()
            message.vision_enabled = self.vision_is_active()

        # let pydantic handle the serialization
        return [message.model_dump() for message in messages]
