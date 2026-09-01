# -*- coding: utf-8 -*-
"""TOKIUM 直アポ大 G/H列 機械監査（ネットワーク不要）。

RULES.md の §3(判定ルール) / §4(出力仕様) / §6(既知の落とし穴) / §8(未検証の懸念)
に対する形式・整合チェックを全行に適用する。

使い方: python3 audit_gh.py <input.csv> [--out <prefix>]
入力CSVは A..H の8列（1行目ヘッダ）。
"""
import re, sys, csv, json, argparse
from collections import Counter, defaultdict

NG_KAKU = ["合同会社","有限会社","信用金庫","信用組合","医療法人","社会福祉法人",
           "農業協同組合","生活協同組合","相互会社","一般社団法人","一般財団法人","財団法人",
           "独立行政法人","合資会社","合名会社","労働金庫","共済組合"]
BANNED_DOMAINS = ["shukatsu-kaigi","syukatsu-kaigi","baseconnect","salesnow","mynavi","rikunabi",
                  "doda.jp","openwork","jobtalk","en-hyouban","lighthouse","wantedly","wikipedia",
                  "nikkei-compass","newspicks","job-","tenshoku","en-japan","hatarako"]
MARKS = ("○","×","△")
HD_WORDS = ["ホールディングス","ホールディング","HD","グループ本社","持株","Holdings","HOLDINGS"]

def parse_oku(g):
    """金額を億円単位で返す。§6-1 の桁誤読対策：兆/億/千万/百万/万 の複合単位、
    ゼロ幅スペース、分断された小数点に対応する。読めなければ None。"""
    if not g: return None
    s = g
    for ch in ("\\", ",", " ", "\u3000", "\u200b", "\ufeff"):
        s = s.replace(ch, "")
    s = re.sub(r"(\d)\.\s*(\d)", r"\1.\2", s)   # "398. 64億円" の分断を修復
    n = r"\d+(?:\.\d+)?"
    # 兆（+億）
    m = re.search(rf"({n})兆(?:({n})億)?(?:({n})百万)?円", s)
    if m:
        v = float(m.group(1))*10000
        if m.group(2): v += float(m.group(2))
        if m.group(3): v += float(m.group(3))/100
        return v
    # 億 + 下位単位
    m = re.search(rf"({n})億({n})千万円", s)
    if m: return float(m.group(1)) + float(m.group(2))/10
    m = re.search(rf"({n})億({n})百万円", s)
    if m: return float(m.group(1)) + float(m.group(2))/100
    m = re.search(rf"({n})億({n})万円", s)
    if m: return float(m.group(1)) + float(m.group(2))/10000
    m = re.search(rf"({n})億円", s)
    if m: return float(m.group(1))
    m = re.search(rf"({n})百万円", s)
    if m: return float(m.group(1))/100
    m = re.search(rf"({n})万円", s)
    if m: return float(m.group(1))/10000
    return None

def fiscal_year(g):
    m = re.search(r"(\d{4})年\d{1,2}月期", g or "")
    if m: return int(m.group(1))
    m = re.search(r"(\d{4})年度", g or "")
    return int(m.group(1)) if m else None

