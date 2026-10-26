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
import re, argparse, json, os, shutil, subprocess, sys, tempfile
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
        b = p.chromium.launch(args=["--disable-gpu", "--disable-renderer-backgrounding", "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows", "--force-color-profile=srgb"]); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.add_init_script("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";")
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(Path(html).resolve().as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
        # פיקסל שקוף אחד בפינה: בלעדיו כרום שומר פריים אטום (רקע נייר / משבצות) כ-RGB בלי שקיפות,
        # הפורמט מתחלף באמצע, ffmpeg בונה מחדש את הגרף ומאבד פריימים
        pg.add_style_tag(content="body{clip-path:polygon(0 0,100% 0,100% calc(100% - 1px),calc(100% - 1px) calc(100% - 1px),calc(100% - 1px) 100%,0 100%)}")
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


def keep_awake():
    """במק, מסך שנרדם עוצר את הרינדור של הדפדפן. caffeinate מעיר אותו ומחזיק ער עד שהתהליך מסתיים"""
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        try: subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception: pass


def main():
    keep_awake()
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", help="צילום בסיס. בלי: סרטון מושן בלבד על רקע --bg באורך --duration")
    ap.add_argument("--duration", type=float); ap.add_argument("--bg", default="#110E2B")
    ap.add_argument("--audio", help="קובץ קול/קריינות לסרטון מושן בלבד")
    ap.add_argument("--overlay"); ap.add_argument("--data")
    ap.add_argument("--behind", help="שכבת HTML שמצוירת מאחורי האדם (טקסט על הקיר, מגזין, פתקים). מפעיל הפרדת אדם")
    ap.add_argument("--behind-data", help="DATA לשכבה האחורית (ברירת מחדל: אותו --data)")
    ap.add_argument("--outline", help='קו סביב האדם, בטווחי זמן: "marker:1.1-2.5,torn:2.5-3.9" (marker = קו טוש לבן שרועד, torn = שוליים לבנים קרועים כמו גזיר עיתון)')
    ap.add_argument("--grade", help='צבע לכל קטע: "0-0.9:bw,2.1-5.5:cool,5.5-8.8:warm,8.8-12:punch" (bw / cool / warm / punch)')
    ap.add_argument("--shake", help='רעידת מצלמה: "0.95-1.3:14,6.3-6.5:8" (התחלה-סוף:עוצמה בפיקסלים, עד 20)')
    ap.add_argument("--glitch", help='גליץ\' של הפרדת צבעים ורעש סביב רגעים: "2.1,5.56,8.88"')
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
    zp = ""
    if a.zooms:
        z = zoom_expr(a.zooms, a.fps)
        zp = (f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih*{a.focus_y}-(ih/zoom*{a.focus_y})'"
              f":d=1:s=1080x1920:fps={a.fps}")
    # אפקטים על התמונה המורכבת (צילום + רקעים + אדם), לפני הכתוביות, כדי שהטקסט יישאר חד ויציב
    post = []
    GR = {"bw": "hue=s=0,eq=contrast=1.28:brightness=-0.03", "cool": "colorbalance=rs=-0.06:bs=0.12:rm=-0.04:bm=0.08,eq=saturation=1.1",
          "warm": "colorbalance=rs=0.12:gs=0.04:bs=-0.12:rm=0.08:bm=-0.08,eq=saturation=0.85:contrast=1.06", "punch": "eq=contrast=1.14:saturation=1.3"}
    for g in (a.grade or "").split(","):
        if not g.strip(): continue
        rng, kind = g.split(":"); ga, gb = rng.split("-"); en = f"enable='between(t,{float(ga) - t0:.3f},{float(gb) - t0:.3f})'"
        post += [f"{f}:{en}" if "=" in f else f for f in GR[kind].split(",")]
    if a.shake:
        amp = "+".join(f"{min(20, float(x.split(':')[1]))}*between(t,{float(x.split(':')[0].split('-')[0]) - t0:.3f},{float(x.split(':')[0].split('-')[1]) - t0:.3f})" for x in a.shake.split(",") if x.strip())
        post += [f"crop=1040:1880:x='20+({amp})*sin(n*2.7)':y='20+({amp})*cos(n*3.1)'", "scale=1080:1920"]
    if a.glitch:
        win = "+".join(f"between(t,{float(x) - t0 - 0.06:.3f},{float(x) - t0 + 0.16:.3f})" for x in a.glitch.split(",") if x.strip())
        post += ["format=gbrp", f"rgbashift=rh=-26:bh=26:gv=8:enable='{win}'", f"noise=alls=40:allf=t:enable='{win}'"]
    post_s = ("," + ",".join(post)) if post else ""
    if zp and not a.behind: vf += "," + zp   # עם שכבה אחורית הזום רץ אחרי ההרכבה של הרקע והאדם, כדי שהמסכה לא תזוז מהגוף
    vf += (post_s if not a.behind else "") + "[b0]"
    cmd = [FF, "-v", "error", "-y", "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", str(base)]
    graph, last, idx = [vf], "b0", 1
    if a.behind:
        cmd += ["-framerate", str(a.fps), "-i", str(tmp / "behind" / "%05d.png")]
        cmd += ["-c:v", "libvpx-vp9", "-i", str(person)]
        graph.append(f"[{idx}:v]format=rgba[bh];[{last}][bh]overlay=0:0:format=auto[b1]")
        last_b = "b1"
        segs = [x.split(":") for x in (a.outline or "").split(",") if x.strip()]
        n_out = len(segs)
        graph.append(f"[{idx + 1}:v]fps={a.fps},scale=1080:1920,format=rgba,split={n_out + 1}[ps]" + "".join(f"[po{k}]" for k in range(n_out)))
        for k, (kind, rng) in enumerate(segs):
            sa, sb = rng.split("-")
            en = f"enable='between(t,{float(sa) - t0:.3f},{float(sb) - t0:.3f})'"
            # מסכה מוגדלת של האדם ברבע רזולוציה (מהיר), ואז חזרה לגודל מלא וסף חד
            grow = ",".join(["dilation"] * (6 if kind == "torn" else 4))
            base_m = f"[po{k}]alphaextract,scale=270:480,{grow}"
            if kind == "torn":
                graph.append(f"{base_m},scale=1080:1920,noise=alls=60:allf=t,lut=y='if(gt(val\\,110)\\,255\\,0)',format=gray[m{k}];"
                             f"color=c=0xFFFDF6:s=1080x1920:r={a.fps}[w{k}];[w{k}][m{k}]alphamerge[ol{k}];[{last_b}][ol{k}]overlay=0:0:{en}[bo{k}]")
            else:   # marker: טבעת לבנה (הפרש בין שתי הגדלות), רועדת כל 3 פריימים
                graph.append(f"{base_m},split[mb{k}][mx{k}];[mx{k}]erosion,erosion[ms{k}];[mb{k}][ms{k}]blend=all_mode=difference,scale=1080:1920,lut=y='if(gt(val\\,60)\\,255\\,0)',format=gray[m{k}];"
                             f"color=c=white:s=1080x1920:r={a.fps}[w{k}];[w{k}][m{k}]alphamerge[ol{k}];"
                             f"[{last_b}][ol{k}]overlay=x='5*sin(floor(n/3)*2.1)':y='5*cos(floor(n/3)*1.7)':{en}[bo{k}]")
            last_b = f"bo{k}"
        graph.append(f"[{last_b}][ps]overlay=0:0:format=auto" + (f",{zp}" if zp else "") + post_s + "[b2]")
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
    # בדיקה עצמית: כמה פריימים יצאו בפועל (חור בציר = שכבות לא מסונכרנות)
    st = subprocess.run([FF, "-i", str(out), "-map", "0:v", "-c", "copy", "-f", "null", "-"], capture_output=True, text=True).stderr
    got = int(re.findall(r"frame=\s*(\d+)", st)[-1]) if re.findall(r"frame=\s*(\d+)", st) else -1
    if got < n - 2: print(f"אזהרה: יצאו {got} פריימים מתוך {n}. יש חור בסרטון, לא להראות לפני שמתקנים")
    print(f"done: {out}  ({t1 - t0:.1f}s, {W}x{H}{', preview' if a.preview else ''})")


if __name__ == "__main__":
    main()
