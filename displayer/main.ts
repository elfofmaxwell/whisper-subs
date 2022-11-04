import { app, BrowserWindow, ipcMain } from 'electron';
import * as fs from "fs";
import * as path from "path";
import * as child_process from "child_process";

interface SubtitleCur {
    cur: number;
}

interface ChildProcessTracker {
    [index: string]: child_process.ChildProcess;
}


let childProcessTracker: ChildProcessTracker = {};

function createWindow(): void {
    const win = new BrowserWindow(
        {
            width: 1080, 
            height: 200,
            transparent: true, 
            frame: false,
            webPreferences: {
                preload: path.join(__dirname, "preload.js"), 
            }, 
        }
    );

    let subtitleCur: SubtitleCur = {cur: 0};
    let subtitleFPath: string = "./test.txt";

    function loadSubtitle(): void {
        childProcessTracker.liveTranscripterProc = child_process.spawn(
            "python", 
            ["/home/ciel/Documents/Projects/whisper-subs/transcripter/emulated_source.py"]
        )

        childProcessTracker.liveTranscripterProc.stdout?.on('data', (data: string): void=>{
            console.log(data);
        });

        childProcessTracker.liveTranscripterProc.stderr?.on("data", (data: string): void => {
            console.log(`err ${data}`);
        });
    }

    loadSubtitle();

    win.loadFile('index.html');
    //win.webContents.openDevTools();
};


app.whenReady().then(
    () => {
        createWindow();

        app.on('activate', () => {
            if (BrowserWindow.getAllWindows().length === 0) {
                createWindow();
            }
        }); 
    }
);


app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        app.quit();
    }

    for (let childProcKey in childProcessTracker) {
        childProcessTracker[childProcKey].kill();
    }
});