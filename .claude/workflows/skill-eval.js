export const meta = {
  name: 'skill-eval',
  description: 'skill 多臂对照评测：用例 × 臂 × 重复次数，执行 agent 作答后由不知臂别的评分 agent 逐条断言判定',
  whenToUse: 'skill-creator 迭代中需要对比新 skill / 旧 skill 快照 / 无 skill 的效果时，通过 args 传入用例与臂配置',
  phases: [
    { title: '预检', detail: '基线污染检查（args.preflight 给出条件时才运行）' },
    { title: '执行', detail: '有 skill 的臂先读 skill 再作答；无 skill 的臂直接作答' },
    { title: '评分', detail: '只拿到回答正文与断言，不知道臂别，不读文件' },
  ],
}

// ---------------------------------------------------------------------------
// 引数の正規化
//   この script はファイルシステムに触れないため、用例本文・断言は args で受け取る。
//   args 例:
//   {
//     iterationDir: 'C:/tmp/claude-skills/module-first-workspace/iteration-4',
//     tag: 'iter4',                       // 省略時は iterationDir の末尾ディレクトリ名
//     arms: [
//       { name: 'with_skill',    skill: 'C:/tmp/claude-skills/module-first/SKILL.md' },
//       { name: 'old_skill',     skill: 'C:/tmp/claude-skills/module-first-workspace/skill-snapshot-v3/SKILL.md' },
//       { name: 'without_skill', skill: null },
//     ],
//     evals: <evals.json の内容そのまま、または evals 配列>,
//     runs: 2,
//     executorModel: 'sonnet', graderModel: 'opus', preflightModel: 'sonnet',
//     graderRetries: 1,                   // 評分 agent が構造化出力に失敗したときの再試行回数
//     preflight: ['C:/Users/lsc/.claude/skills/module-first が存在しない', ...],   // 省略可
//   }
//   評分 agent は長い JSON を返すため haiku では構造化出力に失敗しやすい（煙テストで実証）。sonnet 以上を使う。
// ---------------------------------------------------------------------------
const A = args && typeof args === 'object' ? args : {}
const slash = p => String(p).replace(/\\/g, '/').replace(/\/+$/, '')
const fail = msg => { throw new Error(`skill-eval: ${msg}`) }
const NAME_RE = /^[A-Za-z0-9][A-Za-z0-9_-]*$/

if (!A.iterationDir) fail('args.iterationDir 必填（本轮产出目录，如 .../module-first-workspace/iteration-4）')
const ITER = slash(A.iterationDir)
const TAG = A.tag ? String(A.tag) : ITER.split('/').pop()
if (!/^[A-Za-z0-9_.-]+$/.test(TAG)) fail(`tag "${TAG}" 只能含字母数字 _ . -`)
const RUNS = Number.isInteger(A.runs) && A.runs > 0 ? A.runs : 2
const MIN_ANSWER_CHARS = Number.isInteger(A.minAnswerChars) ? A.minAnswerChars : 200
const GRADER_RETRIES = Number.isInteger(A.graderRetries) && A.graderRetries >= 0 ? A.graderRetries : 1
const MODELS = {
  executor: A.executorModel || 'sonnet',
  grader: A.graderModel || 'opus',
  preflight: A.preflightModel || 'sonnet',
}

const ARMS = (Array.isArray(A.arms) ? A.arms : []).map(a => ({
  name: String((a && a.name) || ''),
  skill: a && a.skill ? slash(a.skill) : null,
}))
if (!ARMS.length) fail('args.arms 至少一个，如 [{name:"with_skill", skill:"<SKILL.md 路径>"}, {name:"without_skill", skill:null}]')
ARMS.forEach(a => { if (!NAME_RE.test(a.name)) fail(`臂名 "${a.name}" 只能含字母数字 _ -（会用作目录名）`) })
if (new Set(ARMS.map(a => a.name)).size !== ARMS.length) fail('臂名重复')

const rawEvals = Array.isArray(A.evals) ? A.evals
  : (A.evals && Array.isArray(A.evals.evals)) ? A.evals.evals : []
