import { app, BrowserWindow, ipcMain } from 'electron';
import * as fs from "fs";
import * as path from "path";
import * as child_process from "child_process";
import * as yargs from "yargs";


interface ChildProcessTracker {
    [index: string]: child_process.ChildProcess;
}


const argv = yargs.option(
    'url', 
    {
        description: "The stream url", 
        type: "string",
        alias: 'u',
    }
).option(
    'model', 
    {
        alias: 'm', 
        description: "The model used to transcribe", 
        type: 'string', 
        default: "small", 
    }
).option(
    'language', 
    {
        alias: 'l', 
        description: "Language of the stream", 
        type: 'string', 
        default: "Japanese", 
    }
).option(
    'interval', 
    {
        alias: 'i', 
        description: "The interval to slice the audio", 
        type: 'number',
        default: 2,  
    }
).option(
    "historyBuffer", 
    {
        alias: 'b', 
        description: "The history buffer size for previous transcribed text", 
        type: "number",
        default: 0, 
    }
).help().alias('help', 'h').parseSync();


if (argv.url === undefined) {
    throw new Error("No url provided");
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


    function loadSubtitle(): void {
        childProcessTracker.liveTranscripterProc = child_process.spawn(
            "python", 
            [
                "-u", 
                path.join(path.dirname(__dirname), "transcripter", "transcripter.py"),
                argv.url!,
                "--model", argv.model, 
                "--language", argv.language, 
                "--task", "transcribe", 
                "--interval", String(argv.interval), 
                "--history_buffer_size", String(argv.historyBuffer), 
            ]
        )

        childProcessTracker.liveTranscripterProc.stdout?.on('data', (data: Buffer): void=>{
            console.log(data.toString('utf-8'));
            win.webContents.send('update-subtitle', data.toString('utf-8'));
        });

        childProcessTracker.liveTranscripterProc.stderr?.on("data", (data: Buffer): void => {
            console.log(`err ${data}`);
        });
    }

    loadSubtitle();
    //console.log(childProcessTracker);
    win.loadFile('index.html');
    // win.webContents.openDevTools();
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