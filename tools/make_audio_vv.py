# 講義と確認問題をMP3にする（VOICEVOX版）。先に VOICEVOX エンジンを起動しておく（tools/voicevox.ps1）
# 使い方: python tools/make_audio_vv.py [sec ...]   （省略で全Section。中身と声が同じなら作り直さない）
import json, os, sys, io, wave, struct, hashlib, subprocess, urllib.request, urllib.parse, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_audio import D, clean, lecture_parts, quiz_parts, quiz_ids, to_mp3, duration, secs, LEC, TMP
API = "http://127.0.0.1:50021"
SPEAKER = int(os.environ.get("VV_SPEAKER", "0"))   # 声の番号（tools/voicevox_voice.txt に決めた声）
SPEED = float(os.environ.get("VV_SPEED", "1.0"))
VOICE_TAG = f"vv{SPEAKER}s{SPEED}i{os.environ.get('VV_INTON', '1.25')}e2"
RATE = 24000
# 会話形式の講義（data/talk_*.json）：A=進行役 青山龍星(13)・B=相方 四国めたん(2)。2026-10-05 下田さんがラジオ風を選択
TALK_SPK = {"A": int(os.environ.get("VV_TALK_A", "13")), "B": int(os.environ.get("VV_TALK_B", "2"))}
TALK = {}
for _f in sorted(__import__("glob").glob(D("data", "talk_*.json"))):
    TALK.update(json.load(open(_f, encoding="utf-8")))
TALK_TAG = f"talk{TALK_SPK['A']}x{TALK_SPK['B']}"

def post(path, params=None, body=None, ctype="application/json"):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, data=body if body is not None else b"", method="POST", headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=600) as r: return r.read()

INTONATION = float(os.environ.get("VV_INTON", "1.25"))   # 全体の抑揚（1.0=標準）
EMPH = {"pitch": 0.14, "vlen": 1.25, "clen": 1.15, "pause": 0.22}  # 《》の所：高く・ゆっくり・前に間
_kcache = {}; EMPH_STAT = {"ok": 0, "ng": 0}
def mora_kana(text, spk=None):  # その語句をVOICEVOXが読むときの音の並び（カナ）
    spk = SPEAKER if spk is None else spk
    if (text, spk) not in _kcache:
        q = json.loads(post("/audio_query", {"text": text, "speaker": spk}))
        _kcache[(text, spk)] = [m["text"] for ap in q["accent_phrases"] for m in ap["moras"]]
    return _kcache[(text, spk)]
def find_sub(seq, sub, start):
    n = len(sub)
    for i in range(start, len(seq) - n + 1):
        if seq[i:i + n] == sub: return i
    return -1
def emphasize(q, spans, spk=None):
    flat = [(ai, mi, m) for ai, ap in enumerate(q["accent_phrases"]) for mi, m in enumerate(ap["moras"])]
    seq = [m["text"] for _, _, m in flat]; cur = 0
    for sp in spans:
        sub = mora_kana(sp, spk); pos = -1
        # 前後の1音は文脈で読みが変わることがあるので、ずらしても探す
        for cand in (sub, sub[1:], sub[:-1], sub[1:-1]):
            if len(cand) >= 2 and (pos := find_sub(seq, cand, cur)) >= 0: sub = cand; break
        if pos < 0: EMPH_STAT["ng"] += 1; continue
        EMPH_STAT["ok"] += 1
        for ai, mi, m in flat[pos:pos + len(sub)]:
            if m["pitch"] > 0: m["pitch"] += EMPH["pitch"]
            m["vowel_length"] *= EMPH["vlen"]
            if m.get("consonant_length"): m["consonant_length"] *= EMPH["clen"]
        ai0, mi0, _ = flat[pos]
        if mi0 == 0 and ai0 > 0 and q["accent_phrases"][ai0 - 1]["pause_mora"] is None:
            q["accent_phrases"][ai0 - 1]["pause_mora"] = {"text": "、", "consonant": None, "consonant_length": None, "vowel": "pau", "vowel_length": EMPH["pause"], "pitch": 0.0}
        cur = pos + len(sub)
