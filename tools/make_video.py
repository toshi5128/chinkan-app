# 図解動画（絵が動く＋2人の声）を作る。data/videos.json と audio/video/<id>.mp3 を出力
# 使い方: VOICEVOX を起動（tools/voicevox.ps1）→ python tools/make_video.py
# 2026-11-11 下田さん「水道増圧ポンプとか水道系の種類が分からないから、イラスト付きの動画を作ってアプリに入れて」
import json, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_audio_vv as V
from make_audio import D, clean, to_mp3, duration, TMP

A, B = "A", "B"  # A=進行役 青山龍星 / B=相方 四国めたん（講義と同じ2人）

# ---------- 絵の部品 ----------
W = "var(--a)"      # 水の色
INK, SUB, LINE, NG, OK = "var(--ink)", "var(--sub)", "var(--line)", "var(--ng)", "var(--ok)"

def t(x, y, s, size=12, col=INK, bold=False, anchor="middle", cls=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" text-anchor="{anchor}"{" font-weight=\"bold\"" if bold else ""}{f" class=\"{cls}\"" if cls else ""}>{s}</text>'

def pipe(pts, flow=True, w=4, col=W, cls=""):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    base = f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" opacity=".35"/>'
    return base + (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" class="fl {cls}"/>' if flow else "")

def ground(y=212):
    return (f'<line x1="0" y1="{y}" x2="360" y2="{y}" stroke="{SUB}" stroke-width="1.5"/>'
            f'<rect x="0" y="{y}" width="360" height="{260 - y}" fill="var(--track)" opacity=".6"/>')

def main_pipe(y=236, label=True):
    s = pipe([(0, y), (360, y)], w=8)
    return s + (t(300, y - 8, "水道本管（道路の下）", 10, SUB) if label else "")

def building(x, top, floors, w=70, base=212, taps=True):
    h = base - top; fh = h / floors
    s = f'<rect x="{x}" y="{top}" width="{w}" height="{h}" fill="var(--card)" stroke="{INK}" stroke-width="1.5"/>'
    for i in range(1, floors):
        s += f'<line x1="{x}" y1="{top + fh * i}" x2="{x + w}" y2="{top + fh * i}" stroke="{LINE}"/>'
    if taps:
        for i in range(floors):
            y = top + fh * i + fh * .55
            s += f'<circle cx="{x + w - 12}" cy="{y}" r="3.2" fill="{W}"/>'
    return s

def riser(x, top, floors, base=212, w=70, flow=True):  # 建物の中の縦の管と各階への枝
    h = base - top; fh = h / floors
    s = pipe([(x + 10, base), (x + 10, top + fh * .55)], flow)
    for i in range(floors):
        y = top + fh * i + fh * .55
        s += pipe([(x + 10, y), (x + w - 15, y)], flow, w=3)
    return s

def pump(x, y, label="ポンプ", col=NG):
    return (f'<g><circle cx="{x}" cy="{y}" r="11" fill="var(--card)" stroke="{col}" stroke-width="2.5"/>'
            f'<g class="spin" style="transform-origin:{x}px {y}px"><path d="M{x - 6},{y} L{x + 6},{y} M{x},{y - 6} L{x},{y + 6}" stroke="{col}" stroke-width="2.5"/></g></g>'
            + t(x, y + 24, label, 10, col, True))

def tank(x, y, w, h, label, col=W, lab_dy=-6):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="var(--card)" stroke="{INK}" stroke-width="1.5"/>'
            f'<rect x="{x + 2}" y="{y + h * .35}" width="{w - 4}" height="{h * .65 - 2}" fill="{col}" opacity=".55" class="wave"/>'
            + t(x + w / 2, y + lab_dy, label, 10, INK, True))

def tag(x, y, s, col=NG, w=None):
    w = w or len(s) * 11 + 14
    return f'<g class="pop"><rect x="{x - w / 2}" y="{y - 13}" width="{w}" height="19" rx="9" fill="{col}"/>' + t(x, y + 1, s, 11, "#fff", True) + "</g>"

def cross(x, y):
    return f'<g class="pop"><path d="M{x - 9},{y - 9} L{x + 9},{y + 9} M{x + 9},{y - 9} L{x - 9},{y + 9}" stroke="{NG}" stroke-width="4"/></g>'

def svg(body, title):
    return (f'<svg viewBox="0 0 360 260" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">'
            + t(180, 18, title, 14, INK, True) + body + "</svg>")

# ---------- 場面 ----------
S = []

