# desk helper ui

A small, hackable desktop workspace for chat, projects, history, manual tasks and **human-confirmed** local tools. MIT licensed, copyright Li-Syuan Hong.

**Offline demo by default.** The built-in backend is synthetic, not an AI model. Bring a trusted backend through a small Python interface; no accounts, keys, paid APIs or network connections are required to run the demo. This initial public edition uses Tk and SQLite, with no third-party Python dependencies or bundled artwork.

## Run from a clone or Code ZIP

Python **3.10+ with Tk and venv** is required. Tested on Windows x64 / Python 3.10.4; other Python versions and operating systems are not yet verified. Tk may need a separate OS package on Linux. No WebView2 or .NET is required. Obtain prerequisites through your approved software channel; the scripts do not install system software or download packages.

Windows CMD, in the complete extracted project folder:

```bat
install-offline.bat "C:\approved\Python\python.exe"
test.bat
start-app.bat
```

Replace the example Python path with your actual approved interpreter. The installer creates this project's `.venv`, refuses to overwrite an existing environment, and needs no wheels or network. `test.bat` runs AST checks, core tests and real Tk UI tests. A desktop display is required for the UI tests.

Alternatively:

```sh
python -m venv .venv
# Use .venv/Scripts/python.exe on Windows or .venv/bin/python on Unix:
python -m desk_helper_ui
python scripts/check.py
```

The `python` in the last two lines must be the new environment's interpreter. There is no package installation step. For a headless test, run `python scripts/check.py --core-only`; this does not validate the UI.

## Try the workspace

1. Create a project; chat and tasks stay separate between projects. Unsent drafts survive project switching within the session.
2. Send a message; the offline demo labels its synthetic response. History is saved locally.
3. Send `/task Review the result`. Open **Tasks & confirmed tools** and review the proposal. Nothing is created before **Review & confirm**; the dialog defaults to No.
4. Confirm once, or decline. Repeated confirmation returns the existing receipt. Mark completion yourself; model text never marks work complete.
5. Cancel a running request. Late output is discarded locally; cancellation does not guarantee a remote model stopped. New sends wait for the actual worker to finish. Errors do not fall back to demo or retry automatically.

`start-app.bat` stores persistent data in the current user's `desk-helper-ui` directory (LOCALAPPDATA on Windows). `start-demo.bat` uses a **temporary** workspace removed on exit. Custom location: `start-app.bat --data-dir "C:\your\workspace"`. Do not use another app's database or run two UI instances against the same workspace.

## Replace the model backend

```bat
start-app.bat --backend "examples\custom_backend.py"
```

This included replacement is also local/synthetic and proves backend selection. See [backend contract](docs/BACKENDS.md). A backend implements `reply(messages, cancelled, request_id) -> Reply`. A real model client is **not bundled or live-tested**; add your own client with explicit data/credential consent, TLS verification, bounded timeouts and dependency/license review.

Plugins are arbitrary trusted Python code, **not sandboxed**. They are loaded only through the explicit `--backend` argument. Do not run untrusted files. Replies are plain text; proposed tools are restricted to local task creation through a confirmation transaction. No shell, arbitrary URL tool, remote integration, scheduler, enterprise identity or permission bypass is included.

## Modify it

- `desk_helper_ui/app.py`: desktop widgets and project navigation.
- `desk_helper_ui/backends.py`: backend protocol, demo and reply validation.
- `desk_helper_ui/core.py`: SQLite data, request lifecycle and confirmed task tool.
- `tests/`: isolation, cancellation, failure, idempotency and native UI checks.

Keep approval, cancellation, project isolation and no-replay guarantees when extending it. See [contributor rules](AGENTS.md), [validation](docs/VALIDATION.md), [third-party notices](THIRD-PARTY-NOTICES.md), [license](LICENSE).

## 繁體中文快速開始

以 VS Code 開啟整個 clone／解壓資料夾。先讀 README 與 AGENTS；核對 Python 3.10+／Tk。CMD 用實際 Python 路徑執行 `install-offline.bat` → `test.bat` → `start-app.bat`。不需公司服務、第三方 wheels、WebView2 或 .NET。`start-demo.bat` 為暫存展示，正常啟動則保存本機歷史。可自行修改 UI 與 backend；真實模型需要另接，本版不宣稱已完成外部 API 驗證。
