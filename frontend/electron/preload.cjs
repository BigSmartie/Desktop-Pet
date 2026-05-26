const { contextBridge, ipcRenderer } = require('electron');

const backendBaseUrl = process.env.MYAGENT_BACKEND_URL
  || `http://127.0.0.1:${process.env.MYAGENT_BACKEND_PORT || '8000'}`;

contextBridge.exposeInMainWorld('myAgentDesktop', {
  backendBaseUrl,
  minimize: () => ipcRenderer.invoke('window:minimize'),
  close: () => ipcRenderer.invoke('window:close'),
  toggleMain: () => ipcRenderer.invoke('window:toggle-main'),
  getAutoLaunch: () => ipcRenderer.invoke('app:get-auto-launch'),
  setAutoLaunch: (openAtLogin) => ipcRenderer.invoke('app:set-auto-launch', openAtLogin),
  getBackendStatus: () => ipcRenderer.invoke('backend:get-status'),
  onBackendStatus: (callback) => {
    const listener = (_event, status) => callback(status);
    ipcRenderer.on('backend:status', listener);
    return () => ipcRenderer.removeListener('backend:status', listener);
  },
  setIgnoreMouseEvents: (ignore) => ipcRenderer.invoke('pet:set-ignore-mouse-events', ignore),
});
