export type ThemeId = "midnight" | "charcoal" | "neon" | "daylight" | "bloom";

const TKEYS = [
  "background","panel","elevated","border","border-muted",
  "text-primary","text-secondary","text-muted",
  "info","success","warning","review","danger","audit",
] as const;

interface ThemeDef {
  id: ThemeId;
  name: string;
  vars: Record<string, string>;
  swatch: string[];
}

function mk(id: ThemeId, name: string, c: string[], stage: string, glow: string, dot: string): ThemeDef {
  const vars: Record<string, string> = {};
  TKEYS.forEach((k, i) => { vars[`--color-${k}`] = c[i] ?? ""; });
  vars["--stage"] = stage;
  vars["--stage-glow"] = glow;
  vars["--tex-dot"] = dot;
  return { id, name, vars, swatch: [c[1] ?? "", c[8] ?? "", c[9] ?? "", c[10] ?? "", c[12] ?? ""] };
}

export const THEMES: ThemeDef[] = [
  mk("midnight", "Midnight",
    ["#0B0F12","#101820","#1A2530","#2A3A4A","#1E2A38","#E6EDF3","#B8C5D6","#6B7280","#42D9FF","#5EE08B","#F5B84B","#FF9F43","#FF5C5C","#A78BFA"],
    "#05080A", "rgba(66,217,255,0.05)", "rgba(66,217,255,0.05)"),
  mk("charcoal", "Charcoal",
    ["#171717","#1F1F1F","#2B2B2B","#3C3C3C","#2D2D2D","#ECECEC","#B9B9B9","#7B7B7B","#45C7B6","#6FCB8C","#E6B45A","#EA9A57","#E86A6A","#AC9EE2"],
    "#0D0D0D", "rgba(69,199,182,0.05)", "rgba(255,255,255,0.03)"),
  mk("neon", "Neon",
    ["#07090E","#0E101A","#161A28","#2C3350","#191E2E","#EAF1FF","#A9B4D2","#5A6486","#34E3FF","#45FFA3","#FFC24B","#FF9F50","#FF5C72","#B98CFF"],
    "#030409", "rgba(52,227,255,0.12)", "rgba(52,227,255,0.06)"),
  mk("daylight", "Daylight",
    ["#F7F8FA","#FFFFFF","#EEF1F5","#D9DFE7","#E9EDF2","#293445","#525E73","#9098A6","#1B7FC4","#1E9E5A","#B07D14","#C56A1E","#D24545","#7857C8"],
    "#E7EAEF", "rgba(27,127,196,0.06)", "rgba(41,52,69,0.035)"),
  mk("bloom", "Bloom",
    ["#F7F3FC","#FFFFFF","#F2ECF9","#E4DCF0","#EDE6F6","#3E3659","#655B82","#9C93B0","#5B62D0","#4FB487","#C99334","#D77E4F","#D55F76","#9173CE"],
    "#ECE5F4", "rgba(91,98,208,0.07)", "rgba(91,98,208,0.045)"),
];

export function applyTheme(id: ThemeId, texture: boolean): void {
  const t = THEMES.find(x => x.id === id) ?? THEMES[0]!;
  const r = document.documentElement;
  r.classList.add("no-transition");
  for (const k in t.vars) r.style.setProperty(k, t.vars[k] ?? "");
  const root = document.getElementById("root");
  if (root) root.setAttribute("data-texture", texture ? "on" : "off");
  void r.offsetWidth;
  requestAnimationFrame(() => r.classList.remove("no-transition"));
  try {
    localStorage.setItem("ps-theme", id);
    localStorage.setItem("ps-texture", texture ? "1" : "0");
  } catch (_) {}
}

export function readStoredTheme(): ThemeId {
  try { return (localStorage.getItem("ps-theme") as ThemeId) || "midnight"; } catch (_) { return "midnight"; }
}

export function readStoredTexture(): boolean {
  try { return localStorage.getItem("ps-texture") === "1"; } catch (_) { return false; }
}
