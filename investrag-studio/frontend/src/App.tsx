import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type Health, type QueryResponse, type SourceVersion } from './api'

type Tab = 'overview' | 'data-room' | 'research' | 'retrieval' | 'evaluation'

const tabs: { id: Tab; label: string; eyebrow: string }[] = [
  { id: 'overview', label: 'Overview', eyebrow: 'Control plane' },
  { id: 'data-room', label: 'Data Room', eyebrow: 'Ingestion' },
  { id: 'research', label: 'Research Workspace', eyebrow: 'Cited answers' },
  { id: 'retrieval', label: 'Retrieval Lab', eyebrow: 'Rank diagnostics' },
  { id: 'evaluation', label: 'Evaluation Studio', eyebrow: 'Evidence quality' },
]

const benchmarkData = [
  { name: 'FAISS', ndcg: 0.78, recall: 0.84, latency: 42 },
  { name: 'Chroma', ndcg: 0.76, recall: 0.82, latency: 58 },
  { name: 'Qdrant', ndcg: 0.81, recall: 0.88, latency: 67 },
  { name: 'pgvector', ndcg: 0.79, recall: 0.86, latency: 74 },
]

function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'good' | 'warn' | 'neutral' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="metric-card">
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      <span className="muted">{detail}</span>
    </div>
  )
}

function Header({ health, onRefresh }: { health: Health | null; onRefresh: () => void }) {
  return (
    <header className="topbar">
      <div className="brand-lockup">
        <div className="brand-mark">IR</div>
        <div>
          <div className="brand-name">InvestRAG <span>Studio</span></div>
          <div className="brand-subtitle">Evidence-first investment intelligence</div>
        </div>
      </div>
      <div className="topbar-actions">
        <div className="system-status"><span className="status-dot" /> local runtime <span className="muted">·</span> {health?.embedding_fallback ? 'hash fallback' : 'BGE-M3 ready'}</div>
        <button className="icon-button" onClick={onRefresh} aria-label="Refresh system status">↻</button>
      </div>
    </header>
  )
}

function Overview({ health, sources }: { health: Health | null; sources: SourceVersion[] }) {
  const ready = sources.filter((source) => source.status === 'ready').length
  return (
    <>
      <section className="page-intro">
        <div><span className="eyebrow">Portfolio intelligence / local control plane</span><h1>Know what the model knows.</h1><p>Trace every answer from source artifact to parser, chunk, vector ranking and cited evidence.</p></div>
        <Badge tone="good">All data stays on this laptop</Badge>
      </section>
      <section className="metric-grid">
        <Metric label="Indexed chunks" value={String(health?.indexed_chunks ?? 0)} detail="FAISS active collection" />
        <Metric label="Source versions" value={String(sources.length)} detail={`${ready} ready · ${sources.length - ready} need review`} />
        <Metric label="Embedding model" value={health?.embedding_fallback ? 'Hash-512' : 'BGE-M3'} detail={health?.embedding_fallback ? 'offline deterministic fallback' : '1,024-dimensional dense vectors'} />
        <Metric label="Active profile" value="Hybrid" detail="dense + BM25 + RRF" />
      </section>
      <section className="split-grid">
        <div className="panel panel-tall"><div className="panel-heading"><div><span className="eyebrow">Runtime health</span><h2>Services at a glance</h2></div><Badge tone="good">operational</Badge></div><div className="health-list">{(health?.available_vector_stores ?? []).map((store) => <div className="health-row" key={store.name}><span className={`health-icon ${store.implemented ? 'health-on' : 'health-off'}`}>{store.implemented ? '✓' : '·'}</span><div><strong>{store.name}</strong><span className="muted">{store.description}</span></div><span className="row-state">{store.implemented ? 'ready' : 'planned'}</span></div>)}</div></div>
        <div className="panel panel-tall"><div className="panel-heading"><div><span className="eyebrow">Evaluation preview</span><h2>Portable leaderboard</h2></div><Badge>illustrative fixture</Badge></div><ResponsiveContainer width="100%" height={240}><BarChart data={benchmarkData} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#e6eaf0" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis domain={[0, 1]} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="ndcg" name="nDCG@10" radius={[5, 5, 0, 0]}>{benchmarkData.map((entry, index) => <Cell key={entry.name} fill={index === 0 ? '#e37c45' : '#274c77'} />)}</Bar></BarChart></ResponsiveContainer><p className="chart-note">Fixture values appear until a benchmark is run on your corpus. They are not résumé claims.</p></div>
      </section>
    </>
  )
}

