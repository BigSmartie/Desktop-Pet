# MyAgent Pet Frontend

Vue 3 + Vite control console for the personal desktop pet. The Electron shell can open both the main console window and the floating pet window.

## Commands

```bash
npm run dev
```

Starts the Vite web frontend only.

```bash
npm run desktop
```

Builds the frontend, opens Electron, and attempts to start the FastAPI backend with the local Python environment.

```bash
npm run desktop:dev
```

Opens Electron against a running Vite dev server at `http://127.0.0.1:5173`.

```bash
npm run desktop:build
```

Builds a Windows NSIS installer in `release/`. The installer includes the frontend and backend source resources. A Python runtime is still required; set `MYAGENT_PYTHON` if the app cannot find the intended environment.

```bash
npm run desktop:dir
```

Builds an unpacked desktop app directory for quick packaging checks.

## Desktop Backend Options

The Electron shell checks `http://127.0.0.1:8000/health/live`. If no backend is running, it starts:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Useful environment variables:

- `MYAGENT_PYTHON`: absolute path to the Python executable.
- `MYAGENT_BACKEND_PORT`: backend port, default `8000`.
- `MYAGENT_BACKEND_URL`: full backend URL, default `http://127.0.0.1:8000`.
- `MYAGENT_AUTOSTART_BACKEND=false`: disable backend autostart.

Backend logs are written to `../logs/electron-backend.log`.

The app also supports tray controls, Windows login startup, recent log viewing, and daily report generation from the console settings panel.
