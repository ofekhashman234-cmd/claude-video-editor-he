#!/usr/bin/env bash
# העורך (video-editor skill) - התקנה חד־פעמית. רץ על macOS. בטוח להריץ שוב.
# יוצר סביבת Python אחת ב-~/.video-editor/venv, מתקין את הכלים, מוריד דפדפן לרינדור ו-ffmpeg/ffprobe.
set -euo pipefail

VENV="$HOME/.video-editor/venv"
BIN="$HOME/.local/bin"

say() { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }

say "בודק Python (צריך 3.9 ומעלה)"
PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "לא נמצא python3. במק: הריצו xcode-select --install (או התקינו מ-python.org) והריצו שוב."; exit 1
fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 9), sys.version' || { echo "צריך Python 3.9 ומעלה"; exit 1; }

if [ ! -x "$VENV/bin/python" ]; then
  say "יוצר סביבה נפרדת ב-$VENV"
  mkdir -p "$(dirname "$VENV")"
  "$PYTHON" -m venv "$VENV"
fi
PY="$VENV/bin/python"

say "מתקין ספריות (playwright, numpy, pillow, faster-whisper, yt-dlp, ffmpeg)"
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q playwright numpy pillow imageio-ffmpeg faster-whisper yt-dlp static-ffmpeg

say "מוריד את הדפדפן שמצלם את הפריימים (Chromium, כ-150MB)"
"$PY" -m playwright install chromium

say "מכין ffmpeg ו-ffprobe"
FFDIR="$("$PY" -c 'import static_ffmpeg.run as r, os; ff, fp = r.get_or_fetch_platform_executables_else_raise(); print(os.path.dirname(ff))')"
mkdir -p "$BIN"
ln -sf "$FFDIR/ffmpeg" "$BIN/ffmpeg"
ln -sf "$FFDIR/ffprobe" "$BIN/ffprobe"

say "בדיקה"
"$BIN/ffmpeg" -version | head -1
"$BIN/ffprobe" -version | head -1
"$PY" -c 'import playwright, faster_whisper, numpy, PIL; print("ספריות: תקין")'

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo
     echo "⚠️  $BIN לא נמצא ב-PATH. הוסיפו את השורה הבאה לקובץ ~/.zshrc ופתחו טרמינל חדש:"
     echo "    export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

cat <<'MSG'

✅ העורך מוכן.
   מודל התמלול לעברית (כ-1.6GB) יורד אוטומטית בפעם הראשונה שתתמללו סרטון.

אופציונלי, לאפקטים שמפרידים אתכם מהרקע (טקסט מאחורי הראש, מגזין, החלפת רקע):
   claude plugin marketplace add heygen-com/hyperframes
   claude plugin install hyperframes@hyperframes

נסו עכשיו ב-Claude Code:  "תראה לי סגנונות עריכה"  או  "תעשה סרטון על ..."
MSG