# 0 全体像
body = ground() + main_pipe()
body += building(40, 120, 3) + riser(40, 120, 3) + pipe([(50, 236), (50, 212)])
body += t(75, 108, "① 直結", 12, W, True) + t(75, 60, "水道管から", 10, SUB) + t(75, 74, "そのまま蛇口へ", 10, SUB)
body += building(230, 70, 6) + tank(180, 180, 40, 30, "受水槽", lab_dy=-5) + pipe([(200, 236), (200, 212)]) + pipe([(220, 196), (240, 196), (240, 212)])
body += riser(230, 70, 6)
body += t(270, 58, "② 受水槽", 12, W, True) + t(270, 44, "いったんタンクにためる", 10, SUB)
S.append({"h": "全体像：2つのグループ", "svg": svg(body, "水の届け方は大きく2つ"), "lines": [
    [A, "今日は、マンションに水を届ける仕組み、給水方式を、絵で見ていきます。"],
    [B, "増圧ポンプとか、受水槽とか、名前が似ていて、ごちゃごちゃになるんですよね。"],
    [A, "まず大きく2つに分けます。ひとつは、道路の下の水道管から、《そのまま蛇口へ》届ける「直結」のグループ。"],
    [A, "もうひとつは、いったん《受水槽というタンクにためてから》配る、「受水槽」のグループです。"],
    [B, "タンクがあるか、ないか。まずそこで分けるんですね。"],
    [A, "そうです。試験のひっかけは、ほとんどが「この方式に受水槽はあるか」の入れ替えです。"],
]})

# 1 直結直圧
body = ground() + main_pipe()
body += building(140, 130, 3) + riser(140, 130, 3) + pipe([(150, 236), (150, 212)])
body += f'<path d="M110,200 L128,200" stroke="{NG}" stroke-width="3" class="pop"/><path d="M122,194 L130,200 L122,206" fill="none" stroke="{NG}" stroke-width="3" class="pop"/>'
body += t(80, 196, "本管の圧力", 11, NG, True) + t(80, 210, "だけで押し上げ", 11, NG, True)
body += tag(270, 130, "ポンプなし", OK) + tag(270, 156, "受水槽なし", OK) + tag(270, 182, "停電でも出る", OK) + tag(270, 208, "断水で止まる", NG)
body += t(175, 120, "2〜3階くらいまで", 11, SUB)
S.append({"h": "① 直結直圧方式", "svg": svg(body, "① 直結直圧方式"), "lines": [
    [A, "1つ目は、直結直圧方式。水道管の《水の圧力だけ》で、蛇口まで水を押し上げます。"],
    [B, "ポンプも、タンクも、なし。一番シンプルですね。"],
    [A, "電気を使わないので、《停電しても水が出ます》。そのかわり、水道が断水すると、ためた水がないので《すぐ止まります》。"],
    [A, "水道管の圧力には限りがあるので、2階や3階くらいの、《低い建物向き》です。"],
]})

# 2 直結増圧
body = ground() + main_pipe()
body += building(200, 50, 7) + riser(200, 50, 7) + pipe([(130, 236), (130, 212), (130, 200), (210, 200), (210, 212)])
body += pump(160, 200, "増圧ポンプ")
body += f'<rect x="100" y="191" width="18" height="18" fill="var(--card)" stroke="{INK}" stroke-width="1.5"/>' + t(109, 204, "逆", 10, INK, True)
body += t(70, 168, "逆流防止器", 11, NG, True) + t(70, 182, "（必ず付ける）", 10, NG)
body += cross(60, 120) + t(60, 100, "受水槽", 11, SUB) + t(60, 145, "いらない", 11, NG, True)
body += f'<path d="M210,196 L210,60" stroke="{NG}" stroke-width="2" stroke-dasharray="4 4" class="pop"/>'
S.append({"h": "② 直結増圧方式", "svg": svg(body, "② 直結増圧方式（増圧ポンプ）"), "lines": [
    [A, "2つ目が、下田さんが気になっていた、直結増圧方式です。"],
    [A, "水道管に《直接つないだ増圧ポンプ》で、水の勢いを足して、上の階まで押し上げます。"],
    [B, "水道管の力に、ポンプで上乗せするんですね。"],
    [A, "そうです。ここが一番大事で、水道管から直接もらうので、《受水槽はいりません》。"],
    [A, "そのかわり、建物の中の水が、水道管のほうへ逆に流れて汚さないように、《逆流防止器を必ず付けます》。"],
    [B, "試験では、「直結増圧は受水槽が必要」と出たら、バツですね。"],
    [A, "その通り。ポンプは電気で動くので、停電すると、上の階には水が届かなくなります。"],
]})

# 3 高置水槽
body = ground() + main_pipe()
body += building(170, 60, 6) + tank(178, 34, 54, 22, "高置水槽（屋上）", lab_dy=-4)
body += tank(90, 182, 46, 28, "受水槽", lab_dy=-5) + pipe([(113, 236), (113, 212)])
body += pipe([(136, 196), (150, 196), (150, 45), (178, 45)], cls="up") + pump(150, 150, "") + t(110, 154, "揚水ポンプ", 10, NG, True)
body += pipe([(232, 45), (250, 45), (250, 212)], cls="down")
for i in range(6):
    y = 60 + (212 - 60) / 6 * i + (212 - 60) / 6 * .55
    body += pipe([(250, y), (225, y)], w=3)
