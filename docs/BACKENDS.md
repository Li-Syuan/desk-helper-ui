# Backend contract

`create_backend()` returns an object with a display `name` and `reply(messages, cancelled, request_id)`. Messages are a project-specific list of role/content dictionaries: completed context plus the current input. Return `desk_helper_ui.backends.Reply(text, tasks=())`; task titles are proposals, limited to five titles of up to 200 characters. Model output is never an instruction to execute code.

The UI runs reply outside its thread. Respect the `threading.Event` cancellation flag and use bounded I/O timeouts. A backend that never returns prevents orderly shutdown; plugins are trusted local code, not a sandbox. Do not share mutable history between projects. The request ID is stable for one call; it is not permission to retry a request with an unknown remote outcome.

Successful validated replies are persisted to the originating project even if the user switches projects. Failed or cancelled replies cannot create proposals. Raw backend exceptions are not stored or shown. There is no automatic retry, model fallback or remote recovery protocol in this initial version.

A proposal is immutable review content with a ten-minute expiry. Confirmation checks project, completed request, status, expiry and reviewed payload; SQLite BEGIN IMMEDIATE makes concurrent confirmations return one receipt. Decline does not create tasks. Only local task creation is currently allowed. Add other capabilities only with explicit schema/scope, revision-bound confirmation, side-effect reporting and appropriate tests.

The included custom backend is synthetic. No real model API, credentials or enterprise integrations are configured. Load a trusted backend explicitly with `python -m desk_helper_ui --backend path/to/backend.py`; no plugin discovery, package installer or arbitrary module name is accepted. Credentials must stay outside Git and logs. Explicit backend code can perform arbitrary Python operations, so the interface is not a security sandbox.
