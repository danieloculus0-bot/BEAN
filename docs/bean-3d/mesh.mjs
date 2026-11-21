// BEAN 3D Studio: deterministic, offline parametric mesh generation.
// Units are millimeters. No third-party dependencies or ML claims.
const TAU = Math.PI * 2;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

function meshBuilder() {
  const vertices = [];
  const triangles = [];
  return {
    vertices, triangles,
    vertex(x, y, z) { vertices.push(x, y, z); return vertices.length / 3 - 1; },
    face(a, b, c) { if (a !== b && b !== c && c !== a) triangles.push(a, b, c); },
    quad(a, b, c, d) { this.face(a, b, c); this.face(a, c, d); },
    finish(kind) { return {kind, vertices: new Float32Array(vertices), triangles: new Uint32Array(triangles)}; }
  };
}

// Single-piece, solid coaster with an embossed continuous over-under rope pattern.
export function wovenCoaster({diameter = 96, thickness = 2.4, pitch = 7, relief = 0.65, radialSteps = 72, angularSteps = 192} = {}) {
  diameter = clamp(+diameter || 96, 35, 250);
  thickness = clamp(+thickness || 2.4, 1.2, 15);
  pitch = clamp(+pitch || 7, 3, 30);
  relief = clamp(+relief || 0.65, 0, 2);
  radialSteps = Math.round(clamp(+radialSteps || 72, 12, 140));
  angularSteps = Math.round(clamp(+angularSteps || 192, 48, 384));
  const radius = diameter / 2;
  const b = meshBuilder();
  const h = (x, y, r) => {
    const a = Math.pow(0.5 + 0.5 * Math.cos(TAU * x / pitch), 4);
    const c = Math.pow(0.5 + 0.5 * Math.cos(TAU * y / pitch), 4);
    const cross = Math.sin(Math.PI * x / pitch) * Math.sin(Math.PI * y / pitch);
    const weave = clamp(0.17 + 0.43 * (a + c) + 0.26 * (a - c) * cross, 0, 1.2);
    const edgeFade = clamp((radius - r) / Math.max(1.5, pitch * 0.45), 0, 1);
    return thickness + relief * weave * edgeFade;
  };
  const centers = [b.vertex(0, 0, h(0, 0, 0)), b.vertex(0, 0, 0)];
  const top = [], bottom = [];
  for (let j = 1; j <= radialSteps; j++) {
    const r = radius * j / radialSteps, upper = [], lower = [];
    for (let k = 0; k < angularSteps; k++) {
      const angle = TAU * k / angularSteps, x = r * Math.cos(angle), y = r * Math.sin(angle);
      upper.push(b.vertex(x, y, h(x, y, r)));
      lower.push(b.vertex(x, y, 0));
    }
    top.push(upper); bottom.push(lower);
  }
  for (let k = 0; k < angularSteps; k++) {
    const n = (k + 1) % angularSteps;
    b.face(centers[0], top[0][k], top[0][n]);
    b.face(centers[1], bottom[0][n], bottom[0][k]);
  }
  for (let j = 0; j < radialSteps - 1; j++) {
    for (let k = 0; k < angularSteps; k++) {
      const n = (k + 1) % angularSteps;
      b.quad(top[j][k], top[j + 1][k], top[j + 1][n], top[j][n]);
      b.quad(bottom[j][n], bottom[j + 1][n], bottom[j + 1][k], bottom[j][k]);
    }
  }
  for (let k = 0; k < angularSteps; k++) {
    const n = (k + 1) % angularSteps;
    const j = radialSteps - 1;
    b.quad(top[j][k], bottom[j][k], bottom[j][n], top[j][n]);
  }
  return b.finish("woven-coaster");
}

