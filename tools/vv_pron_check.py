# VOICEVOXの読み（audio_queryのkana）と辞書(unidic)の読みを比べ、違う言葉を出す
import json, re, os, sys, collections, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import fugashi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_audio import D, clean, LEC, Q
texts = []
for L in LEC.values(): texts += [L["intro"], L["summary"]] + [p["h"] + "。" + p["t"] for p in L["points"]]
texts += [q["q"] for q in Q] + [q["exp"] for q in Q]
texts += [n["item"] + "。" + n["num"] for n in json.load(open(D("data", "numbers.json"), encoding="utf-8"))]
tag = fugashi.Tagger(); KAN = re.compile(r"[\u4e00-\u9fff々]")
freq = collections.Counter(); reading = {}
for t in texts:
    toks = [(w.surface, w.feature.kana or "") for w in tag(clean(t))]
    run = []
    for s, k in toks + [("", "")]:
        if s and KAN.search(s) and k: run.append((s, k)); continue
        if run:
            for s2, k2 in run: freq[s2] += 1; reading.setdefault(s2, k2)
            if len(run) > 1: ss = "".join(x[0] for x in run); freq[ss] += 1; reading.setdefault(ss, "".join(x[1] for x in run))
            run = []
def vv(w):
    url = "http://127.0.0.1:50021/audio_query?" + urllib.parse.urlencode({"text": w, "speaker": 30})
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=60).read())["kana"]
V = "アイウエオ"; ROW = {c: v for v, cs in zip(V, ["アカサタナハマヤラワガザダバパャァ", "イキシチニヒミリギジヂビピィ", "ウクスツヌフムユルグズヅブプュゥ", "エケセテネヘメレゲゼデベペェ", "オコソトノホモヨロゴゾドボポョォ"]) for c in cs}
def norm(k):
    k = re.sub(r"[ '/_、？]", "", k)
    out = ""
    for c in k:
        r = ROW.get(out[-1], "") if out else ""
        if r and ((c == "ウ" and r in "ウオ") or (c == "イ" and r == "エ")): c = r
        out += c
    return out.replace("ヲ", "オ").replace("ヅ", "ズ").replace("ヂ", "ジ")
words = [w for w, _ in freq.most_common()]
# 照会結果は保存しながら（止まっても続きから）
CP = D("tools", "vv_cache.json"); cache = json.load(open(CP, encoding="utf-8")) if os.path.exists(CP) else {}
todo = [w for w in words if w not in cache]
for i in range(0, len(todo), 400):
    part = todo[i:i + 400]
    with ThreadPoolExecutor(4) as ex: cache.update(zip(part, ex.map(vv, part)))
    json.dump(cache, open(CP, "w", encoding="utf-8"), ensure_ascii=False)
    print("cached", len(cache), flush=True)
got = [cache[w] for w in words]
res = [{"w": w, "dict": reading[w], "vv": g, "n": freq[w]} for w, g in zip(words, got) if norm(g) != norm(reading[w])]
json.dump(res, open(D("tools", "vv_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("words", len(words), "mismatch", len(res))
