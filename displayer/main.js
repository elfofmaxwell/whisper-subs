"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path = __importStar(require("path"));
const child_process = __importStar(require("child_process"));
const yargs = __importStar(require("yargs"));
const argv = yargs.option('url', {
    description: "The stream url",
    type: "string",
    alias: 'u',
}).option('model', {
    alias: 'm',
    description: "The model used to transcribe",
    type: 'string',
    default: "small",
}).option('language', {
    alias: 'l',
    description: "Language of the stream",
    type: 'string',
    default: "Japanese",
}).option('interval', {
    alias: 'i',
    description: "The interval to slice the audio",
    type: 'number',
    default: 2,
}).option("historyBuffer", {
    alias: 'b',
    description: "The history buffer size for previous transcribed text",
    type: "number",
    default: 0,
}).help().alias('help', 'h').parseSync();
if (argv.url === undefined) {
    throw new Error("No url provided");
}
let childProcessTracker = {};
function createWindow() {
    const win = new electron_1.BrowserWindow({
        width: 1080,
        height: 200,
        transparent: true,
        frame: false,
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
        },
    });
    function loadSubtitle() {
        var _a, _b;
        childProcessTracker.liveTranscripterProc = child_process.spawn("python", [
            "-u",
            path.join(path.dirname(__dirname), "transcripter", "transcripter.py"),
            argv.url,
            "--model", argv.model,
            "--language", argv.language,
            "--task", "transcribe",
            "--interval", String(argv.interval),
            "--history_buffer_size", String(argv.historyBuffer),
        ]);
        (_a = childProcessTracker.liveTranscripterProc.stdout) === null || _a === void 0 ? void 0 : _a.on('data', (data) => {
            console.log(data.toString('utf-8'));
            win.webContents.send('update-subtitle', data.toString('utf-8'));
        });
        (_b = childProcessTracker.liveTranscripterProc.stderr) === null || _b === void 0 ? void 0 : _b.on("data", (data) => {
            console.log(`err ${data}`);
        });
    }
    loadSubtitle();
    //console.log(childProcessTracker);
    win.loadFile('index.html');
    // win.webContents.openDevTools();
}
;
electron_1.app.whenReady().then(() => {
    createWindow();
    electron_1.app.on('activate', () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});
electron_1.app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        electron_1.app.quit();
    }
    for (let childProcKey in childProcessTracker) {
        childProcessTracker[childProcKey].kill();
    }
});
