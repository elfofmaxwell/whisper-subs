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
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
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
    let subtitleCur = { cur: 0 };
    let subtitleFPath = "./test.txt";
    function loadSubtitle() {
        console.log(subtitleCur.cur);
        fs.readFile(subtitleFPath, 'utf-8', (err, data) => {
            if (err) {
                console.log(err);
            }
            else {
                let subLines = data.split('\n');
                let newSubs = subLines.slice(subtitleCur.cur).join("<br>");
                subtitleCur.cur = subLines.length;
                console.log(newSubs);
                win.webContents.send('update-subtitle', newSubs);
            }
        });
        setTimeout(loadSubtitle, 1000);
    }
    loadSubtitle();
    win.loadFile('index.html');
    //win.webContents.openDevTools();
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
});
