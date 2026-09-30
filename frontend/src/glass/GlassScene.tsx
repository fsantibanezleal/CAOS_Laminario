// The 3D scene of a set of glass slides (U17): real glass (soda-lime, refractive index 1.5, 1 mm thick, green at its
// edges), frosted ends written with the slide's name and facts, a coverslip over the sample, and the arrangement the
// visitor chose around them: a carousel, the drawer of a steel filing cabinet pulled out, a slide box with its lid
// open, a cardboard folder. It renders only when something changes (a hidden tab renders nothing), moves only when
// asked (no motion at all under reduced motion), and reports where each slide lies on the screen so the page's
// accessible layer and the gates can reach it.
import { Edges, Environment, Lightformer } from "@react-three/drei";
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import * as THREE from "three";
import {
  COVERSLIP_MM, GLASS_MM, SLOT_MM, BOX_ROWS, cameraFor, coverslipSide, folderPages, layout, FOLDER_PLACES,
  type Arrangement, type GlassItem, type Placement,
} from "./model";
import { iconTexture, labelFacesReady, labelTextures, pictureTexture, type LabelSides } from "./textures";

/** Where a slide lies on the screen: its bounding box, and a point on it the pointer can reach (the top strip of a
 * standing slide, which the one in front does not cover). */
export interface ScreenSpot {
  left: number;
  top: number;
  width: number;
  height: number;
  pickX: number;
  pickY: number;
}

export interface GlassSceneProps {
  items: GlassItem[];
  arrangement: Arrangement;
  selected: number;
  onSelect: (index: number) => void;
  onOpen: (index: number) => void;
  /** Reduced motion: every change is a cut, nothing moves. */
  still: boolean;
  /** The words on the label holder of a drawer, a box's lid or a folder's cover. */
  title: string;
  /** The colour of the set's collection, for the drawer's label and the folder's band. */
  hue: string;
  accent: string;
  /** The room's colour of the surface the slides lie on and of the backdrop: glass shows what is behind it. */
  ground: string;
  onSpots: (spots: (ScreenSpot | null)[]) => void;
}

/** The glass itself: one material for every slide and coverslip, so the renderer's single transmission pass serves
 * them all. */
function useGlass() {
  return useMemo(() => new THREE.MeshPhysicalMaterial({
    color: "#ffffff",
    metalness: 0,
    roughness: 0.03,
    transmission: 1,
    thickness: GLASS_MM,
    ior: 1.5,
    attenuationColor: new THREE.Color("#a8d5bd"),
    attenuationDistance: 9,
    specularIntensity: 1,
    clearcoat: 0.4,
    clearcoatRoughness: 0.05,
    envMapIntensity: 1.3,
  }), []);
}

const damp = THREE.MathUtils.damp;

/** A soft silhouette, blurred as a shadow cast by a diffuse light: one texture for every slide's shadow. */
function useShadowTexture() {
  return useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.filter = "blur(14px)";
      ctx.fillStyle = "rgba(0,0,0,1)";
      ctx.fillRect(40, 36, 176, 56);
    }
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, []);
}

/** Where the surface lies under a set: the table a carousel stands on, a folder's board. */
function surfaceOf(arrangement: Arrangement): number | null {
  if (arrangement === "carousel") return -15.3;
  if (arrangement === "folder") return -0.55;
  return null;
}

