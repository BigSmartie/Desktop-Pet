const { app, BrowserWindow, Menu, Tray, ipcMain, nativeImage, screen } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const projectRoot = app.isPackaged
  ? path.join(process.resourcesPath, 'backend')
  : path.resolve(__dirname, '../..');
const useDevServer = process.argv.includes('--dev') || Boolean(process.env.VITE_DEV_SERVER_URL);
const devUrl = process.env.VITE_DEV_SERVER_URL || 'http://127.0.0.1:5173';
const defaultBackendPort = process.env.MYAGENT_BACKEND_PORT || '8000';
const backendBaseUrl = process.env.MYAGENT_BACKEND_URL || `http://127.0.0.1:${defaultBackendPort}`;
const backendPort = resolveBackendPort();
const autoStartBackend = process.env.MYAGENT_AUTOSTART_BACKEND !== 'false';

let mainWindow = null;
let petWindow = null;
let tray = null;
let backendProcess = null;
let backendManaged = false;
let backendHealthTimer = null;
let isQuitting = false;
let backendStatus = {
  baseUrl: backendBaseUrl,
  state: 'unknown',
  managed: false,
  pid: null,
  lastError: '',
};
const hasSingleInstanceLock = app.requestSingleInstanceLock();

if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!mainWindow) {
      createMainWindow();
      return;
    }
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  });
}

function resolveBackendPort() {
  try {
    return process.env.MYAGENT_BACKEND_PORT || new URL(backendBaseUrl).port || defaultBackendPort;
  } catch {
    return defaultBackendPort;
  }
}

function appUrl(windowName) {
  if (useDevServer) {
    return `${devUrl}/?window=${windowName}`;
  }

  const indexUrl = pathToFileURL(path.join(__dirname, '../dist/index.html'));
  indexUrl.searchParams.set('window', windowName);
  return indexUrl.toString();
}

function fileUrl(windowName) {
  const indexUrl = pathToFileURL(path.join(__dirname, '../dist/index.html'));
  indexUrl.searchParams.set('window', windowName);
  return indexUrl.toString();
}

function attachLoadFallback(win, windowName) {
  if (!useDevServer) return;

  win.webContents.once('did-fail-load', () => {
    win.loadURL(fileUrl(windowName));
  });
}

function notifyBackendStatus() {
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('backend:status', backendStatus);
  }
}

function setBackendStatus(nextStatus) {
  backendStatus = { ...backendStatus, ...nextStatus };
  notifyBackendStatus();
}

function stopBackendMonitor() {
  if (backendHealthTimer) {
    clearInterval(backendHealthTimer);
    backendHealthTimer = null;
  }
}

function requestUrl(url, timeoutMs = 900) {
  return new Promise((resolve) => {
    let req = null;
    try {
      const client = url.startsWith('https:') ? https : http;
      req = client.get(url, (res) => {
        res.resume();
        resolve(res.statusCode >= 200 && res.statusCode < 500);
      });
    } catch {
      resolve(false);
      return;
    }

    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve(false);
    });

    req.on('error', () => resolve(false));
  });
}

async function backendIsAlive() {
  return requestUrl(`${backendBaseUrl}/health/live`);
}

async function markBackendReadyIfAlive() {
  if (!(await backendIsAlive())) {
    return false;
  }

  setBackendStatus({
    state: backendManaged ? 'running' : 'external',
    managed: backendManaged,
    pid: backendProcess?.pid || null,
    lastError: '',
  });
  stopBackendMonitor();
  return true;
}

function monitorBackendUntilReady() {
  if (backendHealthTimer) return;

  backendHealthTimer = setInterval(() => {
    if (backendStatus.state === 'running' || backendStatus.state === 'external') {
      stopBackendMonitor();
      return;
    }

    markBackendReadyIfAlive();
  }, 2500);

  if (backendHealthTimer.unref) {
    backendHealthTimer.unref();
  }
}

function resolvePythonExecutable() {
  const candidates = [
    process.env.MYAGENT_PYTHON,
    path.join(projectRoot, '.venv', 'Scripts', 'python.exe'),
    'D:\\MiniConda\\envs\\myagent\\python.exe',
    'python',
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate === 'python' || fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return 'python';
}

function appendBackendLog(stream, chunk) {
  stream.write(chunk);
  if (process.env.MYAGENT_BACKEND_STDIO === 'inherit') {
    process.stdout.write(chunk);
  }
}

function startBackendProcess() {
  const logsDir = path.join(projectRoot, 'logs');
  fs.mkdirSync(logsDir, { recursive: true });
  const logStream = fs.createWriteStream(path.join(logsDir, 'electron-backend.log'), { flags: 'a' });
  const pythonPath = resolvePythonExecutable();
  const args = ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', backendPort];

  backendManaged = true;
  backendProcess = spawn(pythonPath, args, {
    cwd: projectRoot,
    env: { ...process.env, PYTHONUTF8: '1' },
    windowsHide: true,
  });

  setBackendStatus({
    state: 'starting',
    managed: true,
    pid: backendProcess.pid,
    lastError: '',
  });

  backendProcess.stdout.on('data', (chunk) => appendBackendLog(logStream, chunk));
  backendProcess.stderr.on('data', (chunk) => appendBackendLog(logStream, chunk));

  backendProcess.on('error', (error) => {
    setBackendStatus({
      state: 'error',
      lastError: error.message,
      pid: null,
    });
  });

  backendProcess.on('exit', (code, signal) => {
    logStream.end(`\n[backend exited] code=${code} signal=${signal}\n`);
    backendProcess = null;
    stopBackendMonitor();
    setBackendStatus({
      state: backendManaged ? 'stopped' : 'external',
      pid: null,
      lastError: code ? `Backend exited with code ${code}` : '',
    });
  });
}

async function waitForBackendReady(maxAttempts = 80) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (await markBackendReadyIfAlive()) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 750));
  }

  setBackendStatus({
    state: 'starting',
    lastError: 'Backend is still initializing local models. This can take a while on first launch.',
  });
  monitorBackendUntilReady();
  return false;
}

