import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

function layout(notes, spring, repulsion) {
  const points = notes.map((_, index) => {
    const angle = index * 2.399963;
    const radius = 1.1 + Math.sqrt(index) * (1.5 + repulsion * 1.5);
    return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(index * 1.7) * 1.35, Math.sin(angle) * radius);
  });
  for (let pass = 0; pass < 26; pass += 1) {
    notes.forEach((note, index) => {
      const force = new THREE.Vector3();
      points.forEach((other, otherIndex) => {
        if (index === otherIndex) return;
        const delta = points[index].clone().sub(other);
        const distanceSquared = Math.max(delta.lengthSq(), 0.25);
        force.add(delta.normalize().multiplyScalar((1.8 + repulsion * 2) / distanceSquared));
      });
      for (const linkedTitle of note.links || []) {
        const target = notes.findIndex((item) => item.title === linkedTitle || item.id === linkedTitle);
        if (target >= 0) force.add(points[target].clone().sub(points[index]).multiplyScalar(spring * 0.055));
      }
      points[index].add(force.clampLength(0, 0.14));
    });
  }
  return points;
}

function Sphere({ note, position, active, onSelect }) {
  const mesh = useRef();
  useFrame((state, delta) => { if (mesh.current) mesh.current.scale.lerp(new THREE.Vector3(active ? 1.24 : 1, active ? 1.24 : 1, active ? 1.24 : 1), 1 - Math.exp(-delta * 9)); });
  return <group position={position}>
    <mesh ref={mesh} onClick={(event) => { event.stopPropagation(); onSelect(note); }} onPointerOver={(event) => { event.stopPropagation(); document.body.style.cursor = "pointer"; }} onPointerOut={() => { document.body.style.cursor = "default"; }}>
      <sphereGeometry args={[active ? 0.22 : 0.17, 28, 28]} />
      <meshStandardMaterial color={note.color} emissive={note.color} emissiveIntensity={active ? 0.42 : 0.12} roughness={0.38} metalness={0.18} />
    </mesh>
    <Html position={[0, 0.35, 0]} center distanceFactor={10} style={{ pointerEvents: "none", whiteSpace: "nowrap" }}><span className={`node-label ${active ? "active" : ""}`}>{note.title}</span></Html>
  </group>;
}

function Graph({ notes, selected, onSelect, spring, repulsion, showSemantic }) {
  const positions = useMemo(() => layout(notes, spring, repulsion), [notes, spring, repulsion]);
  const edges = [];
  const noteIndex = new Map(notes.map((note, index) => [note.title, index]));
  notes.forEach((note, index) => (note.links || []).forEach((title) => {
    const target = noteIndex.get(title);
    if (target > index) edges.push([index, target, false]);
  }));
  if (showSemantic) notes.forEach((note, index) => (note.semanticLinks || []).forEach((title) => {
    const target = noteIndex.get(title);
    if (target !== undefined && target > index) edges.push([index, target, true]);
  }));
  return <>
    {edges.map(([from, to, semantic], index) => <Line key={`${from}-${to}-${index}`} points={[positions[from], positions[to]]} color={semantic ? "#8aa6c5" : "#477dbb"} transparent opacity={semantic ? 0.52 : 0.76} lineWidth={semantic ? 0.9 : 1.05} dashed={semantic} dashSize={0.12} gapSize={0.1} />)}
    {notes.map((note, index) => <Sphere key={note.id} note={note} position={positions[index]} active={selected?.id === note.id} onSelect={onSelect} />)}
  </>;
}

function FpsCounter({ onFps }) {
  const frames = useRef(0);
  const last = useRef(performance.now());
  useFrame(() => {
    frames.current += 1;
    const now = performance.now();
    if (now - last.current >= 1000) {
      onFps(Math.round((frames.current * 1000) / (now - last.current)));
      frames.current = 0;
      last.current = now;
    }
  });
  return null;
}

export default function Scene({ notes, selected, onSelect, spring, repulsion, showSemantic, controlsRef, onFps }) {
  return <Canvas camera={{ position: [11, 10, 13], fov: 39 }} dpr={[1, 1.75]} gl={{ antialias: true, preserveDrawingBuffer: true }} onPointerMissed={() => onSelect(null)}>
    <color attach="background" args={["#f6f9fd"]} />
    <ambientLight intensity={1.05} /><directionalLight position={[5, 8, 5]} intensity={1.15} />
    <FpsCounter onFps={onFps} />
    <gridHelper args={[50, 50, "#d6e1ef", "#eaf0f7"]} position={[0, -4, 0]} />
    <Graph notes={notes} selected={selected} onSelect={onSelect} spring={spring} repulsion={repulsion} showSemantic={showSemantic} />
    <OrbitControls ref={controlsRef} makeDefault enableDamping dampingFactor={0.08} minDistance={5} maxDistance={38} />
  </Canvas>;
}
