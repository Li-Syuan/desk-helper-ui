"""Explicit replacement example; no API credentials, network or tools."""
from desk_helper_ui.backends import Reply
class LocalBackend:
    name='Custom local backend example (synthetic)'
    def reply(self, messages, cancelled, request_id):
        if cancelled.is_set():return Reply('Cancelled.')
        return Reply('Custom backend received: '+messages[-1]['content'])
def create_backend():return LocalBackend()