def audit_row(n, cells):
    acc_id, houjin, name, web, rng, memo, G, H = [(c or "").strip() for c in (list(cells)+[""]*8)[:8]]
    f = []
    mark  = H[:1] if H else ""
    amt   = parse_oku(G)
    under = "【300億未満】" in G
    urls  = re.findall(r"https?://[^\s、。）)\]]+", H)
    is_hd = any(w in name for w in HD_WORDS)

    # --- §4 出力仕様 ---
    if not H:
        f.append(("H_EMPTY", "H列が空"))
    elif mark not in MARKS:
        f.append(("H_NO_MARK", f"H列先頭に判定記号なし（先頭='{H[:8]}'）"))
    if not G:
        f.append(("G_EMPTY", "G列が空"))
    if len(H) > 300:
        f.append(("H_TOO_LONG", f"H列{len(H)}字（上限300字超過）"))

    # --- §4 【300億未満】接頭辞（§8 の宿題） ---
    if amt is not None and amt < 300 and not under and "対象外" not in G:
        f.append(("MISSING_PREFIX", f"G列{amt:,.2f}億円<300なのに【300億未満】なし"))
    if amt is not None and amt >= 300 and under:
        f.append(("WRONG_PREFIX", f"G列{amt:,.2f}億円>=300なのに【300億未満】あり"))

    # --- G/H 整合 ---
    if mark == "○":
        if under or "対象外" in G or "確認不可" in G:
            f.append(("OK_BUT_NG", "H列○なのにG列がNG内容"))
        if amt is not None and amt < 300:
            f.append(("OK_BUT_UNDER", f"H列○なのにG列{amt:,.2f}億円<300"))
        if amt is None and "確認不可" not in G:
            f.append(("OK_NO_AMOUNT", "H列○だがG列から金額を読み取れない"))
        if not urls:
            f.append(("OK_NO_URL", "H列○だが参照URLなし"))
    if mark == "△" and "確認不可" not in G:
        f.append(("TRI_NOT_UNKNOWN", "H列△なのにG列が確認不可でない"))
    if mark == "×" and amt is not None and amt >= 300 \
       and not any(k in H for k in ("子会社","法人格","合同会社","有限会社","消滅","合併")):
        f.append(("NG_UNEXPLAINED", f"H列×だがG列{amt:,.2f}億円>=300で除外理由が不明"))

    # --- §3-6 法人格 ---
    hit = [k for k in NG_KAKU if k in name]
    if hit and mark != "×":
        f.append(("KAKU_NOT_NG", f"社名に「{hit[0]}」を含むがH列が×でない"))

    # --- §3-3 / §6-4 子会社に連結値を適用（最重要） ---
    if "子会社" in H and "連結" in (G + H) and not is_hd and mark == "○":
        if "単体" not in G:
            f.append(("SUB_CONSOLIDATED",
                      "子会社と明記され連結値の疑い。§3-3により子会社は単体300億以上のみOK"))

    # --- §3-4 禁止ソース ---
    # D列の自社ドメインは承認ソース①なので、社名との衝突で誤検出しないよう除外する
    own = set()
    m = re.search(r"https?://([^/]+)", web or "")
    if m: own.add(re.sub(r"^www\.", "", m.group(1).lower()))
    for u in urls:
        lu = u.lower()
        host = re.sub(r"^www\.", "", re.sub(r"https?://", "", lu).split("/")[0])
        if host in own or any(host.endswith("." + o) or o.endswith("." + host) for o in own):
            continue  # 自社ドメイン
        for b in BANNED_DOMAINS:
            if b in host:
                f.append(("BANNED_SOURCE", f"禁止ソースURL（{b}）: {u[:80]}"))
                break
    # 自治体等の求人ナビは公的機関と求人媒体の境界（要人的判断）
    for u in urls:
        h = re.sub(r"^www\.", "", re.sub(r"https?://", "", u.lower()).split("/")[0])
        if h.endswith(".lg.jp") and ("job" in u.lower() or "navi" in h):
            f.append(("GOV_JOBSITE", f"自治体の求人ナビ（公的機関か求人媒体か要判断）: {u[:80]}"))

    # --- §7-1 catr.jp（先方承認未確認） ---
    if any("catr.jp" in u.lower() for u in urls):
        kind = "CATR_ONLY" if all("catr.jp" in u.lower() for u in urls) else "CATR_MIXED"
        f.append((kind, "catr.jp出典（§7-1 承認可否が先方未確認）"))

    # --- 法人番号 ---
    if not re.fullmatch(r"\d{13}", houjin):
        f.append(("HOUJIN_BAD", f"法人番号が13桁でない（'{houjin}'）"))

    # --- §3-8 決算期の鮮度（直近3期＝2023年以降） ---
    fy = fiscal_year(G)
    if fy is not None and fy < 2023:
        f.append(("STALE_FY", f"決算期{fy}年（直近3期外）"))

    return {"行": n, "取引先ID": acc_id, "法人番号": houjin, "取引先名": name,
            "E列": rng, "G列": G, "H列": H, "判定": mark, "金額億": amt,
            "指摘": f}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--out", default="audit")
    a = ap.parse_args()
    rows = list(csv.reader(open(a.csv, encoding="utf-8-sig")))[1:]
    res = [audit_row(i+2, r) for i, r in enumerate(rows)]

    # 同名・法人番号重複（§6-2）
    by_name, by_h = defaultdict(list), defaultdict(list)
    for r in res:
        by_name[r["取引先名"]].append(r["行"])
        if re.fullmatch(r"\d{13}", r["法人番号"]): by_h[r["法人番号"]].append(r["行"])
    for r in res:
        if len(by_name[r["取引先名"]]) > 1:
            r["指摘"].append(("DUP_NAME", f"同名が{len(by_name[r['取引先名']])}件（行{by_name[r['取引先名']]}）§6-2"))
        if r["法人番号"] in by_h and len(by_h[r["法人番号"]]) > 1:
            r["指摘"].append(("DUP_HOUJIN", f"法人番号重複（行{by_h[r['法人番号']]}）"))

    flagged = [r for r in res if r["指摘"]]
    codes = Counter(c for r in res for c, _ in r["指摘"])
    marks = Counter(r["判定"] or "(空)" for r in res)

    print(f"検査対象 {len(res)}行 / 指摘のある行 {len(flagged)}行\n")
    print("--- H列 判定記号の分布 ---")
    for k, v in marks.most_common():
        print(f"  {k}  {v:5d}  ({v/len(res)*100:5.1f}%)")
    print("\n--- 指摘コード別 件数 ---")
    for k, v in codes.most_common():
        print(f"  {v:5d}  {k}")

    json.dump(flagged, open(f"{a.out}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(f"{a.out}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["行","取引先ID","法人番号","取引先名","判定","G列","指摘コード","指摘内容"])
        for r in flagged:
            w.writerow([r["行"], r["取引先ID"], r["法人番号"], r["取引先名"], r["判定"], r["G列"],
                        ";".join(c for c, _ in r["指摘"]),
                        " / ".join(m for _, m in r["指摘"])])
    print(f"\n出力: {a.out}.json, {a.out}.csv")

if __name__ == "__main__":
    main()
