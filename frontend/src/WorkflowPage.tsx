import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Check, ChevronDown, CircleHelp, FileCode2, GitPullRequest, LoaderCircle, ShieldCheck, Sparkles, TestTube2 } from 'lucide-react'
import { api } from './api'

type Issue = { number?: number; title: string; body: string; labels?: string[]; stack_trace?: string; origin: 'demo' | 'github' | 'manual'; repository?: string }
type Evidence = { file_path: string; symbol: string; line_start: number; line_end: number; excerpt: string }
type Workflow = {
  workflow_id: string; repository_id: string; status: string; final_status?: string | null; issue: Issue
  investigation?: { root_cause: string; confidence: number; affected_files: string[]; affected_symbols: string[]; evidence: Evidence[]; recommendations: string[] } | null
  plan?: { step: string; detail: string; files_to_modify: string[] }[] | null
  patch?: { unified_diff: string; additions: string[]; deletions: string[]; changed_symbols: string[]; risk_warnings: string[]; applied_to_repository: boolean } | null
  test?: { file: string; code: string; expected_behavior: string; framework: string } | null
  verification?: { status: string; isolation?: string; before?: RunResult; after?: RunResult; changed_files?: string[] } | null
  review?: Record<string, any> | null; approval?: { approved: boolean; decision?: string } | null
}
type RunResult = { status: string; command: string; exit_code: number | null; stdout: string; stderr: string }

const stages = ['ISSUE', 'INVESTIGATE', 'PLAN', 'PATCH', 'TEST', 'VERIFY', 'REVIEW']

