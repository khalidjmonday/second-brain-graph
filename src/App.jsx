import { useMemo, useRef, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, BrainCircuit, FileText, Link2, Search, Sparkles, X } from "lucide-react";
import { toPng } from "html-to-image";
import Sidebar from "./components/Sidebar.jsx";
import Scene from "./components/Scene.jsx";
import ControlPanel, { CameraPanel } from "./components/ControlPanel.jsx";
import { DEMO_NOTES, parseMarkdownFiles } from "./data.js";

function App() {
  const [notes, setNotes] = useState(DEMO_NOTES);
  const [selected, setSelected] = useState(DEMO_NOTES[1]);
  const [query, setQuery] = useState("");
  const [terminalQuery, setTerminalQuery] = useState("main.py search 'BFS vs DFS'");
  const [spring, setSpring] = useState(0.3);
  const [repulsion, setRepulsion] = useState(0.6);
  const [showSemantic, setShowSemantic] = useState(true);
  const [activeTopic, setActiveTopic] = useState("All topics");
  const [fps, setFps] = useState(0);
  const controls = useRef();
  const viewport = useRef();
  const graphEdges = useMemo(() => notes.reduce((total, note) => total + (note.links?.length || 0), 0), [notes]);
  const semanticCount = useMemo(() => notes.reduce((total, note) => total + (note.semanticLinks?.length || 0), 0), [notes]);
  const context = useMemo(() => selected ? notes.filter((note) => note.id !== selected.id && (selected.links?.includes(note.title) || note.links?.includes(selected.title))) : [], [notes, selected]);

  async function importFolder(files) {
    const imported = await parseMarkdownFiles(files || []);
    if (imported.length) { setNotes(imported); setSelected(imported[0]); setActiveTopic("All topics"); }
  }

  function runSearch(value = query) {
    const phrase = value.trim();
    const normalized = phrase.toLowerCase();
    const found = normalized && notes.find((note) => note.title.toLowerCase().includes(normalized) || note.text.toLowerCase().includes(normalized));
    if (found) setSelected(found);
    setTerminalQuery(phrase);
  }

  async function exportSlide() {
    if (!viewport.current) return;
    try {
      const dataUrl = await toPng(viewport.current, { pixelRatio: 2, backgroundColor: "#f6f9fd", cacheBust: true });
      const link = document.createElement("a"); link.download = "Second-Brain-Graph.png"; link.href = dataUrl; link.click();
    } catch { // WebGL canvases can be blocked by browser memory limits; fall back to the raw canvas.
      const canvas = viewport.current.querySelector("canvas");
      if (canvas) { const link = document.createElement("a"); link.download = "Second-Brain-Graph.png"; link.href = canvas.toDataURL("image/png"); link.click(); }
    }
  }

  return <main className="app-shell">
    <Sidebar notes={notes} selected={selected} onSelect={setSelected} onUpload={importFolder} query={query} setQuery={setQuery} onSearch={() => runSearch()} activeTopic={activeTopic} setActiveTopic={setActiveTopic} />
    <section className="workspace">
      <header className="workspace-bar"><div className="crumb"><span>Workspace</span><span className="crumb-sep">/</span><strong>Knowledge map</strong></div><div className="workspace-meta"><span><b>{notes.length}</b> notes</span><span><b>{graphEdges}</b> wikilink references</span><span className="privacy"><i /> Browser session</span></div></header>
      <div className="graph-viewport" ref={viewport}>
        <Scene notes={notes} selected={selected} onSelect={setSelected} spring={spring} repulsion={repulsion} showSemantic={showSemantic} controlsRef={controls} onFps={setFps} />
        <div className="viewport-caption"><span className="caption-kicker"><BrainCircuit size={13} /> SECOND BRAIN ATLAS</span><h1>Vault graph</h1><p>Browse notes and follow their links.</p></div>
        <div className="legend"><span><i className="legend-solid" /> Wikilink</span><button disabled={!semanticCount} onClick={() => setShowSemantic((value) => !value)}><i className="legend-dash" /> Suggested links {semanticCount ? (showSemantic ? "on" : "off") : "unavailable"}</button></div>
        <div className="camera-wrap"><CameraPanel fps={fps} onReset={() => controls.current?.reset()} /></div>
        {selected && <aside key={selected.id} className="inspector-card">
          <button className="inspect-close" onClick={() => setSelected(null)} aria-label="Close note details"><X size={14} /></button>
          <div className="inspect-kind"><FileText size={13} /> MARKDOWN NOTE <span className="cluster-chip" style={{ "--cluster": selected.color }}>{selected.cluster}</span></div>
          <h2>{selected.title}</h2><div className="inspect-path">{selected.folder}/{selected.title}</div>
          <div className="metadata-label">NOTE PREVIEW</div>
          <p className="inspect-summary">{selected.text}</p>
          <div className="inspect-links"><span><Link2 size={13} /> {selected.links?.length || 0} outgoing</span><span><Sparkles size={13} /> {context.length} related</span></div>
        </aside>}
        <ControlPanel spring={spring} setSpring={setSpring} repulsion={repulsion} setRepulsion={setRepulsion} onExport={exportSlide} />
        <div className="terminal-card"><div className="terminal-head"><span><Search size={13} /> Find in notes</span><span className="terminal-hint">TITLE + PREVIEW</span></div><form onSubmit={(event) => { event.preventDefault(); runSearch(terminalQuery); }}><input aria-label="Search note titles and previews" placeholder="Search this vault…" value={terminalQuery} onChange={(event) => setTerminalQuery(event.target.value)} /><button aria-label="Find note"><ArrowUpRight size={14} /></button></form><div className="terminal-result">{selected ? `Selected: ${selected.title.replace(".md", "")}` : "Enter a title or phrase"}<span className="terminal-context">{context.length} linked notes</span></div></div>
        <div className="zoom-hint"><span><ArrowDownLeft size={12} /> Drag to orbit</span><span>Scroll to zoom</span></div>
      </div>
      <footer className="status-bar"><span><i className="status-online" /> Notes stay in this browser session</span><span><Search size={12} /> Search checks note titles and previews</span><span>3D graph <b>·</b> WebGL</span></footer>
    </section>
  </main>;
}

export default App;
