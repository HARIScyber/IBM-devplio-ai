import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, BookOpenText, Bot, Bug, Check, ChevronDown, ChevronRight, CircleHelp, Clock3, Code2, Command, FileCode2, FileSearch, GitBranch, GitPullRequest, LayoutDashboard, LockKeyhole, Menu, MessageSquareText, MoreHorizontal, Play, Plus, Search, Send, Settings2, ShieldAlert, ShieldCheck, Sparkles, TerminalSquare, TestTube2, Upload, X } from 'lucide-react'
import { api, type ChatResult, type Finding, type Repo } from './api'
import WorkflowPage from './WorkflowPage'

type Page = 'Dashboard' | 'Repository' | 'AI Chat' | 'Code Analysis' | 'Security' | 'Testing' | 'Documentation' | 'Planner' | 'PR Review' | 'Issue Workflow' | 'Evaluation' | 'Issues' | 'Pull Requests' | 'Activity' | 'Settings'
const nav: { label: Page; icon: typeof LayoutDashboard; group: string }[] = [
  { label: 'Dashboard', icon: LayoutDashboard, group: 'WORKSPACE' }, { label: 'Repository', icon: Code2, group: 'WORKSPACE' }, { label: 'AI Chat', icon: MessageSquareText, group: 'WORKSPACE' },
  { label: 'Code Analysis', icon: Bug, group: 'INSPECT' }, { label: 'Security', icon: ShieldCheck, group: 'INSPECT' }, { label: 'Testing', icon: TestTube2, group: 'INSPECT' },
  { label: 'Documentation', icon: BookOpenText, group: 'BUILD' }, { label: 'Planner', icon: Sparkles, group: 'BUILD' }, { label: 'PR Review', icon: GitPullRequest, group: 'BUILD' },
  { label: 'Issue Workflow', icon: Sparkles, group: 'BUILD' }, { label: 'Evaluation', icon: Activity, group: 'BUILD' },
  { label: 'Issues', icon: CircleHelp, group: 'BUILD' }, { label: 'Pull Requests', icon: GitPullRequest, group: 'BUILD' },
  { label: 'Activity', icon: Activity, group: 'BUILD' }, { label: 'Settings', icon: Settings2, group: 'SYSTEM' },
]