function Slide({ item, index, placement, glass, still, chosen, accent, onHover, onSelect, onOpen, register,
  arrangement, shadowMap }: {
  item: GlassItem; index: number; placement: Placement; glass: THREE.Material; still: boolean; chosen: boolean;
  arrangement: Arrangement; shadowMap: THREE.Texture;
  accent: string; onHover: (index: number | null) => void; onSelect: (index: number) => void;
  onOpen: (index: number) => void; register: (index: number, group: THREE.Group | null) => void;
}) {
  const group = useRef<THREE.Group>(null);
  const shadow = useRef<THREE.Mesh>(null);
  const surface = surfaceOf(arrangement);
  const invalidate = useThree((s) => s.invalidate);
  const { long, short, label } = item.format;
  const side = coverslipSide(item.format);
  const [labels, setLabels] = useState<LabelSides | null>(null);
  const [icon, setIcon] = useState<THREE.Texture | null>(null);
  const [picture, setPicture] = useState<THREE.Texture | null>(null);
  const [photo, setPhoto] = useState<THREE.Texture | null>(null);

  const labelKey = `${item.name}|${item.reference ?? ""}|${item.facts.join("|")}|${item.hue}|${long}x${short}`;
  useEffect(() => {
    if (item.photo) return undefined;
    let alive = true;
    let made: LabelSides | null = null;
    labelFacesReady().then(() => {
      if (!alive) return;
      made = labelTextures(item, item.format);
      setLabels(made);
      invalidate();
    });
    return () => {
      alive = false;
      made?.left.dispose();
      made?.right.dispose();
    };
    // The label is redrawn when its words change (another language), not when the item object is rebuilt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [labelKey, item.photo, invalidate]);

  useEffect(() => {
    let alive = true;
    if (item.photo) {
      pictureTexture(item.photo, long / short).then((t) => { if (alive) { setPhoto(t); invalidate(); } });
    } else if (item.image) {
      pictureTexture(item.image, 1).then((t) => { if (alive) { setPicture(t); invalidate(); } });
    }
    if (!item.photo && item.icon) {
      iconTexture(item.icon, item.hue).then((t) => { if (alive) { setIcon(t); invalidate(); } });
    }
    return () => { alive = false; };
  }, [item.photo, item.image, item.icon, item.hue, long, short, invalidate]);

  useEffect(() => {
    // Turned about the vertical first, then leaned in its own frame: a carousel slide leans back wherever it stands.
    group.current?.rotation.reorder("YXZ");
    register(index, group.current);
    return () => register(index, null);
  }, [index, register]);

  // Move toward the placement: damped (a slide glides), or at once under reduced motion.
  useFrame((_, delta) => {
    const g = group.current;
    if (!g) return;
    g.visible = placement.visible;
    const [px, py, pz] = placement.position;
    const [rx, ry, rz] = placement.rotation;
    if (still) {
      g.position.set(px, py, pz);
      g.rotation.set(rx, ry, rz);
      return;
    }
    const k = 9;
    g.position.set(damp(g.position.x, px, k, delta), damp(g.position.y, py, k, delta), damp(g.position.z, pz, k, delta));
    g.rotation.set(damp(g.rotation.x, rx, k, delta), damp(g.rotation.y, ry, k, delta), damp(g.rotation.z, rz, k, delta));
    const far = Math.abs(g.position.x - px) + Math.abs(g.position.y - py) + Math.abs(g.position.z - pz)
      + Math.abs(g.rotation.x - rx) + Math.abs(g.rotation.y - ry) + Math.abs(g.rotation.z - rz);
    if (far > 0.002) invalidate();
    const sh = shadow.current;
    if (sh && surface !== null) {
      // The shadow stays on the surface, under the slide, fainter as the slide rises.
      sh.visible = g.visible;
      sh.position.set(g.position.x, surface, g.position.z + (arrangement === "folder" ? 1.2 : 0));
      sh.rotation.set(-Math.PI / 2, 0, arrangement === "folder" ? 0 : g.rotation.y);
      (sh.material as THREE.MeshBasicMaterial).opacity = Math.max(0.12, 0.42 - g.position.y * 0.02);
    }
  });

  const click = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (e.delta > 6) return; // the end of a drag, not a click
    if (chosen) onOpen(index);
    else onSelect(index);
  };
  const top = GLASS_MM / 2;

  return (
    <>
    {surface !== null ? (
      <mesh ref={shadow} renderOrder={-1}>
        <planeGeometry args={arrangement === "folder" ? [long * 1.3, short * 1.6] : [long * 1.35, 12]} />
        <meshBasicMaterial map={shadowMap} transparent depthWrite={false} color="#000000" opacity={0.42}
          toneMapped={false} />
      </mesh>
    ) : null}
    <group ref={group} name={`slide-${item.id}`}
      onPointerOver={(e) => { e.stopPropagation(); onHover(index); }}
      onPointerOut={() => onHover(null)} onClick={click}>
      <mesh material={glass}>
        <boxGeometry args={[long, short, GLASS_MM]} />
        <Edges threshold={20} color={chosen ? accent : "#7fae96"} />
      </mesh>
      {item.photo ? (
        photo ? (
          <mesh position={[0, 0, top + 0.02]}>
            <planeGeometry args={[long, short]} />
            <meshStandardMaterial map={photo} roughness={0.3} metalness={0} />
          </mesh>
        ) : null
      ) : (
        <>
          {labels ? (
            <>
              <mesh position={[-long / 2 + label / 2, 0, top + 0.02]}>
                <planeGeometry args={[label, short]} />
                <meshStandardMaterial map={labels.left} roughness={0.95} transparent opacity={item.empty ? 0.7 : 1} />
              </mesh>
              <mesh position={[long / 2 - label / 2, 0, top + 0.02]}>
                <planeGeometry args={[label, short]} />
                <meshStandardMaterial map={labels.right} roughness={0.95} transparent opacity={item.empty ? 0.7 : 1} />
              </mesh>
            </>
          ) : null}
          {picture ? (
            <mesh position={[0, 0, top + 0.01]}>
              <planeGeometry args={[side, side]} />
              <meshStandardMaterial map={picture} roughness={0.55} />
            </mesh>
          ) : icon ? (
            <mesh position={[0, 0, top + 0.01]}>
              <planeGeometry args={[side * 0.82, side * 0.82]} />
              <meshBasicMaterial map={icon} alphaTest={0.4} toneMapped={false}
                color={item.empty ? "#b9b4ad" : "#ffffff"} />
            </mesh>
          ) : null}
          <mesh material={glass} position={[0, 0, top + COVERSLIP_MM / 2 + 0.03]}>
            <boxGeometry args={[side, side, COVERSLIP_MM]} />
          </mesh>
        </>
      )}
    </group>
    </>
  );
}

/** A canvas texture with words, for a label holder, a lid's index card or a folder's cover. */
function useWords(lines: string[], hue: string, widthMm: number, heightMm: number, ground = "#f4efe3") {
  const key = lines.join("|");
  return useMemo(() => {
    const mm = 10;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(widthMm * mm);
    canvas.height = Math.round(heightMm * mm);
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = ground;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = hue;
      ctx.fillRect(0, 0, canvas.width, 1.6 * mm);
      ctx.fillStyle = "#251c16";
      ctx.textBaseline = "middle";
      const size = Math.min(3.6 * mm, (canvas.height - 2 * mm) / Math.max(1, lines.length) / 1.2);
      ctx.font = `700 ${size}px "Courier Prime", "Courier New", monospace`;
      lines.forEach((line, i) => {
        let text = line;
        while (text.length > 1 && ctx.measureText(text).width > canvas.width - 2 * mm) text = text.slice(0, -1);
        ctx.fillText(text === line ? line : `${text.trimEnd()}…`, mm,
          1.6 * mm + (canvas.height - 1.6 * mm) * ((i + 0.5) / lines.length));
      });
    }
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, hue, widthMm, heightMm, ground]);
}

