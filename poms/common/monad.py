"""
Common object to report result of any service call:
if status is data_ready, then data provided
if status is task_ready, then service created a task which id is in task_id field
if status is error, that message should contain description of the problem
if status is no_answer - no meaningfully results
"""

from dataclasses import dataclass
from typing import Any


class Status:
    NO_ANSWER = 0
    DATA_READY = 1
    TASK_READY = 2
    ERROR = 666


@dataclass
class Monad:
    status: int = Status.NO_ANSWER
    task_id: int = 0
    message: str = ""
    data: Any = None
