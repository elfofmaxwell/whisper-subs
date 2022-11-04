"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld("refresher", { onUpdateSub: (callback) => {
        electron_1.ipcRenderer.on('update-subtitle', callback);
    } });