function DataRoom({ sources, onIngest, busy, error }: { sources: SourceVersion[]; onIngest: (file: File) => void; busy: boolean; error: string }) {
  return <><section className="page-intro"><div><span className="eyebrow">Ingestion / provenance</span><h1>Data Room</h1><p>Bring in mixed-format research material and inspect what the parser actually recovered.</p></div><label className="primary-button">{busy ? 'Processing…' : '+ Import source'}<input type="file" hidden onChange={(event) => event.target.files?.[0] && onIngest(event.target.files[0])} disabled={busy} /></label></section>{error && <div className="callout callout-warn">{error}</div>}<section className="panel"><div className="panel-heading"><div><span className="eyebrow">Source registry</span><h2>Immutable source versions</h2></div><span className="muted">{sources.length} artifacts</span></div>{sources.length === 0 ? <div className="empty-state"><div className="empty-icon">+</div><strong>Drop a source to begin</strong><span>PDF, DOCX, PPTX, XLSX, CSV, HTML, JSON, Markdown, TXT, EML and MSG are supported.</span></div> : <div className="table-wrap"><table><thead><tr><th>Source</th><th>Parser</th><th>Quality</th><th>Elements</th><th>Chunks</th><th>Status</th></tr></thead><tbody>{sources.map((source) => <tr key={source.source_id}><td><strong>{source.name}</strong><span className="table-sub">{source.media_type}</span></td><td><code>{source.parser}</code></td><td><div className="quality"><span style={{ width: `${Math.round(source.quality_score * 100)}%` }} /><b>{Math.round(source.quality_score * 100)}%</b></div></td><td>{source.element_count}</td><td>{source.chunk_count}</td><td><Badge tone={source.status === 'ready' ? 'good' : 'warn'}>{source.status}</Badge></td></tr>)}</tbody></table></div>}</section></>
}

function ResearchWorkspace({ onQuery, result, busy, error }: { onQuery: (question: string, profile: string) => void; result: QueryResponse | null; busy: boolean; error: string }) {
  const [question, setQuestion] = useState('What does the indexed corpus say about revenue growth and risk?')
  const [profile, setProfile] = useState('hybrid')
  return <><section className="page-intro"><div><span className="eyebrow">Research / cited answer</span><h1>Research Workspace</h1><p>Ask a question, then follow every claim back to the exact source location.</p></div><Badge tone="good">evidence required</Badge></section><section className="research-grid"><div className="panel query-panel"><div className="panel-heading"><div><span className="eyebrow">Question</span><h2>Ask the corpus</h2></div><select value={profile} onChange={(event) => setProfile(event.target.value)}><option value="hybrid">Hybrid + RRF</option><option value="dense">Dense similarity</option><option value="mmr">MMR diversity</option></select></div><textarea value={question} onChange={(event) => setQuestion(event.target.value)} /><button className="primary-button submit-button" disabled={busy} onClick={() => onQuery(question, profile)}>{busy ? 'Retrieving evidence…' : 'Run cited query  →'}</button>{error && <div className="callout callout-warn">{error}</div>}<div className="query-hints"><span>Try asking:</span><button onClick={() => setQuestion('Which documents contain numerical evidence of changing margins?')}>numerical evidence</button><button onClick={() => setQuestion('What is not supported by the indexed evidence?')}>abstention behavior</button></div></div><div className="panel answer-panel"><div className="panel-heading"><div><span className="eyebrow">Answer / verifier</span><h2>{result?.insufficient_evidence ? 'Insufficient evidence' : result ? 'Grounded response' : 'Waiting for a question'}</h2></div>{result && <Badge tone={result.insufficient_evidence ? 'warn' : 'good'}>{result.insufficient_evidence ? 'abstain' : 'citations attached'}</Badge>}</div>{result ? <><div className="answer-copy">{result.answer}</div><div className="citation-list">{result.citations.map((citation) => <div className="citation-card" key={citation.label}><span className="citation-label">{citation.label}</span><div><strong>{citation.source_name}</strong><span className="table-sub">{citation.page ? `Page ${citation.page}` : citation.sheet ? `${citation.sheet} · ${citation.cell_range ?? 'range'}` : citation.json_path ?? 'source excerpt'}</span><p>{citation.excerpt}</p></div></div>)}</div><div className="trace-strip"><span>retrieval {result.trace.retrieval_ms} ms</span><span>generation {result.trace.generation_ms} ms</span><span>{result.trace.final_context_chunks} context chunks</span><span>{result.trace.embedding_fallback ? 'hash fallback' : result.trace.embedding_model}</span></div></> : <div className="empty-state answer-empty"><div className="empty-icon">⌁</div><strong>Your answer will appear here</strong><span>Every citation will open the source location and remain visible in the query trace.</span></div>}</div></section></>
}