/** The drawer of a steel slide filing cabinet, pulled out; the cabinet behind it with its closed drawers. Slides stand
 * on their long edge from front to back, as they are filed. */
function CabinetDrawer({ n, title, hue }: { n: number; title: string; hue: string }) {
  const depth = Math.max(40, n * SLOT_MM) + 16;
  const steel = useMemo(() => new THREE.MeshStandardMaterial({ color: "#aeb4b9", metalness: 0.55, roughness: 0.42 }), []);
  const body = useMemo(() => new THREE.MeshStandardMaterial({ color: "#8d949a", metalness: 0.5, roughness: 0.5 }), []);
  const card = useWords([title], hue, 40, 11);
  const floor = -13.8;
  const front = depth / 2 + 2;
  return (
    <group>
      <mesh material={steel} position={[0, floor - 0.75, 0]}><boxGeometry args={[94, 1.5, depth]} /></mesh>
      <mesh material={steel} position={[-47.5, floor + 9, 0]}><boxGeometry args={[1.2, 20, depth]} /></mesh>
      <mesh material={steel} position={[47.5, floor + 9, 0]}><boxGeometry args={[1.2, 20, depth]} /></mesh>
      <mesh material={steel} position={[0, floor + 9, -depth / 2]}><boxGeometry args={[94, 20, 1.2]} /></mesh>
      <mesh material={steel} position={[0, floor + 17, front]}><boxGeometry args={[102, 38, 2.4]} /></mesh>
      <mesh position={[0, floor + 26, front + 1.3]}>
        <planeGeometry args={[40, 11]} />
        <meshStandardMaterial map={card} roughness={0.9} />
      </mesh>
      <mesh material={body} position={[0, floor + 11, front + 3.2]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[1.6, 1.6, 34, 16]} />
      </mesh>
      {/* The cabinet: the drawer comes out of it; the drawers above are closed. */}
      <mesh material={body} position={[0, floor + 96, -depth / 2 - 50]}><boxGeometry args={[112, 150, 124]} /></mesh>
      {[0, 1, 2].map((k) => (
        <group key={k} position={[0, floor + 44 + k * 40, -depth / 2 + 12.2]}>
          <mesh material={steel}><boxGeometry args={[102, 36, 2.4]} /></mesh>
          <mesh material={body} position={[0, -6, 2.4]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[1.4, 1.4, 30, 12]} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/** A 100-place slide box, its lid open behind it: slides stand in its grooved slots, in two rows. */
function SlideBox({ n, title, hue }: { n: number; title: string; hue: string }) {
  const perRow = Math.ceil(n / BOX_ROWS);
  const depth = Math.max(40, perRow * SLOT_MM) + 14;
  const plastic = useMemo(() => new THREE.MeshStandardMaterial({ color: "#4f5f70", metalness: 0.05, roughness: 0.45 }),
    []);
  const sheet = useWords([title], hue, 150, Math.max(24, depth * 0.4), "#fbfaf6");
  const floor = -13.8;
  const width = 186;
  return (
    <group>
      <mesh material={plastic} position={[0, floor - 1, 0]}><boxGeometry args={[width, 2, depth]} /></mesh>
      <mesh material={plastic} position={[-width / 2, floor + 11, 0]}><boxGeometry args={[2, 24, depth]} /></mesh>
      <mesh material={plastic} position={[width / 2, floor + 11, 0]}><boxGeometry args={[2, 24, depth]} /></mesh>
      <mesh material={plastic} position={[0, floor + 11, depth / 2]}><boxGeometry args={[width, 24, 2]} /></mesh>
      <mesh material={plastic} position={[0, floor + 11, -depth / 2]}><boxGeometry args={[width, 24, 2]} /></mesh>
      <mesh material={plastic} position={[0, floor + 6, 0]}><boxGeometry args={[4, 12, depth]} /></mesh>
      {/* The lid, hinged at the back and opened past upright, its index sheet inside. */}
      <group position={[0, floor + 23, -depth / 2]} rotation={[-1.95, 0, 0]}>
        <mesh material={plastic} position={[0, 0, depth / 2]}><boxGeometry args={[width, 2, depth]} /></mesh>
        <mesh position={[0, -1.1, depth / 2]} rotation={[Math.PI / 2, 0, 0]}>
          <planeGeometry args={[150, Math.max(24, depth * 0.4)]} />
          <meshStandardMaterial map={sheet} roughness={0.95} />
        </mesh>
      </group>
    </group>
  );
}

/** A 20-place cardboard folder lying open: two columns of ten numbered recesses, the page of the chosen slide. */
function Folder({ n, page, title, hue }: { n: number; page: number; title: string; hue: string }) {
  const board = useMemo(() => {
    const mm = 3;
    const canvas = document.createElement("canvas");
    canvas.width = 196 * mm;
    canvas.height = 336 * mm;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#d9c9a6";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = hue;
      ctx.fillRect(0, 0, canvas.width, 3 * mm);
      ctx.font = `700 ${5 * mm}px "Courier Prime", monospace`;
      ctx.textBaseline = "middle";
      for (let k = 0; k < FOLDER_PLACES; k += 1) {
        const col = Math.floor(k / 10);
        const row = k % 10;
        const cx = (98 + (col - 0.5) * 86) * mm;
        const cy = (168 + (row - 4.5) * 30) * mm;
        ctx.fillStyle = "#c8b58f";
        ctx.fillRect(cx - 40 * mm, cy - 14 * mm, 80 * mm, 28 * mm);
        ctx.fillStyle = "#6b5a3d";
        ctx.fillText(String(page * FOLDER_PLACES + k + 1), col === 0 ? 2 * mm : cx + 41 * mm, cy);
      }
    }
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    return t;
  }, [page, hue]);
  const cover = useWords([title, `${page + 1} / ${folderPages(n)}`], hue, 60, 16);
  return (
    <group position={[0, -1.2, 0]}>
      <mesh position={[0, -0.6, 0]}><boxGeometry args={[196, 1.2, 336]} /><meshStandardMaterial color="#cbb993" roughness={0.95} /></mesh>
      <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[196, 336]} />
        <meshStandardMaterial map={board} roughness={0.96} />
      </mesh>
      <mesh position={[0, 0.03, -150]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[60, 16]} />
        <meshStandardMaterial map={cover} roughness={0.9} />
      </mesh>
    </group>
  );
}

/** The camera goes where the arrangement is seen best, gliding there (or cutting under reduced motion). */
function CameraRig({ arrangement, n, still }: { arrangement: Arrangement; n: number; still: boolean }) {
  const { camera, invalidate } = useThree();
  const aim = useMemo(() => cameraFor(arrangement, n), [arrangement, n]);
  const look = useRef(new THREE.Vector3(...aim.target));
  useFrame((_, delta) => {
    const cam = camera as THREE.PerspectiveCamera;
    const [x, y, z] = aim.position;
    if (still) {
      cam.position.set(x, y, z);
      look.current.set(...aim.target);
    } else {
      cam.position.set(damp(cam.position.x, x, 5, delta), damp(cam.position.y, y, 5, delta),
        damp(cam.position.z, z, 5, delta));
      look.current.set(damp(look.current.x, aim.target[0], 5, delta), damp(look.current.y, aim.target[1], 5, delta),
        damp(look.current.z, aim.target[2], 5, delta));
      if (cam.position.distanceTo(new THREE.Vector3(x, y, z)) > 0.05) invalidate();
    }
    if (cam.fov !== aim.fov) {
      cam.fov = aim.fov;
      cam.updateProjectionMatrix();
    }
    cam.lookAt(look.current);
  });
  return null;
}

/** After every frame that moved something, where each slide lies on the screen. */
function Spots({ groups, items, arrangement, onSpots }: {
  groups: MutableRefObject<(THREE.Group | null)[]>; items: GlassItem[]; arrangement: Arrangement;
  onSpots: (spots: (ScreenSpot | null)[]) => void;
}) {
  const { camera, size } = useThree();
  const last = useRef("");
  const corner = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    const spots = items.map((item, i) => {
      const g = groups.current[i];
      if (!g || !g.visible) return null;
      g.updateWorldMatrix(true, false);
      let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity;
      const { long, short } = item.format;
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) {
        corner.set((sx * long) / 2, (sy * short) / 2, (sz * GLASS_MM) / 2).applyMatrix4(g.matrixWorld).project(camera);
        const px = ((corner.x + 1) / 2) * size.width;
        const py = ((1 - corner.y) / 2) * size.height;
        minX = Math.min(minX, px); maxX = Math.max(maxX, px); minY = Math.min(minY, py); maxY = Math.max(maxY, py);
      }
      // Standing slides are reached by their top strip, which the slide in front does not cover.
      const standing = arrangement === "drawer" || arrangement === "box";
      corner.set(0, standing ? short / 2 - 1.2 : 0, GLASS_MM / 2).applyMatrix4(g.matrixWorld).project(camera);
      return { left: minX, top: minY, width: maxX - minX, height: maxY - minY,
        pickX: ((corner.x + 1) / 2) * size.width, pickY: ((1 - corner.y) / 2) * size.height };
    });
    const key = spots.map((s) => (s ? `${Math.round(s.pickX)},${Math.round(s.pickY)},${Math.round(s.width)}` : "-"))
      .join(";");
    if (key !== last.current) {
      last.current = key;
      onSpots(spots);
    }
  });
  return null;
}

