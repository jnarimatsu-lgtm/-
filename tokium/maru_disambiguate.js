export const meta = {
  name: 'tokium-maru-disambiguate',
  description: '元△×で I列が「○」の294行を、架電可か架電不可かに読み分ける',
  phases: [{ title: 'Disambiguate', detail: 'I列の結論を読んで判定を確定' }],
}

const SP = '/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad'
const NB = 6

const SCHEMA = {
  type: 'object',
  required: ['block', 'decisions'],
  properties: {
    block: { type: 'integer' },
    decisions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['row', 'callable', 'reason'],
        properties: {
          row: { type: 'integer' },
          callable: { type: 'boolean', description: 'true＝架電可。false＝架電不可' },
          g_correction: { type: 'boolean', description: 'G列の訂正が要るか' },
          amount_oku: { type: ['number', 'null'] },
          period: { type: 'string' },
          reason: { type: 'string' },
        },
      },
    },
    callable_count: { type: 'integer' },
    notes: { type: 'string' },
  },
}

const PROMPT = (b) => `判断基準は /home/user/-/tokium/RULES.md。§3-3 §3-5 §3-6 §3-8 を読め。
担当データ: ${SP}/maru/in_b${b}.json（配列。行・取引先名・元H判定・いまの最終判定・I・J）

## 直さなければいけないバグ
集計プログラムが **I列の「○」の意味を取り違えている。**

元のH列が △ や × だった行に、検証エージェントが「○ 妥当」と書いたとき、
プログラムは一律に「**元の除外が正しかった**」と解釈して架電不可にしていた。
ところが実際には、エージェントは2つの意味で「○ 妥当」を使っていた:

- **(a) 除外が正しい** … 例「○ 妥当（△判定が正しい）。…したがって単体売上高は非公表で確認不可」
- **(b) この会社は基準を満たす。ただしG列に訂正が要る** … 例「○ 妥当（G列訂正：601億円
  （2026年3月期・単体））…単体601億で300億以上のため架電可」

(b) を架電不可にすると、**架電できたはずの企業を落とす**ことになる（§1が実害と明記）。
実例: 東海旅客鉄道（連結営業収益2兆62億円）が架電不可になっていた。

## お前の仕事
担当行を1行ずつ読み、**その会社に架電してよいか**を決めろ。I列に書かれた結論に従え。

### callable = true にする条件（すべて満たす）
1. I列が、その会社が**300億円以上**の売上高を持つと述べている。
2. §3-3 を満たす。**子会社なら単体で300億以上**であること。
   I列が「子会社だが単体◯◯億」と書いていれば可。「連結値しか無い子会社」なら不可。
   親会社・持株会社なら連結値でよい。
3. §3-8 を満たす。**決算期が直近3期以内**であること。
4. §3-6 を満たす。株式会社等であること（合同会社・有限会社・個人事業は不可）。
5. 法人格が消滅していない（合併で消えた会社は不可）。

### callable = false にする行
- I列が「△判定が正しい」「確認不可で正しい」「除外結論は維持」「載せてはいけない」など、
  **明示的に除外を支持している**行。
- 売上高が承認ソースで確認できていない行。**金額が無いなら架電可にはできない。**
- 300億未満、決算期が古い、子会社なのに連結値しかない、法人格が消滅した行。

**迷ったら false にしろ。** 誤って架電可にすると、アポインターが基準を満たさない企業に
架電して無報酬になる（§1で最も避けるべき事故）。

## 禁止
- **WebSearch も WebFetch も使うな。** 手元のI列を読むだけで完結する作業だ。
  この環境は外部ドメインが全遮断されているので、そもそも到達できない。
- 新しい数値を自分で作るな。I列に書かれている数値だけを使え。
- **百万円・千円表記は自分で億円に直せ**（1,000百万円=10億円 / 1,000,000千円=10億円）。
  例: 2,006,218百万円＝2兆62.18億円。

担当ブロック番号 ${b} を block に入れ、decisions には**担当した全行**を入れろ。`

const out = await parallel(
  Array.from({ length: NB }, (_, b) => () =>
    agent(PROMPT(b), { label: `maru:b${b}`, phase: 'Disambiguate', schema: SCHEMA })
      .catch(e => ({ block: b, decisions: [], error: String(e) })))
)
return out
