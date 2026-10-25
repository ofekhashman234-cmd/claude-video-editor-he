#!/usr/bin/env python3
"""
תמלול עברית עם זמן לכל מילה (ivrit-ai/whisper-large-v3-turbo, רץ מקומית).

  "$PY" transcribe.py video.mp4 [--out words.json] [--model ivrit-ai/whisper-large-v3-turbo-ct2]

יוצא:
  words.json      [{"w": "מילה", "s": 1.23, "e": 1.51}, ...]  (זמנים בשניות מתחילת הקובץ)
  transcript.txt  משפט בכל שורה עם זמנים, לאישור המשתמש ולתיקון מילים לפני הכתוביות
אחרי חיתוך לא מתמללים שוב: מחשבים זמנים חדשים מהתמלול המקורי (מתמלול חוזר יוצאות טעויות חדשות).
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path
import numpy as np


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def load_audio(path):
    # מפענחים עם ffmpeg ישירות למערך, כי ה-av של faster-whisper לא תואם לגרסה המותקנת
    raw = subprocess.run([ffmpeg_exe(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media"); ap.add_argument("--out", default="words.json")
    ap.add_argument("--model", default="ivrit-ai/whisper-large-v3-turbo-ct2")
    ap.add_argument("--lang", default="he")
    a = ap.parse_args()
    from faster_whisper import WhisperModel
    audio = load_audio(a.media)
    m = WhisperModel(a.model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio, language=a.lang, word_timestamps=True, vad_filter=True,
                           vad_parameters={"min_silence_duration_ms": 300})
    words, lines = [], []
    for s in segs:
        for w in s.words or []:
            t = w.word.strip()
            if t:
                words.append({"w": t, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
        lines.append(f"[{s.start:6.2f} - {s.end:6.2f}] {s.text.strip()}")
    out = Path(a.out)
    out.write_text(json.dumps(words, ensure_ascii=False, indent=0), encoding="utf-8")
    (out.parent / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    unsure = [w for w in words if w["p"] < 0.5]
    print(f"{len(words)} words -> {out}  | transcript -> {out.parent / 'transcript.txt'}")
    if unsure:
        print("מילים שהמודל לא בטוח בהן (לבדוק באוזן):", ", ".join(f"{w['w']}@{w['s']:.1f}" for w in unsure[:30]))


if __name__ == "__main__":
    main()
