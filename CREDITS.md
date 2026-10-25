# ממי למדנו

"העורך" נבנה בהשראת ניתוח של תוכן ציבורי של יוצרי ה-AI המובילים בישראל: 21 רילס, פריים אחרי פריים, ושני מדריכים חינמיים. אף אחד מהם לא היה מעורב בבניית הסקיל, והסקיל לא כולל תוכן שלהם. כאן יש רק הפניות. מומלץ ללמוד ישירות מהם:

| יוצר | מה למדנו | איפה |
|---|---|---|
| **עדן ביבס / Brain** | מסך מפוצל עם מושן על רקע כהה, כתובית בגלולה לבנה עם מילה צבועה, כרטיס ציטוט, כתבות מוטות. המדריכים "10 סגנונות עריכת וידאו שקלוד קוד יוצר" ו"עריכת וידאו עם קלוד קוד" | [instagram.com/eden_bibas](https://www.instagram.com/eden_bibas/) · [brainai.co.il/guides](https://brainai.co.il/guides/) |
| **איילון גרופר** | פתיח קינטי, החלפת פריסות כל כמה שניות, אפקטים בתלת ממד (לוגו על כף היד, טקסט על הקיר, שכבות), ובדיקה עצמית עם מבקר. המדריך "עריכת וידאו עם Claude" והסקילים החינמיים שלו | [instagram.com/eilon.grouper](https://www.instagram.com/eilon.grouper/) · [eilon.co/claude-video-editing-guide](https://eilon.co/claude-video-editing-guide/) |
| **בני פרבר** | מילים ענקיות בלי מסגרת, מסך מלא עם הראש בפינה, סגנון סינמטי שחור-אדום (ארגז כלים, טרמינל, טיימליין), סגנון "דוקו" עם עמודות | [instagram.com/bennyfarber](https://www.instagram.com/bennyfarber/) |

## כלים שהסקיל משתמש בהם
- [HyperFrames](https://github.com/heygen-com/hyperframes) של HeyGen (Apache 2.0): הפרדת אדם מהרקע. אופציונלי.
- [Playwright](https://playwright.dev), [ffmpeg](https://ffmpeg.org) (דרך [static-ffmpeg](https://pypi.org/project/static-ffmpeg/)), [faster-whisper](https://github.com/SYSTRAN/faster-whisper) עם המודל של [ivrit.ai](https://huggingface.co/ivrit-ai) לתמלול עברית, ו-[yt-dlp](https://github.com/yt-dlp/yt-dlp).
- פונטים: Rubik, Heebo ו-Amatic SC מ-Google Fonts, ברישיון SIL OFL (`assets/fonts/OFL.txt`).

הורדה של סרטונים של אחרים נועדה ללמידה ולמחקר בלבד. לא מעלים תוכן של אחרים בתור שלכם.
