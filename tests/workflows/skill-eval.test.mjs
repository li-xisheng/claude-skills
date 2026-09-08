// skill-eval.js の単体テスト。
// Workflow ランタイム（agent / pipeline / log ...）をモックして、失敗の帰属・評分の再試行・
// 盲評（評分 prompt に臂名やパスが漏れない）・引数検証を確定的に確認する。
// 実行: node tests/workflows/skill-eval.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SCRIPT = resolve(here, '../../.claude/workflows/skill-eval.js')
// 実ランタイムと同じく「async 関数の本体」として評価する（export を外し、グローバルを引数で渡す）
const body = readFileSync(SCRIPT, 'utf8').replace(/^export const meta/m, 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const script = new AsyncFunction('args', 'agent', 'pipeline', 'parallel', 'log', 'phase', 'budget', 'workflow', body)

// pipeline のモック：項目ごとに段階を順に通し、段階が throw したら null（実ランタイムと同じ挙動）
async function pipeline(items, ...stages) {
  return Promise.all(items.map(async (item, i) => {
    let prev = item
    for (const stage of stages) {
      try { prev = await stage(prev, item, i) } catch { return null }
    }
    return prev
  }))
}
const parallel = thunks => Promise.all(thunks.map(t => t().catch(() => null)))

function harness(agentImpl) {
  const calls = []
  const logs = []
  const agent = async (prompt, opts) => {
    calls.push({ prompt, opts })
    return agentImpl(prompt, opts, calls.length)
  }
  const budget = { total: null, spent: () => 0, remaining: () => Infinity }
  const run = args => script(args, agent, pipeline, parallel, m => logs.push(m), () => {}, budget, null)
  return { run, calls, logs }
}

const LONG_ANSWER = '这是一段足够长的回答，用来通过最短长度检查。'.repeat(20)
const role = prompt => /\[role: (executor|grader)\]/.exec(prompt)?.[1]
const grading = (n, passed = n) => ({
  expectations: Array.from({ length: n }, (_, i) => ({ text: `a${i}`, passed: i < passed, evidence: 'e' })),
  claims: [],
  eval_feedback: { suggestions: [], overall: '' },
  quality_note: '',
})

const baseArgs = () => ({
  iterationDir: 'C:\\ws\\iteration-9',
  arms: [{ name: 'with_skill', skill: 'C:\\skills\\demo\\SKILL.md' }, { name: 'without_skill', skill: null }],
  evals: { skill_name: 'demo', evals: [{ id: 3, eval_name: 'case-a', prompt: '问题正文', assertions: ['断言一', '断言二', '断言三'] }] },
  runs: 1,
  executorModel: 'haiku',
  graderModel: 'sonnet',
})

test('正常系：返回形状、盲评、各臂指示只差读 skill 那一句', async () => {
  const h = harness(p => (role(p) === 'executor' ? LONG_ANSWER : grading(3, 2)))
  const out = await h.run(baseArgs())

  assert.equal(out.tag, 'iteration-9')
  assert.equal(out.iteration_dir, 'C:/ws/iteration-9')
  assert.equal(out.runs.length, 2)
  assert.deepEqual(out.runs.map(r => r.summary.passed), [2, 2])
  assert.equal(out.runs[0].run_dir, 'C:/ws/iteration-9/eval-3-case-a/with_skill/run-1')
  assert.equal(out.runs[0].configuration, 'with_skill')
  assert.equal(out.evals[0].eval_id, 3)
  assert.equal(out.evals[0].eval_name, 'case-a')

  const graders = h.calls.filter(c => role(c.prompt) === 'grader')
  assert.equal(graders.length, 2)
  for (const g of graders) {
    for (const leak of ['with_skill', 'without_skill', 'old_skill', 'SKILL.md', 'C:/', 'C:\\']) {
      assert.ok(!g.prompt.includes(leak), `评分 prompt 泄露了 ${leak}`)
    }
    assert.ok(g.prompt.includes(LONG_ANSWER), '评分 prompt 必须内嵌完整回答')
    assert.ok(g.prompt.includes('1. 断言一\n2. 断言二\n3. 断言三'))
    assert.equal(g.opts.model, 'sonnet')
    assert.deepEqual(g.opts.schema.required, ['expectations', 'claims', 'eval_feedback', 'quality_note'])
  }

  const execs = h.calls.filter(c => role(c.prompt) === 'executor')
  assert.equal(execs.length, 2)
  assert.ok(execs.every(c => c.opts.model === 'haiku'))
  assert.ok(!execs[0].prompt.includes('断言一'), '执行 prompt 不得含断言')
  const strip = s => s
    .replace(/^\[eval-job [^\]]+\] \[role: executor\]/, '')
    .replace(/先用 Read 工具完整阅读这个 skill 文件：[^\n]*\n然后严格遵循该 skill 的规范来回答下面的问题。\n\n/, '回答下面的问题。\n\n')
  assert.equal(strip(execs[0].prompt), strip(execs[1].prompt))
})