const EVALS = rawEvals.map(e => ({
  id: e.id,
  name: String(e.name || e.eval_name || ''),
  prompt: String(e.prompt || ''),
  assertions: Array.isArray(e.assertions) ? e.assertions.map(String) : [],
}))
if (!EVALS.length) fail('args.evals 为空（可直接传 evals.json 的内容，或其中的 evals 数组）')
EVALS.forEach(e => {
  if (!Number.isInteger(e.id)) fail(`用例 "${e.name}" 的 id 必须是整数`)
  if (!NAME_RE.test(e.name)) fail(`用例名 "${e.name}" 只能含字母数字 _ -（会用作目录名）`)
  if (!e.prompt.trim()) fail(`用例 ${e.id} 缺 prompt`)
  if (!e.assertions.length) fail(`用例 ${e.id} 缺 assertions`)
})
if (new Set(EVALS.map(e => e.id)).size !== EVALS.length) fail('用例 id 重复')

const PREFLIGHT = (Array.isArray(A.preflight) ? A.preflight : []).map(String).filter(s => s.trim())

// ---------------------------------------------------------------------------
// ジョブ生成
//   marker は後処理がトランスクリプトを run に対応付けるための目印。
//   評分 agent には臂名を一切渡さない（label は進捗表示専用で agent には見えない）。
// ---------------------------------------------------------------------------
const jobs = EVALS.flatMap(e => ARMS.flatMap(arm =>
  Array.from({ length: RUNS }, (_, k) => ({ e, arm, run: k + 1 })),
)).map((j, i) => ({ ...j, id: i }))
const runDir = j => `${ITER}/eval-${j.e.id}-${j.e.name}/${j.arm.name}/run-${j.run}`
const marker = (j, role) => `[eval-job ${TAG}#${j.id}] [role: ${role}]`

// ---------------------------------------------------------------------------
// 予検（任意）：基線臂が汚染されていないかを実測で確認する
// ---------------------------------------------------------------------------
const PREFLIGHT_SCHEMA = {
  type: 'object',
  properties: {
    checks: { type: 'array', items: { type: 'object', properties: {
      condition: { type: 'string' }, ok: { type: 'boolean' }, evidence: { type: 'string' } },
      required: ['condition', 'ok', 'evidence'] } },
  },
  required: ['checks'],
}

function preflightPrompt() {
  const list = PREFLIGHT.map((c, i) => `${i + 1}. ${c}`).join('\n')
  return `你是评测前的环境预检员。逐条用 Bash / Read 等工具实际核实下面的条件是否成立。只读，不要修改任何文件。

每条返回：condition（逐字复制条件原文）、ok（true = 条件成立）、evidence（你实际执行的命令与关键输出，一两行）。
拿不准的判 ok=false。

条件：
${list}`
}

// ---------------------------------------------------------------------------
// 執行 agent：skill 有無だけが異なり、それ以外の指示は全臂で同一
// ---------------------------------------------------------------------------
function execPrompt(j) {
  const head = j.arm.skill
    ? `先用 Read 工具完整阅读这个 skill 文件：${j.arm.skill}\n然后严格遵循该 skill 的规范来回答下面的问题。\n\n`
    : '回答下面的问题。\n\n'
  return `${marker(j, 'executor')}（上一行是归档标记，与问题无关，不要在回答中提及）

${head}问题：
${j.e.prompt}

要求：
- 像直接回复提问者一样作答（markdown）。不要写「根据 skill」「按照规范」之类的元叙述，也不要提到你读过什么文件。
- 不要创建或写入任何文件。
- 你的最终返回值必须就是完整的回答正文本身，逐字、完整，前后不加任何说明、确认或标记。`
}