async function ensureBackendRunning() {
  if (await backendIsAlive()) {
    backendManaged = false;
    setBackendStatus({
      state: 'external',
      managed: false,
      pid: null,
      lastError: '',
    });
    return;
  }

  if (backendProcess) {
    waitForBackendReady();
    monitorBackendUntilReady();
    return;
  }

  if (!autoStartBackend) {
    setBackendStatus({
      state: 'disabled',
      managed: false,
      lastError: 'Backend autostart is disabled.',
    });
    return;
  }

  startBackendProcess();
  waitForBackendReady();
  monitorBackendUntilReady();
}

function createMainWindow() {
  const iconPath = path.join(__dirname, '../build/icon.ico');
  mainWindow = new BrowserWindow({
    width: 1240,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    show: false,
    title: 'MyAgent Pet Console',
    icon: iconPath,
    backgroundColor: '#eef3f2',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  attachLoadFallback(mainWindow, 'console');
  mainWindow.loadURL(appUrl('console'));
  mainWindow.once('ready-to-show', () => mainWindow.show());

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  if (process.argv.includes('--devtools')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

function createPetWindow() {
  const { workArea } = screen.getPrimaryDisplay();
  const iconPath = path.join(__dirname, '../build/icon.ico');

  petWindow = new BrowserWindow({
    width: 240,
    height: 320,
    x: workArea.x + workArea.width - 280,
    y: workArea.y + workArea.height - 380,
    frame: false,
    transparent: true,
    resizable: false,
    maximizable: false,
    fullscreenable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    show: false,
    backgroundColor: '#00000000',
    icon: iconPath,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  petWindow.setAlwaysOnTop(true, 'floating');
  attachLoadFallback(petWindow, 'pet');
  petWindow.loadURL(appUrl('pet'));
  petWindow.once('ready-to-show', () => petWindow.show());

  petWindow.on('closed', () => {
    petWindow = null;
  });
}

function toggleMainWindow() {
  if (!mainWindow) {
    createMainWindow();
    return;
  }

  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
}

function togglePetWindow() {
  if (!petWindow) {
    createPetWindow();
    return;
  }

  if (petWindow.isVisible()) {
    petWindow.hide();
  } else {
    petWindow.show();
  }
}

function createTray() {
  const iconPath = path.join(__dirname, '../build/icon.ico');
  const icon = nativeImage.createFromPath(iconPath);

  tray = new Tray(icon);
  refreshTrayMenu();
  tray.on('double-click', () => toggleMainWindow());
}

function refreshTrayMenu() {
  if (!tray) return;

  const autoLaunch = app.getLoginItemSettings().openAtLogin;
  tray.setToolTip('MyAgent Pet');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show Console', click: () => toggleMainWindow() },
    { label: 'Show Pet', click: () => togglePetWindow() },
    { label: 'Backend Health', click: () => ensureBackendRunning() },
    {
      label: 'Start at Login',
      type: 'checkbox',
      checked: autoLaunch,
      click: (item) => setAutoLaunch(item.checked),
    },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ]));
}

function setAutoLaunch(openAtLogin) {
  app.setLoginItemSettings({
    openAtLogin: Boolean(openAtLogin),
    openAsHidden: false,
  });
  refreshTrayMenu();
  return app.getLoginItemSettings();
}

if (hasSingleInstanceLock) {
  app.whenReady().then(() => {
    Menu.setApplicationMenu(null);
    ensureBackendRunning();
    createMainWindow();
    createPetWindow();
    createTray();

    app.on('activate', () => {
      if (!mainWindow) createMainWindow();
      if (!petWindow) createPetWindow();
    });
  });
}

app.on('window-all-closed', (event) => {
  if (!isQuitting) {
    event.preventDefault();
  }
});

ipcMain.handle('window:minimize', (event) => {
  BrowserWindow.fromWebContents(event.sender)?.minimize();
});

ipcMain.handle('window:close', (event) => {
  BrowserWindow.fromWebContents(event.sender)?.hide();
});

ipcMain.handle('window:toggle-main', () => {
  toggleMainWindow();
});

ipcMain.handle('backend:get-status', () => backendStatus);

ipcMain.handle('app:get-auto-launch', () => app.getLoginItemSettings());

ipcMain.handle('app:set-auto-launch', (_event, openAtLogin) => setAutoLaunch(openAtLogin));

ipcMain.handle('pet:set-ignore-mouse-events', (event, ignore) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  win?.setIgnoreMouseEvents(Boolean(ignore), { forward: true });
});

app.on('before-quit', () => {
  isQuitting = true;
  backendManaged = false;
  if (backendProcess) {
    backendProcess.kill();
  }
});
