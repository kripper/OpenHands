import copy
import os
import warnings
from functools import partial
from time import sleep
from typing import Union

import requests

from openhands.core.config import LLMConfig
from openhands.core.message import Message

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm

    litellm.suppress_debug_info = True
from litellm import ModelInfo, PromptTokensDetails
from litellm import completion as litellm_completion
from litellm import completion_cost as litellm_completion_cost

# from litellm.caching import Cache
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
    'claude-3-5-sonnet-20241022',
    'claude-3-5-sonnet-20240620',
    'claude-3-5-haiku-20241022',
    'claude-3-haiku-20240307',
    'claude-3-opus-20240229',
]

# function calling supporting models
FUNCTION_CALLING_SUPPORTED_MODELS = [
    'claude-3-5-sonnet',
    'claude-3-5-sonnet-20240620',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022',
    'gpt-4o-mini',
    'gpt-4o',
    'grok-beta',
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
        self._tried_model_info = False
        self.metrics: Metrics = (
            metrics if metrics is not None else Metrics(model_name=config.model)
        )
        self.cost_metric_supported: bool = True
        self.config: LLMConfig = copy.deepcopy(config)
        self.log_prompt_once = True
        self.reload_counter = 0
        self.api_idx = 0

        # if self.config.enable_cache:
        #     litellm.cache = Cache()

        # litellm actually uses base Exception here for unknown model
        self.model_info: ModelInfo | None = None

        if self.config.log_completions:
            if self.config.log_completions_folder is None:
                raise RuntimeError(
                    'log_completions_folder is required when log_completions is enabled'
                )
            os.makedirs(self.config.log_completions_folder, exist_ok=True)

        # Set the max tokens in an LM-specific way if not set
        if config.max_input_tokens is None:
            try:
                self.config.max_input_tokens = self.model_info['max_input_tokens']  # type: ignore
            except Exception:
                # Safe fallback for any potentially viable model
                self.config.max_input_tokens = 4096

        if self.vision_is_active():
            logger.debug('LLM: model has vision enabled')
        if self.is_caching_prompt_active():
            logger.debug('LLM: caching prompt enabled')
        if self.is_function_calling_active():
            logger.debug('LLM: model supports function calling')

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

        if self.config.model.split('/')[-1].startswith('o1-'):
            #  temperature, top_p and n are fixed at 1, while presence_penalty and frequency_penalty are fixed at 0.
            self.config.temperature = 1
            self.config.top_p = 1

        self._completion = partial(
            litellm_completion,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            api_version=self.config.api_version,
            custom_llm_provider=self.config.custom_llm_provider,
            max_tokens=self.config.max_output_tokens,
            timeout=self.config.timeout,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            caching=self.config.enable_cache,
            drop_params=self.config.drop_params,
        )

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.init_model_info()
        if self.vision_is_active():
            logger.debug('LLM: model has vision enabled')
        if self.is_caching_prompt_active():
            logger.debug('LLM: caching prompt enabled')
        if self.is_function_calling_active():
            logger.debug('LLM: model supports function calling')

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

        self._completion_unwrapped = self._completion

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
            mock_function_calling = kwargs.pop('mock_function_calling', False)

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
            # original_fncall_messages = copy.deepcopy(messages)
            mock_fncall_tools = None
            if mock_function_calling:
                assert (
                    'tools' in kwargs
                ), "'tools' must be in kwargs when mock_function_calling is True"
                # messages = convert_fncall_messages_to_non_fncall_messages(
                #     messages, kwargs['tools']
                # )  # type: ignore
                # kwargs['messages'] = messages
                # kwargs['stop'] = STOP_WORDS
                # mock_fncall_tools = kwargs.pop('tools')

            if self.config.model.split('/')[-1].startswith('o1-'):
                # Message types: user and assistant messages only, system messages are not supported.
                messages[0].role = 'user'

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
                        if message_back:
                            resp = {'choices': [{'message': {'content': message_back}}]}
            if resp:
                pass
            else:
                kwargs2 = kwargs.copy()
                for _ in range(5):
                    if os.getenv('attempt_number'):
                        attempt_number = int(os.getenv('attempt_number', '-1'))
                        if attempt_number != -1:
                            try:
                                from api_keys import api_keys

                                self.api_idx = (self.api_idx + 1) % len(api_keys)
                                print('Using API key', self.api_idx)
                                kwargs['api_key'] = api_keys[self.api_idx]
                            except Exception as e:
                                print('Error in changing API key', e)
                                pass
                            os.environ['attempt_number'] = '-1'
                    resp = self._completion_unwrapped(*args, **kwargs)
                    # non_fncall_response = copy.deepcopy(resp)
                    if mock_function_calling:
                        # assert len(resp.choices) == 1
                        assert mock_fncall_tools is not None
                        # non_fncall_response_message = resp.choices[0].message
                        # fn_call_messages_with_response = (
                        #     convert_non_fncall_messages_to_fncall_messages(
                        #         messages + [non_fncall_response_message],
                        #         mock_fncall_tools,
                        #     )
                        # )  # type: ignore
                        # fn_call_response_message = fn_call_messages_with_response[-1]
                        # if not isinstance(fn_call_response_message, LiteLLMMessage):
                        #     fn_call_response_message = LiteLLMMessage(
                        #         **fn_call_response_message
                        #     )
                        # resp.choices[0].message = fn_call_response_message
                    message_back = resp['choices'][0]['message']['content']
                    self_analyse = int(os.environ.get('SELF_ANALYSE', '0'))
                    if self_analyse:
                        logger.info(f'{self_analyse=}')
                        kwargs2['messages'].append(
                            {'role': 'assistant', 'content': message_back}
                        )
                        self_analyse_question = (
                            'If the above approach is wrong, just reply yes.'
                        )
                        kwargs2['messages'].append(
                            {'role': 'user', 'content': self_analyse_question}
                        )
                        self_analyse_response = self._completion_unwrapped(
                            *args, **kwargs2
                        )
                        self_analyse_response_content = self_analyse_response[
                            'choices'
                        ][0]['message']['content'].strip()
                        print(f'{self_analyse_response_content=}')
                        if self_analyse_response_content == 'yes':
                            logger.info(
                                f'Response is incorrect. {self_analyse_response_content}'
                            )
                            new_messages = [
                                {'role': 'assistant', 'content': message_back},
                                {'role': 'user', 'content': self_analyse_question},
                                {
                                    'role': 'assistant',
                                    'content': self_analyse_response_content,
                                },
                                {
                                    'role': 'user',
                                    'content': 'Then, please correctly respond.',
                                },
                            ]
                            kwargs['messages'].extend(new_messages)
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
                assert self.config.log_completions_folder is not None
                # log_file = os.path.join(
                #     self.config.log_completions_folder,
                #     # use the metric model name (for draft editor)
                #     f'{self.metrics.model_name}-{time.time()}.json',
                # )
                # with open(log_file, 'w') as f:
                #     json.dump(
                #         {
                #             'messages': messages,
                #             'response': resp,
                #             'args': args,
                #             'kwargs': kwargs,
                #             'timestamp': time.time(),
                #             'cost': self._completion_cost(resp),
                #         },
                #         f,
                #     )

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

    def init_model_info(self):
        if self._tried_model_info:
            return
        self._tried_model_info = True
        try:
            if self.config.model.startswith('openrouter'):
                self.model_info = litellm.get_model_info(self.config.model)
        except Exception as e:
            logger.debug(f'Error getting model info: {e}')

        if self.config.model.startswith('litellm_proxy/'):
            # IF we are using LiteLLM proxy, get model info from LiteLLM proxy
            # GET {base_url}/v1/model/info with litellm_model_id as path param
            response = requests.get(
                f'{self.config.base_url}/v1/model/info',
                headers={'Authorization': f'Bearer {self.config.api_key}'},
            )
            resp_json = response.json()
            if 'data' not in resp_json:
                logger.error(
                    f'Error getting model info from LiteLLM proxy: {resp_json}'
                )
            all_model_info = resp_json.get('data', [])
            current_model_info = next(
                (
                    info
                    for info in all_model_info
                    if info['model_name']
                    == self.config.model.removeprefix('litellm_proxy/')
                ),
                None,
            )
            if current_model_info:
                self.model_info = current_model_info['model_info']

        # Last two attempts to get model info from NAME
        if not self.model_info:
            try:
                self.model_info = litellm.get_model_info(
                    self.config.model.split(':')[0]
                )
            # noinspection PyBroadException
            except Exception:
                pass
        if not self.model_info:
            try:
                self.model_info = litellm.get_model_info(
                    self.config.model.split('/')[-1]
                )
            # noinspection PyBroadException
            except Exception:
                pass
        logger.debug(f'Model info: {self.model_info}')

        # Set the max tokens in an LM-specific way if not set
        if self.config.max_input_tokens is None:
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

    def vision_is_active(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
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
        # Check both the full model name and the name after proxy prefix for vision support
        return (
            litellm.supports_vision(self.config.model)
            or litellm.supports_vision(self.config.model.split('/')[-1])
            or (
                self.model_info is not None
                and self.model_info.get('supports_vision', False)
            )
        )

    def is_caching_prompt_active(self) -> bool:
        """Check if prompt caching is supported and enabled for current model.

        Returns:
            boolean: True if prompt caching is supported and enabled for the given model.
        """
        if self.config.model.startswith('gemini'):
            # GeminiException - Gemini Context Caching only supports 1 message/block of continuous messages. Cause: Environment reminder is added in the prompt?
            return False
        return (
            self.config.caching_prompt is True
            and (
                self.config.model in CACHE_PROMPT_SUPPORTED_MODELS
                or self.config.model.split('/')[-1] in CACHE_PROMPT_SUPPORTED_MODELS
            )
            # We don't need to look-up model_info, because only Anthropic models needs the explicit caching breakpoint
        )

    def is_function_calling_active(self) -> bool:
        # Check if model name is in supported list before checking model_info
        model_name_supported = (
            self.config.model in FUNCTION_CALLING_SUPPORTED_MODELS
            or self.config.model.split('/')[-1] in FUNCTION_CALLING_SUPPORTED_MODELS
            or any(m in self.config.model for m in FUNCTION_CALLING_SUPPORTED_MODELS)
        )
        return model_name_supported

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

            # read the prompt cache hit, if any
            prompt_tokens_details: PromptTokensDetails = usage.get(
                'prompt_tokens_details'
            )
            cache_hit_tokens = (
                prompt_tokens_details.cached_tokens if prompt_tokens_details else None
            )
            if cache_hit_tokens:
                stats += 'Input tokens (cache hit): ' + str(cache_hit_tokens) + '\n'

            # For Anthropic, the cache writes have a different cost than regular input tokens
            # but litellm doesn't separate them in the usage stats
            # so we can read it from the provider-specific extra field
            model_extra = usage.get('model_extra', {})
            cache_write_tokens = model_extra.get('cache_creation_input_tokens')
            if cache_write_tokens:
                stats += 'Input tokens (cache write): ' + str(cache_write_tokens) + '\n'

        # log the stats
        # if stats:
        #     logger.debug(stats)

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
            logger.debug(f'Using custom cost per token: {cost_per_token}')
            extra_kwargs['custom_cost_per_token'] = cost_per_token

        try:
            # try directly get response_cost from response
            cost = getattr(response, '_hidden_params', {}).get('response_cost', None)
            if cost is None:
                cost = litellm_completion_cost(
                    completion_response=response, **extra_kwargs
                )
            self.metrics.add_cost(cost)
            return cost
        except Exception:
            self.cost_metric_supported = False
            logger.debug('Cost calculation not supported for this model.')
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
        self.metrics.reset()

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
        if output or 1:
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
