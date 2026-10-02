"""Backends propose text/tasks. They never receive Store or execution authority."""
from dataclasses import dataclass
from typing import Protocol
import importlib.util
from pathlib import Path

@dataclass(frozen=True)
class Reply:
    text: str
    tasks: tuple = ()

class Backend(Protocol):
    name: str
    def reply(self, messages, cancelled, request_id) -> Reply: ...

class DemoBackend:
    name = 'Offline demo (synthetic; no model/API)'
    def reply(self, messages, cancelled, request_id):
        if cancelled.is_set():
            return Reply('Cancelled.')
        prompt = messages[-1]['content']
        if prompt.startswith('/task '):
            title = prompt[6:].strip()
            return Reply('Demo proposed a local task. Review it below; nothing has been created.', (title,))
        return Reply('Offline demo: ' + prompt + '\nUse /task followed by a title to propose a task. This response is synthetic.')

def validate_reply(value):
    if not isinstance(value, Reply) or not isinstance(value.text, str) or not 1 <= len(value.text.strip()) <= 30000:
        raise ValueError('invalid_backend_reply')
    if not isinstance(value.tasks, tuple) or len(value.tasks) > 5:
        raise ValueError('invalid_task_proposal')
    for title in value.tasks:
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200 or any(ord(c) < 32 for c in title):
            raise ValueError('invalid_task_title')
    return Reply(value.text, tuple(title.strip() for title in value.tasks))

def _load_backend(path):
    """Explicit trusted local code only; never auto-discover plugins or install packages."""
    file = Path(path).resolve(strict=True)
    if file.suffix != '.py' or not file.is_file():
        raise ValueError('backend_must_be_a_trusted_python_file')
    spec = importlib.util.spec_from_file_location('desk_helper_user_backend', file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    backend = module.create_backend()
    if not callable(getattr(backend, 'reply', None)) or not isinstance(getattr(backend, 'name', None), str):
        raise ValueError('invalid_backend_interface')
    return backend


def load_backend(path):
    try:
        return _load_backend(path)
    except Exception:
        raise ValueError('backend_initialization_failed') from None
