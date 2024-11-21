import json
import os
from typing import Any, Literal, Optional

import requests
from pydantic import BaseModel

from openhands.core.logger import openhands_logger as logger


class FeedbackDataModel(BaseModel):
    version: str
    email: str
    polarity: Literal['positive', 'negative']
    feedback: Literal[
        'positive', 'negative'
    ]  # TODO: remove this, its here for backward compatibility
    permissions: Literal['public', 'private']
    trajectory: Optional[list[dict[str, Any]]]


FEEDBACK_URL = 'https://share-od-trajectory-3u9bw9tx.uc.gateway.dev/share_od_trajectory'


def store_feedback(feedback: FeedbackDataModel) -> dict[str, str]:
    # Start logging
    feedback.feedback = feedback.polarity
    display_feedback = feedback.model_dump()
    if 'trajectory' in display_feedback:
        display_feedback['trajectory'] = (
            f"elided [length: {len(display_feedback['trajectory'])}"
        )
    if 'token' in display_feedback:
        display_feedback['token'] = 'elided'
    logger.debug(f'Got feedback: {display_feedback}')
    config = {
        'action': 'initialize',
        'args': {
            'LLM_MODEL': os.environ['OPENHANDS_MODEL'],
            'AGENT': os.environ['OPENHANDS_AGENT'],
            'LANGUAGE': os.environ['OPENHANDS_LANGUAGE'],
        },
    }
    feedback.trajectory = [config] + feedback.trajectory if feedback.trajectory else []
    for idx, item in enumerate(feedback.trajectory):
        if item.get('log'):
            item = {'step': item['log'].split()[-1]}
            feedback.trajectory[idx] = item
    # Start actual request
    response = requests.post(
        FEEDBACK_URL,
        headers={'Content-Type': 'application/json'},
        json=feedback.model_dump(),
    )
    if response.status_code != 200:
        raise ValueError(f'Failed to store feedback: {response.text}')
    response_data = json.loads(response.text)
    logger.debug(f'Stored feedback: {response.text}')
    return response_data
