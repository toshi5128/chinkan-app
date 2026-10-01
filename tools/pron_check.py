# 講義・問題・数字まとめの「漢字の言葉」を集め、音声エンジンの読みと辞書の読みを比べて、違うものを出す
import json, re, os, sys, subprocess, collections
import fugashi
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = lambda *p: os.path.join(ROOT, *p)
TMP = os.path.join(os.environ["TEMP"], "ph")
sys.path.insert(0, D("tools")); from make_audio import clean, LEC, Q
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
            # 単語ごと＋漢字が続くひとかたまり
            for s2, k2 in run: freq[s2] += 1; reading.setdefault(s2, k2)
            if len(run) > 1:
                ss = "".join(x[0] for x in run); freq[ss] += 1; reading.setdefault(ss, "".join(x[1] for x in run))
            run = []
words = [w for w, _ in freq.most_common()]
print("words", len(words))
inp = os.path.join(TMP, "in.txt"); out = os.path.join(TMP, "out.txt")
with open(inp, "w", encoding="utf-8") as f:
    for w in words: f.write(w + "\n" + reading[w] + "\n")
subprocess.run([r"C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.6.0_x64__8wekyb3d8bbwe\pwsh.exe", "-NoProfile", "-File", os.path.join(TMP, "ph2.ps1"), "-InFile", inp, "-OutFile", out], check=True)
lines = open(out, encoding="utf-8-sig").read().rstrip("\n").split("\n")
norm = lambda p: re.sub(r"[ˈ↗|_\s]", "", p).replace("ː", "")
res = []
for i in range(0, len(lines) - 1, 2):
    w, pw = lines[i].split("\t", 1); k, pk = lines[i + 1].split("\t", 1)
    if norm(pw) != norm(pk): res.append({"w": w, "kana": k, "n": freq[w], "tts": pw.strip(), "ref": pk.strip()})
json.dump(res, open(D("tools", "pron_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("mismatch", len(res))