function SceneContents(props: GlassSceneProps) {
  const { items, arrangement, selected, onSelect, onOpen, still, title, hue, accent, ground, onSpots } = props;
  const table = useMemo(() => new THREE.Color(ground), [ground]);
  const glass = useGlass();
  const shadowMap = useShadowTexture();
  const [hover, setHover] = useState<number | null>(null);
  const invalidate = useThree((s) => s.invalidate);
  const lifted = arrangement === "drawer" || arrangement === "box" || arrangement === "folder" ? hover ?? selected : null;
  const placements = useMemo(() => layout(arrangement, items.length, selected, lifted),
    [arrangement, items.length, selected, lifted]);
  const groups = useRef<(THREE.Group | null)[]>([]);
  const register = useMemo(() => (index: number, group: THREE.Group | null) => { groups.current[index] = group; },
    []);
  useEffect(() => { invalidate(); }, [placements, invalidate]);
  useEffect(() => {
    document.body.style.cursor = hover === null ? "" : "pointer";
    return () => { document.body.style.cursor = ""; };
  }, [hover]);

  return (
    <>
      <CameraRig arrangement={arrangement} n={items.length} still={still} />
      <color attach="background" args={[ground]} />
      {/* The surface the set stands or lies on, the page's own: the glass refracts it and it takes their shadows. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, arrangement === "folder" ? -2.6 : -15.4, 0]}>
        <planeGeometry args={[6000, 6000]} />
        <meshBasicMaterial color={table} toneMapped={false} />
      </mesh>
      <ambientLight intensity={0.55} />
      <directionalLight position={[90, 180, 140]} intensity={1.5} />
      <directionalLight position={[-120, 60, -80]} intensity={0.35} />
      <Environment resolution={128} frames={1}>
        <Lightformer form="rect" intensity={2.4} position={[0, 160, 90]} rotation={[-Math.PI / 3, 0, 0]} scale={[320, 90, 1]} />
        <Lightformer form="rect" intensity={1.2} position={[-200, 40, 0]} rotation={[0, Math.PI / 2, 0]} scale={[200, 120, 1]} />
        <Lightformer form="rect" intensity={1.2} position={[200, 40, 0]} rotation={[0, -Math.PI / 2, 0]} scale={[200, 120, 1]} />
        <Lightformer form="ring" intensity={0.8} position={[0, 60, -220]} scale={80} />
        {/* A broad soft light behind the visitor: the front of the glass reflects it as a bright band, as a slide held
            under a window does. */}
        <Lightformer form="rect" intensity={1.6} position={[0, 70, 280]} rotation={[0, Math.PI, 0]} scale={[280, 36, 1]} />
      </Environment>
      {arrangement === "drawer" ? <CabinetDrawer n={items.length} title={title} hue={hue} /> : null}
      {arrangement === "box" ? <SlideBox n={items.length} title={title} hue={hue} /> : null}
      {arrangement === "folder" ? (
        <Folder n={items.length} page={Math.floor(selected / FOLDER_PLACES)} title={title} hue={hue} />
      ) : null}
      {items.map((item, i) => (
        <Slide key={item.id} item={item} index={i} placement={placements[i]} glass={glass} still={still}
          chosen={i === selected} accent={accent} onHover={setHover} onSelect={onSelect} onOpen={onOpen}
          register={register} arrangement={arrangement} shadowMap={shadowMap} />
      ))}
      <Spots groups={groups} items={items} arrangement={arrangement} onSpots={onSpots} />
    </>
  );
}

export default function GlassScene(props: GlassSceneProps) {
  const start = cameraFor(props.arrangement, props.items.length);
  return (
    <Canvas frameloop="demand" dpr={[1, 1.75]} camera={{ fov: start.fov, position: start.position, near: 1, far: 4000 }}
      gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
      data-glass-scene={props.arrangement} aria-hidden="true">
      <SceneContents {...props} />
    </Canvas>
  );
}
