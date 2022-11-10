import argparse
import multiprocessing
import os
import re
import sys
from datetime import datetime
import time
from typing import Any, Optional, Tuple
import warnings
import streamlink
import subprocess
import threading
import ffmpeg
import numpy as np
import whisper
from whisper.audio import SAMPLE_RATE
from typing import List

import subtitle_displayer

class RingBuffer:
    def __init__(self, size: int) -> None:
        self.size = size
        self.data = []
        self.full = False
        self.cur = 0

    def append(self, x: np.ndarray | Any) -> None:
        if self.size <= 0:
            return
        if self.full:
            self.data[self.cur] = x
            self.cur = (self.cur + 1) % self.size
        else:
            self.data.append(x)
            if len(self.data) == self.size:
                self.full = True

    def get_all(self) -> List[np.ndarray | Any]:
        """ Get all elements in chronological order from oldest to newest. """
        all_data = []
        for i in range(len(self.data)):
            idx = (i + self.cur) % self.size
            all_data.append(self.data[idx])
        return all_data

    def has_repetition(self) -> bool:
        prev = None
        for elem in self.data:
            if elem == prev:
                return True
            prev = elem
        return False

    def clear(self) -> None:
        self.data = []
        self.full = False
        self.cur = 0


def writer(
    streamlink_proc: subprocess.Popen, ffmpeg_proc: subprocess.Popen
) -> None:
    while (not streamlink_proc.poll()) and (not ffmpeg_proc.poll()):
        try:
            chunk = streamlink_proc.stdout.read(1024)
            ffmpeg_proc.stdin.write(chunk)
        except (BrokenPipeError, OSError):
            pass