function RetrievalLab() {
  const stageData = [{ stage: 'Dense', score: 0.91 }, { stage: 'BM25', score: 0.76 }, { stage: 'RRF', score: 0.88 }, { stage: 'Rerank', score: 0.95 }]
  return <><section className="page-intro"><div><span className="eyebrow">Diagnostics / ranking trace</span><h1>Retrieval Lab</h1><p>See which evidence survives each stage of the retrieval pipeline.</p></div><Badge>FAISS local slice</Badge></section><section className="split-grid"><div className="panel panel-tall"><div className="panel-heading"><div><span className="eyebrow">Rank movement</span><h2>One question, four stages</h2></div><span className="muted">demo trace</span></div><ResponsiveContainer width="100%" height={260}><LineChart data={stageData} margin={{ top: 12, right: 16, left: -18, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#e6eaf0" vertical={false} /><XAxis dataKey="stage" tick={{ fontSize: 11 }} /><YAxis domain={[0, 1]} tick={{ fontSize: 11 }} /><Tooltip /><Line type="monotone" dataKey="score" stroke="#e37c45" strokeWidth={3} dot={{ r: 5, fill: '#e37c45' }} /></LineChart></ResponsiveContainer><div className="legend-row"><span><i className="dot dot-orange" /> normalized relevance</span><span><i className="dot dot-blue" /> same chunk identity retained</span></div></div><div className="panel panel-tall"><div className="panel-heading"><div><span className="eyebrow">Evidence packet</span><h2>Trace contract</h2></div><Badge tone="good">auditable</Badge></div><div className="trace-list"><div><b>01</b><span>Original question preserved</span><code>risk + margin evidence</code></div><div><b>02</b><span>Filters validated against allowlist</span><code>source_id: none</code></div><div><b>03</b><span>Dense + lexical candidates fused</span><code>RRF · top 20</code></div><div><b>04</b><span>Context bounded before generation</span><code>top 6 chunks</code></div><div><b>05</b><span>Citations resolve to source elements</span><code>verifier: pass</code></div></div></div></section></>
}

function EvaluationStudio() {
  const data = useMemo(() => benchmarkData.map((item) => ({ ...item, fixture: item.ndcg })), [])
  return <><section className="page-intro"><div><span className="eyebrow">Evaluation / reproducibility</span><h1>Evaluation Studio</h1><p>Separate parser quality, retrieval relevance, answer grounding and system performance.</p></div><Badge>backend benchmark pending</Badge></section><section className="callout callout-warn">The charts below are illustrative fixtures. They stay visibly labelled until a golden-set experiment is run against your corpus.</section><section className="metric-grid"><Metric label="Success@5" value="—" detail="run a golden-set experiment" /><Metric label="nDCG@10" value="—" detail="run a golden-set experiment" /><Metric label="Citation validity" value="—" detail="run a golden-set experiment" /><Metric label="p95 latency" value="—" detail="run a golden-set experiment" /></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">Portable track / fixture</span><h2>Vector store comparison</h2></div><span className="muted">same embeddings · same corpus · same pipeline</span></div><ResponsiveContainer width="100%" height={300}><BarChart data={data} margin={{ top: 12, right: 20, left: -12, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#e6eaf0" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis domain={[0, 1]} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="fixture" name="illustrative nDCG@10" fill="#274c77" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer><div className="table-wrap"><table><thead><tr><th>Query class</th><th>Questions</th><th>Recall@10</th><th>Abstention</th><th>Failure note</th></tr></thead><tbody><tr><td>Numerical / tables</td><td>8</td><td>—</td><td>—</td><td>unit preservation will be checked</td></tr><tr><td>Cross-document</td><td>6</td><td>—</td><td>—</td><td>parent expansion will be checked</td></tr><tr><td>Unanswerable</td><td>4</td><td>—</td><td>—</td><td>controlled refusal will be checked</td></tr></tbody></table></div></section></>
}

export function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [health, setHealth] = useState<Health | null>(null)
  const [sources, setSources] = useState<SourceVersion[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<QueryResponse | null>(null)

  const refresh = () => {
    Promise.all([api.health(), api.sources()]).then(([nextHealth, nextSources]) => { setHealth(nextHealth); setSources(nextSources); setError('') }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'API is not reachable. Start the backend on port 8000.'))
  }
  useEffect(refresh, [])
  const ingest = (file: File) => { setBusy(true); setError(''); api.ingest(file).then(() => refresh()).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Ingestion failed.')).finally(() => setBusy(false)) }
  const query = (question: string, profile: string) => { setBusy(true); setError(''); api.query(question, profile).then(setResult).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Query failed.')).finally(() => setBusy(false)) }
  const content = tab === 'overview' ? <Overview health={health} sources={sources} /> : tab === 'data-room' ? <DataRoom sources={sources} onIngest={ingest} busy={busy} error={error} /> : tab === 'research' ? <ResearchWorkspace onQuery={query} result={result} busy={busy} error={error} /> : tab === 'retrieval' ? <RetrievalLab /> : <EvaluationStudio />
  return <div className="app-shell"><Header health={health} onRefresh={refresh} /><div className="app-body"><aside className="sidebar"><div className="sidebar-label">Workspace</div><nav>{tabs.map((item) => <button key={item.id} className={tab === item.id ? 'nav-item active' : 'nav-item'} onClick={() => { setTab(item.id); setError('') }}><span className="nav-icon">{item.id === 'overview' ? '◈' : item.id === 'data-room' ? '▦' : item.id === 'research' ? '⌕' : item.id === 'retrieval' ? '↗' : '▥'}</span><span><b>{item.label}</b><small>{item.eyebrow}</small></span></button>)}</nav><div className="sidebar-footer"><div className="profile-dot">LK</div><div><strong>Local operator</strong><span>localhost only</span></div></div></aside><main className="main-content">{content}</main></div></div>
}