body += t(305, 80, "重力で", 11, NG, True) + t(305, 94, "下へ配る", 11, NG, True)
body += f'<path d="M290,104 L290,140" stroke="{NG}" stroke-width="2.5"/><path d="M284,134 L290,144 L296,134" fill="none" stroke="{NG}" stroke-width="2.5"/>'
body += tag(305, 175, "停電でも", OK, 70) + t(305, 196, "屋上の残りは", 10, SUB) + t(305, 208, "使える", 10, SUB)
S.append({"h": "③ 高置水槽方式", "svg": svg(body, "③ 高置水槽方式"), "lines": [
    [A, "ここからは、受水槽のあるグループです。3つ目は、高置水槽方式。"],
    [A, "水道の水を、まず1階の《受水槽にためて》、揚水ポンプで、《屋上の高置水槽までくみ上げます》。"],
    [B, "タンクが2つあるんですね。下と、上に。"],
    [A, "はい。屋上のタンクからは、《重力で》上から下へ流して配ります。"],
    [A, "だから停電でポンプが止まっても、《屋上のタンクに残っている分は》、しばらく使えます。"],
    [B, "上から落とすので、屋上に近い最上階は、水の勢いが弱めになるんですね。"],
]})

# 4 ポンプ直送
body = ground() + main_pipe()
body += building(200, 60, 6) + riser(200, 60, 6)
body += tank(90, 182, 46, 28, "受水槽", lab_dy=-5) + pipe([(113, 236), (113, 212)])
body += pipe([(136, 196), (210, 196), (210, 212)]) + pump(168, 196, "加圧ポンプ")
body += cross(150, 60) + t(150, 42, "高置水槽", 11, SUB) + t(150, 88, "なし", 11, NG, True)
body += tag(300, 120, "受水槽あり", NG, 84)
S.append({"h": "④ ポンプ直送方式", "svg": svg(body, "④ ポンプ直送方式（加圧給水）"), "lines": [
    [A, "4つ目は、ポンプ直送方式。加圧給水方式とも言います。"],
    [A, "《受水槽にためた水を》、加圧ポンプで、各部屋へ《直接送ります》。屋上のタンクは、ありません。"],
    [B, "あれ、増圧ポンプとそっくりですね。"],
    [A, "そこが、ひっかけです。どちらもポンプで送りますが、増圧方式は《受水槽なし》、ポンプ直送方式は《受水槽あり》。"],
    [B, "「ポンプ直送方式には受水槽がない」と出たら、バツ。覚えました。"],
]})

# 5 圧力水槽
body = ground() + main_pipe()
body += building(220, 80, 5) + riser(220, 80, 5)
body += tank(60, 182, 46, 28, "受水槽", lab_dy=-5) + pipe([(83, 236), (83, 212)])
body += pump(130, 196, "ポンプ") + pipe([(106, 196), (150, 196)])
body += f'<rect x="152" y="150" width="34" height="56" rx="14" fill="var(--card)" stroke="{INK}" stroke-width="1.5"/><rect x="154" y="178" width="30" height="26" rx="10" fill="{W}" opacity=".55"/>'
body += t(169, 170, "空気", 10, SUB) + t(169, 142, "圧力水槽", 10, INK, True)
body += pipe([(186, 196), (230, 196), (230, 212)])
body += t(300, 60, "空気の力で", 11, NG, True) + t(300, 74, "押し出す", 11, NG, True)
S.append({"h": "⑤ 圧力水槽方式", "svg": svg(body, "⑤ 圧力水槽方式"), "lines": [
    [A, "おまけで、圧力水槽方式もあります。受水槽の水を、ポンプで《圧力タンクに送り》、中の空気の力で押し出して配ります。"],
    [B, "これも、受水槽のあるグループですね。"],
    [A, "はい。ポンプを使う方式なので、停電すると止まります。"],
]})

# 6 受水槽の管理
body = ""
body += f'<rect x="20" y="40" width="150" height="100" rx="4" fill="var(--card)" stroke="{INK}" stroke-width="1.5"/><rect x="22" y="80" width="146" height="58" fill="{W}" opacity=".45" class="wave"/>'
body += t(95, 70, "受水槽", 13, INK, True)
for x, y in [(95, 32), (95, 158), (8, 90), (182, 90)]:
    body += f'<circle cx="{x}" cy="{y}" r="5" fill="{OK}" class="pop"/>'