// ---------------------------------------------------------------------------
// 評分 agent：回答本文と断言だけを渡す（ファイルもパスも渡さない → 臂別を知り得ない）
// ---------------------------------------------------------------------------
const GRADING_SCHEMA = {
  type: 'object',
  properties: {
    expectations: { type: 'array', items: { type: 'object', properties: {
      text: { type: 'string' }, passed: { type: 'boolean' }, evidence: { type: 'string' } },
      required: ['text', 'passed', 'evidence'] } },
    claims: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, type: { type: 'string', enum: ['factual', 'process', 'quality'] },
      verified: { type: 'boolean' }, evidence: { type: 'string' } },
      required: ['claim', 'type', 'verified', 'evidence'] } },
    eval_feedback: { type: 'object', properties: {
      suggestions: { type: 'array', items: { type: 'object', properties: {
        assertion: { type: 'string' }, reason: { type: 'string' } }, required: ['reason'] } },
      overall: { type: 'string' } }, required: ['suggestions', 'overall'] },
    quality_note: { type: 'string' },
  },
  required: ['expectations', 'claims', 'eval_feedback', 'quality_note'],
}

function gradePrompt(j, answer) {
  const list = j.e.assertions.map((a, i) => `${i + 1}. ${a}`).join('\n')
  return `${marker(j, 'grader')}（上一行是归档标记，与评分无关）

你是评分员。评估一份 AI 对用户问题的回答是否满足一组断言。
你只能依据下面给出的文本评分：不要读取任何文件，不要推测这份回答是在什么条件下生成的。

用户的原始问题：
${j.e.prompt}

被评估的回答（完整原文，位于 <<<ANSWER 与 ANSWER>>> 之间）：
<<<ANSWER
${answer}
ANSWER>>>

断言清单：
${list}

评分规则：
- PASS 需要回答中有明确、具体的证据，且是实质性地满足断言，而不是表面提到关键词。evidence 必须引用回答原文。
- 断言要求「给出具体机制/手段/信号/判据」的，回答只声明规则而无具体手段，判 FAIL。
- 「贴题」与「内部一致」是减分型断言：发现用户未提及的设定被当作既定前提、或前后矛盾的表述，即 FAIL 并引用原文。
- FAIL：找不到证据、证据相反、或只是擦边提及。举证责任在断言一方——不确定就 FAIL。
- expectations 与断言清单一一对应、顺序一致，text 字段逐字复制断言原文。

评完断言后：列出值得核验的隐含主张（claims）并判断；批评断言本身（eval_feedback，标准放高——只提用例作者会说「good catch」的问题，没有就空数组）；quality_note 给独立的整体判断。`
}

// ---------------------------------------------------------------------------
// 実行
// ---------------------------------------------------------------------------
if (PREFLIGHT.length) {
  log(`预检 ${PREFLIGHT.length} 项基线条件（${MODELS.preflight}）`)
}
const preflight = PREFLIGHT.length
  ? await agent(preflightPrompt(), { label: 'preflight', phase: '预检', model: MODELS.preflight, effort: 'low', schema: PREFLIGHT_SCHEMA })
  : null
if (PREFLIGHT.length) {
  const bad = preflight ? preflight.checks.filter(c => !c.ok) : [{ condition: '(预检 agent 无返回)', ok: false, evidence: '' }]
  if (bad.length) {
    bad.forEach(c => log(`预检未通过：${c.condition} —— ${c.evidence}`))
    return { aborted: true, reason: '预检未通过，未运行任何评测', tag: TAG, iteration_dir: ITER, preflight }
  }
  log('预检通过')
}

log(`${EVALS.length} 用例 × ${ARMS.length} 臂 × ${RUNS} 次 = ${jobs.length} 个执行 agent（${MODELS.executor}），各自完成后立即评分（${MODELS.grader}）`)

// 段階の中で throw すると pipeline はその項目を null にして以降を飛ばし、
// 「どこで失敗したか」も回答本文も失われる。失敗は各段階の中で捕まえて run に記録する。
const describe = err => (err && err.message) ? err.message : String(err)
const answerOk = a => typeof a === 'string' && a.trim().length >= MIN_ANSWER_CHARS
const jobName = j => `${j.arm.name}:${j.e.name}#${j.run}`

