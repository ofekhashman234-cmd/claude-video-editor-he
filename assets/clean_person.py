"""מנקה שאריות מעל הראש בשכבת האדם (עמוד חלון שנכנס להפרדה): בכל פריים מוצאים את השורה הראשונה מלמעלה
שבה הגוף רחב מ-190 פיקסלים (תחילת הראש), ומאפסים את השקיפות של כל מה שמעליה, פחות 30 פיקסלים לקודקוד."""
import subprocess, sys, numpy as np
FF, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
W, H = 1080, 1920
dec = subprocess.Popen([FF, "-v", "error", "-c:v", "libvpx-vp9", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "28", dst], stdin=subprocess.PIPE)
n = 0
while True:
    buf = dec.stdout.read(W * H * 4)
    if len(buf) < W * H * 4: break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 4).copy()
    a = f[:, :, 3] > 128
    widths = a.sum(1)
    rows = np.where(widths > 190)[0]
    if len(rows):
        top = max(0, rows[0] - 30)
        # מעל הקודקוד: משאירים רק פיקסלים בטווח הרוחב של הראש בשורה הראשונה הרחבה
        cols = np.where(a[rows[0]])[0]; c0, c1 = cols.min(), cols.max()
        f[:top, :, 3] = 0
        band = f[top:rows[0], :, 3]; band[:, :c0] = 0; band[:, c1 + 1:] = 0
    enc.stdin.write(f.tobytes()); n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print("cleaned", n, "frames ->", dst)