function App() {
  const [page, setPage] = useState<Page>('Dashboard')
  const [repo, setRepo] = useState<Repo | null>(null)
  const [health, setHealth] = useState<{ demo_mode: boolean; provider: string } | null>(null)
  const [apiStatus, setApiStatus] = useState<'starting' | 'ready' | 'unavailable'>('starting')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [url, setUrl] = useState('')
  const [mobileNav, setMobileNav] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chat, setChat] = useState<ChatResult | null>(null)
  const [planInput, setPlanInput] = useState('')
  const [plan, setPlan] = useState<any>(null)
  const [testTarget, setTestTarget] = useState('')
  const [testDraft, setTestDraft] = useState<any>(null)
  const [docs, setDocs] = useState<any>(null)
  const [diff, setDiff] = useState('')
  const [review, setReview] = useState<any>(null)
  const [githubData, setGithubData] = useState<any>(null)
  const [activity, setActivity] = useState<any[]>([])
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
  const [toast, setToast] = useState('')
  const [workflow, setWorkflow] = useState<any>(null)
  const [initialIssue, setInitialIssue] = useState<any>(null)

  useEffect(() => { api<{ demo_mode: boolean; provider: string }>('/api/health').then(value => { setHealth(value); setApiStatus('ready') }).catch(() => { setApiStatus('unavailable'); setError('Backend is waking up or temporarily unavailable. Please retry in a few seconds.') }) }, [])
  useEffect(() => { if (toast) { const timer = setTimeout(() => setToast(''), 2800); return () => clearTimeout(timer) } }, [toast])
  const findings = repo?.findings ?? []
  const securityFindings = findings.filter(item => item.kind === 'security')
  const bugFindings = findings.filter(item => item.kind === 'bug')

  async function loadDemo() {
    setLoading(true); setError('')
    try { const data = await api<Repo>('/api/repositories/demo', { method: 'POST' }); setRepo(data); setPage('Dashboard'); setChat(null); setToast('Sample repository indexed') }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not load demo') }
    finally { setLoading(false) }
  }
  async function analyzeUrl(event: React.FormEvent) {
    event.preventDefault(); if (!url.trim()) return
    setLoading(true); setError('')
    try { const data = await api<Repo>('/api/repositories/analyze', { method: 'POST', body: JSON.stringify({ url }) }); setRepo(data); setPage('Dashboard'); setToast('Repository analysis complete') }
    catch (e) { setError(e instanceof Error ? e.message : 'Repository analysis failed') }
    finally { setLoading(false) }
  }
  async function uploadZip(file?: File) {
    if (!file) return
    setLoading(true); setError('')
    const body = new FormData(); body.append('file', file)
    try { const data = await api<Repo>('/api/repositories/upload', { method: 'POST', body }); setRepo(data); setPage('Dashboard'); setToast('ZIP repository indexed') }
    catch (e) { setError(e instanceof Error ? e.message : 'ZIP upload failed') }
    finally { setLoading(false) }
  }
  async function ask(question = chatInput) {
    if (!repo || !question.trim()) return
    setLoading(true); setError('')
    try { const data = await api<ChatResult>('/api/chat', { method: 'POST', body: JSON.stringify({ repository_id: repo.id, question }) }); setChat(data); setChatInput('') }
    catch (e) { setError(e instanceof Error ? e.message : 'Chat request failed') }
    finally { setLoading(false) }
  }
  async function generatePlan() {
    if (!repo || !planInput.trim()) return
    setLoading(true)
    try { setPlan(await api('/api/generate/plan', { method: 'POST', body: JSON.stringify({ repository_id: repo.id, requirement: planInput }) })) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not generate plan') }
    finally { setLoading(false) }
  }
  async function generateTests() {
    if (!repo) return
    setLoading(true)
    try { setTestDraft(await api('/api/generate/tests', { method: 'POST', body: JSON.stringify({ repository_id: repo.id, target: testTarget }) })) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not generate test draft') }
    finally { setLoading(false) }
  }
  async function generateDocs() {
    if (!repo) return
    setLoading(true)
    try { setDocs(await api('/api/generate/docs', { method: 'POST', body: JSON.stringify({ repository_id: repo.id }) })) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not generate docs') }
    finally { setLoading(false) }
  }
  async function reviewDiff() {
    if (!diff.trim()) return
    setLoading(true)
    try { setReview(await api('/api/review', { method: 'POST', body: JSON.stringify({ diff }) })) }
    catch (e) { setError(e instanceof Error ? e.message : 'Review failed') }
    finally { setLoading(false) }
  }
  async function openGithub(kind: 'issues' | 'pull-requests') {
    setLoading(true)
    try { setGithubData(await api(kind === 'issues' ? '/api/issues' : '/api/pull-requests')) }
    catch (e) { setError(e instanceof Error ? e.message : 'GitHub request failed') }
    finally { setLoading(false) }
  }
  async function openActivity() {
    try { const data = await api<{ items: any[] }>('/api/activity'); setActivity(data.items) } catch { setActivity([]) }
  }
  function navigate(next: Page) {
    setPage(next); setMobileNav(false); setError('')
    if (next === 'Issues') void openGithub('issues')
    if (next === 'Pull Requests') void openGithub('pull-requests')
    if (next === 'Activity') void openActivity()
  }
  function copyText(text: string) { void navigator.clipboard?.writeText(text).then(() => setToast('Copied to clipboard')).catch(() => setToast('Select the text to copy')) }

  const languageBars = useMemo(() => repo?.languages.slice(0, 4) ?? [], [repo])
  const navGroups = [...new Set(nav.map(item => item.group))]

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Command size={18}/></div><div><strong>devpilot<span>.ai</span></strong><small>ENGINEERING WORKSPACE</small></div><button className="icon-button mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={17}/></button></div>
      <button className="workspace-picker"><span className="workspace-dot">D</span><span className="workspace-name">Personal workspace<small>Free plan</small></span><ChevronDown size={15}/></button>
      <nav className="main-nav" aria-label="Main navigation">{navGroups.map(group => <div className="nav-group" key={group}><p>{group}</p>{nav.filter(item => item.group === group).map(item => { const Icon = item.icon; return <button key={item.label} className={`nav-item ${page === item.label ? 'active' : ''}`} onClick={() => navigate(item.label)}><Icon size={17}/><span>{item.label}</span>{item.label === 'Security' && securityFindings.length > 0 && <b className="nav-count">{securityFindings.length}</b>}{item.label === 'Code Analysis' && bugFindings.length > 0 && <b className="nav-count muted-count">{bugFindings.length}</b>}</button>})}</div>)}</nav>
      <div className="sidebar-bottom"><div className="usage-card"><div className="usage-head"><span><Sparkles size={14}/> Agent usage</span><span>DEMO</span></div><div className="usage-meter"><i/></div><small>Local workspace · no token configured</small></div><button className="profile-row"><div className="avatar">DP</div><span>DevPilot user<small>Developer</small></span><MoreHorizontal size={18}/></button></div>
    </aside>
    {mobileNav && <button className="nav-scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation"/>}
    <main className="main-shell">
      <header className="topbar"><div className="top-left"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={19}/></button><span className="crumb">Workspace</span><ChevronRight size={14} className="crumb-sep"/><span className="crumb-current">{page}</span>{repo && <><span className="crumb-sep">/</span><span className="repo-crumb"><span className="repo-status-dot"/>{repo.name}</span></>}</div><div className="top-actions"><span className="system-status"><i/>{apiStatus === 'starting' ? 'Starting DevPilot AI backend…' : apiStatus === 'ready' ? 'All systems normal' : 'Backend unavailable'}</span><button className="icon-button" aria-label="Search" onClick={() => navigate('Repository')}><Search size={17}/></button><button className="icon-button notification" aria-label="Activity" onClick={() => navigate('Activity')}><Activity size={17}/></button><div className="top-avatar">DP</div></div></header>
      <section className="content">
        {error && <div className="alert error-alert"><ShieldAlert size={17}/><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss"><X size={15}/></button></div>}
        {!repo ? <EmptyWorkspace onDemo={loadDemo} onAnalyze={() => navigate('Repository')} loading={loading} /> : <>
          {page === 'Dashboard' && <Dashboard repo={repo} health={health} security={securityFindings.length} bugs={bugFindings.length} languageBars={languageBars} onNavigate={navigate} onDemo={loadDemo} loading={loading} />}
          {page === 'Repository' && <RepositoryPage repo={repo} url={url} setUrl={setUrl} onAnalyze={analyzeUrl} onUpload={uploadZip} loading={loading} onAsk={ask} />}
          {page === 'AI Chat' && <ChatPage repo={repo} input={chatInput} setInput={setChatInput} result={chat} onAsk={ask} loading={loading} />}
          {page === 'Code Analysis' && <FindingsPage title="Code analysis" subtitle="Potential runtime, error-handling, and maintainability issues found in indexed files." findings={bugFindings} icon={<Bug size={19}/>} onSelect={setSelectedFinding} empty="No potential code findings were detected by the configured static checks." />}
          {page === 'Security' && <FindingsPage title="Security analysis" subtitle="Evidence-backed heuristic checks. Findings are potential risks and need human review." findings={securityFindings} icon={<ShieldCheck size={19}/>} onSelect={setSelectedFinding} empty="No security patterns matched the current checks. This is not a complete security audit." />}
          {page === 'Testing' && <TestingPage repo={repo} target={testTarget} setTarget={setTestTarget} draft={testDraft} generate={generateTests} loading={loading} copy={copyText} />}
          {page === 'Documentation' && <DocsPage docs={docs} generate={generateDocs} loading={loading} copy={copyText} />}
          {page === 'Planner' && <PlannerPage input={planInput} setInput={setPlanInput} plan={plan} generate={generatePlan} loading={loading} />}
          {page === 'PR Review' && <ReviewPage diff={diff} setDiff={setDiff} review={review} run={reviewDiff} loading={loading} />}
          {page === 'Issue Workflow' && <WorkflowPage repositoryId={repo.id} workflow={workflow} setWorkflow={setWorkflow} initialIssue={initialIssue} clearInitialIssue={() => setInitialIssue(null)} />}
          {page === 'Evaluation' && <EvaluationPage />}
          {page === 'Issues' && <GitHubList title="GitHub issues" data={githubData} loading={loading} kind="issue" onInvestigate={item => { setInitialIssue({ ...item, origin: 'github' }); navigate('Issue Workflow') }} />}
          {page === 'Pull Requests' && <GitHubList title="Pull requests" data={githubData} loading={loading} kind="pull" />}
          {page === 'Activity' && <ActivityPage items={activity} />}
          {page === 'Settings' && <SettingsPage health={health} />}
          {selectedFinding && <FindingModal finding={selectedFinding} close={() => setSelectedFinding(null)} />}
          <footer className="content-footer"><span>DevPilot AI <span className="footer-dot">·</span> v0.1.0</span><span>Repository-aware engineering, with evidence.</span></footer>
        </>}
      </section>
    </main>
    {toast && <div className="toast"><Check size={15}/>{toast}</div>}
  </div>
}

function PageHeading({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description: string; actions?: React.ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow ?? 'DEV PILOT · ENGINEERING'}</div><h1>{title}</h1><p>{description}</p></div>{actions && <div className="heading-actions">{actions}</div>}</div>
}
function EmptyWorkspace({ onDemo, onAnalyze, loading }: { onDemo: () => void; onAnalyze: () => void; loading: boolean }) {
  return <div className="welcome-screen"><div className="welcome-glow"/><div className="welcome-content"><div className="welcome-icon"><Command size={25}/></div><div className="eyebrow">YOUR AI SOFTWARE ENGINEERING PARTNER</div><h1>Build with your codebase<br/><span>in context.</span></h1><p>Understand codebases, detect potential bugs, review security, generate tests and docs, and turn requirements into actionable plans.</p><div className="welcome-actions"><button className="button primary-button" onClick={onAnalyze}>Analyze a repository <ArrowRight size={16}/></button><button className="button secondary-button" disabled={loading} onClick={onDemo}>{loading ? <span className="spinner"/> : <Play size={15}/>} Try the demo</button></div><div className="welcome-foot"><span><ShieldCheck size={14}/> Demo works without API keys</span><span><FileSearch size={14}/> Answers cite repository lines</span></div></div><div className="welcome-preview"><div className="preview-bar"><div className="window-dots"><i/><i/><i/></div><span>devpilot.ai / overview</span><span className="preview-live"><i/> READY</span></div><div className="preview-body"><div className="preview-title"><span>Repository intelligence</span><span className="demo-chip">DEMO DATA</span></div><div className="preview-file"><FileCode2 size={14}/><span>backend/</span></div><div className="preview-file indented"><Code2 size={14}/><span>auth.py</span><b>3 functions</b></div><div className="preview-file indented"><Code2 size={14}/><span>tasks.py</span><b>3 symbols</b></div><div className="preview-divider"/><div className="preview-response"><span className="preview-bot"><Sparkles size={13}/></span><div><strong>Repository answer</strong><p>Account lookup is handled in <code>backend/auth.py:4</code> and compares normalized email addresses.</p><span className="citation"><FileCode2 size={11}/> auth.py : 4–8</span></div></div></div></div></div>
}
function Dashboard({ repo, health, security, bugs, languageBars, onNavigate, onDemo, loading }: { repo: Repo; health: { demo_mode: boolean; provider: string } | null; security: number; bugs: number; languageBars: Repo['languages']; onNavigate: (p: Page) => void; onDemo: () => void; loading: boolean }) {
  const scoreCards = [
    { label: 'Repository files', value: repo.file_count.toLocaleString(), note: `${repo.loc.toLocaleString()} non-empty lines`, icon: Code2, tint: 'blue' },
    { label: 'Potential findings', value: String(security + bugs), note: `${security} security · ${bugs} code`, icon: ShieldAlert, tint: security + bugs ? 'amber' : 'green' },
    { label: 'Test structure', value: repo.has_tests ? `${repo.test_files.length} files` : 'Not detected', note: 'Coverage not measured', icon: TestTube2, tint: 'purple' },
    { label: 'Documentation', value: repo.has_docs ? 'README found' : 'Not detected', note: 'Completeness not scored', icon: BookOpenText, tint: 'teal' },
  ]
  return <><PageHeading eyebrow="OVERVIEW" title="Good to see you, developer" description="Here's what we found in your active repository." actions={<><button className="button secondary-button" onClick={() => onNavigate('Repository')}><Plus size={15}/> Add repository</button><button className="button primary-button" onClick={onDemo} disabled={loading}><Play size={14}/> Re-run demo</button></>}/>
    {(health?.demo_mode || repo.source.startsWith('demo/')) && <div className="demo-banner"><span className="banner-icon"><Sparkles size={15}/></span><div><strong>Demo Mode is active</strong><span>You're viewing the bundled Northstar Tasks sample repository. Results are labeled as demo data.</span></div><button onClick={() => onNavigate('Repository')}>Connect a repository <ArrowRight size={14}/></button></div>}
    <div className="section-label"><span>REPOSITORY HEALTH</span><span className="updated-label"><Clock3 size={13}/> Indexed just now</span></div><div className="metric-grid">{scoreCards.map((card, index) => { const Icon = card.icon; return <article className="metric-card" key={card.label}><div className={`metric-icon ${card.tint}`}><Icon size={17}/></div><span className="metric-label">{card.label}</span><strong className="metric-value">{card.value}</strong><span className="metric-note">{card.note}</span><div className="metric-corner">0{index + 1}</div></article>})}</div>
    <div className="dashboard-grid"><section className="panel overview-panel"><div className="panel-header"><div><h2>Repository overview</h2><p>Signals from the indexed source files</p></div><button className="button text-button" onClick={() => onNavigate('Repository')}>Explore repo <ArrowUpRight size={14}/></button></div><div className="repo-summary"><div className="repo-summary-icon"><Code2 size={18}/></div><div><strong>{repo.name}</strong><span>{repo.source}</span></div><span className="index-badge"><i/> Indexed</span></div><div className="repo-stats"><div><span>Primary language</span><b>{repo.primary_language}</b></div><div><span>Frameworks detected</span><b>{repo.frameworks.join(', ') || 'No clear match'}</b></div><div><span>Entry points</span><b>{repo.entry_points.length || 'Not detected'}</b></div></div><div className="language-list"><div className="mini-heading">LANGUAGE DISTRIBUTION <span>by file count</span></div>{languageBars.length ? languageBars.map((item, index) => <div className="language-row" key={item.name}><span>{item.name}</span><div className="language-track"><i style={{ width: `${Math.max(7, item.files / Math.max(...languageBars.map(row => row.files)) * 100)}%` }} className={`lang-${index}`}/></div><b>{item.files}</b></div>) : <div className="muted-line">No programming languages detected.</div>}</div></section>
      <section className="panel findings-panel"><div className="panel-header"><div><h2>Findings</h2><p>Potential issues with source evidence</p></div><button className="icon-button" onClick={() => onNavigate('Security')} aria-label="View security"><MoreHorizontal size={17}/></button></div>{repo.findings.slice(0, 4).map(item => <button className="finding-row" key={item.id} onClick={() => onNavigate(item.kind === 'security' ? 'Security' : 'Code Analysis')}><span className={`severity-mark ${item.severity.toLowerCase()}`}/><div><strong>{item.title}</strong><span>{item.file}:{item.line} <i>·</i> {item.category}</span></div><ChevronRight size={15}/></button>)}{repo.findings.length === 0 && <div className="empty-inline"><ShieldCheck size={22}/><strong>No matching rules</strong><span>Static checks did not find known patterns.</span></div>}<button className="panel-link" onClick={() => onNavigate('Code Analysis')}>View all analysis <ArrowRight size={14}/></button></section>
      <section className="panel architecture-panel"><div className="panel-header"><div><h2>Architecture at a glance</h2><p>Inferred from folders and project config</p></div><span className="confidence-tag">STRUCTURAL HINTS</span></div><div className="architecture-flow">{(repo.components.length ? repo.components.slice(0, 4) : ['repository root']).map((part, index) => <div className="arch-step" key={part}><span className="arch-num">0{index + 1}</span><span>{part}</span>{index < Math.min(repo.components.length || 1, 4) - 1 && <ArrowRight size={14}/>}</div>)}</div><div className="architecture-note"><Sparkles size={14}/><span>Directory names are structural hints; validate the architecture against the source.</span></div></section>
      <section className="panel quick-panel"><div className="panel-header"><div><h2>Continue building</h2><p>Pick a focused engineering workflow</p></div></div><div className="quick-actions"><button onClick={() => onNavigate('AI Chat')}><span className="quick-icon blue"><MessageSquareText size={16}/></span><span><b>Ask your repository</b><small>Get answers with file citations</small></span><ArrowRight size={14}/></button><button onClick={() => onNavigate('Testing')}><span className="quick-icon purple"><TestTube2 size={16}/></span><span><b>Draft a test</b><small>Generate a reviewable test template</small></span><ArrowRight size={14}/></button><button onClick={() => onNavigate('Documentation')}><span className="quick-icon teal"><BookOpenText size={16}/></span><span><b>Write documentation</b><small>Preview a repository overview</small></span><ArrowRight size={14}/></button><button onClick={() => onNavigate('Security')}><span className="quick-icon amber"><LockKeyhole size={16}/></span><span><b>Review security</b><small>Inspect heuristic findings</small></span><ArrowRight size={14}/></button></div></section></div>
  </>
}
function RepositoryPage({ repo, url, setUrl, onAnalyze, onUpload, loading, onAsk }: { repo: Repo; url: string; setUrl: (v: string) => void; onAnalyze: (e: React.FormEvent) => void; onUpload: (f?: File) => void; loading: boolean; onAsk: (q: string) => void }) {
  const [filter, setFilter] = useState('')
  const files = repo.files.filter(file => file.path.toLowerCase().includes(filter.toLowerCase()))
  return <><PageHeading eyebrow="SOURCE CONTROL" title="Repository" description="Browse repository structure, source files, and detected project signals." actions={<div className="repo-status-pill"><i/> INDEXED</div>}/><div className="repo-ingest panel"><div><h2>Connect a repository</h2><p>Public GitHub HTTPS URL · ZIP uploads paused until secure account ownership is available.</p></div><form onSubmit={onAnalyze} className="repo-url-form"><GitBranch size={16}/><input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/owner/repository" aria-label="GitHub repository URL"/><button className="button primary-button" disabled={loading}>{loading ? <span className="spinner"/> : <Search size={14}/>} Analyze</button></form><label className="button secondary-button upload-button" title="ZIP uploads are paused until secure account ownership is available"><Upload size={14}/> ZIP upload paused<input type="file" accept=".zip,application/zip" disabled onChange={e => void onUpload(e.target.files?.[0])}/></label></div><div className="repo-headline panel"><div className="repo-avatar"><Code2 size={20}/></div><div><h2>{repo.name}</h2><p>{repo.source}</p></div><span className="demo-chip">{repo.source.startsWith('demo/') ? 'DEMO DATA' : 'INDEXED'}</span><div className="repo-head-stats"><span><b>{repo.file_count}</b> files</span><span><b>{repo.loc.toLocaleString()}</b> lines</span><span><b>{repo.primary_language}</b></span></div></div><div className="repository-layout"><section className="panel file-panel"><div className="panel-header"><div><h2>File explorer</h2><p>{files.length} indexed files</p></div><div className="file-filter"><Search size={14}/><input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Filter files" aria-label="Filter files"/></div></div><div className="file-tree">{files.slice(0, 300).map(file => <div className="tree-file" key={file.path}><FileCode2 size={14}/><span>{file.path}</span><small>{file.language}</small></div>)}{!files.length && <div className="empty-inline">No files match.</div>}</div></section><aside className="repo-side"><section className="panel"><div className="mini-heading">DETECTED FRAMEWORKS</div><div className="tag-list">{repo.frameworks.length ? repo.frameworks.map(item => <span className="tag" key={item}>{item}</span>) : <span className="muted-line">No frameworks detected</span>}</div><div className="divider"/><div className="mini-heading">ENTRY POINTS</div>{repo.entry_points.length ? repo.entry_points.map(item => <div className="path-mini" key={item}><TerminalSquare size={14}/><span>{item}</span></div>) : <div className="muted-line">No conventional entry point found</div>}</section><section className="panel"><div className="mini-heading">QUICK QUESTIONS</div>{['How does account lookup work?', 'Where are the test files?', 'Explain the repository architecture.'].map(q => <button className="question-chip" key={q} onClick={() => onAsk(q)}>{q}<ArrowUpRight size={12}/></button>)}</section></aside></div></>
}
function ChatPage({ repo, input, setInput, result, onAsk, loading }: { repo: Repo; input: string; setInput: (v: string) => void; result: ChatResult | null; onAsk: (q?: string) => void; loading: boolean }) {
  const suggestions = ['How does account lookup work?', 'Where is the test structure?', 'Which files are the main entry points?']
  return <><PageHeading eyebrow="REPOSITORY ASSISTANT" title="Ask your codebase" description="Answers use matching indexed lines and show their source. Live model calls require a configured provider." actions={<span className="mode-pill"><span className="green-dot"/> {result?.mode ?? 'DEMO RETRIEVAL'}</span>}/><div className="chat-layout"><section className="panel chat-main"><div className="chat-context"><div className="context-avatar"><Sparkles size={15}/></div><div><strong>Repository context attached</strong><span>{repo.name} · {repo.file_count} files indexed</span></div><span className="context-tag">CITED ANSWERS</span></div><div className="chat-messages">{!result ? <div className="chat-welcome"><div className="welcome-icon small"><MessageSquareText size={20}/></div><h2>What do you want to understand?</h2><p>Ask about a function, feature, configuration, or architecture decision.</p><div className="suggestion-grid">{suggestions.map(q => <button key={q} onClick={() => onAsk(q)}>{q}<ArrowUpRight size={13}/></button>)}</div></div> : <><div className="message user-message"><div className="avatar tiny">YOU</div><div><div className="message-label">You</div><p>{result.sources.length ? 'Question answered with repository context.' : 'Repository question'}</p></div></div><div className="message assistant-message"><div className="chat-bot"><Sparkles size={14}/></div><div className="answer-body"><div className="message-label">DevPilot assistant <span className="demo-chip">{result.mode}</span></div><p className="answer-text">{result.answer.split('\n').map((line, i) => <span key={i}>{line.startsWith('- ') ? <><br/>• {line.slice(2)}</> : <>{line}<br/></>}</span>)}</p><div className="reasoning-summary"><span>RETRIEVAL SUMMARY</span><p>{result.reasoning_summary}</p></div>{result.suggested_actions?.length > 0 && <div className="suggested-actions"><span>SUGGESTED ACTIONS</span>{result.suggested_actions.map(item => <span key={item}><Check size={12}/>{item}</span>)}</div>}</div></div></>}</div><form className="chat-composer" onSubmit={e => { e.preventDefault(); onAsk() }}><textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onAsk() } }} placeholder="Ask a question about this repository…" rows={2}/><div className="composer-bottom"><span><Command size={12}/> Enter to ask · Shift + Enter for new line</span><button className="button primary-button" disabled={loading || !input.trim()}>{loading ? <span className="spinner"/> : <Send size={14}/>} Ask</button></div></form></section><aside className="panel sources-panel"><div className="panel-header"><div><h2>Relevant files</h2><p>{result?.sources.length ?? 0} cited excerpts</p></div><FileSearch size={16}/></div>{result?.sources.length ? result.sources.map((source, i) => <article className="source-card" key={`${source.file}:${source.line}:${i}`}><div className="source-path"><FileCode2 size={13}/><span>{source.file}</span></div><div className="source-line">LINE {source.line}</div><code>{source.excerpt}</code></article>) : <div className="sources-empty"><FileSearch size={23}/><span>Sources appear here<br/>with each answer.</span></div>}<div className="source-foot"><ShieldCheck size={13}/> Citations come from indexed text lines.</div></aside></div></>
}
function FindingsPage({ title, subtitle, findings, icon, onSelect, empty }: { title: string; subtitle: string; findings: Finding[]; icon: React.ReactNode; onSelect: (f: Finding) => void; empty: string }) {
  const [severity, setSeverity] = useState('ALL')
  const filtered = severity === 'ALL' ? findings : findings.filter(f => f.severity === severity)
  return <><PageHeading eyebrow="STATIC ANALYSIS" title={title} description={subtitle} actions={<button className="button secondary-button" onClick={() => setSeverity('ALL')}><FileSearch size={14}/> {findings.length} potential findings</button>}/><div className="analysis-summary panel"><span className="analysis-icon">{icon}</span><div><strong>Local evidence checks</strong><p>Heuristic patterns with file and line references. A clean result does not prove code is secure or bug-free.</p></div><span className="analysis-source">STATIC RULES</span></div><div className="filter-row"><span>FINDINGS <b>{filtered.length}</b></span><div>{['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map(level => <button key={level} className={`filter-chip ${severity === level ? 'selected' : ''}`} onClick={() => setSeverity(level)}>{level}</button>)}</div></div>{filtered.length ? <div className="finding-list">{filtered.map(item => <button className="finding-card panel" key={item.id} onClick={() => onSelect(item)}><div className="finding-severity"><span className={`severity-mark ${item.severity.toLowerCase()}`}/><b>{item.severity}</b></div><div className="finding-main"><h3>{item.title}</h3><p>{item.problem}</p><code>{item.file}:{item.line}</code></div><div className="finding-category">{item.category}</div><ChevronRight size={17}/></button>)}</div> : <div className="panel empty-panel"><div className="empty-icon"><Check size={22}/></div><h2>{empty.includes('No') ? 'No pattern matches' : 'No findings'}</h2><p>{empty}</p><span>Scanner scope is listed in README limitations.</span></div>}</>
}
function TestingPage({ repo, target, setTarget, draft, generate, loading, copy }: { repo: Repo; target: string; setTarget: (v: string) => void; draft: any; generate: () => void; loading: boolean; copy: (v: string) => void }) {
  const pythonFiles = repo.files.filter(f => f.language === 'Python')
  return <><PageHeading eyebrow="TEST WORKFLOW" title="Test generator" description="Create a reviewable test draft from a selected repository module. Generated tests are not auto-applied or executed."/><div className="tool-layout"><section className="panel tool-form"><div className="form-title"><div className="quick-icon purple"><TestTube2 size={17}/></div><div><h2>Choose a target</h2><p>Python functions are used for targeted scaffolding.</p></div></div><label className="field-label" htmlFor="test-target">FILE PATH</label><select id="test-target" value={target} onChange={e => setTarget(e.target.value)}><option value="">Auto-select entry point</option>{pythonFiles.map(file => <option key={file.path} value={file.path}>{file.path}</option>)}</select><div className="callout subtle-callout"><CircleHelp size={15}/><span>The generated code is a draft. Review imports, inputs, and expected behavior before running it.</span></div><button className="button primary-button wide-button" onClick={generate} disabled={loading}>{loading ? <span className="spinner"/> : <Sparkles size={15}/>} Generate test draft</button></section><section className="panel output-panel"><div className="panel-header"><div><h2>Test preview</h2><p>{draft?.file ?? 'Choose a module to generate a test template'}</p></div>{draft && <button className="button secondary-button" onClick={() => copy(draft.code)}><ArrowDownToLine size={14}/> Copy test</button>}</div>{draft ? <><div className="output-note"><span className="demo-chip">DRAFT</span>{draft.note}</div><pre className="code-output"><code>{draft.code}</code></pre></> : <div className="output-placeholder"><TestTube2 size={23}/><span>Generated test code will be shown here for review.</span></div>}</section></div></>
}
function DocsPage({ docs, generate, loading, copy }: { docs: any; generate: () => void; loading: boolean; copy: (v: string) => void }) {
  return <><PageHeading eyebrow="DOCUMENTATION" title="Documentation studio" description="Draft an overview from detected repository metadata, then review it before publishing." actions={<button className="button primary-button" disabled={loading} onClick={generate}>{loading ? <span className="spinner"/> : <Sparkles size={14}/>} Generate overview</button>}/><div className="docs-layout"><div className="panel docs-sidebar"><div className="mini-heading">GENERATORS</div>{['README overview', 'API docs', 'Architecture', 'Developer onboarding'].map((item, index) => <div className={`docs-generator ${index === 0 ? 'current' : 'coming'}`} key={item}><BookOpenText size={15}/><span>{item}</span>{index > 0 && <small>METADATA</small>}</div>)}<p className="docs-hint">The MVP supports an overview draft based on detected structure. Other formats need deeper project-specific analysis.</p></div><section className="panel docs-preview"><div className="panel-header"><div><h2>{docs?.title ?? 'Generated preview'}</h2><p>Review text before copying into your repository</p></div>{docs && <button className="button secondary-button" onClick={() => copy(docs.content)}><ArrowDownToLine size={14}/> Copy markdown</button>}</div>{docs ? <><div className="output-note"><span className="demo-chip">PREVIEW</span>{docs.note}</div><pre className="markdown-output">{docs.content}</pre></> : <div className="output-placeholder"><BookOpenText size={23}/><span>Generate a draft from the current repository.</span></div>}</section></div></>
}
function PlannerPage({ input, setInput, plan, generate, loading }: { input: string; setInput: (v: string) => void; plan: any; generate: () => void; loading: boolean }) {
  return <><PageHeading eyebrow="IMPLEMENTATION PLANNING" title="Turn a requirement into a plan" description="Create a repository-aware sequence of reviewable engineering steps."/><div className="tool-layout"><section className="panel tool-form"><label className="field-label" htmlFor="plan-requirement">REQUIREMENT</label><textarea id="plan-requirement" value={input} onChange={e => setInput(e.target.value)} placeholder="Add OAuth authentication" rows={5}/><div className="callout subtle-callout"><CircleHelp size={15}/><span>The plan is a starting point. Confirm the integration points and acceptance criteria against your repository.</span></div><button className="button primary-button wide-button" disabled={loading || input.trim().length < 5} onClick={generate}>{loading ? <span className="spinner"/> : <Sparkles size={15}/>} Generate plan</button></section><section className="panel output-panel"><div className="panel-header"><div><h2>{plan?.requirement ?? 'Plan preview'}</h2><p>{plan?.mode ?? 'Steps grounded in repository metadata'}</p></div></div>{plan?.steps ? <ol className="plan-steps">{plan.steps.map((item: {step: string; detail: string}, index: number) => <li className="plan-step" key={`${index}-${item.step}`}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{item.step}</strong><p>{item.detail}</p></div></li>)}</ol> : <div className="output-placeholder"><Sparkles size={23}/><span>Enter a requirement to preview an implementation plan.</span></div>}</section></div></>
}
function ReviewPage({ diff, setDiff, review, run, loading }: { diff: string; setDiff: (v: string) => void; review: any; run: () => void; loading: boolean }) {
  return <><PageHeading eyebrow="CHANGE REVIEW" title="Review a pull request diff" description="Run lightweight local heuristics to flag possible risks and suggest checks. Human review is still required."/><div className="tool-layout"><section className="panel tool-form"><label className="field-label" htmlFor="review-diff">UNIFIED DIFF</label><textarea id="review-diff" value={diff} onChange={e => setDiff(e.target.value)} placeholder={'diff --git a/example.py b/example.py\n+password = "replace-me"'} rows={12}/><div className="callout subtle-callout"><CircleHelp size={15}/><span>Paste a unified diff. Analysis uses basic local heuristics and does not contact GitHub.</span></div><button className="button primary-button wide-button" disabled={loading || !diff.trim()} onClick={run}>{loading ? <span className="spinner"/> : <GitPullRequest size={15}/>} Review diff</button></section><section className="panel output-panel"><div className="panel-header"><div><h2>Review summary</h2><p>{review?.source ?? 'Potential issues, risks, and suggested checks'}</p></div></div>{review ? <div className="review-results"><p className="review-summary">{review.summary}</p>{review.security_concerns?.length ? <><h3>Potential security concerns</h3>{review.security_concerns.map((item: any, index: number) => <div className="review-risk" key={index}><strong>{item.severity} · {item.title}</strong><code>{item.evidence}</code></div>)}</> : <p>No configured risk patterns matched the added lines.</p>}<h3>Suggested checks</h3><ul>{review.testing_suggestions?.map((item: string) => <li key={item}>{item}</li>)}</ul></div> : <div className="output-placeholder"><GitPullRequest size={23}/><span>Paste a diff and run the local review.</span></div>}</section></div></>
}
function GitHubList({ title, data, loading, kind, onInvestigate }: { title: string; data: any; loading: boolean; kind: 'issue' | 'pull'; onInvestigate?: (issue: any) => void }) {
  const Icon = kind === 'issue' ? CircleHelp : GitPullRequest
  return <><PageHeading eyebrow="GITHUB INTEGRATION" title={title} description="Read-only repository queue. A backend token and GITHUB_REPOSITORY=owner/repo are required." actions={<span className="read-only-pill"><LockKeyhole size={13}/> READ ONLY</span>}/>{loading && <div className="loading-inline"><span className="spinner"/> Loading from GitHub…</div>}{!loading && data && <div className="panel github-panel">{data.message && <div className="callout subtle-callout"><CircleHelp size={15}/>{data.message}</div>}{data.items?.length ? data.items.map((item: any) => <div className="github-row" key={item.number}><span className="gh-item-icon"><Icon size={16}/></span><div className="github-item-content"><a href={item.url} target="_blank" rel="noreferrer"><strong>#{item.number} {item.title}</strong><span>Opened by {item.user} · {item.state}</span></a>{kind === 'issue' && <button className="button secondary-button" onClick={() => onInvestigate?.(item)}>Investigate</button>}</div><ArrowUpRight size={15}/></div>) : !data.message ? <div className="empty-inline">No open items found.</div> : null}</div>}</>
}
function EvaluationPage() {
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  async function run() {
    setLoading(true); setError('')
    try { setResult(await api('/api/evaluation/run')) }
    catch (e) { setError(e instanceof Error ? e.message : 'Benchmark run failed') }
    finally { setLoading(false) }
  }
  return <><PageHeading eyebrow="MEASURED RETRIEVAL" title="Evaluate repository search" description="Run a fixed, labeled benchmark against the bundled demo repository." actions={<button className="button primary-button" disabled={loading} onClick={run}>{loading ? <span className="spinner"/> : <Activity size={15}/>} Run benchmark</button>}/>{error && <div className="alert error-alert">{error}</div>}{result ? <><div className="metric-grid evaluation-metrics">{Object.entries(result.metrics).filter(([key]) => key.endsWith('_rate') || key === 'citation_line_validity').map(([key, value]) => <article className="panel metric-card" key={key}><span className="metric-label">{key.replaceAll('_', ' ')}</span><strong>{Math.round(Number(value) * 100)}%</strong><small>{key === 'expected_symbol_hit_rate' ? `${result.metrics.labeled_symbol_cases} labeled symbols` : `${result.case_count} labeled questions`} · top {result.cutoff}</small></article>)}</div><div className="panel evaluation-table"><div className="panel-header"><div><h2>{result.benchmark}</h2><p>Each row compares the expected file and symbol against actual retrieval output.</p></div></div>{result.cases.map((row: any) => <div className="evaluation-row" key={row.id}><div><strong>{row.id}</strong><span>{row.query}</span><small>Expected: {row.expected_file}{row.expected_symbol ? ` · ${row.expected_symbol}` : ''}</small><small>Retrieved: {row.retrieved_files.join(', ') || 'no results'}</small></div><span className={`status-pill ${row.file_hit && (row.symbol_hit ?? true) && row.citations_valid ? 'status-ready' : 'status-failed'}`}>{row.file_hit ? 'FILE HIT' : 'MISS'}{row.expected_symbol ? ` · ${row.symbol_hit ? 'SYMBOL HIT' : 'SYMBOL MISS'}` : ''}</span></div>)}<p className="evaluation-note">{result.limitations}</p></div></> : <div className="panel output-placeholder evaluation-empty"><Activity size={23}/><span>Run the benchmark to calculate file hit rate, symbol hit rate, and citation line validity.</span></div>}</>
}
function ActivityPage({ items }: { items: any[] }) {
  return <><PageHeading eyebrow="WORKSPACE HISTORY" title="Activity" description="Recent repository analysis and generated workflow actions."/><div className="panel activity-list">{items.length ? items.map((item, index) => <div className="activity-row" key={item.id}><div className="activity-mark"><Activity size={15}/></div><div><strong>{item.action}</strong><span>{item.detail}</span></div><time>{item.created_at ? new Date(item.created_at + 'Z').toLocaleString() : 'Recently'}</time>{index < items.length - 1 && <i className="activity-line"/>}</div>) : <div className="empty-inline"><Clock3 size={20}/>Activity appears after you analyze a repository or generate a plan.</div>}</div></>
}
function SettingsPage({ health }: { health: { demo_mode: boolean; provider: string } | null }) {
  return <><PageHeading eyebrow="CONFIGURATION" title="Workspace settings" description="Runtime settings are configured on the backend. No secrets are exposed to this browser."/><div className="settings-grid"><section className="panel setting-card"><div className="setting-icon"><Bot size={18}/></div><div><h2>AI provider</h2><p>Provider configured in backend environment</p></div><span className="setting-value">{health?.provider ?? 'unknown'}</span><div className="setting-description">Optional: IBM watsonx.ai, Gemini, or Ollama. Without provider credentials, repository chat uses labeled local retrieval.</div></section><section className="panel setting-card"><div className="setting-icon green"><ShieldCheck size={18}/></div><div><h2>Demo Mode</h2><p>Bundled repository and deterministic checks</p></div><span className={`setting-value ${health?.demo_mode ? 'green-text' : ''}`}>{health?.demo_mode ? 'ENABLED' : 'DISABLED'}</span><div className="setting-description">The sample repository is fictional. Demo findings reflect source patterns and are labeled as data from the demo.</div></section><section className="panel setting-card"><div className="setting-icon amber"><GitBranch size={18}/></div><div><h2>GitHub access</h2><p>Token remains server-side</p></div><span className="setting-value">OPTIONAL</span><div className="setting-description">Public issue and pull request lists can use a configured repository slug. Private access requires per-user authorization and is not available yet.</div></section><section className="panel setting-card"><div className="setting-icon purple"><DatabaseIcon/></div><div><h2>Data storage</h2><p>Local single-user prototype</p></div><span className="setting-value">SQLITE</span><div className="setting-description">Repository metadata, chat answers, and activity are stored locally. Source files stay in local backend storage.</div></section></div></>
}
function DatabaseIcon() { return <span className="database-glyph">▤</span> }
function FindingModal({ finding, close }: { finding: Finding; close: () => void }) {
  return <div className="modal-backdrop" role="presentation" onClick={close}><section className="finding-modal panel" role="dialog" aria-modal="true" aria-labelledby="finding-title" onClick={e => e.stopPropagation()}><div className="modal-header"><div><span className={`severity-pill ${finding.severity.toLowerCase()}`}>{finding.severity}</span><span className="finding-category">{finding.category}</span></div><button className="icon-button" onClick={close} aria-label="Close finding"><X size={17}/></button></div><h2 id="finding-title">{finding.title}</h2><p>{finding.problem}</p><div className="mini-heading">SOURCE EVIDENCE</div><div className="evidence-block"><span>{finding.file}:{finding.line}</span><code>{finding.evidence}</code></div><div className="mini-heading">SUGGESTED NEXT STEP</div><p>{finding.suggested_fix}</p><div className="confidence-note"><ShieldAlert size={14}/>{finding.confidence}. Review surrounding code before changing it.</div><button className="button primary-button modal-done" onClick={close}>Done</button></section></div>
}

export default App