def synth(text, spk=None):
    spk = SPEAKER if spk is None else spk
    spans = re.findall(r"《(.+?)》", text); plain = text.replace("《", "").replace("》", "")
    q = json.loads(post("/audio_query", {"text": plain, "speaker": spk}))
    q.update({"speedScale": SPEED, "intonationScale": INTONATION, "outputSamplingRate": RATE, "outputStereo": False, "prePhonemeLength": 0.05, "postPhonemeLength": 0.1})
    if spans: emphasize(q, spans, spk)
    wav = post("/synthesis", {"speaker": spk}, json.dumps(q).encode())
    with wave.open(io.BytesIO(wav)) as w: return w.readframes(w.getnframes())

def split(t, n=180):  # 長い段落は文で区切る（エンジンの負担を減らす）
    out, cur = [], ""
    for s in re.findall(r"[^。！？]+[。！？]?", t):
        if len(cur) + len(s) > n and cur: out.append(cur); cur = ""
        cur += s
    if cur.strip(): out.append(cur)
    return out

def render(parts, wav_path):
    """parts: {"t", "spk"?} 話す / {"b": 秒} 間 / {"mark": 1} ここから次のかたまり。かたまりの開始秒のリストを返す"""
    global LINE_STARTS
    pcm = bytearray(); marks = []; LINE_STARTS = []
    for p in parts:
        if "mark" in p: marks.append(round(len(pcm) / 2 / RATE, 2))
        elif "b" in p: pcm += b"\x00\x00" * int(RATE * p["b"])
        else:
            LINE_STARTS.append(round(len(pcm) / 2 / RATE, 2))  # 吹き出し1つごとの話し始め（アプリが今読んでいる行に色を付ける）
            for chunk in split(p["t"]): pcm += synth(chunk, p.get("spk"))
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(bytes(pcm))
    return marks

secs_title = {s[0]: s[1] for s in secs}
def talk_parts(sid):
    """会話形式の講義。題名と各かたまりの前に mark（アプリが今どこを話しているか表示するため）"""
    P = [{"mark": 1}, {"t": clean(f"Section {sid.replace('-', 'の')}、{secs_title[sid]}。"), "spk": TALK_SPK["A"]}, {"b": 0.6}]
    for b in TALK[sid]["blocks"]:
        P.append({"mark": 1})
        for w, t in b["lines"]:
            P += [{"t": clean(t), "spk": TALK_SPK[w]}, {"b": 0.22}]
        P.append({"b": 0.7})
    return P

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
        talk = sid in TALK
        for kind, parts in (("lec", talk_parts(sid) if talk else lecture_parts(sid)), ("q", quiz_parts(sid))):
            tag = TALK_TAG + VOICE_TAG if kind == "lec" and talk else VOICE_TAG
            h = hashlib.md5((tag + json.dumps(parts, ensure_ascii=False)).encode()).hexdigest()[:10]
            mp3 = D("audio", kind, sid + ".mp3")
            if idx.get(sid, {}).get(kind + "_hash") == h and os.path.exists(mp3): continue
            wav = os.path.join(TMP, f"vv_{kind}_{sid}.wav"); marks = render(parts, wav); to_mp3(wav, mp3); os.remove(wav)
            e = idx.setdefault(sid, {}); e[kind] = duration(mp3); e[kind + "_hash"] = h; e[kind + "_voice"] = tag
            if kind == "lec":
                if talk: e["lec_marks"] = marks; e["lec_lines"] = LINE_STARTS[1:]  # 先頭は題名なので除く
                else: e.pop("lec_marks", None); e.pop("lec_lines", None)
            if kind == "q": e["q_ids"] = [q["id"] for q in quiz_ids(sid)]
            json.dump(idx, open(idx_path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
            print(f"{sid} {kind} {e[kind]}s  経過{int(time.time()-t0)}s  強調{EMPH_STAT}", flush=True)