export default function WorkflowPage({ repositoryId, workflow, setWorkflow, initialIssue, clearInitialIssue }: {
  repositoryId: string; workflow: Workflow | null; setWorkflow: (value: Workflow) => void
  initialIssue: Issue | null; clearInitialIssue: () => void
}) {
  const [issues, setIssues] = useState<Issue[]>([])
  const [issue, setIssue] = useState<Issue | null>(initialIssue)
  const [stackTrace, setStackTrace] = useState('')
  const [githubMessage, setGithubMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null)

  useEffect(() => {
    api<{ items: Issue[] }>('/api/workflow/demo-issues').then(result => {
      const rows = result.items.map(item => ({ ...item, origin: 'demo' as const }))
      setIssues(rows)
      if (!initialIssue) setIssue(current => current ?? rows[0] ?? null)
    }).catch(() => setError('Could not load the bundled demo issues. Check that the API is running.'))
    if (!workflow) {
      api<Workflow[]>(`/api/workflow?repository_id=${encodeURIComponent(repositoryId)}`)
        .then(rows => { if (rows.length) setWorkflow(rows[0]) })
        .catch(() => undefined)
    }
  }, [repositoryId])

  useEffect(() => {
    if (initialIssue) {
      setIssue(initialIssue)
      setStackTrace(initialIssue.stack_trace ?? '')
      clearInitialIssue()
    }
  }, [initialIssue])

  const completed = useMemo(() => [
    Boolean(workflow), Boolean(workflow?.investigation), Boolean(workflow?.plan),
    Boolean(workflow?.patch), Boolean(workflow?.test), workflow?.verification?.status === 'PASS', Boolean(workflow?.review),
  ], [workflow])

  async function loadGithubIssues() {
    setBusy(true); setError(''); setGithubMessage('')
    try {
      const result = await api<{ items: any[]; message?: string }>('/api/issues')
      if (!result.items.length) { setGithubMessage(result.message ?? 'No open GitHub issues were returned.'); return }
      const rows = result.items.map(row => ({ number: row.number, title: row.title, body: row.body ?? '', labels: row.labels ?? [], origin: 'github' as const, repository: row.repository }))
      setIssues(current => [...current.filter(item => item.origin !== 'github'), ...rows])
      setIssue(rows[0])
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load GitHub issues.') }
    finally { setBusy(false) }
  }

  async function investigateIssue() {
    if (!issue) return
    if (issue.origin !== 'demo' || issue.number !== 1) {
      setError('Issue investigation is currently limited to the bundled demo issue until per-user authorization is available.')
      return
    }
    setBusy(true); setError('')
    try {
      const result = await api<Workflow>('/api/workflow/investigate', { method: 'POST', body: JSON.stringify({
        repository_id: repositoryId, origin: issue.origin, issue_number: issue.number,
        issue_title: issue.title, issue_body: issue.body, stack_trace: stackTrace, labels: issue.labels ?? [],
      }) })
      setWorkflow(result)
    } catch (e) { setError(e instanceof Error ? e.message : 'Issue investigation failed.') }
    finally { setBusy(false) }
  }

  async function action(name: string, body?: unknown) {
    if (!workflow) return
    setBusy(true); setError('')
    try {
      const result = await api<Workflow>(`/api/workflow/${encodeURIComponent(workflow.workflow_id)}/${name}`, {
        method: 'POST', ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      })
      setWorkflow(result)
    } catch (e) { setError(e instanceof Error ? e.message : `Workflow ${name} failed.`) }
    finally { setBusy(false) }
  }

  async function approveAndVerify() {
    if (!workflow) return
    setBusy(true); setError('')
    try {
      const approved = await api<Workflow>(`/api/workflow/${encodeURIComponent(workflow.workflow_id)}/approve`, { method: 'POST', body: JSON.stringify({ approved: true }) })
      setWorkflow(approved)
      const verified = await api<Workflow>(`/api/workflow/${encodeURIComponent(workflow.workflow_id)}/verify`, { method: 'POST' })
      setWorkflow(verified)
    } catch (e) { setError(e instanceof Error ? e.message : 'Verification failed.') }
    finally { setBusy(false) }
  }

  return <div className="workflow-page">
    <div className="page-heading"><div><div className="eyebrow">ISSUE TO VERIFIED FIX</div><h1>Investigate an issue</h1><p>Follow the evidence from issue report to a reviewed, testable patch proposal.</p></div><span className="demo-chip">DEMO MODE · PATCH PREVIEW ONLY</span></div>
    {error && <div className="alert error-alert" role="alert"><AlertTriangle size={16}/><span>{error}</span></div>}
    <div className="workflow-steps" aria-label="Workflow progress">{stages.map((stage, index) => <div className={`workflow-stage ${completed[index] ? 'complete' : ''} ${workflow?.status === 'FAILED' && stage === 'VERIFY' ? 'failed' : ''}`} key={stage}><span className="workflow-stage-mark">{completed[index] ? <Check size={13}/> : String(index + 1).padStart(2, '0')}</span><b>{stage}</b>{index < stages.length - 1 && <i/>}</div>)}</div>

    <section className="workflow-section panel issue-section">
      <div className="workflow-section-head"><div><span className="workflow-step-no">01</span><div><h2>Issue</h2><p>Use the bundled issue for an end-to-end run. GitHub issues can be viewed, but investigation awaits per-user authorization.</p></div></div><div className="workflow-head-actions"><button className="button secondary-button" disabled={busy} onClick={loadGithubIssues}>Load public GitHub issues</button>{issues.length > 0 && <label className="sr-only" htmlFor="workflow-issue">Select issue</label>}<select id="workflow-issue" value={issue ? `${issue.origin}:${issue.number ?? issue.title}` : ''} onChange={event => { const selected = issues.find(item => `${item.origin}:${item.number ?? item.title}` === event.target.value); setIssue(selected ?? null) }}><option value="">Select issue</option>{issues.map((item, index) => <option key={`${item.origin}-${item.number}-${index}`} value={`${item.origin}:${item.number ?? item.title}`}>{item.origin === 'github' ? `#${item.number}` : 'DEMO'} · {item.title}</option>)}</select></div></div>
      {githubMessage && <div className="callout subtle-callout"><CircleHelp size={15}/>{githubMessage}</div>}
      {issue ? <div className="workflow-issue-content"><div className="issue-meta"><span>{issue.origin === 'github' ? `#${issue.number ?? '—'} · ${issue.repository ?? 'GitHub issue'}` : `DEMO ISSUE #${issue.number ?? '—'}`}</span>{issue.labels?.map(label => <span className="tag" key={label}>{label}</span>)}</div><h3>{issue.title}</h3><p>{issue.body}</p><label className="field-label" htmlFor="issue-stack">STACK TRACE (OPTIONAL)</label><textarea id="issue-stack" value={stackTrace} onChange={event => setStackTrace(event.target.value)} placeholder="Paste a relevant stack trace if available" rows={3}/><button className="button primary-button" disabled={busy || !issue.body.trim()} onClick={investigateIssue}>{busy ? <LoaderCircle className="spin" size={15}/> : <Sparkles size={15}/>} Investigate issue</button></div> : <div className="output-placeholder"><CircleHelp size={22}/><span>Select a demo issue or load issues from GitHub.</span></div>}
    </section>

    {workflow && <>
      <section className="workflow-section panel">
        <div className="workflow-section-head"><div><span className="workflow-step-no">02</span><div><h2>Investigation</h2><p>Root cause and evidence from indexed repository code.</p></div></div><span className={`status-pill ${workflow.investigation?.confidence ? 'status-ready' : ''}`}>{workflow.status}</span></div>
        {workflow.investigation ? <><div className="investigation-grid"><article><small>SUSPECTED ROOT CAUSE</small><p>{workflow.investigation.root_cause}</p><span>Confidence: {Math.round(workflow.investigation.confidence * 100)}%</span></article><article><small>AFFECTED FILES & SYMBOLS</small>{workflow.investigation.affected_files.map(file => <p className="workflow-path" key={file}><FileCode2 size={14}/>{file}</p>)}<span>{workflow.investigation.affected_symbols.join(', ') || 'No symbol established'}</span></article></div><div className="workflow-evidence"><h3>Evidence</h3>{workflow.investigation.evidence.length ? workflow.investigation.evidence.map((item, index) => { const key = `${item.file_path}:${item.line_start}:${index}`; const expanded = expandedEvidence === key; return <article className="evidence-card" key={key}><button aria-expanded={expanded} onClick={() => setExpandedEvidence(expanded ? null : key)}><FileCode2 size={14}/><span><b>{item.file_path}</b>{item.symbol && <small>{item.symbol} · </small>}lines {item.line_start}–{item.line_end}</span><ChevronDown size={14}/></button>{expanded && <pre><code>{item.excerpt}</code></pre>}</article> }) : <p>No relevant source evidence was found. The system has not inferred a root cause.</p>}</div><ul className="recommendation-list">{workflow.investigation.recommendations.map(item => <li key={item}>{item}</li>)}</ul></> : <p className="muted-line">Run investigation to see affected code and confidence.</p>}
      </section>

      <section className="workflow-section panel">
        <div className="workflow-section-head"><div><span className="workflow-step-no">03</span><div><h2>Plan</h2><p>Proposed steps and files for the reported behavior.</p></div></div>{workflow.investigation && <button className="button secondary-button" disabled={busy} onClick={() => action('plan', { requirement: workflow.issue.title })}><Sparkles size={14}/> {workflow.plan ? 'Regenerate plan' : 'Generate plan'}</button>}</div>
        {workflow.plan?.length ? <ol className="plan-steps">{workflow.plan.map((item, index) => <li className="plan-step" key={`${index}-${item.step}`}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{item.step}</strong><p>{item.detail}</p>{item.files_to_modify.length > 0 && <small>Files: {item.files_to_modify.join(', ')}</small>}</div></li>)}</ol> : <p className="muted-line">Generate a plan after the investigation.</p>}
      </section>

      <section className="workflow-section panel">
        <div className="workflow-section-head"><div><span className="workflow-step-no">04</span><div><h2>Proposed patch</h2><p>Review the exact diff. The repository source remains unchanged.</p></div></div>{workflow.plan && <button className="button secondary-button" disabled={busy} onClick={() => action('patch')}><Sparkles size={14}/>{workflow.patch ? 'Regenerate patch' : 'Propose patch'}</button>}</div>
        {workflow.patch ? <><div className="diff-toolbar"><span>{workflow.patch.changed_symbols.join(', ')}</span><span><ins>+{workflow.patch.additions.length}</ins> <del>−{workflow.patch.deletions.length}</del></span><span className="read-only-pill">PREVIEW · NOT APPLIED</span></div><pre className="workflow-diff"><code>{workflow.patch.unified_diff}</code></pre>{workflow.patch.risk_warnings.map(warning => <div className="callout subtle-callout" key={warning}><AlertTriangle size={15}/>{warning}</div>)}<div className="workflow-actions"><button className="button secondary-button" disabled={busy} onClick={() => action('reject')}>Reject patch</button>{!workflow.test && <button className="button secondary-button" disabled={busy} onClick={() => action('test')}><TestTube2 size={14}/> Generate regression test</button>}{workflow.test && !workflow.approval?.approved && <button className="button primary-button" disabled={busy} onClick={approveAndVerify}>{busy ? <LoaderCircle className="spin" size={14}/> : <ShieldCheck size={14}/>} Approve & verify in temporary copy</button>}</div></> : <p className="muted-line">A patch is available only when the evidence supports a known safe fix.</p>}
      </section>

      {workflow.test && <section className="workflow-section panel"><div className="workflow-section-head"><div><span className="workflow-step-no">05</span><div><h2>Regression test</h2><p>{workflow.test.expected_behavior}</p></div></div><span className="tag">{workflow.test.framework}</span></div><p className="file-label">{workflow.test.file}</p><pre className="workflow-code"><code>{workflow.test.code}</code></pre></section>}

      {workflow.verification && <section className="workflow-section panel"><div className="workflow-section-head"><div><span className="workflow-step-no">06</span><div><h2>Verification</h2><p>{workflow.verification.isolation}</p></div></div><span className={`status-pill ${workflow.verification.status === 'PASS' ? 'status-ready' : 'status-failed'}`}>{workflow.verification.status}</span></div><div className="verify-grid"><RunCard title="BEFORE PATCH" result={workflow.verification.before}/><RunCard title="AFTER PATCH" result={workflow.verification.after}/></div><p className="changed-files">Changed in temporary copy: {workflow.verification.changed_files?.join(', ')}</p><button className="button primary-button" disabled={busy || Boolean(workflow.review)} onClick={() => action('review')}><GitPullRequest size={14}/> Run final review</button></section>}

      {workflow.review && <section className="workflow-section panel"><div className="workflow-section-head"><div><span className="workflow-step-no">07</span><div><h2>AI review</h2><p>Evidence and deterministic verification summary. Human review remains required.</p></div></div><span className="status-pill status-ready">{workflow.final_status}</span></div><div className="review-grid">{['correctness', 'regression_risk', 'security', 'maintainability', 'test_coverage'].map(key => <article key={key}><small>{key.replaceAll('_', ' ').toUpperCase()}</small><p>{workflow.review?.[key]}</p></article>)}</div><ul className="recommendation-list">{workflow.review.review_notes?.map((item: string) => <li key={item}>{item}</li>)}</ul><div className="callout subtle-callout"><ShieldCheck size={15}/>READY FOR HUMAN REVIEW · no source file was changed, and no merge or push was performed.</div></section>}
    </>}
  </div>
}

function RunCard({ title, result }: { title: string; result?: RunResult }) {
  return <article className="run-card"><div><strong>{title}</strong><span className={`status-pill ${result?.status === 'PASS' ? 'status-ready' : result?.status === 'FAIL' ? 'status-failed' : ''}`}>{result?.status ?? 'NOT RUN'}</span></div>{result && <><code>{result.command}</code><p>Exit code: {result.exit_code ?? '—'}</p><details><summary>Output</summary><pre>{result.stdout || '(no stdout)'}</pre></details>{result.stderr && <details><summary>Errors</summary><pre>{result.stderr}</pre></details>}</>}</article>
}
