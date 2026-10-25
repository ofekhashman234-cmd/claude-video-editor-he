#!/usr/bin/env python3
"""
לוח סגנונות: מציג איך כל סגנון עריכה ייראה, על פריים אמיתי מהסרטון של המשתמש.

שימוש:
  PY=~/.video-editor/venv/bin/python
  "$PY" board.py --video video.mp4 --out board/ --animate \
      --hook "תפסיקו לכתוב פרומפטים" --key "לופים" \
      --caption "רוב האוטומציות נופלות בהתחלה" --capkey "בהתחלה" \
      --styles split,hook,pill,circle,chat,magazine,notes,motion,screen

  בלי סרטון (למשל סרטון בלי פנים): --frame image.png, או בלי כלום והפריים יהיה צללית.
  צבעים: --bg "#110E2B" --accent "#FF6B2C" --hi "#E5322D"

יוצא: out/<style>.png לכל סגנון, out/board.html (לוח השוואה), out/board.jpg (גיליון אחד).
"""
import argparse, html, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
W, H = 1080, 1920

STYLE_INFO = {
    "split":    ("מסך מפוצל: אנימציה למעלה, אתה למטה", "הפורמט של עדן ביבס ואיילון גרופר. כל משפט מקבל המחשה על רקע כהה, והפנים נשארות על המסך. מתאים להסברים."),
    "hook":     ("פתיח קינטי: כותרת ענק על המילים הראשונות", "3 השניות הראשונות. המסר בגדול על המסך, מילה אחת מודגשת בבלוק צבע. עוצר גלילה."),
    "pill":     ("נקי: כתובית בגלולה וזום קפיצי", "הבסיס שכל סרטון צריך. כתובית לבנה עם מילת מפתח צבועה, וזום קטן על המילה החשובה."),
    "circle":   ("מסגרת עגולה + אובייקט מוסבר", "אתה בעיגול בצד, ובצד השני מוצר, ממשק או דיאגרמה שמתפרקים לחלקים עם הסברים."),
    "chat":     ("צ'אט שמקליד לבד ליד הראש", "טלפון צף עם פרומפט שמוקלד ותשובה שזורמת. מושלם לתוכן על AI."),
    "magazine": ("שער של מגזין", "שם ענק מאחורי הראש, כותרות משנה וברקוד. רגע של 'וואו' לפתיחה."),
    "notes":    ("קיר של תגובות אמיתיות", "פתקים עם תגובות אמיתיות נדבקים על הקיר. הוכחה חברתית שנבנית מול העיניים."),
    "motion":   ("מושן מלא, בלי פנים", "רק אנימציה וטקסט קינטי על רקע כהה עם קו ניאון, וקריינות שלך. בלי לצלם את עצמך."),
    "bigword":  ("מילים ענקיות בלי מסגרת", "מילה או שתיים בכל פעם, ענק, באמצע הגוף. הסגנון של בני פרבר ושל עדן ביבס בעבר. אנרגטי ומהיר."),
    "behind":   ("טקסט על הקיר מאחוריך", "הכותרת נכתבת על הקיר, והראש שלך מסתיר חלק ממנה כאילו היא באמת בחדר. רגע 'וואו' לפתיחה."),
    "bgswap":   ("החלפת רקע", "הרקע מאחוריך מתחלף לרקע של המותג (או שקיעה מטושטשת כמו אצל בני). נראה מקצועי בלי לצלם בסטודיו."),
    "pip":      ("מסך מלא + הראש שלך בפינה", "האפליקציה או האתר על כל המסך, ואתה חתוך בפינה ומסביר. כמו בני פרבר כשהוא מראה כלי."),
    "cinematic":("סינמטי שחור-אדום, בלי פנים", "ארגז כלים, טרמינל שמקליד לבד, טיימליין עם מספריים וחותמת. הסגנון של בני פרבר בסרטון שערך עם Claude Code."),
    "docu":     ("דוקו נטפליקס", "גרף עמודות שעולות עם מספרים רצים, תווית שם מתחת לדובר, אווירה חמה וכהה. לסיפור עם נתונים."),
    "quotecard":("כרטיס ציטוט מעל הראש", "משפט חזק בכרטיס לבן למעלה עם מילים צבועות, ואימוג'י שקופץ ליד הראש. הפתיח של עדן ביבס."),
    "screen":   ("הקלטת מסך + קול, בלי פנים", "המסך שלך בחלון מעוצב על רקע המותג, עם כתוביות. הכי מהיר לייצר, מראה עבודה אמיתית."),
}


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def grab_frame(video, out_png, at=None):
    ff = ffmpeg_exe()
    if at is None:
        info = subprocess.run([ff, "-hide_banner", "-i", str(video)], capture_output=True, text=True).stderr
        dur = 6.0
        for line in info.splitlines():
            if "Duration:" in line:
                hms = line.split("Duration:")[1].split(",")[0].strip().split(":")
                dur = float(hms[0]) * 3600 + float(hms[1]) * 60 + float(hms[2])
        at = max(0.5, dur * 0.35)
    subprocess.run([ff, "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1",
                    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", str(out_png)], check=True)


def font_css():
    f = FONTS.as_uri()
    return f"""
@font-face{{font-family:Rubik;src:url('{f}/rubik-hebrew-300-900.woff2') format('woff2');font-weight:300 900;unicode-range:U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F}}
@font-face{{font-family:Rubik;src:url('{f}/rubik-latin-300-900.woff2') format('woff2');font-weight:300 900}}
@font-face{{font-family:Heebo;src:url('{f}/heebo-hebrew-100-900.woff2') format('woff2');font-weight:100 900}}
@font-face{{font-family:Amatic;src:url('{f}/amatic-sc-hebrew-700.woff2') format('woff2');font-weight:700}}
"""


def esc(s):
    return html.escape(s or "")


def mark(text, key, cls="k"):
    t = esc(text)
    if key and key in text:
        t = t.replace(esc(key), f'<span class="{cls}">{esc(key)}</span>', 1)
    return t


def page(body, a, extra_css=""):
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
{font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{a.bg};font-family:Rubik,Heebo,sans-serif;color:#fff}}
.full{{position:absolute;inset:0;background:url('frame.png') center/cover}}
.pill{{position:absolute;left:50%;transform:translateX(-50%);background:#fff;color:#111;font-weight:800;font-size:46px;padding:14px 30px;border-radius:18px;white-space:nowrap;box-shadow:0 8px 24px rgba(0,0,0,.35)}}
.pill .k{{color:{a.hi}}}
.waves{{position:absolute;inset:0;background:
  repeating-radial-gradient(ellipse at 120% 140%, rgba(120,110,255,.0) 0 38px, rgba(120,110,255,.22) 39px 41px, rgba(120,110,255,0) 42px 80px), {a.bg}}}
.glow{{filter:drop-shadow(0 0 14px {a.line}) drop-shadow(0 0 4px {a.line})}}
.tag{{position:absolute;top:28px;right:28px;background:rgba(0,0,0,.55);color:#fff;font-size:30px;font-weight:700;padding:8px 18px;border-radius:12px}}
{extra_css}
</style></head><body>{body}{ANIM_JS}</body></html>"""



ANIM_JS = """
<script>
(function(){
const cl=x=>Math.max(0,Math.min(1,x)), sp=x=>x<=0?0:x>=1?1:1-Math.exp(-6*x)*Math.cos(9*x);
document.querySelectorAll('.pill:not([data-fx])').forEach(el=>{el.dataset.fx='pop';el.dataset.at=el.dataset.at||'0.9';el.dataset.base='translateX(-50%)';});
document.querySelectorAll('.full:not([data-fx])').forEach(el=>{el.dataset.fx='zoom';});
document.querySelectorAll('svg.glow').forEach(el=>{if(!el.closest('[data-fx]')){el.dataset.fx='draw';el.dataset.at='0.2';}});
window.render=function(t){document.querySelectorAll('[data-fx]').forEach(el=>{
  const at=+(el.dataset.at||0), fx=el.dataset.fx, b=el.dataset.base||'', x=(t-at)/0.45;
  if(fx==='zoom'){el.style.transform=b+' scale('+(1+0.06*cl(t/3))+')';return;}
  if(fx==='punch'){el.style.transform='scale('+(1+0.12*sp((t-at)/0.35))+')';return;}
  if(fx==='draw'){el.querySelectorAll('path,circle,rect,line').forEach(s=>{const L=s.getTotalLength?s.getTotalLength():1000;s.style.strokeDasharray=L;s.style.strokeDashoffset=L*(1-cl((t-at)/1.2));});return;}
  el.style.opacity=cl(x*3);
  if(fx==='pop')el.style.transform=b+' scale('+(0.8+0.2*sp(x))+')';
  else if(fx==='rise')el.style.transform=b+' translateY('+((1-sp(x))*60)+'px)';
  else if(fx==='up')el.style.transform=b+' translateY('+((1-sp(x))*500)+'px)';
  else if(fx==='slide')el.style.transform=b+' translateX('+((1-sp(x))*-520)+'px)';
  else if(fx==='drop')el.style.transform=b+' translateY('+((1-sp(x))*-140)+'px) scale('+(1.2-0.2*sp(x))+')';
});};
window.render(99);
})();
</script>"""


def lineart_phone(color):
    return f"""<svg class="glow" width="300" height="520" viewBox="0 0 300 520" fill="none" stroke="{color}" stroke-width="7" stroke-linecap="round">
<rect x="20" y="10" width="260" height="500" rx="44"/><line x1="115" y1="40" x2="185" y2="40"/>
<rect x="60" y="120" width="180" height="46" rx="14"/><rect x="60" y="190" width="180" height="46" rx="14"/><rect x="60" y="260" width="120" height="46" rx="14"/>
<circle cx="150" cy="420" r="34"/></svg>"""


def style_html(name, a):
    hook, key, cap, capkey = a.hook, a.key, a.caption, a.capkey
    if name == "split":
        body = f"""<div class="waves" style="position:absolute;left:0;right:0;top:0;height:960px"></div>
<div data-fx="rise" data-at="0.1" style="position:absolute;top:150px;left:0;right:0;display:flex;justify-content:center">{lineart_phone(a.line)}</div>
<div data-fx="zoom" style="position:absolute;top:960px;left:0;right:0;bottom:0;background:url('frame.png') center 30%/cover"></div>
<div class="pill" style="top:925px">{mark(cap, capkey)}</div>"""
        return page(body, a)
    if name == "hook":
        body = f"""<div class="full"></div><div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.05),rgba(0,0,0,.45))"></div>
<div style="position:absolute;top:560px;left:60px;right:60px;text-align:center">
 <div data-fx="pop" data-at="0.1" style="display:inline-block;background:#111;color:#fff;border-radius:999px;font-size:40px;font-weight:600;padding:14px 34px;margin-bottom:26px">{esc(hook)}</div>
 <div data-fx="rise" data-at="0.6" style="font-size:150px;font-weight:900;line-height:1.02;text-shadow:0 6px 30px rgba(0,0,0,.5)"><span style="background:{a.hi};padding:0 22px;border-radius:12px">{esc(key)}</span></div></div>"""
        return page(body, a)
    if name == "pill":
        body = f"""<div class="full" data-fx="punch" data-at="1.2" style="transform-origin:50% 32%"></div>
<div class="pill" style="top:1250px;font-size:54px">{mark(cap, capkey)}</div>"""
        return page(body, a)
    if name == "circle":
        body = f"""<div class="waves"></div>
<div data-fx="pop" data-at="0.1" style="position:absolute;top:300px;left:90px;width:460px;height:460px;border-radius:50%;border:8px solid {a.accent};background:url('frame.png') center 25%/cover;box-shadow:0 0 50px {a.accent}66"></div>
<div style="position:absolute;top:880px;right:90px;left:90px;height:620px;border:3px solid {a.line};border-radius:28px;display:grid;grid-template-columns:1fr 1fr;gap:26px;padding:40px" class="glow">
 {''.join(f'<div data-fx="rise" data-at="{0.5+i*0.3:.2f}" style="border:3px solid {a.line};border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:38px;font-weight:700;color:#fff">{t}</div>' for i,t in enumerate(['טריגר','סינון','תשובה','דיווח']))}
</div><div class="pill" style="top:1600px">{mark(cap, capkey)}</div>"""
        return page(body, a)
    if name == "chat":
        body = f"""<div class="full"></div>
<div data-fx="slide" data-at="0.15" data-base="rotate(-6deg)" style="position:absolute;top:330px;left:70px;width:430px;height:780px;background:#0d0d14;border:10px solid #1d1d28;border-radius:62px;transform:rotate(-6deg);box-shadow:0 30px 70px rgba(0,0,0,.6);padding:90px 28px 28px">
 <div data-fx="pop" data-at="0.9" style="background:{a.accent};color:#fff;font-size:30px;font-weight:600;padding:18px 22px;border-radius:24px 24px 6px 24px;margin-bottom:22px;margin-right:40px">{esc(hook)}</div>
 <div data-fx="pop" data-at="1.7" style="background:#26263a;color:#e9e7ff;font-size:28px;padding:18px 22px;border-radius:24px 24px 24px 6px;margin-left:30px;line-height:1.45">רגע לפני שאני בונה, מה צריך לקרות כשמישהו ממלא את הטופס?</div>
 <div style="position:absolute;bottom:40px;left:28px;right:28px;height:64px;border-radius:32px;background:#1a1a26;border:2px solid #333"></div></div>
<div class="pill" style="top:1320px">{mark(cap, capkey)}</div>"""
        return page(body, a)
    if name == "magazine":
        body = f"""<div class="full" style="filter:brightness(.72) sepia(.15)"></div>
<div data-fx="drop" data-at="0.2" style="position:absolute;top:150px;left:0;right:0;text-align:center;font-family:Georgia,'Times New Roman',serif;font-size:250px;letter-spacing:6px;color:#fff;line-height:1">{esc(a.mag)}</div>
<div style="position:absolute;top:120px;right:60px;font-size:30px;font-weight:600;color:#fff">גיליון 07 · 2026</div>{"<img src='person.png' style='position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness(.95)' data-fx='zoom'>" if a.has_person else ""}
<div data-fx="rise" data-at="1.0" style="position:absolute;top:1180px;right:70px;width:430px;font-size:54px;font-weight:800;line-height:1.15;color:#fff">{esc(hook)}</div>
<div style="position:absolute;bottom:170px;left:70px;width:170px;height:90px;background:repeating-linear-gradient(90deg,#fff 0 6px,transparent 6px 10px,#fff 10px 13px,transparent 13px 19px)"></div>"""
        return page(body, a)
    if name == "notes":
        notes = a.notes or ["חסך לי שעתיים ביום", "סוף סוף מישהו עונה מהר", "הלקוחות מקבלים תשובה תוך שניות", "למה לא עשיתי את זה קודם?", "פשוט עובד"]
        pos = [(70, 180, -6), (600, 150, 5), (60, 560, 4), (640, 560, -5), (360, 100, -2)]
        items = ''.join(f'<div data-fx="drop" data-at="{0.3+i*0.35:.2f}" data-base="rotate({r}deg)" style="position:absolute;left:{x}px;top:{y}px;width:380px;background:#f6efdc;color:#222;font-family:Amatic,Rubik;font-weight:700;font-size:54px;line-height:1.05;padding:26px 24px;transform:rotate({r}deg);box-shadow:0 10px 24px rgba(0,0,0,.45)"><div style="position:absolute;top:-16px;left:140px;width:100px;height:34px;background:rgba(255,255,255,.55)"></div>{esc(n)}</div>' for i, (n, (x, y, r)) in enumerate(zip(notes, pos)))
        body = f"""<div class="full" style="filter:brightness(.8)"></div>{items}"""
        return page(body, a)
    if name == "motion":
        body = f"""<div class="waves"></div>
<svg class="glow" style="position:absolute;top:330px;left:240px" width="600" height="600" viewBox="0 0 600 600" fill="none" stroke="{a.line}" stroke-width="6" stroke-linecap="round">
<circle cx="300" cy="300" r="250" stroke-dasharray="14 18"/><circle cx="300" cy="300" r="160"/><path d="M220 300h160M300 220v160"/>
<circle cx="300" cy="50" r="22" fill="{a.line}"/><circle cx="517" cy="425" r="22" fill="{a.line}"/><circle cx="83" cy="425" r="22" fill="{a.line}"/></svg>
<div data-fx="rise" data-at="0.7" style="position:absolute;top:1080px;left:60px;right:60px;text-align:center;font-size:118px;font-weight:900;line-height:1.05">{mark(hook, key, 'kk')}</div>
<div class="pill" style="top:1560px">{mark(cap, capkey)}</div>"""
        return page(body, a, f".kk{{color:{a.hi}}}")
    if name == "screen":
        shot = "url('screen.png') center top/cover" if a.has_screen else f"linear-gradient(180deg,#f4f4f8,#e6e6f0)"
        body = f"""<div style="position:absolute;inset:0;background:radial-gradient(circle at 80% 10%,{a.accent}55,transparent 45%),radial-gradient(circle at 10% 90%,{a.line}44,transparent 45%),{a.bg}"></div>
<div data-fx="rise" data-at="0.1" style="position:absolute;top:150px;left:60px;right:60px;text-align:center;font-size:84px;font-weight:900;line-height:1.1">{mark(hook, key, 'kk')}</div>
<div data-fx="up" data-at="0.4" style="position:absolute;top:520px;left:50px;right:50px;height:880px;border-radius:26px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.6);background:#fff">
 <div style="height:58px;background:#e9e9ef;display:flex;gap:12px;align-items:center;padding:0 24px;direction:ltr"><i style="width:18px;height:18px;border-radius:50%;background:#ff5f57"></i><i style="width:18px;height:18px;border-radius:50%;background:#febc2e"></i><i style="width:18px;height:18px;border-radius:50%;background:#28c840"></i></div>
 <div style="position:absolute;top:58px;left:0;right:0;bottom:0;background:{shot}"></div></div>
<div class="pill" style="top:1500px">{mark(cap, capkey)}</div>"""
        return page(body, a, f".kk{{color:{a.hi}}}")
    P = "<img src='person.png' style='position:absolute;inset:0;width:100%;height:100%;object-fit:cover' data-fx='zoom'>" if a.has_person else ""
    if name == "bigword":
        body = f"""<div class="full"></div>
<div data-fx="pop" data-at="0.3" style="position:absolute;top:1080px;left:40px;right:40px;text-align:center;font-size:170px;font-weight:900;color:#fff;text-shadow:0 8px 0 rgba(0,0,0,.35),0 0 40px rgba(0,0,0,.6)">{mark(a.key, a.key, 'kk')}</div>"""
        return page(body, a, f".kk{{color:{a.hi}}}")
    if name == "behind":
        body = f"""<div class="full"></div>
<div data-fx="rise" data-at="0.2" style="position:absolute;top:200px;left:30px;right:30px;text-align:center;font-size:{min(170, int(2600/max(8,len(a.hook))))}px;font-weight:900;line-height:1;color:#fff;text-shadow:0 10px 40px rgba(0,0,0,.35)">{mark(a.hook, a.key, 'kk')}</div>{P}
<div class="pill" style="top:1320px">{mark(cap, capkey)}</div>"""
        return page(body, a, f".kk{{color:{a.hi}}}")
    if name == "bgswap":
        body = f"""<div class="waves"></div><div style="position:absolute;inset:0;background:radial-gradient(circle at 75% 20%,{a.accent}55,transparent 45%),radial-gradient(circle at 20% 80%,{a.line}55,transparent 50%)"></div>{P or '<div class="full" style="opacity:.25"></div>'}
<div class="pill" style="top:1320px">{mark(cap, capkey)}</div>"""
        return page(body, a)
    if name == "pip":
        shot = "url('screen.png') center top/cover" if a.has_screen else "linear-gradient(180deg,#fafafa,#e9e9f0)"
        head = (f"<div data-fx='pop' data-at='0.5' style=\"position:absolute;bottom:120px;right:40px;width:430px;height:600px;background:url('person.png') center 20%/cover\"></div>" if a.has_person
                else f"<div data-fx='pop' data-at='0.5' style=\"position:absolute;bottom:160px;right:60px;width:380px;height:380px;border-radius:50%;border:8px solid #fff;background:url('frame.png') center 25%/cover\"></div>")
        body = f"""<div style="position:absolute;inset:0;background:{shot}"></div>{head}
<div data-fx="pop" data-at="0.9" style="position:absolute;top:1020px;left:60px;right:60px;text-align:center;font-size:120px;font-weight:900;color:#fff;text-shadow:0 6px 0 rgba(0,0,0,.4),0 0 30px rgba(0,0,0,.6)">{mark(a.key, a.key, 'kk')}</div>"""
        return page(body, a, f".kk{{color:{a.hi}}}")
    if name == "cinematic":
        tiles = ''.join(f'<div data-fx="pop" data-at="{0.4+i*0.12:.2f}" style="display:flex;flex-direction:column;align-items:center;gap:10px;font-size:24px;color:#cfc8d8"><b style="width:120px;height:120px;border-radius:28px;display:grid;place-items:center;font-size:56px;background:{c};{"outline:5px solid #E5322D" if i==3 else ""}">{ic}</b>{nm}</div>' for i,(nm,ic,c) in enumerate([("HyperFrames","H","#3a2a5a"),("Playwright","P","#1f4a2a"),("ffmpeg","F","#145a32"),("Claude Code","✳","#c2562c"),("Whisper","W","#333"),("Make","M","#5a2a6a")]))
        body = f"""<div style="position:absolute;inset:0;background:radial-gradient(ellipse 90% 40% at 50% 100%,rgba(229,50,45,.45),transparent 70%),#0A0607"></div>
<div data-fx="rise" data-at="0.1" style="position:absolute;top:420px;left:90px;right:90px;padding:40px 30px;border-radius:40px;background:rgba(20,16,24,.92);border:2px solid #2a2230;display:grid;grid-template-columns:repeat(3,1fr);gap:30px"><h3 style="grid-column:1/-1;text-align:center;font-size:54px;font-weight:900">ארגז הכלים</h3>{tiles}</div>
<div data-fx="drop" data-at="1.6" data-base="rotate(-8deg)" style="position:absolute;top:1150px;left:280px;border:8px solid #E5322D;color:#E5322D;font-weight:900;font-size:80px;padding:4px 34px;border-radius:14px;transform:rotate(-8deg)">בלי פרימייר</div>
<div data-fx="pop" data-at="0.9" data-base="translateX(-50%)" style="position:absolute;top:1500px;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:78px;font-weight:900;color:#fff;text-shadow:0 6px 0 rgba(0,0,0,.35)">{mark(cap, capkey, 'kr')}</div>"""
        return page(body, a, ".kr{color:#E5322D}")
    if name == "docu":
        body = f"""<div style="position:absolute;inset:0;background:radial-gradient(ellipse 80% 50% at 50% 40%,rgba(224,122,63,.22),transparent 70%),#17110D"></div>
<div style="position:absolute;top:420px;left:120px;right:120px;height:820px;display:flex;align-items:flex-end;justify-content:center;gap:90px">
 <div style="display:flex;flex-direction:column;align-items:center;width:260px"><div style="font-size:40px;font-weight:800;margin-bottom:12px">120 דק'</div><div style="width:110px;height:110px;border-radius:26px;background:#fff;color:#111;display:grid;place-items:center;font-size:52px;margin-bottom:14px">✋</div><div data-fx="up" data-at="0.2" style="width:100%;height:560px;background:linear-gradient(90deg,#c9c9cf,#8e8e96);border-radius:10px 10px 0 0"></div><div style="font-size:40px;margin-top:16px">ידני</div></div>
 <div style="display:flex;flex-direction:column;align-items:center;width:260px"><div data-fx="pop" data-at="1.3" style="font-size:80px">👑</div><div style="font-size:40px;font-weight:800;margin-bottom:12px">4 דק'</div><div style="width:110px;height:110px;border-radius:26px;background:#fff;color:#111;display:grid;place-items:center;font-size:52px;margin-bottom:14px">⚡</div><div data-fx="up" data-at="0.4" style="width:100%;height:60px;background:linear-gradient(90deg,#ff8a50,#c24e1c);border-radius:10px 10px 0 0"></div><div style="font-size:40px;margin-top:16px">אוטומטי</div></div></div>
<div data-fx="slide" data-at="0.8" style="position:absolute;bottom:420px;right:70px;display:flex;flex-direction:column;align-items:flex-end;gap:8px"><b style="background:#111;color:#fff;font-size:50px;font-weight:900;padding:8px 26px;border-right:10px solid #E07A3F">השם שלך</b><span style="background:rgba(0,0,0,.6);color:#ddd;font-size:34px;padding:6px 22px">התפקיד שלך</span></div>"""
        return page(body, a)
    if name == "quotecard":
        body = f"""<div class="full"></div>
<div data-fx="pop" data-at="0.1" style="position:absolute;top:230px;left:110px;right:110px;background:#fff;color:#111;border-radius:30px;padding:34px 40px;font-size:62px;font-weight:900;line-height:1.25;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,.35)">{mark(a.hook, a.key, 'kq')}</div>
<div data-fx="pop" data-at="0.6" style="position:absolute;top:700px;left:760px;font-size:150px">🥊</div>"""
        return page(body, a, ".kq{color:#d1245f}")
    raise SystemExit(f"unknown style {name}")


def board_html(styles, a):
    media = (lambda s: f'<video src="{s}.mp4" poster="{s}.png" autoplay loop muted playsinline></video>' if getattr(a, "animate", False) else f'<img src="{s}.png" alt="">')
    cards = ''.join(f"""<figure><div class="n">{i}</div>{media(s)}<figcaption><b>{esc(STYLE_INFO[s][0])}</b><span>{esc(STYLE_INFO[s][1])}</span></figcaption></figure>""" for i, s in enumerate(styles, 1))
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>לוח סגנונות</title><style>
{font_css()}
body{{margin:0;background:#0f0d22;color:#fff;font-family:Rubik,sans-serif;padding:40px}}
h1{{font-size:34px;margin:0 0 6px}} p.s{{color:#b9b4dd;margin:0 0 30px;font-size:18px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:26px}}
figure{{margin:0;background:#1b1838;border-radius:18px;overflow:hidden;position:relative}}
figure img,figure video{{width:100%;display:block;aspect-ratio:9/16;object-fit:cover}}
.n{{position:absolute;top:10px;right:10px;width:40px;height:40px;border-radius:50%;background:#FF6B2C;color:#111;font-weight:800;display:grid;place-items:center;font-size:20px}}
figcaption{{padding:14px 16px 18px;display:grid;gap:6px}} figcaption b{{font-size:18px}} figcaption span{{font-size:15px;color:#c9c5ea;line-height:1.5}}
</style></head><body><h1>איך הסרטון שלך ייראה, בכל סגנון</h1><p class="s">פריים אמיתי מהסרטון, עם העיצוב של כל סגנון. בחר מספר (אפשר גם לשלב: פתיח מסגנון אחד וגוף מסגנון אחר).</p><div class="g">{cards}</div></body></html>"""


def scenes_board(a):
    """לוח של שילובים: כל scenes.json מרונדר כקליפ של --secs שניות ממנוע הסצנות (reel.html)"""
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    files = [Path(x.strip()).resolve() for x in a.scenes.split(",") if x.strip()]
    labels = [x.strip() for x in (a.labels or "").split(",")] if a.labels else [f.stem for f in files]
    reel = HERE / "scenes" / "reel.html"
    from playwright.sync_api import sync_playwright
    cards = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for i, f in enumerate(files):
            data = json.loads(f.read_text(encoding="utf-8"))
            # תמונות יחסיות נפתרות מול תיקיית ה-json
            for sc in data.get("scenes", []):
                for k in ("img",):
                    v = sc.get(k)
                    if isinstance(v, str) and not v.startswith(("file:", "http")): sc[k] = (f.parent / v).resolve().as_uri()
                    if isinstance(v, list): sc[k] = [x if x.startswith(("file:", "http")) else (f.parent / x).resolve().as_uri() for x in v]
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.add_init_script("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";")
            pg.goto(reel.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
            dur = pg.evaluate("window.CONFIG.DUR"); secs = min(a.secs if a.secs != 3.0 else 4.0, dur)
            name = f"combo{i + 1}"
            ff = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-y", "-f", "image2pipe", "-framerate", "24", "-c:v", "png", "-i", "-",
                                   "-vf", "scale=540:960", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", "-preset", "veryfast",
                                   "-movflags", "+faststart", str(out / f"{name}.mp4")], stdin=subprocess.PIPE)
            for k in range(int(secs * 24)):
                pg.evaluate(f"window.render({k / 24:.4f})"); ff.stdin.write(pg.screenshot(type="png"))
            ff.stdin.close(); ff.wait()
            pg.evaluate(f"window.render({min(dur - 0.2, secs * 0.6):.3f})"); pg.screenshot(path=str(out / f"{name}.png"))
            pg.close()
            desc = data.get("desc") or f"{len(data.get('scenes', []))} סצנות · {dur:.0f} שניות · {data.get('theme', 'brand')}"
            cards.append((name, labels[i] if i < len(labels) else f.stem, desc))
        page_html = f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>לוח שילובים</title><style>
{font_css()}
body{{margin:0;background:#0f0d22;color:#fff;font-family:Rubik,sans-serif;padding:40px}}
h1{{font-size:34px;margin:0 0 6px}} p.s{{color:#b9b4dd;margin:0 0 30px;font-size:18px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:26px}}
figure{{margin:0;background:#1b1838;border-radius:18px;overflow:hidden;position:relative}}
figure img,figure video{{width:100%;display:block;aspect-ratio:9/16;object-fit:cover}}
.n{{position:absolute;top:10px;right:10px;width:40px;height:40px;border-radius:50%;background:#FF6B2C;color:#111;font-weight:800;display:grid;place-items:center;font-size:20px}}
figcaption{{padding:14px 16px 18px;display:grid;gap:6px}} figcaption b{{font-size:19px}} figcaption span{{font-size:15px;color:#c9c5ea;line-height:1.5}}
</style></head><body><h1>השילובים לסרטון שלך</h1><p class="s">כל קליפ הוא {secs:.0f} השניות הראשונות של הסרטון האמיתי בשילוב הזה. בחר מספר.</p><div class="g">
{''.join(f'<figure><div class="n">{i + 1}</div><video src="{n}.mp4" poster="{n}.png" autoplay loop muted playsinline></video><figcaption><b>{esc(l)}</b><span>{esc(d)}</span></figcaption></figure>' for i, (n, l, d) in enumerate(cards))}
</div></body></html>"""
        (out / "board.html").write_text(page_html, encoding="utf-8")
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        pg.goto((out / "board.html").as_uri()); pg.evaluate("document.fonts.ready")
        pg.evaluate("document.querySelectorAll('video').forEach(v => { v.removeAttribute('src'); v.load(); })"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(out / "board.jpg"), full_page=True, type="jpeg", quality=80)
        b.close()
    print("board:", out / "board.html"); print("sheet:", out / "board.jpg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video"); ap.add_argument("--frame"); ap.add_argument("--at", type=float)
    ap.add_argument("--screen", help="צילום מסך לסגנון screen")
    ap.add_argument("--out", default="board")
    ap.add_argument("--scenes", help="מצב ב: רשימת קבצי scenes.json מופרדת בפסיקים (שילוב אחד לכל קובץ). מציג כל שילוב כקליפ אמיתי ממנוע הסצנות")
    ap.add_argument("--labels", help="שמות לשילובים, מופרדים בפסיקים")
    ap.add_argument("--animate", action="store_true", help="קליפ של 3 שניות לכל סגנון (board.html מנגן אותם)")
    ap.add_argument("--secs", type=float, default=3.0)
    ap.add_argument("--styles", default="split,hook,pill,behind,bigword,pip,quotecard,motion,cinematic")
    ap.add_argument("--hook", default="ה-AI שבונה לפני שהוא מבין"); ap.add_argument("--key", default="מבין")
    ap.add_argument("--caption", default="הבעיה היא לא הקוד, היא ההתחלה"); ap.add_argument("--capkey", default="ההתחלה")
    ap.add_argument("--mag", default="BUILD"); ap.add_argument("--notes", help="JSON list of real comments")
    ap.add_argument("--bg", default="#0E0B26"); ap.add_argument("--accent", default="#FF6B2C")
    ap.add_argument("--hi", default="#E5322D"); ap.add_argument("--line", default="#8C7CFF")
    a = ap.parse_args()
    a.notes = json.loads(a.notes) if a.notes else None
    if a.scenes:
        return scenes_board(a)
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    fr = out / "frame.png"
    if a.video: grab_frame(a.video, fr, a.at)
    elif a.frame: shutil.copy(a.frame, fr)
    else:
        fr.write_bytes(b"")
    a.has_screen = bool(a.screen)
    if a.screen: shutil.copy(a.screen, out / "screen.png")
    styles = [s.strip() for s in a.styles.split(",") if s.strip()]
    a.has_person = False
    if any(x in styles for x in ("behind", "bgswap", "pip", "magazine")) and fr.exists() and fr.stat().st_size:
        try:
            subprocess.run(["npx", "-y", "hyperframes", "remove-background", str(fr), "-o", str(out / "person.png")],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
            a.has_person = (out / "person.png").exists()
        except Exception as e:
            print("הפרדת אדם לא עבדה (HyperFrames?):", e)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for s in styles:
            f = out / f"_{s}.html"; f.write_text(style_html(s, a), encoding="utf-8")
            pg.goto(f.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(250)
            pg.screenshot(path=str(out / f"{s}.png"))
            if a.animate:
                ff = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-y", "-f", "image2pipe", "-framerate", "24", "-c:v", "png", "-i", "-",
                                       "-vf", "scale=540:960", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", "-preset", "veryfast",
                                       "-movflags", "+faststart", str(out / f"{s}.mp4")], stdin=subprocess.PIPE)
                for k in range(int(a.secs * 24)):
                    pg.evaluate(f"window.render({k / 24:.4f})")
                    ff.stdin.write(pg.screenshot(type="png"))
                ff.stdin.close(); ff.wait()
                pg.evaluate("window.render(99)")
            f.unlink()
        (out / "board.html").write_text(board_html(styles, a), encoding="utf-8")
        pg.set_viewport_size({"width": 1400, "height": 900})
        pg.goto((out / "board.html").as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(out / "board.jpg"), full_page=True, type="jpeg", quality=80)
        b.close()
    print("board:", (out / "board.html").resolve())
    print("sheet:", (out / "board.jpg").resolve())


if __name__ == "__main__":
    main()
