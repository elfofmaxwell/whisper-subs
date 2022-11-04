import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld(
    "refresher", 
    {onUpdateSub: (callback: (event: any, sub: string)=>void) => {
        ipcRenderer.on('update-subtitle',callback);
    }}
);