// Single closed ring. Useful for holder designs, gaskets and trim prototypes.
export function ring({diameter = 100, thickness = 5, wall = 5, angularSteps = 192} = {}) {
  const radius = clamp(+diameter || 100, 20, 250) / 2;
  const height = clamp(+thickness || 5, 1, 100);
  wall = clamp(+wall || 5, 1, radius - 1);
  const count = Math.round(clamp(+angularSteps || 192, 32, 384));
  const b = meshBuilder(), layers = [];
  for (const [r, z] of [[radius, 0], [radius, height], [radius - wall, height], [radius - wall, 0]]) {
    const layer = [];
    for (let k = 0; k < count; k++) {
      const a = TAU * k / count;
      layer.push(b.vertex(r * Math.cos(a), r * Math.sin(a), z));
    }
    layers.push(layer);
  }
  for (let k = 0; k < count; k++) {
    const n = (k + 1) % count;
    for (let j = 0; j < 4; j++) {
      const next = (j + 1) % 4;
      b.quad(layers[j][k], layers[j][n], layers[next][n], layers[next][k]);
    }
  }
  return b.finish("ring");
}

export function fromPrompt(prompt = "", options = {}) {
  const p = String(prompt).toLowerCase();
  // Explicitly a small constrained parametric parser, NOT free-form AI text-to-3D.
  if (/\bring\b|\bwasher\b|\bholder\b|\bhoop\b/.test(p)) return ring(options);
  return wovenCoaster(options);
}

export function bounds(mesh) {
  const v = mesh.vertices, min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < v.length; i += 3) {
    for (let k = 0; k < 3; k++) {
      min[k] = Math.min(min[k], v[i + k]);
      max[k] = Math.max(max[k], v[i + k]);
    }
  }
  return {min, max, size: max.map((x, k) => x - min[k])};
}

export function binarySTL(mesh) {
  const v = mesh.vertices, f = mesh.triangles;
  if (!f.length || f.length % 3) throw new Error("Mesh must contain triangles");
  const buffer = new ArrayBuffer(84 + (f.length / 3) * 50);
  const view = new DataView(buffer);
  const tag = new TextEncoder().encode("BEAN 3D Studio | millimeters");
  for (let i = 0; i < tag.length; i++) view.setUint8(i, tag[i]);
  view.setUint32(80, f.length / 3, true);
  let o = 84;
  for (let i = 0; i < f.length; i += 3) {
    const A = f[i] * 3, B = f[i + 1] * 3, C = f[i + 2] * 3;
    const u = [v[B] - v[A], v[B + 1] - v[A + 1], v[B + 2] - v[A + 2]];
    const w = [v[C] - v[A], v[C + 1] - v[A + 1], v[C + 2] - v[A + 2]];
    const n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    const d = Math.hypot(...n) || 1;
    for (let k = 0; k < 3; k++) { view.setFloat32(o, n[k] / d, true); o += 4; }
    for (const a of [A, B, C]) for (let k = 0; k < 3; k++) { view.setFloat32(o, v[a + k], true); o += 4; }
    view.setUint16(o, 0, true); o += 2;
  }
  return new Blob([buffer], {type: "application/sla"});
}

export function obj(mesh) {
  const lines = ["# BEAN 3D Studio OBJ; units millimeters", "o " + mesh.kind];
  for (let i = 0; i < mesh.vertices.length; i += 3)
    lines.push("v " + Array.from(mesh.vertices.slice(i, i + 3)).join(" "));
  for (let i = 0; i < mesh.triangles.length; i += 3)
    lines.push("f " + [mesh.triangles[i] + 1, mesh.triangles[i + 1] + 1, mesh.triangles[i + 2] + 1].join(" "));
  return new Blob([lines.join("\n") + "\n"], {type: "text/plain"});
}

export function decodeSTL(buffer) {
  const view = new DataView(buffer);
  if (view.byteLength < 84) throw new Error("Not a binary STL");
  const count = view.getUint32(80, true);
  if (!count || 84 + count * 50 !== view.byteLength || count > 500000) throw new Error("Invalid STL triangle count");
  const vertices = new Float32Array(count * 9), triangles = new Uint32Array(count * 3);
  let o = 84;
  for (let t = 0; t < count; t++) {
    o += 12; // normal
    for (let j = 0; j < 9; j++) { const n = view.getFloat32(o, true); if (!Number.isFinite(n)) throw new Error("Nonfinite STL coordinate"); vertices[t * 9 + j] = n; o += 4; }
    o += 2; // attribute bytes
    for (let j = 0; j < 3; j++) triangles[t * 3 + j] = t * 3 + j;
  }
  return {kind: "reconstructed", vertices, triangles};
}
