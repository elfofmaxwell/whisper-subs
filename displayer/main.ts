import { app, BrowserWindow, ipcMain } from 'electron';
import * as fs from "fs";
import * as path from "path";

interface SubtitleCur {
    cur: number;
}




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
        console.log(subtitleCur.cur);
        fs.readFile(subtitleFPath, 'utf-8', (err, data: string) => {
            if (err) {
                console.log(err);
            } else {
                let subLines: string[] = data.split('\n');
                let newSubs: string = subLines.slice(subtitleCur.cur).join("<br>");
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
});