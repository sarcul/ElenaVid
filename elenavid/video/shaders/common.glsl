// ---------------------------------------------------------------------------------------------
// common.glsl  -  shared library for every scene of ELENA
// ---------------------------------------------------------------------------------------------
in vec2 v_uv;
out vec4 fragColor;

uniform float uTime;      // absolute film time (s)
uniform float uLocal;     // time since the shot began (s)
uniform float uDur;       // shot duration (s)
uniform vec2  uRes;       // framebuffer size
uniform vec4  uP[24];     // per-shot parameters (meaning defined by each scene)
uniform float uVoice;     // Elena's voice envelope (0..~1)
uniform float uScore;     // orchestra envelope
uniform float uBeat;      // conductor beat phase (0..1 within beat)
uniform float uBeatIdx;   // beat index within bar
uniform float uBeatsBar;  // beats per bar
uniform vec3  uCam;       // framing of the 2D scenes: xy = frame centre (screen units), z = log2 zoom.
                          // All zero (the default, and always in the film) = the frame as composed.

// the size of one output pixel in screen units, at the current framing
#define PIXEL (exp2(-uCam.z) / uRes.y)

#define PI 3.14159265359
#define TAU 6.28318530718

float sat(float x) { return clamp(x, 0.0, 1.0); }
vec3 sat3(vec3 x) { return clamp(x, 0.0, 1.0); }

// aspect-correct coordinates: y in [-0.5, 0.5], x in [-0.889, 0.889]
vec2 screen() {
    vec2 p = v_uv - 0.5;
    p.x *= uRes.x / uRes.y;
    return uCam.xy + p * exp2(-uCam.z);
}

float hash11(float p) { p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash21(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33);
                       return fract((p3.x + p3.y) * p3.z); }
vec2 hash22(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * vec3(.1031, .1030, .0973));
                      p3 += dot(p3, p3.yzx + 33.33); return fract((p3.xx + p3.yz) * p3.zy); }

float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + vec2(1, 0)), u.x),
               mix(hash21(i + vec2(0, 1)), hash21(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
    float a = 0.5, s = 0.0;
    for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; }
    return s;
}
float vnoise3(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    vec3 u = f * f * (3.0 - 2.0 * f);
    float n = i.x + i.y * 57.0 + i.z * 113.0;
    float a = hash11(n), b = hash11(n + 1.0), c = hash11(n + 57.0), d = hash11(n + 58.0);
    float e = hash11(n + 113.0), g = hash11(n + 114.0), h = hash11(n + 170.0), k = hash11(n + 171.0);
    return mix(mix(mix(a, b, u.x), mix(c, d, u.x), u.y), mix(mix(e, g, u.x), mix(h, k, u.x), u.y), u.z);
}
float fbm3(vec3 p) {
    float a = 0.5, s = 0.0;
    for (int i = 0; i < 4; i++) { s += a * vnoise3(p); p = p * 2.02 + 3.1; a *= 0.5; }
    return s;
}

// ------------------------------------------------------------------ 2D SDFs
float sdCircle(vec2 p, float r) { return length(p) - r; }
float sdBox(vec2 p, vec2 b) { vec2 d = abs(p) - b; return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0); }
float sdRBox(vec2 p, vec2 b, float r) { return sdBox(p, b - r) - r; }
float sdSeg(vec2 p, vec2 a, vec2 b) { vec2 pa = p - a, ba = b - a;
    float h = sat(dot(pa, ba) / dot(ba, ba)); return length(pa - ba * h); }
float sdCapsule(vec2 p, vec2 a, vec2 b, float r) { return sdSeg(p, a, b) - r; }
float sdEllipse(vec2 p, vec2 r) { float k = length(p / r); return (k - 1.0) * min(r.x, r.y); }
float sdTrap(vec2 p, float r1, float r2, float he) {   // isosceles trapezoid (r1 bottom, r2 top)
    vec2 k1 = vec2(r2, he), k2 = vec2(r2 - r1, 2.0 * he);
    p.x = abs(p.x);
    vec2 ca = vec2(p.x - min(p.x, (p.y < 0.0) ? r1 : r2), abs(p.y) - he);
    vec2 cb = p - k1 + k2 * sat(dot(k1 - p, k2) / dot(k2, k2));
    float s = (cb.x < 0.0 && ca.y < 0.0) ? -1.0 : 1.0;
    return s * sqrt(min(dot(ca, ca), dot(cb, cb)));
}
float sdArc(vec2 p, vec2 c, float r, float a0, float a1, float w) {
    vec2 d = p - c;
    float a = atan(d.y, d.x);
    float am = clamp(a, min(a0, a1), max(a0, a1));
    vec2 q = c + r * vec2(cos(am), sin(am));
    return length(p - q) - w;
}
float smin(float a, float b, float k) { float h = sat(0.5 + 0.5 * (b - a) / k); return mix(b, a, h) - k * h * (1.0 - h); }
float aa(float d, float px) { return 1.0 - smoothstep(-px, px, d); }      // anti-aliased fill
float glow(float d, float w) { return exp(-max(d, 0.0) / w); }

mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }

// ------------------------------------------------------------------ characters
// A standing figure. pose: x = left arm angle, y = right arm angle (radians from hanging),
// z = skirt flare (0 = trousers), w = lean. Height ~ 1 unit at scale 1, feet at y = 0.
// tapered capsule: radius ra at a, rb at b
float sdTaper(vec2 p, vec2 a, vec2 b, float ra, float rb) {
    vec2 pa = p - a, ba = b - a;
    float h = sat(dot(pa, ba) / dot(ba, ba));
    return length(pa - ba * h) - mix(ra, rb, h);
}
float sdEll2(vec2 p, vec2 r) { float k0 = length(p / r); float k1 = length(p / (r * r)); return k0 * (k0 - 1.0) / max(k1, 1e-6); }

// A standing figure, feet at the origin, height 1. Same joints and proportions as before, drawn
// as one soft silhouette: oval head, sloping shoulders, a waist, tapered limbs, hands and feet.
float sdFigure(vec2 p, vec4 pose, float hair) {
    p.x -= p.y * pose.w;
    bool fem = pose.z > 0.0;
    float d = sdEll2(p - vec2(0.0, 0.902), vec2(0.055, 0.067));                       // head
    if (hair > 0.5) d = smin(d, sdEll2(p - vec2(0.006, 0.938), vec2(0.059, 0.046)), 0.02);  // up-do
    if (hair > 1.5) d = smin(d, sdCircle(p - vec2(-0.03, 0.968), 0.034), 0.014);       // chignon
    d = smin(d, sdTaper(p, vec2(0.0, 0.86), vec2(0.0, 0.785), fem ? 0.021 : 0.027, fem ? 0.026 : 0.033), 0.022);
    float shoulders = sdTaper(p, vec2(-0.095, 0.758), vec2(0.095, 0.758), 0.031, 0.031);
    float chest = sdEll2(p - vec2(0.0, 0.69), fem ? vec2(0.09, 0.098) : vec2(0.104, 0.11));
    float waist = sdEll2(p - vec2(0.0, 0.575), fem ? vec2(0.06, 0.07) : vec2(0.083, 0.08));
    d = smin(d, smin(smin(shoulders, chest, 0.05), waist, 0.05), 0.03);
    if (fem) {
        float top = 0.565, bot = 0.012;
        float s = sat((top - p.y) / (top - bot));
        float halfw = mix(0.064, 0.13 + 0.17 * pose.z, pow(s, 1.3));
        float u = p.x / (halfw + 1e-3);
        float sk = max(abs(p.x) - halfw, max(p.y - top, bot + 0.014 * u * u - p.y));
        d = smin(d, sk * 0.9, 0.03);
    } else {
        d = smin(d, sdEll2(p - vec2(0.0, 0.5), vec2(0.08, 0.075)), 0.05);
        float legs = min(sdTaper(p, vec2(-0.045, 0.48), vec2(-0.05, 0.04), 0.037, 0.026),
                         sdTaper(p, vec2(0.045, 0.48), vec2(0.05, 0.04), 0.037, 0.026));
        float feet = min(sdEll2(p - vec2(-0.06, 0.017), vec2(0.036, 0.017)), sdEll2(p - vec2(0.06, 0.017), vec2(0.036, 0.017)));
        d = smin(d, min(legs, feet), 0.02);
    }
    vec2 sl = vec2(-0.112, 0.762), sr = vec2(0.112, 0.762);
    vec2 el = sl + 0.17 * vec2(-sin(pose.x), -cos(pose.x));
    vec2 er = sr + 0.17 * vec2(sin(pose.y), -cos(pose.y));
    vec2 hl = el + 0.16 * vec2(-sin(pose.x * 1.25), -cos(pose.x * 1.25));
    vec2 hr = er + 0.16 * vec2(sin(pose.y * 1.25), -cos(pose.y * 1.25));
    float arms = min(sdTaper(p, sl, el, 0.027, 0.019), sdTaper(p, el, hl, 0.019, 0.0135));
    arms = min(arms, min(sdTaper(p, sr, er, 0.027, 0.019), sdTaper(p, er, hr, 0.019, 0.0135)));
    arms = min(arms, min(sdEll2(p - hl - normalize(hl - el + 1e-5) * 0.017, vec2(0.016, 0.019)),
                         sdEll2(p - hr - normalize(hr - er + 1e-5) * 0.017, vec2(0.016, 0.019))));
    return smin(d, arms, 0.012);
}

