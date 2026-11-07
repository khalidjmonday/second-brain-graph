import { Camera, Download, Gauge, RotateCcw } from "lucide-react";

function Slider({ label, value, onChange, min = 0.1, max = 0.9, step = 0.01 }) {
  return <label className="slider-row"><span>{label}</span><output>{value.toFixed(2)}</output><input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

export function CameraPanel({ onReset, fps }) {
  return <section className="hud-card camera-card"><div className="panel-title"><span><Camera size={14} /> 3D Camera</span><span className="fps"><i />{fps || "—"} FPS</span></div><div className="camera-body"><div className="axis-gizmo"><span className="axis-x">X</span><span className="axis-y">Y</span><span className="axis-z">Z</span><b /></div><div><div className="camera-mode">Orbit / Pan</div><button className="small-action" onClick={onReset}><RotateCcw size={12} /> Reset view</button></div></div></section>;
}

export default function ControlPanel({ spring, setSpring, repulsion, setRepulsion, onExport }) {
  return <section className="hud-card control-card"><div className="panel-title"><span><Gauge size={14} /> Physics adjustment</span><span className="live-label">LIVE</span></div><Slider label="Spring force" value={spring} onChange={setSpring} /><Slider label="Node repulsion" value={repulsion} onChange={setRepulsion} /><button className="export-button" onClick={onExport}><Download size={14} /> Export slide</button></section>;
}
