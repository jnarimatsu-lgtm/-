# -*- coding: utf-8 -*-
"""J列の出典URLに捏造の疑いがあるものを検出する。

RULES §3-1④ は参照URLの記載を求めており、監査可能であることが前提。
存在しないURLが証跡として載っていると、監査時に「出典なし」として
落とされ架電機会を失う（実例: ティーエスアルフレッサでJ列が死リンクに
書き換えられていた）。逆に捏造URLで○が通ると§1の事故になる。
"""
import re, sys, math
from collections import Counter
sys.path.insert(0, "/home/user/-/tokium")
from verdict import build

def entropy(s):
    if not s: return 0.0
    c = Counter(s)
    n = len(s)
    return -sum(v/n * math.log2(v/n) for v in c.values())

def suspicious(url):
    """ファイル名部分が乱打・無意味に見えるURLを拾う。"""
    m = re.search(r"/([A-Za-z0-9_\-]{6,})\.(pdf|html?|php)$", url)
    if not m: return None
    stem = m.group(1)
    if re.fullmatch(r"[0-9_\-]+", stem): return None          # 日付や連番は正常
    # CMSが生成するハッシュは数字を混ぜる・長い・タイムスタンプを含むのが通例。
    # 英小文字だけの短い綴りで母音がほぼ無いものに絞る（乱打の典型）。
    if re.search(r"\d{4,}", stem): return None        # 日付・タイムスタンプはCMS由来
    core = re.sub(r"^\d+|\d+$", "", stem)             # 先頭末尾の1〜3桁は除いて綴りを見る
    if re.search(r"\d", core): return None            # 内部に数字が散るのはCMSハッシュ
    if not re.fullmatch(r"[a-z]{8,14}", core): return None
    stem = core
    vowels = sum(1 for ch in stem if ch in "aeiou")
    ratio = vowels / len(stem)
    if ratio <= 0.12:
        return f"英小文字のみ{len(stem)}字・母音{vowels}個（乱打の疑い）"
    return None

if __name__ == "__main__":
    res = build()
    hits = []
    for r in res:
        for u in re.findall(r"https?://[^\s、。）)\]\"'；;]+", r["J列_ソース"] + " " + r["I列_検証結果"]):
            why = suspicious(u)
            if why:
                hits.append((r["行"], r["取引先名"], r["架電可"], u, why))
    print(f"疑わしいURL: {len(hits)}件")
    print("※ この環境はWebFetchが全ドメイン遮断されており、URLの実在は"
          "一切検証できない。本チェックは綴りの不自然さのみを見る目安。\n")
    for n, nm, ok, u, why in hits:
        print(f"  行{n} [{ok}] {nm[:20]}\n     {u}\n     {why}")
