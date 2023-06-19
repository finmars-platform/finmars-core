"""
Common object to report result of any service call:
if status is data_ready, then data provided
if status is task_ready, then service created a task which id is in task_id field
if status is error, that message should contain description of the problem
if status is no_answer - no meaningfully results
"""

from dataclasses import dataclass


class MonadStatus:
    UNCOMPLETED = "uncompleted"
    DATA_READY = "data_ready"
    TASK_READY = "task_ready"
    ERROR = "error"


@dataclass
class Monad:
    status: int = MonadStatus.UNCOMPLETED
    message: str = ""
    request_id: int = None
    task_id: int = None
    data: dict = None
