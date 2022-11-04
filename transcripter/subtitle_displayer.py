import tkinter as tk
from typing import Tuple
from tkinter import font as tk_font
import warnings

class SubFCursor(): 
    def __init__(self) -> None:
        self.cursor = 0

def main(sub_fname: str, refresh_interval: float=1, window_size: Tuple[int, int] = (1920, 200), alpha: float = 0.6, font_name: str = "Noto Sans") -> None: 
    if alpha < 0 or alpha > 1: 
        raise Exception("Invalid alpha value. ")

    root = tk.Tk()
    if font_name not in tk_font.families(): 
        warnings.warn("Font specified unavailable. Fallback fonts might be used. ")


    root.title('Subtitle')
    root.geometry('%sx%s' % window_size)
    root.configure(bg="#000")

    root.wait_visibility(root)
    root.wm_attributes('-alpha', alpha)
    #root.wm_attributes('-type', 'splash')
    root.update_idletasks()
    root.overrideredirect(True)
    root.update_idletasks()
    root.attributes('-topmost', True)


    subtitle_text = tk.StringVar()
    subtitle_text.set('')
    subtitle_textbox = tk.Label(root, textvariable=subtitle_text, font=(font_name, 20), wraplength=int(window_size[0]*0.9), justify="center", bg="#000", fg="#fff")
    subtitle_textbox.pack()

    sub_f_cursor = SubFCursor()
    

    def refresh_subtitle() -> None: 
        with open(sub_fname) as sub_f: 
            sub_f_lines = sub_f.readlines()
        if len(sub_f_lines) <= sub_f_cursor.cursor:
            pass
        else: 
            subtitle_text.set('\n'.join(sub_f_lines[sub_f_cursor.cursor:]))
            sub_f_cursor.cursor = len(sub_f_lines)
        root.after(int(refresh_interval*1e3), refresh_subtitle)

    root.after(int(1e3), refresh_subtitle)
    root.mainloop()

if __name__ == "__main__": 
    main(refresh_interval=1)