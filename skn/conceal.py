"""Tracked confidentiality masking for the packaging clip.

Tracks the tabletop/box plane with SIFT + RANSAC homographies (re-anchored to the first
frame to avoid drift), carries hand-placed polygons over the product name, the manufacturer
wordmark and a third-party label, and blurs only inside those (feathered) polygons.

Usage: python -I conceal.py IN.mp4 OUT.mp4 [--debug DIR]
"""
import json, os, subprocess, sys
import cv2
import numpy as np

W, H = 1080, 1920

def rot_rect(p0, p1, half):
    """Rectangle around the segment p0->p1, `half` px either side."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = (p1 - p0) / np.linalg.norm(p1 - p0); n = np.array([-d[1], d[0]])
    e = d * 40   # extend past both ends
    return np.array([p0 - e + n * half, p1 + e + n * half, p1 + e - n * half, p0 - e - n * half], np.float32)

# polygons in frame-0 coordinates (1080x1920). Names intentionally not recorded here.
MASKS = {
    "product_name": (rot_rect((555, 1030), (850, 1400), 95), 61),
    "manufacturer_wordmark": (rot_rect((335, 662), (495, 812), 78), 45),
    "box_side_print": (rot_rect((8, 892), (98, 1048), 30), 21),
    "third_party_label": (np.array([[505, 420], [640, 420], [640, 535], [505, 535]], np.float32), 31),
}

def read_frames(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W, 3)

def track(frames):
    sift = cv2.SIFT_create(nfeatures=3000)
    bf = cv2.BFMatcher()
    s = 0.5   # track at half resolution
    def feats(img):
        g = cv2.cvtColor(cv2.resize(img, None, fx=s, fy=s), cv2.COLOR_BGR2GRAY)
        return sift.detectAndCompute(g, None)
    def homog(fa, fb):
        (ka, da), (kb, db) = fa, fb
        if da is None or db is None: return None, 0
        m = [x for x, y in bf.knnMatch(da, db, k=2) if x.distance < 0.75 * y.distance]
        if len(m) < 12: return None, len(m)
        A = np.float32([ka[x.queryIdx].pt for x in m]) / s
        B = np.float32([kb[x.trainIdx].pt for x in m]) / s
        Hm, inl = cv2.findHomography(A, B, cv2.RANSAC, 4.0)
        return Hm, int(inl.sum()) if inl is not None else 0
    f0 = feats(frames[0]); prev_f = f0
    Hs = [np.eye(3)]; prev_H = np.eye(3); stats = []
    for i in range(1, len(frames)):
        fi = feats(frames[i])
        Hd, nd = homog(f0, fi)                       # direct to frame 0 (no drift)
        Hc, nc = homog(prev_f, fi)                   # chained (robust when view changes a lot)
        chained = Hc @ prev_H if Hc is not None else None
        if Hd is not None and nd >= 40:
            Hcur = Hd; src = "direct"
        elif chained is not None:
            Hcur = chained; src = "chain"
        else:
            Hcur = prev_H; src = "hold"
        Hs.append(Hcur); prev_H = Hcur; prev_f = fi
        stats.append((i, src, nd, nc))
    return Hs, stats

def apply(frames, Hs, out_path, debug=None):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", "60", "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "fast",
                            "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)
    polys_log = []
    for i, (fr, Hm) in enumerate(zip(frames, Hs)):
        img = fr.copy()
        plog = {}
        for name, (poly, k) in MASKS.items():
            p = cv2.perspectiveTransform(poly[None], Hm)[0]
            plog[name] = p.round(1).tolist()
            # local zoom of the tracked plane at this polygon: blur scales with it
            c = poly.mean(0)
            q = cv2.perspectiveTransform(np.float32([[c, c + [1, 0], c + [0, 1]]]), Hm)[0]
            u, v = q[1] - q[0], q[2] - q[0]
            zoom = float(np.sqrt(abs(u[0] * v[1] - u[1] * v[0])))
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [p.astype(np.int32)], 255)
            m = cv2.dilate(m, np.ones((15, 15), np.uint8))
            mask = cv2.GaussianBlur(m, (0, 0), 9 * max(1.0, zoom)).astype(np.float32) / 255
            if mask.max() <= 0: continue
            x0, y0, w, h = cv2.boundingRect(p.astype(np.int32))
            pad = int(120 * max(1.0, zoom))
            x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
            x1, y1 = min(W, x0 + w + 2 * pad), min(H, y0 + h + 2 * pad)
            if x1 <= x0 or y1 <= y0: continue
            reg = img[y0:y1, x0:x1].astype(np.float32)
            blk = max(4, int(26 * zoom))
            small = cv2.resize(reg, (max(1, (x1 - x0) // blk), max(1, (y1 - y0) // blk)), interpolation=cv2.INTER_AREA)
            frost = cv2.GaussianBlur(cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR), (0, 0), 10 + 22 * zoom)
            mean = frost.reshape(-1, 3).mean(0)
            frost = mean + (frost - mean) * 0.45          # flatten what is left of the letter contrast
            mm = mask[y0:y1, x0:x1, None]
            img[y0:y1, x0:x1] = (reg * (1 - mm) + frost * mm).astype(np.uint8)
        polys_log.append(plog)
        enc.stdin.write(img.tobytes())
        if debug and i % 10 == 0:
            dbg = fr.copy()
            for p in plog.values():
                cv2.polylines(dbg, [np.array(p, np.int32)], True, (0, 0, 255), 4)
            cv2.imwrite(os.path.join(debug, f"dbg_{i:03d}.jpg"), cv2.resize(dbg, (270, 480)))
    enc.stdin.close(); enc.wait()
    return polys_log

if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    debug = sys.argv[sys.argv.index("--debug") + 1] if "--debug" in sys.argv else None
    if debug: os.makedirs(debug, exist_ok=True)
    frames = read_frames(src)
    Hs, stats = track(frames)
    holds = [s for s in stats if s[1] == "hold"]
    print(f"frames {len(frames)}  direct {sum(s[1]=='direct' for s in stats)}  chain {sum(s[1]=='chain' for s in stats)}  hold {len(holds)}")
    logs = apply(frames, Hs, out, debug)
    json.dump({"stats": stats, "polygons": logs}, open(out + ".track.json", "w"))
    print("done", out)
