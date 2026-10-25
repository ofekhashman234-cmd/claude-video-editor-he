# העורך 🎬 · עורך וידאו בעברית ל-Claude Code

**ניתחתי 21 רילס של יוצרי ה-AI הכי גדולים בארץ. ואז לימדתי את Claude לערוך ככה.**
בהשראת עדן ביבס · איילון גרופר · בני פרבר · Brain ([CREDITS.md](CREDITS.md))

"העורך" הוא סקיל ל-Claude Code שהופך אותו לעורך רילס בעברית:

1. **מתמלל בעברית,** עם זמן לכל מילה (מודל של ivrit.ai, רץ אצלכם במחשב).
2. **מציע סגנונות עריכה,** מתוך 42 סגנונות ו-7 שילובים מוכנים.
3. **מראה לפני שהוא עורך:** לוח שבו כל סגנון מתנגן על פריים אמיתי מהסרטון שלכם.
4. **עורך ובודק את עצמו:**
   - חותך שתיקות
   - מוסיף כתוביות עם מילה צבועה, פתיח קינטי וזומים
   - מושן גרפיקס
   - טקסט מאחורי הראש (עם HyperFrames)
   - סאונד בעוצמה אחידה
   - ובסוף בודק את התוצאה פריים אחרי פריים

יש לו גם מצב **"מרעיון לסרטון":** אומרים לו נושא, והוא מציע פתיחים, כותב תסריט ובונה סרטון בלי פנים מסצנות מוכנות.

## התקנה (macOS)

```bash
git clone https://github.com/ofekhashman234-cmd/claude-video-editor-he.git ~/.claude/skills/video-editor
bash ~/.claude/skills/video-editor/setup.sh
```

**בדוק:** פתחו את Claude Code וכתבו `תראה לי סגנונות עריכה`. העורך יציע סגנונות ויבנה לוח.

**אופציונלי, לאפקטים שמפרידים אתכם מהרקע:**
```bash
claude plugin marketplace add heygen-com/hyperframes
claude plugin install hyperframes@hyperframes
```

## מה צריך
- Claude Code עם מנוי בתשלום (מומלץ Opus).
- macOS. נבדק על Apple Silicon.
- כ-2GB הורדות בפעם הראשונה: Chromium, מודל תמלול לעברית, ומודל הפרדת אדם אם מתקינים HyperFrames.

## מה יש בפנים
| | |
|---|---|
| `SKILL.md` | ה"מוח" של העורך: איך הוא עובד, שלב אחרי שלב |
| `assets/board.py` | לוח הסגנונות הוויזואלי והמונפש |
| `assets/compose.py` | הרכבה: חיתוך, זום, שכבות HTML, טקסט מאחורי האדם, סאונד |
| `assets/transcribe.py` | תמלול עברית עם זמן לכל מילה |
| `assets/scenes/reel.html` | מנוע סצנות: סרטון שלם מקובץ JSON. 19 סוגי סצנות, 4 ערכות צבע |
| `references/` | תפריט הסגנונות, ספריית הסצנות, ניתוח הרילס, והצנרת הטכנית |

נבנה על ידי **אופק חשמן**, אוטומציות לעסקים.

---

### English
**"HaOrech" (The Editor)** is a Claude Code skill that turns Claude into a Hebrew-first short-form video editor. It transcribes Hebrew locally, proposes editing styles from a catalog of 42 styles and 7 recipes, and **shows each style animated on a real frame of your footage before editing**. Then it cuts, captions, adds motion graphics, puts text behind you (via HyperFrames), and self-checks the result frame by frame. It was inspired by a frame-level study of 21 reels by top Israeli AI creators (see CREDITS.md).
Install: clone into `~/.claude/skills/video-editor` and run `setup.sh`. MIT licensed, fonts under OFL.
