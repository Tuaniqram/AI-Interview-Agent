const PERM_SIZE = 256
const GRAD3: [number, number, number][] = [
  [1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0],
  [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
  [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1],
  [1, 1, 0], [-1, 1, 0], [0, -1, 1], [0, -1, -1],
]

export class SimplexNoise {
  private perm: number[]

  constructor(seed = Math.random() * 65536) {
    this.perm = new Array(PERM_SIZE * 2)
    const p = new Array(PERM_SIZE)
    for (let i = 0; i < PERM_SIZE; i++) {
      p[i] = i
    }
    let n, q
    for (let i = PERM_SIZE - 1; i > 0; i--) {
      seed = (seed * 16807 + 0) % 2147483647
      n = (seed / 2147483647) * (i + 1) | 0
      q = p[n]
      p[n] = p[i]
      p[i] = q
    }
    for (let i = 0; i < PERM_SIZE * 2; i++) {
      this.perm[i] = p[i & 255]
    }
  }

  noise2D(x: number, y: number): number {
    const F2 = 0.5 * (Math.sqrt(3) - 1)
    const G2 = (3 - Math.sqrt(3)) / 6
    const s = (x + y) * F2
    const i = Math.floor(x + s)
    const j = Math.floor(y + s)
    const t = (i + j) * G2
    const X0 = i - t
    const Y0 = j - t
    const x0 = x - X0
    const y0 = y - Y0
    let i1, j1
    if (x0 > y0) {
      i1 = 1
      j1 = 0
    } else {
      i1 = 0
      j1 = 1
    }
    const x1 = x0 - i1 + G2
    const y1 = y0 - j1 + G2
    const x2 = x0 - 1 + 2 * G2
    const y2 = y0 - 1 + 2 * G2
    const ii = i & 255
    const jj = j & 255
    const gi0 = this.perm[ii + this.perm[jj]] % 12
    const gi1 = this.perm[ii + i1 + this.perm[jj + j1]] % 12
    const gi2 = this.perm[ii + 1 + this.perm[jj + 1]] % 12
    let n0 = 0, n1 = 0, n2 = 0
    let t0 = 0.5 - x0 * x0 - y0 * y0
    if (t0 >= 0) {
      t0 *= t0
      n0 = t0 * t0 * this.dot(GRAD3[gi0], x0, y0)
    }
    let t1 = 0.5 - x1 * x1 - y1 * y1
    if (t1 >= 0) {
      t1 *= t1
      n1 = t1 * t1 * this.dot(GRAD3[gi1], x1, y1)
    }
    let t2 = 0.5 - x2 * x2 - y2 * y2
    if (t2 >= 0) {
      t2 *= t2
      n2 = t2 * t2 * this.dot(GRAD3[gi2], x2, y2)
    }
    return 70 * (n0 + n1 + n2)
  }

  private dot(g: [number, number, number], x: number, y: number): number {
    return g[0] * x + g[1] * y
  }
}

let _instance: SimplexNoise | null = null

export function getNoise(): SimplexNoise {
  if (!_instance) {
    _instance = new SimplexNoise(Date.now())
  }
  return _instance
}
