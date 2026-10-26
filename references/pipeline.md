# הצנרת הטכנית: מה מותקן, איפה, ואיך מריצים

נבדק על macOS (Apple Silicon), אוקטובר 2026.

## כלים ונתיבים
| כלי | איפה | הערה |
|---|---|---|
| Python של הסקילים | `~/.video-editor/venv/bin/python` (להלן `$PY`) | Python 3.14. כל ההתקנות רק בתוכו (`"$PY" -m pip`) |
| ffmpeg / ffprobe | `ffmpeg` ב-PATH (setup.sh מקשר את הבינארים של static-ffmpeg ל-`~/.local/bin`; ). גיבוי: imageio-ffmpeg | בלי Homebrew. HyperFrames צריך את שניהם ב-PATH |
| Chromium לרינדור | מטמון Playwright (`~/Library/Caches/ms-playwright`) | מופעל דרך `$PY` |
| yt-dlp | `~/.video-editor/venv/bin/yt-dlp` | עם `--ffmpeg-location "$FF"` |
| תמלול עברית | faster-whisper + `ivrit-ai/whisper-large-v3-turbo-ct2` | רץ מקומית. 20 שניות של דיבור לוקחות כ-10 שניות. ה-av של faster-whisper לא תואם, ולכן `transcribe.py` מפענח עם ffmpeg |
| HyperFrames | **מותקן** (פלאגין `hyperframes@hyperframes` 0.8.197, 25.10.2026) | `npx -y hyperframes doctor` עובר. ffmpeg/ffprobe 7.0 מ-`static-ffmpeg` (בתוך ה-venv), מקושרים ל-`~/.bun/bin` שנמצא ב-PATH. הפרדת אדם: `npx -y hyperframes remove-background in.mp4 -o person.webm` (או png), כ-0.1 שנייה לפריים על CoreML. בהרצה הראשונה הורד מודל של 168MB |

**HyperFrames הותקן (לתיעוד, אם צריך שוב):**
```
claude plugin marketplace add heygen-com/hyperframes
claude plugin install hyperframes@hyperframes
```
דורש Node 22 ומעלה (יש 24) ו-ffmpeg במערכת. בלי Homebrew, ה-CLI של HyperFrames עלול לא למצוא ffmpeg: לבדוק `npx hyperframes doctor` (אם קיים) ולהפנות אותו לנתיב של imageio-ffmpeg, או לקשר אותו לתיקייה שנמצאת ב-PATH.

## הכלים של הסקיל (`<SKILL>/assets/`)

### 1. `board.py`: לוח סגנונות ויזואלי
```
"$PY" board.py --video video.mp4 --out board/ --hook "<משפט פתיחה>" --key "<מילת מפתח>" \
   --caption "<משפט מהסרטון>" --capkey "<מילה>" --styles split,hook,pill,circle,chat,motion,screen,magazine,notes \
   [--at 4.2] [--frame img.png] [--screen screenshot.png] [--bg #110E2B --accent #FF6B2C --hi #FF6B2C --line #8C7CFF]
```
מוציא תמונה לכל סגנון, `board.html` ו-`board.jpg`. מראים למשתמש את `board.jpg` (Read), ומציעים לפתוח את `board.html`.
הסגנונות בלוח: split, hook, pill, circle, chat, motion, screen, magazine, notes. בסרטון בלי פנים: `--frame` עם צילום מסך, ומתמקדים ב-motion ו-screen.

### 2. `transcribe.py`: תמלול עם זמן לכל מילה
```
"$PY" transcribe.py video.mp4 --out words.json      # וגם transcript.txt, ורשימה של מילים לא בטוחות
```
**חובה:** מראים למשתמש את transcript.txt ואת המילים הלא בטוחות לפני כתוביות, ומתקנים ב-words.json. קוראים כל משפט שלם ומתקנים מילים דומות (למשל "על פיות" במקום "אלפיות"). מונחים באנגלית (Claude, GPT) נשארים באנגלית.

### 3. `compose.py`: הרכבה על צילום אמיתי
```
"$PY" compose.py --video video.mp4 --overlay <SKILL>/assets/overlays/captions.html --data data.json \
   [--keep "0.00-3.40,3.95-9.10"] [--zooms "3.57-4.52:0.12"] [--preview | --t0 S --t1 E] --out out/final.mp4
```
- `--keep`: הקטעים שנשארים אחרי טבלת החיתוכים. הזמנים של words.json צריכים להיות מחושבים מחדש לציר החתוך (מחסירים את מה שנחתך לפני כל מילה; לא מתמללים מחדש).
- `--zooms`: זום של 10 עד 15 אחוז, ממורכז על הפנים (`--focus-y`, ברירת מחדל 0.33), על המילה החשובה. לכל היותר מילה אחת למשפט. **לא** על הקלטות של Screen Studio, שכבר יש בהן זומים.
- `--preview`: 540x960, 15 שניות. כך מאשרים סגנון לפני רינדור מלא.
- קול: highpass ב-70Hz ו-loudnorm ל-‎-14 LUFS (אפשר לבטל עם `--no-loudnorm`).
- רינדור: כ-12 שניות לטיוטה של 10 שניות. מלא ב-1080x1920 לוקח בערך פי 3.

### 4. `overlays/captions.html`: כתוביות + פתיח קינטי
DATA:
```json
{"words":[...], "keywords":["שיטה","אחת"],
 "style":{"hi":"#FF6B2C","y":1180,"size":58,"maxWords":4},
 "hook":{"small":"תפסיקו לכתוב פרומפטים","big":"ותתחילו לכתוב לופים","key":"לופים","s":0,"e":2.98},
 "hide":[[12.0,15.5]]}
```
- כתובית: גלולה לבנה, 2 עד 4 מילים, מילת מפתח בצבע, קפיצה קטנה בכניסה. y=1180 בפנים במסך מלא. במסך מפוצל: y≈925 (על הקו).
- `hide`: טווחים שבהם יש מושן במסך מלא וכתוביות מפריעות.
- overlay חדש (כרטיסים, אייקונים, מסך מפוצל): דף HTML עם `window.render(t)`, רקע שקוף, 1080x1920, כל מצב מחושב מ-t (בלי טיימרים ובלי CSS transitions). מעתיקים את captions.html כבסיס.