async function runExecutor(j) {
  try {
    const answer = await agent(execPrompt(j), { label: jobName(j), phase: '执行', model: MODELS.executor })
    if (answer == null) return { answer: null, exec_error: '执行 agent 无返回（被跳过或终止）' }
    if (!answerOk(answer)) return { answer: String(answer), exec_error: `回答过短（${String(answer).trim().length} 字符 < ${MIN_ANSWER_CHARS}）` }
    return { answer, exec_error: null }
  } catch (err) {
    return { answer: null, exec_error: `执行 agent 出错：${describe(err)}` }
  }
}

async function gradeOnce(j, answer, attempt) {
  const label = `grade:${jobName(j)}${attempt ? `(retry${attempt})` : ''}`
  try {
    const g = await agent(gradePrompt(j, answer), { label, phase: '评分', model: MODELS.grader, effort: 'high', schema: GRADING_SCHEMA })
    return g ? { grading: g, error: null } : { grading: null, error: '评分 agent 无返回（被跳过或终止）' }
  } catch (err) {
    return { grading: null, error: describe(err) }
  }
}

async function runGrader(exec, j) {
  if (exec.exec_error) {
    log(`执行失败 ${jobName(j)} —— ${exec.exec_error}`)
    return { ...exec, grading: null, grade_error: null }
  }
  const errors = []
  for (let attempt = 0; attempt <= GRADER_RETRIES; attempt++) {
    const once = await gradeOnce(j, exec.answer, attempt)
    if (once.grading) return { ...exec, grading: once.grading, grade_error: null }
    errors.push(once.error)
    if (attempt < GRADER_RETRIES) log(`评分重试 ${jobName(j)} —— ${once.error}`)
  }
  const why = `评分失败（${errors.length} 次）：${errors.join(' / ')}`
  log(`${jobName(j)} —— ${why}`)
  return { ...exec, grading: null, grade_error: why }
}

const graded = await pipeline(jobs, runExecutor, runGrader)

// ---------------------------------------------------------------------------
// 集計
//   grading が無い run は summary=null のまま返す（後処理は grading.json を書かず、
//   aggregate はその run を除外する。基盤の失敗を skill の失敗として数えない）。
// ---------------------------------------------------------------------------
const runs = jobs.map((j, i) => {
  const r = graded[i] || { answer: null, exec_error: '流水线中断（该项无结果）', grading: null, grade_error: null }
  const total = j.e.assertions.length
  const ex = r.grading ? r.grading.expectations : null
  const passed = ex ? Math.min(total, ex.filter(x => x.passed).length) : 0
  const countMismatch = ex && ex.length !== total ? `评分返回 ${ex.length} 条，断言 ${total} 条` : null
  const gradeError = r.grade_error || countMismatch
  const summary = ex
    ? { passed, failed: total - passed, total, pass_rate: Math.round((passed / total) * 100) / 100 }
    : null
  return {
    job_id: j.id, eval_id: j.e.id, eval_name: j.e.name, configuration: j.arm.name, run: j.run,
    run_dir: runDir(j), answer: r.answer, exec_error: r.exec_error, grade_error: gradeError,
    grading: r.grading, summary,
  }
})

for (const r of runs) {
  const s = r.summary ? `${r.summary.passed}/${r.summary.total}` : `无有效评分（${r.exec_error || r.grade_error}）`
  const warn = r.grade_error && r.summary ? `（注意：${r.grade_error}）` : ''
  log(`${r.configuration.padEnd(14)} ${r.eval_name}#${r.run}: ${s}${warn}`)
}
for (const arm of ARMS) {
  const all = runs.filter(r => r.configuration === arm.name)
  const ok = all.filter(r => r.summary)
  const p = ok.reduce((s, r) => s + r.summary.passed, 0)
  const t = ok.reduce((s, r) => s + r.summary.total, 0)
  log(`合计 ${arm.name}: ${p}/${t}（${ok.length}/${all.length} 次运行有效）`)
}

return {
  tag: TAG,
  iteration_dir: ITER,
  runs_per_configuration: RUNS,
  models: MODELS,
  arms: ARMS,
  evals: EVALS.map(e => ({ eval_id: e.id, eval_name: e.name, prompt: e.prompt, assertions: e.assertions })),
  preflight,
  runs,
}
