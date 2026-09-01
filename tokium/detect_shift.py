# -*- coding: utf-8 -*-
"""G/H列の行ズレ検出。

RULES.md §5-2 が警告する「書き戻し行数の不一致による全行ズレ」を検出する。
各行の H列（出典URLのドメイン・本文中の社名）が、その行の C列社名 / D列サイトに
対応するか、それとも n±k 行目に対応するかをスコアで判定する。

§6-2 の通り「別会社の数字を書く方が、空欄より危険」であり、ズレた行は
すべて他社の売上高を載せていることになる。
"""
import csv, re, sys, json
from collections import Counter

SUFFIX = ["株式会社","有限会社","合同会社","合資会社","合名会社","(株)","（株）","ホールディングス"]
# 実質的な公開接尾辞（これ単体では企業を識別しない）
PUBLIC_SUFFIX_2 = {
    "co.jp","ne.jp","or.jp","go.jp","lg.jp","ac.jp","ed.jp","gr.jp","ad.jp",
    "co.uk","org.uk","ac.uk","com.au","co.kr","com.cn","com.tw","com.sg","co.th",
}
GENERIC_TLD = {"com","net","org","jp","biz","info","io","co","us","asia","tokyo"}

def norm_name(s):
    s = (s or "").strip()
    for x in SUFFIX: s = s.replace(x, "")
    s = "".join(chr(ord(c)-0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in s)
    return re.sub(r"[\s・･\-ー－。、．,\.]", "", s).lower()

def registrable(h):
    """登録可能ドメインを返す。fujimak.co.jp -> fujimak.co.jp / a.b.bd.com -> bd.com"""
    p = h.split(".")
    if len(p) >= 3 and ".".join(p[-2:]) in PUBLIC_SUFFIX_2:
        return ".".join(p[-3:])
    if len(p) >= 2:
        return ".".join(p[-2:])
    return h

def core_label(h):
    """識別ラベル（登録可能ドメインの先頭）。fujimak.co.jp -> fujimak"""
    lab = registrable(h).split(".")[0]
    return "" if lab in GENERIC_TLD else lab

def doms(text):
    """テキスト中のURLから登録可能ドメイン集合を返す（公開接尾辞は混ぜない）"""
    out = set()
    for u in re.findall(r"https?://([^/\s、。）)\]\"']+)", text or ""):
        h = re.sub(r"^www\d?\.", "", u.lower().strip())
        r = registrable(h)
        if r and r not in PUBLIC_SUFFIX_2 and r not in GENERIC_TLD:
            out.add(r)
    return out

def score(name_C, site_D, H):
    """H列がこの行(C列社名 / D列サイト)に対応するかのスコア。3以上で強い一致。"""
    if not H: return 0
    s = 0
    n = norm_name(name_C)
    if n and len(n) >= 3 and n in norm_name(H):
        s += 3
    elif n and len(n) >= 2 and n in norm_name(H):
        s += 1
    dD, dH = doms(site_D), doms(H)
    if dD & dH:
        s += 4
    else:
        cD = {core_label(x) for x in dD} - {""}
        cH = {core_label(x) for x in dH} - {""}
        if cD & cH: s += 3
    return s

def detect(path, lookahead=3):
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))[1:]
    R = [(list(r)+[""]*8)[:8] for r in rows]
    N = len(R)
    out = []
    for i in range(N):
        H = R[i][7]
        if not H: continue
        self_s = score(R[i][2], R[i][3], H)
        cands = []
        for k in list(range(1, lookahead+1)) + [-x for x in range(1, lookahead+1)]:
            j = i + k
            if 0 <= j < N:
                cands.append((score(R[j][2], R[j][3], H), k))
        best_s, best_k = max(cands) if cands else (0, 0)
        # 自行より他行の方が明確に強く一致し、かつ自行が弱い場合のみズレと判定
        if best_s >= 3 and best_s > self_s and self_s < 3:
            out.append({
                "行": i+2, "ずれ": best_k, "自行スコア": self_s, "対応先スコア": best_s,
                "自行社名": R[i][2], "対応先社名": R[i+best_k][2],
                "自行サイト": R[i][3], "G列": R[i][6][:70], "H列": H[:180],
            })
    return out, R

if __name__ == "__main__":
    f, R = detect(sys.argv[1])
    print(f"行ズレ疑い: {len(f)}行 / 全{len(R)}行  ({len(f)/len(R)*100:.1f}%)")
    print("ずれ幅の分布:", Counter(x['ずれ'] for x in f).most_common())
    rowsn = sorted(x["行"] for x in f)
    runs=[]; s=p=rowsn[0]
    for n in rowsn[1:]:
        if n-p <= 2: p=n
        else: runs.append((s,p)); s=p=n
    runs.append((s,p))
    runs.sort(key=lambda ab: ab[0]-ab[1])
    print(f"\n連続区間 {len(runs)}個（長い順・上位20）:")
    for a,b in runs[:20]:
        cnt = sum(1 for n in rowsn if a<=n<=b)
        print(f"  行{a:>5}〜行{b:<5} 幅{b-a+1:>4}行  検出{cnt}行")
    json.dump(f, open(sys.argv[1]+".shift.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n出力: {sys.argv[1]}.shift.json")
