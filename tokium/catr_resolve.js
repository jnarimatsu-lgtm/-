export const meta = {
  name: 'tokium-catr-resolve',
  description: 'catr.jp（§7-1）が絡む686行を、出典だけが理由の行かどうかで仕分ける',
  phases: [{ title: 'Classify', detail: 'I列を読んで阻害要因を判定' }],
}

const SP = '/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad'
const NB = 8

const SCHEMA = {
  type: 'object',
  required: ['block', 'decisions'],
  properties: {
    block: { type: 'integer' },
    decisions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['row', 'flip', 'reason'],
        properties: {
          row: { type: 'integer' },
          flip: { type: 'boolean', description: 'true＝catr.jpを認めれば架電可にできる' },
          amount_oku: { type: ['number', 'null'], description: '採用すべき売上高（億円）' },
          period: { type: 'string', description: 'その数値の決算期。例 2025年3月期' },
          reason: { type: 'string', description: 'flipの根拠、またはflipできない理由を一文で' },
          I: { type: 'string', description: 'flip=trueのときだけ。書き換え後のI列' },
        },
      },
    },
    flipped: { type: 'integer' },
    notes: { type: 'string' },
  },
}

const PROMPT = (b) => `判断基準は /home/user/-/tokium/RULES.md。§3-3 §3-8 §7-1 を読め。
担当データ: ${SP}/catr/in_b${b}.json（配列。各要素に 行・取引先名・最終判定・I・J がある）

## 背景（重要）
RULES §7-1 は「官報決算公告のまとめサイト catr.jp を承認ソースと認めるか」を
未確定事項として残していた。**この判断は「認める」で確定した。**
理由: 同じRULESの §5-3 が「フォンテラジャパン・豊田スチールセンター → 官報決算公告から取得」を
承認ソースの実績として明記しており、ルール自身が官報決算公告を承認ソースとして扱っている。
また §7-1 自身が「官報の無料公開は直近90日分のみで、二次サイトを使わざるを得ない」と
代替経路の不在を認めている。

## お前の仕事
担当行はすべて現在「架電不可」で、本文に catr.jp か §7-1 が出てくる行だ。
**catr.jp を認めた場合に架電可へ戻せる行はどれか**を、I列の記述を読んで1行ずつ判定しろ。

### flip = true にする条件（すべて満たすこと）
1. **除外の理由が「出典が catr.jp だから」だけである。** I列が「金額自体は整合」
   「独立検索でも一致」のように**数値そのものは確認できたと述べている**こと。
2. 採用すべき売上高が **300億円以上**であること（§3-3。子会社なら単体で）。
3. 決算期が **直近3期以内**であること（§3-8）。I列に決算期が書かれているはずだ。
4. 法人格が株式会社等でよいこと（§3-6。合同会社・有限会社・個人事業はNG）。

### flip = false にする行（よくある型。取り違えるな）
- **数値が300億未満**で除外された行。catr.jpの可否と関係ない（例: 豊田スチールセンター189.65億）。
- **決算期が古い**行。§3-8で失格（例: ヤマザキマザックトレーディングは第58期＝2020年3月期）。
- **本文に到達できず数値が取れていない**行。「PDFの数値は検索で取得できず」「未到達」など。
  catr.jpを認めても数値が無いなら架電可にはできない（例: ENEOS Xploraは保留）。
- I列が「○ 妥当」で始まる行。これは**元の除外判定が正しいと確認済み**の意味であって、
  catr.jpのせいで落ちているのではない。触るな。
- 元判定が × で、その×が妥当と確認されている行。

**判断に迷ったら flip = false にしろ。** 誤って架電可にすると、アポインターが
基準を満たさない企業に架電して無報酬になる（§1で最も避けるべき事故とされている）。
逆に flip し損ねても、元々架電不可だったものが据え置かれるだけで新たな害はない。

### flip = true のとき、I列を書き直せ
「○ 回収（§7-1確定）：」で始め、**売上高・決算期・単体か連結か・出典**を明記し、
最後に「出典は官報決算公告（catr.jp 収録）。§7-1 は承認する方針で確定。」と付けろ。
元のI列に書かれている検算（親会社連結比10%超、桁の確認など）は残せ。

## 禁止
- **WebSearch も WebFetch も使うな。** この作業は手元のI列を読むだけで完結する。
  新しく調べる必要はないし、この環境では外部ドメインに到達できない。
- 数値を自分で作るな。I列に書かれている数値だけを使え。
- **百万円・千円表記があれば自分で億円に直せ**（1,000百万円=10億円 / 1,000,000千円=10億円）。

担当ブロック番号 ${b} を block に入れて返せ。decisions には**担当した全行**を入れろ（flipしない行も）。`

const out = await parallel(
  Array.from({ length: NB }, (_, b) => () =>
    agent(PROMPT(b), { label: `catr:b${b}`, phase: 'Classify', schema: SCHEMA })
      .catch(e => ({ block: b, decisions: [], error: String(e) })))
)
return out
