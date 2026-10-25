#!/usr/bin/env python3
"""
מרכיב עריכה על צילום אמיתי: חיתוכים, זום קפיצי, ושכבת גרפיקה שקופה מ-HTML (כתוביות, כרטיסים, מושן).

  "$PY" compose.py --video video.mp4 --overlay captions.html --data data.json --out out/final.mp4
        [--keep "0.00-3.40,3.95-9.10"]      קטעים שנשארים (אחרי אישור טבלת החיתוכים)
        [--zooms "1.20-2.60:0.12,5.0-6.1:0.10"]  זום על מילים חשובות: התחלה-סוף:עוצמה (זמנים אחרי החיתוך)
        [--preview]                          טיוטה: 540x960, 30fps, רק 15 שניות (או --t0/--t1)
        [--t0 S --t1 E]                      טווח לרינדור (שניות אחרי החיתוך)
        [--no-loudnorm]                      בלי נרמול קול ל-‎-14 LUFS

חוזה דף ה-overlay: window.CONFIG = {W, H} (ברירת מחדל 1080x1920), window.render(t) מצייר את מצב השכבה בזמן t,
והרקע שקוף. הנתונים מ---data נטענים לפני הדף כ-window.DATA. דוגמה: assets/overlays/captions.html.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


FF = ffmpeg_exe()


def probe(path):
    info = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    dur, has_audio = 0.0, " Audio:" in info
    for line in info.splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            dur = float(h) * 3600 + float(m) * 60 + float(s)
    return dur, has_audio


def cut(video, keep, out):
    segs = [tuple(map(float, k.split("-"))) for k in keep.split(",") if k.strip()]
    _, has_audio = probe(video)
    parts, labels = [], ""
    for i, (a, b) in enumerate(segs):
        parts.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}]")
        if has_audio:
            parts.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(0, b - a - 0.02)}:d=0.02[a{i}]")
        labels += f"[v{i}]" + (f"[a{i}]" if has_audio else "")
    parts.append(f"{labels}concat=n={len(segs)}:v=1:a={1 if has_audio else 0}[v]" + ("[a]" if has_audio else ""))
    cmd = [FF, "-v", "error", "-y", "-i", str(video), "-filter_complex", ";".join(parts), "-map", "[v]"]
    if has_audio: cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", str(out)]
    subprocess.run(cmd, check=True)
    print(f"cut: {len(segs)} segments -> {out}")


def render_html(html, data, t0, n, fps, sink):
    """מרנדר דף עם window.render(t) לפריימים שקופים. sink(png_bytes, i)"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.add_init_script("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";")
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(Path(html).resolve().as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
        for i in range(n):
            pg.evaluate(f"window.render({t0 + i / fps:.4f})")
            sink(pg.screenshot(omit_background=True, type="png"), i)
            if i and i % 150 == 0: print(f"  {Path(html).name}: {i}/{n} frames")
        b.close()
        if errs: print("PAGEERROR:", *errs[:5], sep="\n  ")


def zoom_expr(zooms, fps):
    # zoompan על וידאו עם d=1: פריים אחד לכל פריים. env חלק (smoothstep) בכניסה וביציאה של 0.12 שניות
    terms = []
    for z in zooms.split(","):
        if not z.strip(): continue
        rng, amt = z.split(":"); a, b = map(float, rng.split("-"))
        u = f"clip((it-{a})/0.12\\,0\\,1)"; v = f"clip(({b}-it)/0.12\\,0\\,1)"
        terms.append(f"{float(amt)}*{u}*{u}*(3-2*{u})*{v}*{v}*(3-2*{v})")
    return "1+" + "+".join(terms) if terms else "1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", help="צילום בסיס. בלי: סרטון מושן בלבד על רקע --bg באורך --duration")
    ap.add_argument("--duration", type=float); ap.add_argument("--bg", default="#110E2B")
    ap.add_argument("--audio", help="קובץ קול/קריינות לסרטון מושן בלבד")
    ap.add_argument("--overlay"); ap.add_argument("--data")
    ap.add_argument("--behind", help="שכבת HTML שמצוירת מאחורי האדם (טקסט על הקיר, מגזין, פתקים). מפעיל הפרדת אדם")
    ap.add_argument("--behind-data", help="DATA לשכבה האחורית (ברירת מחדל: אותו --data)")
    ap.add_argument("--person", help="שכבת אדם שקופה מוכנה (webm/mov). בלי: נוצרת אוטומטית עם hyperframes remove-background")
    ap.add_argument("--out", default="out/final.mp4"); ap.add_argument("--keep"); ap.add_argument("--zooms")
    ap.add_argument("--preview", action="store_true"); ap.add_argument("--t0", type=float); ap.add_argument("--t1", type=float)
    ap.add_argument("--fps", type=float, default=30); ap.add_argument("--no-loudnorm", action="store_true")
    ap.add_argument("--focus-y", type=float, default=0.33, help="גובה הפנים בפריים, לזום (0 למעלה, 1 למטה)")
    a = ap.parse_args()
    out = Path(a.out).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="compose-"))
    if not a.video:
        if not a.duration: sys.exit("בלי --video צריך --duration")
        base = tmp / "base.mp4"
        cmd0 = [FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={a.bg}:s=1080x1920:r={a.fps}:d={a.duration}"]
        if a.audio: cmd0 += ["-i", str(Path(a.audio).resolve()), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest"]
        subprocess.run(cmd0 + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(base)], check=True)
    else:
        base = Path(a.video).resolve()
    if a.keep:
        cutf = tmp / "cut.mp4"; cut(base, a.keep, cutf); base = cutf
    dur, has_audio = probe(base)
    t0 = a.t0 or 0.0
    t1 = a.t1 if a.t1 is not None else (min(dur, t0 + 15) if a.preview else dur)
    W, H = (540, 960) if a.preview else (1080, 1920)
    n = int(round((t1 - t0) * a.fps))

    data = json.loads(Path(a.data).read_text(encoding="utf-8")) if a.data else {}
    if a.data:   # תמונות יחסיות בסצנות נפתרות מול תיקיית קובץ הנתונים, כך שאפשר להריץ את reel.html ישר מתיקיית הסקיל
        base_dir = Path(a.data).resolve().parent
        for sc in data.get("scenes", []):
            v = sc.get("img")
            fix = lambda x: x if str(x).startswith(("file:", "http", "data:")) else (base_dir / x).resolve().as_uri()
            if isinstance(v, str): sc["img"] = fix(v)
            elif isinstance(v, list): sc["img"] = [fix(x) for x in v]
    bdata = json.loads(Path(a.behind_data).read_text(encoding="utf-8")) if a.behind_data else data
    person = None
    if a.behind:
        if a.zooms: print("אזהרה: זום לא נתמך יחד עם שכבה אחורית, הזום בוטל"); a.zooms = None
        if a.person:
            person = Path(a.person).resolve()
        else:
            seg = tmp / "seg.mp4"
            subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", str(base), "-an",
                            "-vf", f"fps={a.fps},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                            "-c:v", "libx264", "-crf", "14", str(seg)], check=True)
            person = tmp / "person.webm"
            print("מפריד את האדם מהרקע (hyperframes remove-background)...")
            subprocess.run(["npx", "-y", "hyperframes", "remove-background", str(seg), "-o", str(person), "--quality", "best"],
                           check=True, stdout=subprocess.DEVNULL)
        bdir = tmp / "behind"; bdir.mkdir()
        render_html(a.behind, bdata, t0, n, a.fps, lambda png, i: (bdir / f"{i:05d}.png").write_bytes(png))

    vf = f"[0:v]fps={a.fps},scale={1080}:{1920}:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    if a.zooms:
        z = zoom_expr(a.zooms, a.fps)
        vf += (f",zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih*{a.focus_y}-(ih/zoom*{a.focus_y})'"
               f":d=1:s=1080x1920:fps={a.fps}")
    vf += "[b0]"
    cmd = [FF, "-v", "error", "-y", "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", str(base)]
    graph, last, idx = [vf], "b0", 1
    if a.behind:
        cmd += ["-framerate", str(a.fps), "-i", str(tmp / "behind" / "%05d.png")]
        cmd += ["-c:v", "libvpx-vp9", "-i", str(person)]
        graph.append(f"[{idx}:v]format=rgba[bh];[{last}][bh]overlay=0:0:format=auto[b1]")
        graph.append(f"[{idx + 1}:v]fps={a.fps},scale=1080:1920,format=rgba[ps];[b1][ps]overlay=0:0:format=auto[b2]")
        last, idx = "b2", idx + 2
    if a.overlay:
        cmd += ["-f", "image2pipe", "-framerate", str(a.fps), "-c:v", "png", "-i", "-"]
        graph.append(f"[{idx}:v]format=rgba[ov];[{last}][ov]overlay=0:0:format=auto[b3]")
        last = "b3"
    graph.append(f"[{last}]scale={W}:{H},format=yuv420p[v]")
    cmd += ["-filter_complex", ";".join(graph), "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "0:a"]
        if not a.no_loudnorm:
            cmd += ["-af", "highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11"]
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-crf", "20" if a.preview else "17", "-preset", "veryfast" if a.preview else "medium",
            "-movflags", "+faststart", "-shortest", str(out)]

    if not a.overlay:
        subprocess.run(cmd, check=True)
    else:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        render_html(a.overlay, data, t0, n, a.fps, lambda png, i: proc.stdin.write(png))
        proc.stdin.close(); proc.wait()
        if proc.returncode: sys.exit("ffmpeg failed")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"done: {out}  ({t1 - t0:.1f}s, {W}x{H}{', preview' if a.preview else ''})")


if __name__ == "__main__":
    main()