// Render a figure at position pos (feet), height h, with body colour and rim colour.
// Returns premultiplied colour + alpha.
vec4 figure(vec2 p, vec2 pos, float h, vec4 pose, float hair, vec3 body, vec3 rim, vec2 lightDir) {
    vec2 q = (p - pos) / h;
    float d = sdFigure(q, pose, hair) * h;
    float px = 1.5 * PIXEL;
    float a = aa(d, px);
    // rim light: brighter on the side facing the light, inside a thin band
    vec2 e = vec2(0.002, 0.0);
    vec2 gr = vec2(sdFigure((p + e.xy - pos) / h, pose, hair) - sdFigure((p - e.xy - pos) / h, pose, hair),
                   sdFigure((p + e.yx - pos) / h, pose, hair) - sdFigure((p - e.yx - pos) / h, pose, hair));
    vec2 n = normalize(gr + 1e-6);
    float facing = sat(dot(n, normalize(lightDir)) * 0.8 + 0.2);
    float band = exp(-max(-d, 0.0) / (0.006 * h + 0.002)) * a;
    vec3 c = body * (0.82 + 0.1 * sat(q.y) + 0.08 * fbm(q * 7.0)) + rim * band * facing * 1.6;   // cloth, not wood grain
    float halo = glow(d, 0.01 * h) * (1.0 - a) * 0.35 * facing;
    return vec4(c * a + rim * halo, max(a, halo * 0.5));
}

vec3 over(vec3 base, vec4 top) { return base * (1.0 - top.a) + top.rgb; }

// ------------------------------------------------------------------ atmosphere helpers
// soft beam from 'src' in direction 'dir' with angular width 'w'
float beam(vec2 p, vec2 src, vec2 dir, float w, float len) {
    vec2 d = p - src;
    float along = dot(d, normalize(dir));
    if (along < 0.0) return 0.0;
    float across = abs(dot(d, vec2(-normalize(dir).y, normalize(dir).x)));
    float spread = w * along + 0.004;
    return exp(-pow(across / spread, 2.0)) * exp(-along / len);
}

// drifting dust motes in screen space
float dust(vec2 p, float t, float density, float size) {
    float acc = 0.0;
    for (int l = 0; l < 3; l++) {
        float sc = 6.0 + 7.0 * float(l);
        vec2 q = p * sc + vec2(t * 0.05 * (1.0 + float(l)), t * 0.02);
        vec2 id = floor(q), f = fract(q) - 0.5;
        vec2 o = hash22(id + float(l) * 13.0) - 0.5;
        float on = step(1.0 - density, hash21(id + 7.0 + float(l)));
        float tw = 0.5 + 0.5 * sin(t * (1.0 + 2.0 * hash21(id)) + hash21(id + 3.0) * 6.28);
        acc += on * tw * smoothstep(size, 0.0, length(f - o * 0.7)) / (1.0 + float(l));
    }
    return acc;
}

// film grade helpers
vec3 tempTint(vec3 c, float temp) {           // temp > 0 warmer, < 0 colder
    return c * vec3(1.0 + 0.10 * temp, 1.0 + 0.02 * temp, 1.0 - 0.12 * temp);
}
float lum(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

// candle flame at position with height h; returns emission
vec3 candle(vec2 p, vec2 pos, float h, float t, float seed) {
    vec2 q = (p - pos) / h;
    float fl = 0.06 * sin(t * 9.0 + seed * 7.0) + 0.04 * sin(t * 13.7 + seed);
    q.x += fl * q.y;
    float d = length(vec2(q.x * 2.2, (q.y - 0.5) * 1.0)) - 0.5;
    float core = exp(-max(d, 0.0) * 20.0) * step(0.0, q.y + 0.05);
    float halo = exp(-length(p - pos - vec2(0.0, 0.5 * h)) / (2.2 * h));
    return vec3(1.0, 0.62, 0.25) * core * 2.4 + vec3(1.0, 0.55, 0.2) * halo * 0.35;
}
