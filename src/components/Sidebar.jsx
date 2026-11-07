import { useRef, useState } from "react";
import { ChevronDown, ChevronRight, FileText, Folder, FolderOpen, Github, Search, Upload } from "lucide-react";
import BrandMark from "./BrandMark.jsx";

export default function Sidebar({ notes, selected, onSelect, onUpload, query, setQuery, onSearch }) {
  const inputRef = useRef(null);
  const [expanded, setExpanded] = useState({ notes: true, src: true });
  const groups = Object.groupBy ? Object.groupBy(notes, (note) => note.folder || "notes") : notes.reduce((acc, note) => ((acc[note.folder || "notes"] ||= []).push(note), acc), {});
  return <aside className="sidebar">
    <div className="brand"><span className="brand-icon"><BrandMark size={22} /></span><span>Second Brain Atlas<small>KNOWLEDGE MAP</small></span></div>
    <nav className="top-links"><a className="active">Features</a><a href="#docs">Docs</a><a href="https://github.com/khalidjmonday/second-brain-graph" target="_blank" rel="noreferrer"><Github size={14} /> GitHub</a></nav>
    <div className="sidebar-heading"><span>EXPLORER</span><button className="quiet-icon" onClick={() => inputRef.current?.click()} title="Import Markdown folder"><Upload size={14} /></button></div>
    <label className="search-field"><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && onSearch()} placeholder="Find a note..." /></label>
    <div className="tree-list">
      {Object.entries(groups).map(([folder, folderNotes]) => <div key={folder}>
        <button className="tree-folder" onClick={() => setExpanded((state) => ({ ...state, [folder]: !state[folder] }))}>{expanded[folder] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}{expanded[folder] ? <FolderOpen size={15} /> : <Folder size={15} />}<span>{folder}/</span></button>
        {expanded[folder] && folderNotes.map((note) => <button key={note.id} className={`tree-file ${selected?.id === note.id ? "selected" : ""}`} onClick={() => onSelect(note)}><FileText size={14} /><span>{note.title}</span></button>)}
      </div>)}
      {!notes.length && <p className="empty-tree">Choose a Markdown folder to begin.</p>}
    </div>
    <div className="sidebar-bottom">
      <div className="import-card"><div className="import-title"><span className="status-dot" /> LOCAL VAULT</div><p>Markdown stays in this browser session.</p><button onClick={() => inputRef.current?.click()}><Upload size={13} /> Import notes</button></div>
      <input ref={inputRef} hidden type="file" accept=".md,text/markdown" multiple webkitdirectory="" directory="" onChange={(event) => { onUpload(event.target.files); event.target.value = ""; }} />
      <span className="sidebar-footnote">SECOND BRAIN <i>·</i> LOCAL EXPLORER</span>
    </div>
  </aside>;
}