### 5. מושן גרפיקס מאפס (בלי צילום)
הסקיל **motion-studio** (של איילון גרופר, חינמי, אופציונלי; מתקינים בנפרד מ-eilon.co/claude-motion-graphics-prompts): 10 סגנונות אנימציה, עברית RTL, רינדור עם motion blur. משתמשים בו לסצנות של "מושן מלא", לפתיחים ולבירולים מונפשים. אחר כך מחברים לסרטון: כקטע בין חיתוכים (concat), או כחצי עליון במסך מפוצל (`overlay` של קטע מושן 1080x960 מעל הצילום).

### 6. ניתוח והורדה
- **video-analysis** (מותקן): פריימים, כתוביות צרובות, ניתוח סגנון. גיליון מהיר: `"$FF" -i v.mp4 -vf "fps=1,scale=216:-2,tile=8x4:padding=4:color=white" -frames:v 1 sheet.jpg`.
- **video-download** (מותקן): yt-dlp להורדת רפרנסים, לשימוש אישי ולמחקר בלבד.


### 7. סרטון בלי פנים, מושן בלבד (נבדק ב-25.10.2026, רילס 1)
```
"$PY" compose.py --duration 20 --overlay scene.html [--audio voice.m4a] --preview --out out/preview.mp4
```
בלי `--video`: רקע בצבע `--bg` באורך `--duration`, והסצנה (HTML עם `window.render(t)`) מכסה את כל הפריים. דוגמה מלאה, עם פתיח קינטי, לפני ואחרי בצ'אט, תרשים של 4 שלבים, המדריך בתוך טלפון ו"כתבו סקיל": `assets/examples/faceless-reel.html`. רינדור: כ-45 שניות לטיוטה של 20 שניות, ובערך דקה לגרסה המלאה ב-1080x1920.


### 8. שכבה מאחורי האדם (נבדק 25.10.2026)
```
"$PY" compose.py --video v.mp4 --behind <SKILL>/assets/overlays/behind.html --behind-data behind.json [--overlay captions.html --data data.json] --out out/x.mp4
```
סדר השכבות: צילום ← behind (טקסט, מגזין, פתקים, לוגואים) ← האדם (הפרדה אוטומטית) ← overlay (כתוביות). רינדור של 2 שניות, עם הפרדה מוכנה, לוקח כ-5 שניות. הפרדה של 2 שניות לוקחת כ-15 שניות. מפרידים רק את הטווח שצריך (`--t0/--t1`).
**board.py** מפריד את הפריים לבד (person.png) לסגנונות behind, magazine, bgswap ו-pip, כך שהתצוגה המקדימה מראה הסתרה אמיתית.

### מלכודות שנתפסו בניסוי
- **הזזה אופקית ב-RTL:** אלמנט שיוצא מהפריים משמאל (כתם אור, glow) מגדיל את רוחב הדף, והצילום כולו זז ימינה. **חובה** `body{position:relative;contain:paint;width:1080px;height:1920px}` בכל סצנה. בודקים: `document.documentElement.scrollWidth` חייב להיות 1080.
- **כותרת ענק:** מילה קצרה שנופלת לבד לשורה ("לך") נראית שבורה. מקטינים את הפונט (118px לשלוש מילים בשורה) או שוברים שורה ידנית.
- **מגלה העיצוב של impeccable** יתריע על glow בסצנות וידאו. זה מכוון (סגנון קווי הניאון מהמחקר), אז מוסיפים את הקובץ ל-ignore.
- **הדגמה ולא הקלטה:** צ'אט מונפש שמראה איך כלי מתנהג הוא המחשה. אומרים את זה למשתמש, ומציעים להחליף בהקלטת מסך אמיתית כשיש.

## בדיקות לפני שמראים (חובה)
1. גיליון פריימים מכל הטיוטה (fps=2), ובנוסף פריים בכל כניסה של טקסט, אפקט וחיתוך. מסתכלים על כל אחד.
2. בודקים: אין טקסט חתוך, כתובית לא על הפה ולא על הפנים, עברית מימין לשמאל, מילה באנגלית לא הפוכה, כל אפקט נעלם כשהזמן שלו נגמר, אין פריים בלי כתובית באמצע משפט.
3. בפרויקט עם אפקטים: מבקר עצמאי (סוכן נפרד, בלי ההסברים של מי שבנה) שנותן ציון מ-100. מתקנים עד 90 ומעלה. אם אחרי שני סבבים הציון מתחת ל-70, עוצרים ומביאים למשתמש את הפער (CREDITS.md (Eilon), פרומפט 21).

## תקלה ידועה: חור בציר הזמן (פריימים נעלמים)
כרום שומר פריים אטום לגמרי (רקע נייר / משבצות) כ-PNG בלי שקיפות. הפורמט מתחלף באמצע, ffmpeg 7.1 בונה מחדש את הגרף ומאבד עשרות פריימים, והשכבות נראות "קודמות" לזמן. מתוקן ב-`render_html` (פיקסל שקוף אחד בפינה). `compose.py` סופר בסוף את הפריימים ומזהיר אם חסרים. לא להשתמש ב-`-reinit_filter 0`: זה קורא RGB כאילו הוא RGBA, והתמונה יוצאת מפוספסת.
