# 講義と確認問題をMP3にする（バックグラウンド再生用）。Windowsの日本語音声＋ffmpeg
# 使い方: python tools/make_audio.py [sec ...]   （省略で全Section）
import json, re, os, sys, subprocess, random, glob, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
TMP = os.path.join(os.environ.get("TEMP", "."), "chinkan_audio"); os.makedirs(TMP, exist_ok=True)
FFMPEG = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))[0]
VOICE = "Microsoft Haruka"

def clean(t):  # アプリの TTS.clean と同じ読み替え
    t = str(t or "")
    t = t.replace("○", "マル").replace("×", "バツ")
    t = re.sub(r"(\d+)\s*/\s*(\d+)", r"\2分の\1", t)
    t = re.sub(r"㎡|m²", "平方メートル", t).replace("％", "パーセント").replace("%", "パーセント")
    t = re.sub(r"[〜～]", "から", t); t = re.sub(r"p\.(\d+)", r"\1ページ", t)
    t = re.sub(r"(?<![0-9０-９])年(?=[0-9０-９])", "ねん", t)  # 「年14.6パーセント」の年
    t = re.sub(r"[（(]", "、", t); t = re.sub(r"[）)]", "、", t); t = re.sub(r"[「」『』【】]", "", t)
    return t.replace("→", "、つまり、").replace("・", "、")

secs = [s for c in json.load(open(D("sections.json"), encoding="utf-8")) for s in c["secs"]]
title = {s[0]: s[1] for s in secs}
LEC = {}
for f in ["lec_1a", "lec_1b", "lec_2", "lec_3", "lec_4", "lec_5"]:
    LEC.update(json.load(open(D("data", f + ".json"), encoding="utf-8")))
files = ["A","B","C","D","E","X1","X2","X3","X4"] + [f"Y{i:02d}" for i in range(1, 12)]
Q = [q for f in files for q in json.load(open(D("data", f + ".json"), encoding="utf-8"))]

def lecture_parts(sid):
    L = LEC[sid]; P = [{"t": clean(f"Section {sid.replace('-', 'の')}、{title[sid]}。")}, {"b": 0.6}, {"t": clean(L["intro"])}, {"b": 0.9}]
    for i, p in enumerate(L["points"]):
        P += [{"t": clean(f"ポイント{i+1}。《{p['h']}》。")}, {"b": 0.4}, {"t": clean(p["t"])}, {"b": 0.9}]
    P += [{"t": "まとめです。"}, {"b": 0.4}, {"t": clean(L["summary"])}, {"b": 1.0}]
    return P

def quiz_ids(sid, n=5):  # Sectionごとに固定の5問（○×を混ぜる）
    qs = sorted([q for q in Q if q["sec"] == sid], key=lambda q: q["id"])
    rnd = random.Random(sid); rnd.shuffle(qs)
    o = [q for q in qs if q["a"]]; x = [q for q in qs if not q["a"]]
    pick = (o[:3] + x[:2]) if len(o) >= 3 and len(x) >= 2 else qs[:n]
    rnd.shuffle(pick); return pick[:n]

def quiz_parts(sid, think=4):
    P = [{"t": f"ここで、Section {sid.replace('-', 'の')}の確認問題です。マルかバツか、考えてください。"}, {"b": 0.8}]
    for i, q in enumerate(quiz_ids(sid)):
        P += [{"t": clean(f"{i+1}問目。{q['q']}")}, {"b": think}, {"t": clean(f"答えは、{'マル' if q['a'] else 'バツ'}。{q['exp']}")}, {"b": 1.2}]
    return P

def render(jobs):
    jp = os.path.join(TMP, "jobs.json"); json.dump(jobs, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", D("tools", "render_tts.ps1"), "-Jobs", jp, "-Voice", VOICE], check=True, capture_output=True)

def to_mp3(wav, mp3):
    os.makedirs(os.path.dirname(mp3), exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-b:a", "32k", mp3], check=True)

def duration(mp3):
    r = subprocess.run([FFMPEG, "-i", mp3], capture_output=True, text=True, encoding="utf-8", errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); return round(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), 1)

if __name__ == "__main__":
    want = sys.argv[1:] or [s[0] for s in secs if s[0] in LEC]
    idx_path = D("audio", "index.json")
    idx = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {}
    jobs, plan = [], []
    for sid in want:
        for kind, parts in (("lec", lecture_parts(sid)), ("q", quiz_parts(sid))):
            h = hashlib.md5(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[:10]
            mp3 = D("audio", kind, sid + ".mp3")
            if idx.get(sid, {}).get(kind + "_hash") == h and os.path.exists(mp3): continue  # 中身が同じなら作り直さない
            wav = os.path.join(TMP, f"{kind}_{sid}.wav"); jobs.append({"out": wav, "parts": parts}); plan.append((sid, kind, wav, mp3, h))
    if jobs: render(jobs)
    for sid, kind, wav, mp3, h in plan:
        to_mp3(wav, mp3); os.remove(wav)
        e = idx.setdefault(sid, {}); e[kind] = duration(mp3); e[kind + "_hash"] = h
        if kind == "q": e["q_ids"] = [q["id"] for q in quiz_ids(sid)]
        print(sid, kind, e[kind], "sec")
    json.dump(idx, open(idx_path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