def open_stream(
    stream: str, direct_url: bool, preferred_quality: str, cookies: str = ""
) -> Tuple[subprocess.Popen, None] | Tuple[subprocess.Popen, subprocess.Popen]:
    cookies_lines = None
    if cookies: 
        if os.path.isfile(cookies): 
            with open(cookies) as f: 
                cookies_lines = f.readlines()[4:]
    
    cookie_str_ffmpeg = ""
    if type(cookies_lines) == list and cookies_lines: 
        for cookie_line in cookies_lines: 
            cookie_entries = cookie_line.split('\t')
            cookie_entries_str = "%s=%s; domain=%s; path=%s;" % (cookie_entries[5], cookie_entries[6], cookie_entries[0], cookie_entries[2])
            cookie_str_ffmpeg += cookie_entries_str

    if direct_url:
        try:
            ffmpeg_input_kwargs = {"loglevel": "panic"}
            if cookie_str_ffmpeg: 
                ffmpeg_input_kwargs["cookies"] = cookie_str_ffmpeg
            ffmpeg_process = (
                ffmpeg.input(stream, **ffmpeg_input_kwargs)
                .output("pipe:", format="s16le", acodec="pcm_s16le", ac=1, ar=SAMPLE_RATE)
                .run_async(pipe_stdout=True)
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

        return ffmpeg_process, None


    stream_options = streamlink.streams(stream)
    if not stream_options:
        print("No playable streams found on this URL:", stream)
        sys.exit(0)

    option = None
    for quality in [preferred_quality, 'audio_only', 'audio_mp4a', 'audio_opus', 'best']:
        if quality in stream_options:
            option = quality
            break
    if option is None:
        # Fallback
        option = next(iter(stream_options.values()))

    cmd = ['streamlink', stream, option, "-O"]
    streamlink_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    try:
        ffmpeg_process = (
            ffmpeg.input("pipe:", loglevel="panic")
            .output("pipe:", format="s16le", acodec="pcm_s16le", ac=1, ar=SAMPLE_RATE)
            .run_async(pipe_stdin=True, pipe_stdout=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    thread = threading.Thread(target=writer, args=(streamlink_process, ffmpeg_process))
    thread.start()
    return ffmpeg_process, streamlink_process


def run_subscripter(
    url: str, 
    model: str="small", 
    language: Optional[str]=None, 
    interval: int=5, 
    history_buffer_size: int=0, 
    preferred_quality: str="audio_only",
    direct_url: bool=False, 
    use_vad: bool = False, 
    stream_timer: Optional[float] = None, 
    for_display: bool = True,
    keep_sub: bool = False,
    window_size: Tuple[int, int] = (1920, 200),
    alpha: float = 0.6, 
    font_name: str = "Noto Sans",
    refresh_interval: int = 1,
    cookies: str = '',
    **decode_options
) -> None:

    n_bytes = interval * SAMPLE_RATE * 2  # Factor 2 comes from reading the int16 stream as bytes
    audio_buffer = RingBuffer((history_buffer_size // interval) + 1)
    previous_text = RingBuffer(history_buffer_size // interval)

    print("Loading model...")
    model = whisper.load_model(model)
    if use_vad:
        from vad import VAD
        vad = VAD()
    
    print("Opening stream...")
    open_stream_args = [url, direct_url, preferred_quality]
    if cookies: 
        open_stream_args.append(cookies)
    ffmpeg_process, streamlink_process = open_stream(*open_stream_args)

    tmp_sub_fpath = 'sub_' + datetime.now().isoformat() + '.txt'
    displayer_process = None
    if for_display: 
        with open(tmp_sub_fpath, 'w') as f: 
            f.write('')

        displayer_process = multiprocessing.Process(
            target=subtitle_displayer.main, 
            args=(tmp_sub_fpath, ), 
            kwargs={"window_size": window_size, "alpha": alpha, "font_name": font_name, "refresh_interval": refresh_interval}
        )
        displayer_process.start()
        
    
    timer_process = None
    if stream_timer: 
        timer_process = multiprocessing.Process(target=time.sleep, args=(stream_timer))
        timer_process.start()

    try:
        while ffmpeg_process.poll() is None:
            # Read audio from ffmpeg stream
            in_bytes = ffmpeg_process.stdout.read(n_bytes)
            if not in_bytes:
                break

            if timer_process: 
                if not timer_process.is_alive(): 
                    print("Timer finished! Stopping...")
                    break

            audio = np.frombuffer(in_bytes, np.int16).flatten().astype(np.float32) / 32768.0
            if use_vad and vad.no_speech(audio):
                print(f'{datetime.now().strftime("%H:%M:%S")}')
                continue
            audio_buffer.append(audio)

            # Decode the audio
            result = model.transcribe(np.concatenate(audio_buffer.get_all()),
                                      prefix="".join(previous_text.get_all()),
                                      language=language,
                                      without_timestamps=True,
                                      **decode_options)

            clear_buffers = False
            new_prefix = ""
            for segment in result["segments"]:
                if segment["temperature"] < 0.5 and segment["no_speech_prob"] < 0.6:
                    new_prefix += segment["text"]
                else:
                    # Clear history if the translation is unreliable, otherwise prompting on this leads to repetition
                    # and getting stuck.
                    clear_buffers = True

            previous_text.append(new_prefix)

            if clear_buffers or previous_text.has_repetition():
                audio_buffer.clear()
                previous_text.clear()
            
            output_text = (f'{datetime.now().strftime("%H:%M:%S")} '
                  f'{"" if language else "(" + result.get("language") + ")"} {result.get("text")}')

            print(output_text)
            if for_display: 
                with open(tmp_sub_fpath, 'a') as f: 
                    f.write(output_text+'\n')

        print("Stream ended")
    finally:
        ffmpeg_process.kill()
        if streamlink_process:
            streamlink_process.kill()
        if timer_process: 
            timer_process.terminate()
        if displayer_process: 
            displayer_process.terminate()
        if not keep_sub: 
            os.remove(tmp_sub_fpath)



def cli() -> None:
    parser = argparse.ArgumentParser(description="Parameters for translator.py")
    parser.add_argument('URL', type=str, help='Stream website and channel name, e.g. twitch.tv/forsen')
    parser.add_argument('--model', type=str,
                        choices=['tiny', 'tiny.en', 'small', 'small.en', 'medium', 'medium.en', 'large'],
                        default='small',
                        help='Model to be used for generating audio transcription. Smaller models are faster and use '
                             'less VRAM, but are also less accurate. .en models are more accurate but only work on '
                             'English audio.')
    parser.add_argument('--task', type=str, choices=['transcribe', 'translate'], default='translate',
                        help='Whether to transcribe the audio (keep original language) or translate to English.')
    parser.add_argument('--language', type=str, default='auto',
                        help='Language spoken in the stream. Default option is to auto detect the spoken language. '
                             'See https://github.com/openai/whisper for available languages.')
    parser.add_argument('--interval', type=int, default=5,
                        help='Interval between calls to the language model in seconds.')
    parser.add_argument('--history_buffer_size', type=int, default=0,
                        help='Seconds of previous audio/text to use for conditioning the model. Set to 0 to just use '
                             'audio from the last interval. Note that this can easily lead to repetition/loops if the'
                             'chosen language/model settings do not produce good results to begin with.')
    parser.add_argument('--beam_size', type=int, default=5,
                        help='Number of beams in beam search. Set to 0 to use greedy algorithm instead.')
    parser.add_argument('--best_of', type=int, default=5,
                        help='Number of candidates when sampling with non-zero temperature.')
    parser.add_argument('--preferred_quality', type=str, default='audio_only',
                        help='Preferred stream quality option. "best" and "worst" should always be available. Type '
                             '"streamlink URL" in the console to see quality options for your URL.')
    parser.add_argument('--disable_vad', action='store_true',
                        help='Set this flag to disable additional voice activity detection by Silero VAD.')
    parser.add_argument('--direct_url', action='store_true',
                        help='Set this flag to pass the URL directly to ffmpeg. Otherwise, streamlink is used to '
                             'obtain the stream URL.')
    parser.add_argument("--stream_timer", type=int, default=0, help="Set the value to be the minutes to cut the "
                        "stream. If set to be 0, no timer would be activated")
    parser.add_argument("--for_display", action="store_true", help="Set the flag to open subscript display")
    parser.add_argument("--keep_sub", action="store_true", help="whether to save the temporary sub")
    parser.add_argument("--alpha", type=float, default=0.6, help="Alpha value for window transparency")
    parser.add_argument("--window_size", type=str, default="1920x200", help="Size of subtitle window")
    parser.add_argument("--font_name", type=str, default="Noto Sans", help="Font for subtitle")
    parser.add_argument('--cookies', type=str, default="", help="cookies string passed to ffmpeg")

    args = parser.parse_args().__dict__
    url = args.pop("URL")
    args["use_vad"] = not args.pop("disable_vad")

    if args['model'].endswith('.en'):
        if args['model'] == 'large.en':
            print("English model does not have large model, please choose from {tiny.en, small.en, medium.en}")
            sys.exit(0)
        if args['language'] != 'English' and args['language'] != 'en':
            if args['language'] == 'auto':
                print("Using .en model, setting language from auto to English")
                args['language'] = 'en'
            else:
                print("English model cannot be used to detect non english language, please choose a non .en model")
                sys.exit(0)

    if args['language'] == 'auto':
        args['language'] = None

    if args['beam_size'] == 0:
        args['beam_size'] = None
    
    if args["stream_timer"] == 0: 
        args["stream_timer"] = None

    
    resolution_str = args.pop("window_size")
    if not re.match(r'\d+x\d+', resolution_str): 
        warnings.warn("Invalid window size. Default window size would be used. ")
        resolution_str = "1920x200"
    window_size = tuple(str(resolution_str).split('x'))
    args['window_size'] = tuple([int(i) for i in window_size])




    run_subscripter(url, **args)


if __name__ == '__main__':
    cli()