body += t(95, 182, "6面すべて外から点検できる", 11, OK, True) + t(95, 198, "（建物のコンクリートと兼用しない）", 10, SUB)
body += tag(275, 52, "有効容量 10㎥超", NG, 140) + t(275, 76, "＝簡易専用水道", 12, INK, True)
body += tag(275, 108, "清掃 毎年1回以上", "var(--brand)", 140) + tag(275, 136, "検査 毎年1回以上", "var(--brand)", 140)
body += t(275, 160, "登録検査機関", 10, SUB) + t(275, 174, "（国土交通大臣と環境大臣）", 10, SUB)
body += t(275, 206, "あふれた水は排水管に", 10, INK) + t(275, 220, "直接つながない", 10, NG, True)
S.append({"h": "受水槽の管理ルール", "svg": svg(body, "受水槽があると管理のルールがつく"), "lines": [
    [A, "受水槽があるグループには、管理のルールがつきます。"],
    [A, "受水槽の有効容量の合計が、《10立方メートルを超える》と、簡易専用水道になります。"],
    [A, "この場合、《清掃は毎年1回以上》、登録を受けた機関の《検査も毎年1回以上》です。3年ごと、ではありません。"],
    [B, "受水槽を置く場所にも、ルールがありましたよね。"],
    [A, "はい。床、天井、周りの壁を、建物のコンクリートと《兼ねてはいけません》。外から全部の面を点検できるようにするためです。"],
    [A, "あふれた水を流す管は、排水管に《直接つながず》、すき間をあけて流します。汚れた水の逆流を防ぐためです。"],
]})

# 7 まとめ表
rows = [("方式", "受水槽", "ポンプ", "停電"), ("① 直結直圧", "なし", "なし", "出る"), ("② 直結増圧", "なし", "増圧", "上の階は×"),
        ("③ 高置水槽", "あり", "揚水", "屋上の残りOK"), ("④ ポンプ直送", "あり", "加圧", "止まる"), ("⑤ 圧力水槽", "あり", "あり", "止まる")]
body = ""
xs = [62, 152, 214, 300]
for i, r in enumerate(rows):
    y = 52 + i * 33
    if i == 0:
        body += f'<rect x="8" y="{y - 18}" width="344" height="26" rx="4" fill="var(--track)"/>'
    elif i in (2, 4):
        body += f'<rect x="8" y="{y - 18}" width="344" height="26" rx="4" fill="none" stroke="{NG}" stroke-width="2" class="pop"/>'
    for j, c in enumerate(r):
        col = INK if i == 0 or j == 0 else (NG if c == "なし" and j == 1 else (OK if c == "あり" and j == 1 else INK))
        body += t(xs[j], y, c, 12 if j else 12, col, i == 0 or j <= 1)
body += t(180, 248, "赤い枠の2つ＝受水槽の有無を入れ替えるひっかけ", 11, NG, True)
S.append({"h": "まとめ", "svg": svg(body, "まとめ"), "lines": [
    [A, "最後に、まとめです。受水槽がないのは、《直結直圧と直結増圧の2つだけ》。"],
    [A, "高置水槽、ポンプ直送、圧力水槽の3つは、《受水槽があります》。"],
    [B, "そして、一番ねらわれるのが、増圧方式とポンプ直送方式の入れ替えですね。"],
    [A, "その通り。増圧は、受水槽なし、逆流防止器あり。ポンプ直送は、受水槽あり。この2行で、1点取れます。"],
    [B, "停電に強いのは、ポンプのいらない直結直圧と、屋上にタンクのある高置水槽。よし、もう大丈夫です。"],
]})

VIDEOS = [{"id": "kyusui", "title": "給水方式のちがい（増圧ポンプ・受水槽）", "sec": "4-5", "scenes": S}]

if __name__ == "__main__":
    V.VOICE_TAG += "d" + V.register_dict()
    os.makedirs(D("audio", "video"), exist_ok=True)
    for v in VIDEOS:
        parts = []
        for sc in v["scenes"]:
            parts.append({"mark": 1})
            for who, line in sc["lines"]:
                parts += [{"t": clean(line), "spk": V.TALK_SPK[who]}, {"b": 0.25}]
            parts.append({"b": 0.8})
        wav = os.path.join(TMP, v["id"] + "_video.wav")
        marks = V.render(parts, wav)
        starts = V.LINE_STARTS
        mp3 = D("audio", "video", v["id"] + ".mp3"); to_mp3(wav, mp3)
        v["audio"] = f"audio/video/{v['id']}.mp3"; v["dur"] = duration(mp3)
        k = 0
        for i, sc in enumerate(v["scenes"]):
            sc["t"] = marks[i]
            for ln in sc["lines"]:
                ln.append(starts[k]); k += 1
        print(v["id"], v["dur"], "秒")
    json.dump(VIDEOS, open(D("data", "videos.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("ok")
