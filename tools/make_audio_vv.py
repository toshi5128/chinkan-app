# 講義と確認問題をMP3にする（VOICEVOX版）。先に VOICEVOX エンジンを起動しておく（tools/voicevox.ps1）
# 使い方: python tools/make_audio_vv.py [sec ...]   （省略で全Section。中身と声が同じなら作り直さない）
import json, os, sys, io, wave, struct, hashlib, subprocess, urllib.request, urllib.parse, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_audio import D, clean, lecture_parts, quiz_parts, quiz_ids, to_mp3, duration, secs, LEC, TMP
API = "http://127.0.0.1:50021"
SPEAKER = int(os.environ.get("VV_SPEAKER", "0"))   # 声の番号（tools/voicevox_voice.txt に決めた声）
SPEED = float(os.environ.get("VV_SPEED", "1.0"))
VOICE_TAG = f"vv{SPEAKER}s{SPEED}"
RATE = 24000

def post(path, params=None, body=None, ctype="application/json"):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, data=body if body is not None else b"", method="POST", headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=600) as r: return r.read()

def synth(text):
    q = json.loads(post("/audio_query", {"text": text, "speaker": SPEAKER}))
    q.update({"speedScale": SPEED, "outputSamplingRate": RATE, "outputStereo": False, "prePhonemeLength": 0.05, "postPhonemeLength": 0.1})
    wav = post("/synthesis", {"speaker": SPEAKER}, json.dumps(q).encode())
    with wave.open(io.BytesIO(wav)) as w: return w.readframes(w.getnframes())

def split(t, n=180):  # 長い段落は文で区切る（エンジンの負担を減らす）
    out, cur = [], ""
    for s in re.findall(r"[^。！？]+[。！？]?", t):
        if len(cur) + len(s) > n and cur: out.append(cur); cur = ""
        cur += s
    if cur.strip(): out.append(cur)
    return out

def render(parts, wav_path):
    pcm = bytearray()
    for p in parts:
        if "b" in p: pcm += b"\x00\x00" * int(RATE * p["b"])
        else:
            for chunk in split(p["t"]): pcm += synth(chunk)
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(bytes(pcm))

def register_dict():  # 読み方辞書（tools/vv_dict.json）を毎回入れ直す
    cur = json.loads(urllib.request.urlopen(API + "/user_dict").read())
    for uid in cur: urllib.request.urlopen(urllib.request.Request(API + f"/user_dict_word/{uid}", method="DELETE"))
    d = json.load(open(D("tools", "vv_dict.json"), encoding="utf-8"))
    for w, k in d.items():
        post("/user_dict_word", {"surface": w, "pronunciation": k, "accent_type": 0, "word_type": "COMMON_NOUN", "priority": 9})
    return hashlib.md5(json.dumps(d, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:6]

if __name__ == "__main__":
    VOICE_TAG += "d" + register_dict()  # 辞書を変えたら作り直しの対象になる
    want = sys.argv[1:] or [s[0] for s in secs if s[0] in LEC]
    idx_path = D("audio", "index.json")
    idx = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {}
    t0 = time.time()
    for sid in want:
        for kind, parts in (("lec", lecture_parts(sid)), ("q", quiz_parts(sid))):
            h = hashlib.md5((VOICE_TAG + json.dumps(parts, ensure_ascii=False)).encode()).hexdigest()[:10]
            mp3 = D("audio", kind, sid + ".mp3")
            if idx.get(sid, {}).get(kind + "_hash") == h and os.path.exists(mp3): continue
            wav = os.path.join(TMP, f"vv_{kind}_{sid}.wav"); render(parts, wav); to_mp3(wav, mp3); os.remove(wav)
            e = idx.setdefault(sid, {}); e[kind] = duration(mp3); e[kind + "_hash"] = h; e["voice"] = VOICE_TAG
            if kind == "q": e["q_ids"] = [q["id"] for q in quiz_ids(sid)]
            json.dump(idx, open(idx_path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
            print(f"{sid} {kind} {e[kind]}s  経過{int(time.time()-t0)}s", flush=True)
