export const meta = {
  name: 'tokium-edge-verify',
  description: '採用値が300〜350億の64行を再検証する（誤りが判定を反転させる帯）',
  phases: [{ title: 'Verify', detail: '基準ぎりぎりの行を1件ずつ裏取り' }],
}

const SP = '/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad'
const NB = 6

const SCHEMA = {
  type: 'object',
  required: ['block', 'rows'],
  properties: {
    block: { type: 'integer' },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        required: ['row', 'verdict', 'reason'],
        properties: {
          row: { type: 'integer' },
          verdict: { type: 'string', description: '維持 / 降格 のいずれか' },
          confirmed_oku: { type: ['number', 'null'] },
          period: { type: 'string' },
          reason: { type: 'string' },
          I: { type: 'string', description: '書き換える場合のみ' },
          J: { type: 'string' },
        },
      },
    },
    searches_used: { type: 'integer' },
    notes: { type: 'string' },
  },
}

const PROMPT = (b) => `判断基準は /home/user/-/tokium/RULES.md。まず読め。
担当データ: ${SP}/edge/in_b${b}.json（配列。行・取引先名・採用値_億・I・J がある）

## なぜこの行たちなのか
担当行は全て「架電可」で成果物に載っているが、**採用値が300〜350億円**しかない。
基準は300億なので、**数値が少しでも違えば判定が反転する帯**だ。ここだけは
1,000億超の行と同じ扱いにはできない。アポインターが実際に電話する行なので、
誤って載っていると無報酬の架電が発生する（§1で最も避けるべき事故）。

## やること
各行について、**採用値を独立に裏取りしろ。** 具体的には:
1. **金額が正しいか。** 別のクエリで同じ数値が出るか。特に百万円・千円表記の
   桁誤りを疑え（1,000百万円=10億円 / 1,000,000千円=10億円）。
   検索要約は原文の百万円を勝手に億に換算して**桁を落とす**ことがある（実測）。
2. **決算期が直近3期以内か**（§3-8）。検索は見つからないとき前年度の値を
   もっともらしく返すので、必ず「何年何月期か」を確認しろ。
3. **単体か連結か**（§3-3）。子会社なら単体で300億以上が必要。親会社・持株会社なら連結可。
4. **その数字が売上高か**（§3-7）。総資産・取扱高・利益は売上高ではない。

## 判定
- 裏が取れて300億以上 → verdict "維持"。confirmed_oku と period を埋めろ。
- **300億未満と判明した、または数値・決算期・単体連結の別に誤りがあって
  300億以上を主張できなくなった → verdict "降格"。** これが最も重要な成果だ。
  I列を「△」または「×」で始まる文に書き直せ（数値が300億未満と確定したら×、
  確定できないだけなら△）。
- 裏が取れず、かつ元の記述にも疑いが無い → "維持"。ただし reason に
  「独立再現できず」と正直に書け。**検証していない行に「確認した」と書くな。**

## 検索予算
**この実行全体で WebSearch は残り100回程度しかない。お前の上限は15クエリだ。**
11行あるので1行あたり1〜2クエリ。**元の記述が既に強い出典（有報・決算短信・
決算公告）を挙げていて桁も整合している行は0クエリで維持してよい。**
疑わしい行に予算を寄せろ。WebFetch は全ドメイン遮断なので呼ぶな。

担当ブロック番号 ${b} を block に入れ、rows には**担当した全行**を入れろ。`

const out = await parallel(
  Array.from({ length: NB }, (_, b) => () =>
    agent(PROMPT(b), { label: `edge:b${b}`, phase: 'Verify', schema: SCHEMA })
      .catch(e => ({ block: b, rows: [], error: String(e) })))
)
return out