test('评分 agent 抛错一次后重试成功', async () => {
  let graderCalls = 0
  const h = harness(p => {
    if (role(p) === 'executor') return LONG_ANSWER
    graderCalls += 1
    if (graderCalls === 1) throw new Error('StructuredOutput retry cap (5) exceeded')
    return grading(3)
  })
  const out = await h.run({ ...baseArgs(), arms: [{ name: 'with_skill', skill: 'C:/s/SKILL.md' }] })

  assert.equal(graderCalls, 2)
  assert.equal(out.runs[0].grade_error, null)
  assert.equal(out.runs[0].summary.passed, 3)
  assert.ok(h.calls.some(c => c.opts.label.endsWith('(retry1)')))
  assert.ok(h.logs.some(m => m.startsWith('评分重试')))
})

test('评分持续失败：保留回答，标为评分失败而非执行失败，summary 为 null', async () => {
  const h = harness(p => {
    if (role(p) === 'executor') return LONG_ANSWER
    throw new Error('boom')
  })
  const out = await h.run({ ...baseArgs(), arms: [{ name: 'a', skill: null }], graderRetries: 1 })
  const r = out.runs[0]

  assert.equal(r.answer, LONG_ANSWER)
  assert.equal(r.exec_error, null)
  assert.match(r.grade_error, /评分失败（2 次）/)
  assert.equal(r.grading, null)
  assert.equal(r.summary, null)
  assert.equal(h.calls.filter(c => role(c.prompt) === 'grader').length, 2)
})

test('执行 agent 无返回 / 回答过短：记为执行失败且不调用评分', async () => {
  const h = harness(p => {
    if (role(p) !== 'executor') return grading(3)
    return p.includes('SKILL.md') ? null : '短'
  })
  const out = await h.run(baseArgs())

  assert.match(out.runs[0].exec_error, /无返回/)
  assert.match(out.runs[1].exec_error, /回答过短/)
  assert.equal(h.calls.filter(c => role(c.prompt) === 'grader').length, 0)
  assert.ok(out.runs.every(r => r.summary === null && r.grading === null))
})

test('评分条数与断言数不一致：记 grade_error，total 仍按断言数', async () => {
  const h = harness(p => (role(p) === 'executor' ? LONG_ANSWER : grading(2, 2)))
  const out = await h.run({ ...baseArgs(), arms: [{ name: 'a', skill: null }] })

  assert.match(out.runs[0].grade_error, /评分返回 2 条，断言 3 条/)
  assert.deepEqual(out.runs[0].summary, { passed: 2, failed: 1, total: 3, pass_rate: 0.67 })
})

test('预检未通过：中止，不启动任何执行 agent', async () => {
  const h = harness(() => ({ checks: [
    { condition: 'x', ok: true, evidence: '' },
    { condition: 'y', ok: false, evidence: 'exists' },
  ] }))
  const out = await h.run({ ...baseArgs(), preflight: ['x', 'y'] })

  assert.equal(out.aborted, true)
  assert.equal(h.calls.length, 1)
  assert.equal(h.calls[0].opts.model, 'sonnet')
  assert.ok(h.logs.some(m => m.includes('预检未通过：y')))
})

test('参数校验：缺 iterationDir、非法臂名、空用例、非整数 id、非法 tag 都拒绝', async () => {
  const h = harness(() => LONG_ANSWER)
  await assert.rejects(h.run({ ...baseArgs(), iterationDir: undefined }), /iterationDir/)
  await assert.rejects(h.run({ ...baseArgs(), arms: [{ name: 'bad name', skill: null }] }), /臂名/)
  await assert.rejects(h.run({ ...baseArgs(), evals: [] }), /evals 为空/)
  await assert.rejects(h.run({ ...baseArgs(), evals: [{ id: 'x', eval_name: 'n', prompt: 'p', assertions: ['a'] }] }), /id 必须是整数/)
  await assert.rejects(h.run({ ...baseArgs(), tag: 'bad tag' }), /tag/)
  assert.equal(h.calls.length, 0)
})
