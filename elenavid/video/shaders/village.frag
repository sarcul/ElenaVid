#version 430
// THE VILLAGE - Act I, scene 1: a piazza in the Veneto, summer 1948, and the white road out of it.
// Teatro di luce: paper-cut flats at several depths, lit contre-jour by the sun through warm, dusty
// haze. Every flat fades into the air with distance and carries a rim of light along the edges that
// face the sun; flats, crowd and lovers throw long soft shadows across the ground.
//   mode 0  market day: the chorus, bobbing to the beat among striped stalls
//   mode 1  the farewell: the same square, the villagers drifting away one by one
//   mode 2  the white road: Elena alone between poplars and stubble fields; Marco a speck in the sun
#include common

// uP[0].x mode                      uP[0].y camera pan (screen units at the figures' depth)
// uP[0].z crowd 0..1                uP[0].w warmth (0 afternoon gold .. 1 sunset orange)
// uP[1] Elena (feet x, feet y, height, alpha)     uP[2] Marco (feet x, feet y, height, alpha)
// uP[3].x letters 0..1 (envelopes rising and dissolving)     uP[3].y swifts 0..1
// Figure positions are given at pan 0; figures stand on the ground and pan with it.

// ------------------------------------------------------------------ scene state (set in main)
float MODE, PAN, CROWD, WARM, T, PX;
float YH, CAMH, DENS, FOGP, X0;    // horizon, camera height, haze density and falloff, lens shift
vec2 SUN, SH;                       // the sun on screen; its horizontal direction in the world (x, z)
float TANE, SINE;                   // tangent and sine of the sun's elevation
vec3 SUNC, AIRC, SKYA, BNC;         // sunlight, air, skylight, warm bounce from the sunlit ground
vec4 POSE_E, POSE_M;                // the lovers' poses

// ------------------------------------------------------------------ projection and air
// The ground plane: depth z appears at screen height YH - CAMH / z; world x = (x - X0) * z + PAN.
// A flat at depth z is drawn in its own coordinates, shifted by PAN / z (the parallax).
float groundZ(float y) { return CAMH / max(YH - y, 1e-4); }
float yBase(float z) { return YH - CAMH / z; }
vec2 flatP(vec2 p, float z) { return vec2(p.x + PAN / z, p.y); }
float fogF(float z) { return 1.0 - exp(-pow(z * DENS, FOGP)); }  // near flats stay clear, far ones glow
float ign(vec2 f) { return fract(52.9829189 * fract(dot(f, vec2(0.06711056, 0.00583715)))); }
vec2 toSun(vec2 p) { return normalize(SUN - p + vec2(1e-5)); }

// the light scattered towards us by the dusty air along a line of sight. In front of a flat the
// sun's forward glow is gentler than in open sky, so whatever stands against the sun stays a
// silhouette with a luminous edge rather than dissolving into the glare.
float AIRSUN = 1.0;
vec3 air(vec2 p) {
    float r = length((p - SUN) * vec2(0.7, 1.0));
    float up = sat((p.y - YH) * 1.5);
    return AIRC * (1.0 - 0.35 * up) + SUNC * AIRSUN * (0.09 * exp(-r * 2.0) + 0.2 * exp(-r * 7.0));
}

// the grain of each sheet of paper
float paper(vec2 q, float seed) {
    return 0.92 + 0.1 * vnoise(q * 160.0 + seed) + 0.06 * vnoise(q * 13.0 + seed * 1.7);
}

// a rim of sunlight along the edges of a flat that face the sun (dOff: distance a little sunward)
float rimBand(float d, float dOff, float w) { return aa(d, PX) * smoothstep(-0.2 * w, 0.8 * w, dOff); }

// lay a flat over the picture: colour c, depth z (haze), rim strength
float HAZEN = 1.0;   // drifting thickness of the haze at this pixel (set in main)
void lay(inout vec3 col, inout float zf, vec2 p, float d, vec3 c, float z, float rim) {
    float a = aa(d, PX);
    if (a <= 0.0) return;
    float f = sat(fogF(z) * HAZEN);
    AIRSUN = 0.45;
    vec3 lc = mix(c, air(p), f) + SUNC * rim * (1.0 - 0.55 * f);
    AIRSUN = 1.0;
    col = mix(col, lc, a);
    if (a > 0.5) zf = min(zf, z);
}

// a camera-facing wall in the shade: cool sky from above, warm bounce from the sunlit ground
vec3 shadeLight(float hWorld) { return SKYA + BNC * exp(-hWorld * 1.3); }

// ------------------------------------------------------------------ sky, swifts, letters
vec3 skyCol(vec2 p) {
    float h = p.y - YH;
    // a gradient that passes through bright cream rather than grey on its way from gold to blue
    vec3 hor = mix(vec3(1.10, 0.80, 0.45), vec3(1.20, 0.50, 0.20), WARM);
    vec3 mid = mix(vec3(1.00, 0.86, 0.60), vec3(1.00, 0.56, 0.34), WARM);
    vec3 upr = mix(vec3(0.58, 0.68, 0.78), vec3(0.62, 0.40, 0.46), WARM);
    vec3 zen = mix(vec3(0.24, 0.40, 0.64), vec3(0.22, 0.17, 0.34), WARM);
    vec3 c = mix(hor, mid, smoothstep(0.0, 0.16, h));
    c = mix(c, upr, smoothstep(0.12, 0.42, h));
    c = mix(c, zen, smoothstep(0.38, 0.85, h));
    // drifting streaks of cirrus, lit warm from beneath near the sun
    vec2 cq = vec2((p.x + PAN * 0.03) * 1.5 + T * 0.004, h * 8.0);
    float n = fbm(cq + vec2(0.0, 0.35 * sin(cq.x * 0.8 + 1.3)));
    float cl = smoothstep(0.5, 0.78, n) * smoothstep(0.03, 0.14, h) * (1.0 - smoothstep(0.38, 0.6, h));
    float rs = length((p - SUN) * vec2(0.55, 1.0));
    vec3 cc = mix(c * 1.12 + vec3(0.05, 0.04, 0.03), SUNC * 0.75, exp(-rs * 2.2));
    c = mix(c, cc, cl * 0.55);
    // the sun: wide glow, corona and disc
    float r = length(p - SUN);
    c += SUNC * (0.22 * exp(-r * 3.2) + 0.55 * exp(-r * 13.0) + 1.4 * exp(-r * 55.0));
    c += SUNC * 1.8 * smoothstep(0.022, 0.018, r);
    return c;
}

vec2 swiftPos(float fi, float t) {
    float sp = 0.55 + 0.35 * hash11(fi * 1.31);
    float ph = t * sp + fi * 2.17;
    vec2 cen = (MODE < 1.5) ? vec2(-0.36, 0.31) : vec2(-0.05, 0.24);
    cen += vec2(0.25 * sin(t * 0.045 + fi * 0.37), 0.05 * sin(t * 0.06 + fi * 1.1));
    float rx = 0.22 + 0.2 * hash11(fi * 4.7), ry = 0.05 + 0.06 * hash11(fi * 8.3);
    return cen + vec2(rx * sin(ph), ry * sin(ph * 2.0 + fi) + 0.03 * sin(ph * 3.1));
}
float sdSwift(vec2 r, float flap) {   // a swift seen from below: sickle wings, forked tail
    float span = 0.72 + 0.28 * flap;
    vec2 w = vec2(r.x, abs(r.y));
    float d = sdEllipse(r - vec2(0.06, 0.0), vec2(0.30, 0.075));
    vec2 a = vec2(0.04, 0.0), b = vec2(-0.10, 0.40 * span), c = vec2(-0.52, 0.92 * span);
    d = min(d, sdSeg(w, a, b) - 0.085);
    float tw = sat((w.y - b.y) / max(c.y - b.y, 1e-3));
    d = min(d, sdSeg(w, b, c) - mix(0.07, 0.012, tw));
    d = min(d, sdSeg(w, vec2(-0.18, 0.0), vec2(-0.40, 0.07)) - 0.022);
    return d;
}
float swifts(vec2 p, float dens) {
    float acc = 0.0;
    if (dens <= 0.0) return 0.0;
    for (int i = 0; i < 16; i++) {
        float fi = float(i);
        float vis = smoothstep(0.0, 0.08, dens - hash11(fi * 3.71) * 0.95);
        if (vis <= 0.0) continue;
        vec2 pos = swiftPos(fi, T);
        float sc = 0.0075 + 0.008 * hash11(fi * 5.13);
        vec2 r = p - pos;
        if (dot(r, r) > sc * sc * 1.8) continue;
        vec2 v = swiftPos(fi, T + 0.02) - pos;
        vec2 lr = rot(atan(v.y, v.x)) * r / sc;
        float flap = sin(T * 24.0 + fi * 3.0) * smoothstep(-0.2, 0.4, sin(T * 1.1 + fi * 2.3));
        acc = max(acc, aa(sdSwift(lr, flap) * sc, PX * 0.8) * vis);
    }
    return acc;
}

// the letters that never came: envelopes rising from her hands, tumbling, burning away into light
vec4 letters(vec2 p, float amt, vec2 hands, float h) {
    vec4 acc = vec4(0.0);
    if (amt <= 0.0) return acc;
    for (int i = 0; i < 9; i++) {
        float fi = float(i);
        float vis = smoothstep(0.0, 0.12, amt - hash11(fi * 2.31) * 0.85);
        if (vis <= 0.0) continue;
        float life = 7.5 + 3.0 * hash11(fi * 4.13);
        float cyc = T / life + hash11(fi * 6.1);
        float u = fract(cyc), k = floor(cyc);
        vec2 org = hands + vec2(h * 0.5 * (hash11(fi + k * 7.3) - 0.5), 0.0);
        float rise = 0.75 * (0.8 + 0.4 * hash11(fi * 9.7 + k));
        float drift = (hash11(fi * 1.7 + k) - 0.35) * 0.5;
        vec2 pos = org + vec2(drift * u + 0.05 * sin(u * 5.0 + fi), rise * u * (0.6 + 0.4 * u));
        float tum = T * (0.5 + 0.6 * hash11(fi * 3.3)) + fi * 1.9;
        float sc = 0.03 * (0.8 + 0.4 * hash11(fi * 8.1)) * (1.0 - 0.4 * u) * smoothstep(0.0, 0.08, u);
        if (sc <= 1e-4) continue;
        vec2 r = rot(0.5 * sin(tum)) * (p - pos);
        float fl = cos(tum * 0.8);                 // turning over: the width foreshortens
        r.x /= max(abs(fl), 0.12);
        r /= sc;
        if (abs(r.x) > 1.4 || abs(r.y) > 1.0) continue;
        float env = sdBox(r, vec2(1.0, 0.64)) - 0.03;
        float crease = min(sdSeg(r, vec2(-1.0, 0.64), vec2(0.0, -0.06)), sdSeg(r, vec2(1.0, 0.64), vec2(0.0, -0.06)));
        float th = smoothstep(0.42, 0.95, u);       // the dissolve eats in from the edges
        float n = 0.6 * vnoise(r * 2.2 + fi * 7.7) + 0.4 * vnoise(r * 6.0 + fi * 3.1);
        n = 0.8 * n + 0.2 * (1.0 - length(r) / 1.2);
        float keep = smoothstep(th - 0.02, th + 0.02, n);
        float edge = exp(-abs(n - th) * 45.0) * step(0.01, th);
        float shape = aa(env * sc, PX);
        float a = shape * keep * vis;
        vec3 pc = vec3(0.93, 0.89, 0.80) * (SKYA * 1.5 + SUNC * (0.42 + 0.3 * abs(fl)));   // sun through the paper
        pc *= 1.0 - 0.3 * aa(crease * sc - 0.0006, PX);
        acc.rgb = acc.rgb * (1.0 - a) + pc * a + SUNC * edge * shape * vis * 2.2;
        acc.a = max(acc.a, a);
    }
    return acc;
}

// ------------------------------------------------------------------ villagers
// design x, depth, height scale, kind (0 man in a cap, 1 woman, 2 woman with a basket on her head,
// 3 child, 4 old man with a stick); far to near, split at the stalls
const vec4 VIL[16] = vec4[16](
    vec4(0.18, 9.0, 0.95, 1.0), vec4(-0.17, 8.5, 1.0, 0.0), vec4(0.03, 6.8, 1.05, 0.0),
    vec4(-0.05, 6.4, 0.97, 1.0), vec4(-0.66, 4.2, 1.0, 2.0), vec4(0.70, 4.0, 1.03, 4.0),
    vec4(0.45, 3.4, 0.97, 1.0), vec4(-0.33, 3.3, 0.96, 1.0), vec4(-0.46, 3.2, 1.02, 0.0),
    vec4(0.31, 3.2, 1.0, 0.0),
    vec4(0.57, 2.2, 1.02, 0.0), vec4(-0.47, 2.1, 0.6, 3.0), vec4(-0.62, 1.9, 0.98, 1.0),
    vec4(0.41, 1.85, 0.97, 2.0), vec4(-0.36, 1.75, 1.04, 0.0), vec4(0.67, 1.62, 0.93, 1.0));

float sdVillager(vec2 q, vec4 pose, float kind) {
    float hair = (kind > 0.5 && kind < 2.5) ? 1.0 : 0.0;
    float d = sdFigure(q, pose, hair);
    vec2 a = vec2(q.x - q.y * pose.w, q.y);          // the figure's own lean
    if (kind < 0.5 || kind > 3.5) {                   // a flat cap with a peak
        d = min(d, sdEllipse(a - vec2(0.0, 0.952), vec2(0.07, 0.03)));
        d = min(d, sdBox(a - vec2(0.03, 0.937), vec2(0.06, 0.007)));
    }
    if (kind > 0.5 && kind < 1.5) d = min(d, sdCircle(a - vec2(-0.032, 0.958), 0.03));   // a bun
    if (kind > 1.5 && kind < 2.5) d = min(d, sdTrap(a - vec2(0.0, 1.005), 0.085, 0.125, 0.04));
    if (kind > 3.5) d = min(d, sdSeg(a, vec2(0.22, 0.45), vec2(0.30, 0.0)) - 0.012);   // a stick
    return d;
}

// where villager i stands, how tall, how posed, and whether he or she is still in the square
void villagerState(int i, out vec2 wpos, out float h, out vec4 pose, out float kind, out float alpha) {
    vec4 v = VIL[i];
    float fi = float(i), z = v.y;
    kind = v.w;
    float th = 0.12 + 0.8 * hash11(fi * 7.31 + 2.0);       // the crowd level at which they leave
    float gone = 1.0 - smoothstep(th - 0.1, th + 0.1, CROWD);
    alpha = 1.0 - smoothstep(0.6, 1.0, gone);              // they walk away first, fading only at the end
    float dir = (v.x > 0.0) ? 1.0 : -1.0;
    wpos = vec2(v.x * z + dir * 2.4 * gone * gone, z);     // world x (walking off to the wings), depth
    h = 0.5 * v.z;                                          // world height
    float ph = hash11(fi * 3.7) * TAU;
    float sway = sin(T * 0.8 + ph);
    pose = vec4(0.12 + 0.05 * sway, 0.12 - 0.05 * sway, (kind > 0.5 && kind < 2.5) ? 0.3 : 0.0, 0.015 * sway);
    if (kind > 3.5) pose.y = 0.3;
    if (MODE < 0.5) {                                       // market day: arms up on the downbeat
        float lift = (uBeatIdx < 0.5) ? sin(PI * uBeat) : 0.0;
        if (hash11(fi * 5.3) > 0.55 && kind < 3.5) pose.y += 0.9 * lift;
        if (hash11(fi * 6.9) > 0.7) pose.x += 0.5 * lift;
    }
    if (gone > 0.0) {                                       // walking away: the arms swing
        float wk = sin(T * 4.0 + ph);
        pose.x += 0.3 * wk * gone;
        pose.y -= 0.3 * wk * gone;
    }
    if (kind > 1.5 && kind < 2.5) pose.y = 2.5;             // steadying the basket
    if (kind > 2.5 && kind < 3.5) pose.z = 0.15;
}

float bob(int i, float h) {
    if (MODE > 0.5) return 0.0;
    float b = sin(PI * uBeat);
    return h * 0.022 * b * b * (0.6 + 0.4 * hash11(float(i) * 1.9));
}

vec4 drawVillager(vec2 p, int i) {
    vec2 wp; float h; vec4 pose; float kind, alpha;
    villagerState(i, wp, h, pose, kind, alpha);
    if (alpha <= 0.002) return vec4(0.0);
    float z = wp.y;
    float hs = h / z;
    vec2 pos = vec2(X0 + (wp.x - PAN) / z, yBase(z) + bob(i, hs));
    vec2 q = (p - pos) / hs;
    if (abs(q.x) > 0.55 || q.y < -0.05 || q.y > 1.12) return vec4(0.0);
    float d = sdVillager(q, pose, kind) * hs;
    if (d > 0.012 * hs + PX * 3.0) return vec4(0.0);
    float a = aa(d, PX);
    vec2 e = vec2(0.004, 0.0);
    vec2 gr = vec2(sdVillager(q + e.xy, pose, kind) - sdVillager(q - e.xy, pose, kind),
                   sdVillager(q + e.yx, pose, kind) - sdVillager(q - e.yx, pose, kind));
    vec2 n = normalize(gr + 1e-6);
    vec2 L = normalize(SUN - pos - vec2(0.0, 0.6 * hs));
    float facing = pow(sat(dot(n, L)), 2.0);
    float band = exp(-max(-d, 0.0) / (0.0035 * hs + 0.0005)) * a;
    vec3 rimc = SUNC * 0.42;
    vec3 body = vec3(0.16, 0.11, 0.07) * (0.85 + 0.15 * vnoise(q * 14.0 + kind * 3.0));
    vec3 c = body + rimc * band * facing * 1.5;
    float halo = glow(d, 0.006 * hs) * (1.0 - a) * 0.22 * facing;
    vec4 f = vec4(c * a + rimc * halo, max(a, halo * 0.5));
    f.rgb = mix(f.rgb, air(p) * f.a, fogF(z));
    return f * alpha;
}

// sunlight reaching the ground point g = (world x, depth) past a billboard of world height h
// standing at world (fx, fz): project the sun ray onto the billboard's plane
vec2 sunHit(vec2 g, float fz, out float t) {
    t = (fz - g.y) / SH.y;
    return vec2(g.x + t * SH.x, t * TANE);
}

float villagerShadow(vec2 g, int i) {
    vec2 wp; float h; vec4 pose; float kind, alpha;
    villagerState(i, wp, h, pose, kind, alpha);
    if (alpha <= 0.002 || g.y >= wp.y) return 1.0;
    float t;
    vec2 s = sunHit(g, wp.y, t);
    vec2 q = vec2(s.x - wp.x, s.y) / h;
    if (abs(q.x) > 0.55 || q.y > 1.1) return 1.0;
    float soft = (0.006 + 0.025 * t) / h;
    return mix(1.0, smoothstep(-soft, soft, sdVillager(q, pose, kind)), alpha);
}

// ------------------------------------------------------------------ the lovers
float figDepth(vec2 feet) { return (feet.y < YH - 0.002) ? groundZ(feet.y) : 400.0; }

vec4 lover(vec2 p, vec4 P, vec4 pose, float hair, vec3 body, vec3 rim) {
    if (P.w <= 0.0 || P.z <= 0.0) return vec4(0.0);
    float z = figDepth(P.xy);
    vec2 pos = vec2(P.x - PAN / z, P.y);
    vec2 q = (p - pos) / P.z;
    if (q.x < -0.7 || q.x > 0.7 || q.y < -0.1 || q.y > 1.2) return vec4(0.0);
    vec2 L = normalize(SUN - (pos + vec2(0.0, 0.6 * P.z)));
    vec4 f = figure(p, pos, P.z, pose, hair, body, rim, L);
    f.rgb = mix(f.rgb, air(p) * f.a, fogF(min(z, 30.0)) * 0.4);   // even far off they stay dark against the glare
    return f * P.w;
}

float loverShadow(vec2 g, vec4 P, vec4 pose, float hair) {
    if (P.w <= 0.01 || P.z <= 0.0) return 1.0;
    float z = figDepth(P.xy);
    if (g.y >= z) return 1.0;
    float H = P.z * z;
    float t;
    vec2 s = sunHit(g, z, t);
    vec2 q = vec2(s.x - (P.x - X0) * z, s.y) / H;
    if (abs(q.x) > 0.6 || q.y > 1.1) return 1.0;
    float soft = (0.004 + 0.02 * t) / H;
    return mix(1.0, smoothstep(-soft, soft, sdFigure(q, pose, hair)), P.w);
}

void drawLovers(inout vec3 col, vec2 p) {
    // the letters rise from her hands in front of her, so they emerge from behind her shoulders
    if (uP[3].x > 0.0) {
        float ez = figDepth(uP[1].xy);
        vec2 hands = vec2(uP[1].x - PAN / ez, uP[1].y + uP[1].z * 0.62);
        vec4 lt = letters(p, uP[3].x, hands, uP[1].z);
        col = col * (1.0 - lt.a) + lt.rgb;
    }
    vec4 e = lover(p, uP[1], POSE_E, 1.0, vec3(0.45, 0.03, 0.06), vec3(1.0, 0.45, 0.35));
    vec4 m = lover(p, uP[2], POSE_M, 0.0, vec3(0.06, 0.22, 0.18), vec3(0.5, 1.0, 0.8));
    if (figDepth(uP[2].xy) > figDepth(uP[1].xy)) { col = over(col, m); col = over(col, e); }
    else { col = over(col, e); col = over(col, m); }
}

// ================================================================== THE SQUARE (modes 0 and 1)
const float ZFAR = 26.0;   // roofs, a dome and cypresses beyond the square
const float ZB = 11.0;     // the church, its campanile and the houses across the square
const float ZM = 4.5;      // the arcaded houses at either side
const float ZS = 2.6;      // market stalls
const float ZBT = 3.5;     // bunting strung across the square
const float ZFG = 0.78;    // the portico arch framing the shot

float sdArch(vec2 r, vec2 c, float hw, float hs) {   // round-headed opening: base centre, half width, springline
    r -= c;
    return min(sdBox(r - vec2(0.0, hs * 0.5), vec2(hw, hs * 0.5)), length(r - vec2(0.0, hs)) - hw);
}
float sdChimney(vec2 r, vec2 b, float h, float w) {   // a Venetian chimney: shaft and inverted bell
    r -= b;
    float d = sdBox(r - vec2(0.0, h * 0.5), vec2(w, h * 0.5));
    d = min(d, sdTrap(r - vec2(0.0, h + 1.2 * w), w, 2.5 * w, 1.2 * w));
    d = min(d, sdBox(r - vec2(0.0, h + 2.6 * w), vec2(2.8 * w, 0.35 * w)));
    d = min(d, sdTrap(r - vec2(0.0, h + 3.3 * w), 1.7 * w, 0.4 * w, 0.4 * w));
    return d;
}
float sdHouse(vec2 r, vec4 h, float ov) {   // x0, x1, eave height, roof rise; a low hipped roof
    float cx = 0.5 * (h.x + h.y), hw = 0.5 * (h.y - h.x);
    float d = sdBox(r - vec2(cx, h.z * 0.5), vec2(hw, h.z * 0.5));
    return min(d, sdTrap(r - vec2(cx, h.z + h.w * 0.5), hw + ov, hw * 0.45, h.w * 0.5));
}
float sdCypress(vec2 r, float h, float w) {
    float t = r.y / h;
    float prof = w * sqrt(sat(t * 6.0)) * pow(sat(1.0 - t), 0.8) * 1.2;
    return max(abs(r.x) - prof, max(-r.y, r.y - h)) * 0.8;
}
vec3 plaster(float i) {
    if (i < 0.5) return vec3(0.74, 0.50, 0.28);   // ochre
    if (i < 1.5) return vec3(0.76, 0.47, 0.38);   // faded rose
    if (i < 2.5) return vec3(0.80, 0.70, 0.54);   // cream
    if (i < 3.5) return vec3(0.72, 0.40, 0.22);   // burnt orange
    return vec3(0.82, 0.70, 0.42);                 // straw yellow
}
vec3 roofTiles(vec2 r, float s) {   // terracotta coppi in courses
    return vec3(0.52, 0.25, 0.14) * (0.8 + 0.2 * smoothstep(0.2, 0.8, fract(r.y / (0.004 * s))));
}

// ---- the far layer: a ragged roofline, a dome, a slim tower, cypresses
float farSil(vec2 q) {
    vec2 r = vec2(q.x, q.y - yBase(ZFAR));
    if (r.y > 0.3) return r.y - 0.285;
    float k = floor(r.x * 10.0), f = fract(r.x * 10.0);
    float hr = 0.05 + 0.04 * hash11(k * 1.7 + 4.0);
    float d = (r.y - hr - 0.01 * (1.0 - abs(f * 2.0 - 1.0))) * 0.9;
    d = min(d, sdBox(r - vec2(0.13, 0.085), vec2(0.028, 0.085)));
    d = min(d, max(length(r - vec2(0.13, 0.17)) - 0.03, 0.17 - r.y));
    d = min(d, sdBox(r - vec2(0.13, 0.208), vec2(0.005, 0.012)));
    d = min(d, sdBox(r - vec2(0.42, 0.12), vec2(0.011, 0.12)));
    d = min(d, sdTrap(r - vec2(0.42, 0.262), 0.012, 0.001, 0.022));
    d = min(d, sdCypress(r - vec2(-0.68, 0.0), 0.19, 0.014));
    d = min(d, sdCypress(r - vec2(-0.645, 0.0), 0.15, 0.012));
    d = min(d, sdCypress(r - vec2(0.27, 0.0), 0.2, 0.015));
    d = min(d, sdCypress(r - vec2(0.30, 0.0), 0.16, 0.012));
    d = min(d, sdCypress(r - vec2(0.74, 0.0), 0.22, 0.016));
    return d;
}

// ---- the back flat: campanile, church and a row of houses
const float CX = -0.45, CHX = -0.25;
const vec4 BH[6] = vec4[6](vec4(-0.80, -0.49, 0.165, 0.03), vec4(-0.10, 0.04, 0.20, 0.03),
                           vec4(0.04, 0.16, 0.16, 0.028), vec4(0.16, 0.30, 0.215, 0.032),
                           vec4(0.30, 0.42, 0.175, 0.03), vec4(0.42, 0.64, 0.19, 0.03));
// plaster, columns, upper floors, chimney position along the roof (< 0: none)
const vec4 BH2[6] = vec4[6](vec4(0.0, 3.0, 2.0, 0.72), vec4(1.0, 2.0, 2.0, 0.28),
                            vec4(2.0, 2.0, 1.0, -1.0), vec4(3.0, 3.0, 2.0, 0.7),
                            vec4(4.0, 2.0, 2.0, 0.45), vec4(2.0, 3.0, 2.0, 0.3));

float campanile(vec2 r) {
    r.x -= CX;
    if (abs(r.x) > 0.06 || r.y > 0.56) return max(abs(r.x) - 0.045, r.y - 0.545);
    float hw = 0.036;
    float d = sdBox(r - vec2(0.0, 0.152), vec2(hw, 0.152));                  // brick shaft
    d = min(d, sdBox(r - vec2(0.0, 0.306), vec2(hw + 0.006, 0.0045)));       // cornice
    d = min(d, sdBox(r - vec2(0.0, 0.343), vec2(hw + 0.002, 0.034)));        // belfry
    d = min(d, sdBox(r - vec2(0.0, 0.381), vec2(hw + 0.007, 0.0045)));       // upper cornice
    d = min(d, sdBox(r - vec2(0.0, 0.399), vec2(hw - 0.005, 0.014)));        // drum
    d = min(d, sdTrap(r - vec2(0.0, 0.468), 0.027, 0.0015, 0.055));          // conical spire
    vec2 pp = vec2(abs(r.x) - (hw - 0.002), r.y - 0.399);
    d = min(d, sdTrap(pp, 0.0045, 0.0004, 0.0135));                          // corner pinnacles
    d = min(d, sdBox(r - vec2(0.0, 0.53), vec2(0.0008, 0.008)));             // cross
    d = min(d, sdBox(r - vec2(0.0, 0.532), vec2(0.0042, 0.0008)));
    // the belfry: two round-headed openings, a bell hanging in each from its headstock
    vec2 o = vec2(abs(r.x) - 0.0155, r.y);
    float op = sdArch(o, vec2(0.0, 0.314), 0.0105, 0.043);
    vec2 bl = o - vec2(0.0, 0.343);
    float bell = min(sdTrap(bl, 0.0078, 0.0042, 0.0075), sdCircle(bl - vec2(0.0, 0.0075), 0.0042));
    bell = min(bell, sdBox(bl - vec2(0.0, -0.0075), vec2(0.0088, 0.0011)));
    bell = min(bell, sdBox(bl - vec2(0.0, 0.0125), vec2(0.0105, 0.0009)));
    return max(d, -max(op, -bell));
}

float church(vec2 r) {
    r.x -= CHX;
    if (abs(r.x) > 0.17 || r.y > 0.25) return max(abs(r.x) - 0.162, r.y - 0.245);
    float d = sdBox(r - vec2(0.0, 0.075), vec2(0.15, 0.075));
    d = min(d, sdBox(r - vec2(0.0, 0.154), vec2(0.158, 0.0045)));           // entablature
    d = min(d, sdTrap(r - vec2(0.0, 0.1935), 0.16, 0.003, 0.035));          // pediment
    d = min(d, sdBox(r - vec2(0.0, 0.236), vec2(0.0009, 0.009)));            // cross
    d = min(d, sdBox(r - vec2(0.0, 0.239), vec2(0.0048, 0.0009)));
    vec2 f = vec2(abs(r.x) - 0.152, r.y - 0.164);
    d = min(d, min(sdCircle(f - vec2(0.0, 0.006), 0.0045), sdBox(f, vec2(0.003, 0.004))));   // finials
    return d;
}

float backSil(vec2 q) {
    vec2 r = vec2(q.x, q.y - yBase(ZB));
    if (r.y > 0.56) return r.y - 0.545;          // bounds return a true lower bound, never ~0
    float d = min(campanile(r), church(r));
    if (r.y > 0.3) return d;
    for (int i = 0; i < 6; i++) {
        vec4 h = BH[i];
        if (r.x < h.x - 0.03 || r.x > h.y + 0.03) continue;
        float hd = sdHouse(r, h, 0.006);
        float cp = BH2[i].w;
        if (cp > 0.0) hd = min(hd, sdChimney(r, vec2(mix(h.x, h.y, cp), h.z), h.w + 0.012, 0.0032));
        d = min(d, hd);
    }
    return d;
}

// windows with green shutters on a camera-facing facade; r from the house's lower left corner
vec3 facade(vec2 r, float w, float he, float nc, float nf, float gf, float seed, vec3 wall, float s) {
    vec3 c = wall * (0.93 + 0.14 * vnoise(r * 70.0 / s + seed));            // weathered plaster
    c *= 1.0 - 0.22 * aa(abs(r.y - gf) - 0.0011 * s, PX);                   // string course
    c *= 1.0 - 0.45 * smoothstep(0.012 * s, 0.0, he - r.y);                 // shade under the eaves
    vec3 shut = mix(vec3(0.10, 0.22, 0.14), vec3(0.22, 0.25, 0.13), hash11(seed * 3.3));
    float fh = (he - gf) / nf, cw = w / nc;
    if (r.y > gf && r.y < he) {
        vec2 cell = vec2(floor(r.x / cw), floor((r.y - gf) / fh));
        vec2 lc = vec2(r.x - (cell.x + 0.5) * cw, r.y - gf - (cell.y + 0.45) * fh);
        vec2 ws = vec2(min(cw * 0.16, fh * 0.2), fh * 0.28);
        float win = sdBox(lc, ws);
        float st = hash21(cell + seed * 7.1);
        if (st < 0.38) {                                                    // shutters closed
            float slat = 0.78 + 0.22 * sat(sin(lc.y / ws.y * 26.0) * 2.0);
            c = mix(c, shut * slat, aa(win, PX));
        } else {                                                            // open, folded back
            c = mix(c, vec3(0.025, 0.02, 0.018), aa(win, PX));
            float leaf = sdBox(vec2(abs(lc.x) - ws.x * 1.5, lc.y), vec2(ws.x * 0.5, ws.y));
            if (st > 0.86) leaf = max(leaf, lc.x);                          // one leaf only
            c = mix(c, shut * 0.85, aa(leaf, PX));
        }
        c = mix(c, wall * 1.2, aa(sdBox(lc + vec2(0.0, ws.y + 0.0012 * s), vec2(ws.x * 1.25, 0.0011 * s)), PX));
    }
    return c;
}

vec3 groundFloor(vec2 r, float w, float gf, float nc, bool arcade, vec3 c) {
    if (r.y >= gf) return c;
    float cw = w / nc;
    float lx = r.x - (floor(r.x / cw) + 0.5) * cw;
    if (arcade) {
        float ar = sdArch(vec2(lx, r.y), vec2(0.0), cw * 0.36, gf * 0.5);
        vec3 inside = mix(vec3(0.04, 0.03, 0.022), vec3(0.16, 0.10, 0.05), exp(-r.y / (gf * 0.22)));
        c = mix(c, inside, aa(ar, PX));
    } else {
        float door = sdBox(vec2(lx, r.y - gf * 0.37), vec2(cw * 0.15, gf * 0.37));
        c = mix(c, vec3(0.04, 0.03, 0.025), aa(door, PX));
        c *= 1.0 - 0.15 * aa(sdBox(vec2(lx, r.y - gf * 0.4), vec2(cw * 0.22, gf * 0.42)) , PX) * (1.0 - aa(door, PX));
    }
    return c;
}

vec3 backColour(vec2 q) {
    vec2 r = vec2(q.x, q.y - yBase(ZB));
    vec3 L = shadeLight(r.y * ZB);
    vec2 c = vec2(r.x - CX, r.y);
    if (abs(c.x) < 0.046) {                                                 // the campanile
        vec3 brick = vec3(0.52, 0.27, 0.17), stone = vec3(0.80, 0.74, 0.62);
        vec3 a = brick * (1.0 + 0.12 * step(0.028, abs(c.x)));             // corner pilasters
        if (c.y > 0.3 && c.y < 0.412) a = stone * 0.92;
        if (c.y > 0.41) a = brick * 1.05;
        a = mix(a, stone, aa(abs(c.y - 0.2) - 0.002, PX) * step(c.y, 0.3)); // a stone band
        float slit = sdBox(vec2(c.x, mod(c.y, 0.07) - 0.035), vec2(0.0028, 0.011));
        a = mix(a, vec3(0.03), aa(slit, PX) * step(c.y, 0.19) * step(0.03, c.y));
        // the clock, keeping film time
        vec2 cc = c - vec2(0.0, 0.245);
        float cd = length(cc) - 0.0125;
        a = mix(a, stone * 1.1, aa(cd, PX));
        a = mix(a, vec3(0.06), aa(abs(cd + 0.0012) - 0.0006, PX));
        float mins = 20.0 + uTime / 60.0;
        float am = TAU * mins / 60.0, ah = TAU * (5.0 + mins / 60.0) / 12.0;
        float hands = min(sdSeg(cc, vec2(0.0), 0.0095 * vec2(sin(am), cos(am))) - 0.0006,
                          sdSeg(cc, vec2(0.0), 0.0062 * vec2(sin(ah), cos(ah))) - 0.0008);
        a = mix(a, vec3(0.05), aa(hands, PX) * aa(cd, PX));
        return a * L;
    }
    c = vec2(r.x - CHX, r.y);
    if (abs(c.x) < 0.165 && c.y < 0.25) {                                   // the church
        vec3 a = vec3(0.80, 0.74, 0.62);
        float pil = aa(abs(abs(c.x) - 0.07) - 0.006, PX) + aa(abs(abs(c.x) - 0.142) - 0.007, PX);
        a *= 1.0 + 0.1 * pil * step(c.y, 0.15);
        a *= 1.0 + 0.12 * aa(abs(c.y - 0.154) - 0.0045, PX);
        a *= 1.0 - 0.12 * aa(sdTrap(c - vec2(0.0, 0.191), 0.135, 0.006, 0.024), PX);   // tympanum
        a *= 1.0 + 0.1 * step(c.y, 0.008);                                              // steps
        a = mix(a, vec3(0.035, 0.025, 0.02), aa(sdArch(c, vec2(0.0), 0.02, 0.046), PX));  // portal
        float oc = length(c - vec2(0.0, 0.103)) - 0.016;                                // oculus
        a = mix(a, vec3(0.05, 0.04, 0.035), aa(oc, PX));
        a = mix(a, vec3(0.5, 0.45, 0.38), aa(abs(oc + 0.006) - 0.0012, PX));
        a = mix(a, vec3(0.05), aa(sdArch(vec2(abs(c.x) - 0.105, c.y), vec2(0.0, 0.045), 0.009, 0.03), PX) * 0.8);
        return a * L;
    }
    for (int i = 0; i < 6; i++) {
        vec4 h = BH[i];
        if (r.x < h.x - 0.007 || r.x > h.y + 0.007) continue;
        vec4 h2 = BH2[i];
        if (r.y > h.z) {
            vec3 a = roofTiles(r, 1.0);
            float cp = h2.w;
            if (cp > 0.0 && abs(r.x - mix(h.x, h.y, cp)) < 0.01) a = plaster(h2.x) * 0.9;
            return a * L;
        }
        vec3 wall = plaster(h2.x);
        vec2 f = vec2(r.x - h.x, r.y);
        float w = h.y - h.x, gf = h.z * 0.3;
        vec3 a = facade(f, w, h.z, h2.y, h2.z, gf, float(i) * 3.17, wall, 1.0);
        a = groundFloor(f, w, gf, h2.y, (i == 1 || i == 3), a);
        return a * L;
    }
    return vec3(0.3) * L;
}

// ---- the arcaded houses at either side
float midSil(vec2 q) {
    vec2 r = vec2(q.x, q.y - yBase(ZM));
    if (abs(r.x) < 0.5) return 0.538 - abs(r.x);
    if (r.y > 0.5) return r.y - 0.48;
    float d = sdHouse(r, vec4(0.56, 1.4, 0.40, 0.03), 0.022);
    d = min(d, sdChimney(r, vec2(0.86, 0.40), 0.05, 0.008));
    d = min(d, sdHouse(r, vec4(-1.4, -0.62, 0.36, 0.03), 0.022));
    return d;
}

vec3 midColour(vec2 q) {
    vec2 r = vec2(q.x, q.y - yBase(ZM));
    vec3 L = shadeLight(r.y * ZM);
    if (r.x > 0.0) {                                       // the arcaded house on the right
        if (r.y > 0.40) return (abs(r.x - 0.86) < 0.025 ? plaster(0.0) * 0.85 : roofTiles(r, 2.4)) * L;
        vec2 f = vec2(r.x - 0.56, r.y);
        vec3 wall = vec3(0.78, 0.55, 0.34);
        vec3 c = wall * (0.92 + 0.16 * vnoise(f * 38.0));
        float pitch = 0.17;
        float k = floor(f.x / pitch);
        float lx = f.x - (k + 0.5) * pitch;
        // the portico: deep shade, a warm glow where the sun reaches the paving inside
        float arch = sdArch(vec2(lx, f.y), vec2(0.0), 0.066, 0.10);
        vec3 inside = mix(vec3(0.03, 0.022, 0.018), vec3(0.2, 0.12, 0.06), exp(-f.y / 0.025));
        inside += vec3(0.25, 0.15, 0.07) * exp(-pow((lx + 0.03) / 0.02, 2.0) - pow((f.y - 0.05) / 0.03, 2.0)) * step(0.5, hash11(k + 3.0));
        c *= 1.0 - 0.18 * aa(abs(abs(lx) - 0.076) - 0.003, PX) * step(f.y, 0.155);   // pillar edges
        c = mix(c, inside, aa(arch, PX));
        c *= 1.0 - 0.25 * aa(abs(f.y - 0.155) - 0.003, PX);                         // string course
        // piano nobile: tall windows, a balcony with an iron railing in the middle bay
        vec2 w1 = vec2(lx, f.y - 0.218);
        float win1 = sdBox(w1, vec2(0.021, 0.043));
        float st = hash11(k * 2.7 + 1.0);
        vec3 shut = vec3(0.10, 0.22, 0.14);
        if (st < 0.4) c = mix(c, shut * (0.78 + 0.22 * sat(sin(w1.y * 300.0) * 2.0)), aa(win1, PX));
        else {
            c = mix(c, vec3(0.025, 0.02, 0.018), aa(win1, PX));
            c = mix(c, shut * 0.85, aa(sdBox(vec2(abs(w1.x) - 0.032, w1.y), vec2(0.0105, 0.043)), PX));
        }
        c = mix(c, wall * 1.2, aa(sdBox(w1 - vec2(0.0, 0.052), vec2(0.03, 0.004)), PX));   // pediment cap
        if (k > 0.5 && k < 1.5) {
            vec2 b = vec2(lx, f.y - 0.178);
            float rail = max(sdBox(b, vec2(0.04, 0.02)), -sdBox(b, vec2(0.037, 0.017)));
            rail = min(rail, max(abs(mod(b.x, 0.008) - 0.004) - 0.0008, abs(b.y) - 0.02));
            rail = max(rail, abs(b.x) - 0.04);
            c = mix(c, vec3(0.03), aa(rail, PX));
            c = mix(c, wall * 1.1, aa(sdBox(vec2(lx, f.y - 0.157), vec2(0.044, 0.003)), PX));
        }
        // second floor: smaller windows; a line of washing between the first two bays
        vec2 w2 = vec2(lx, f.y - 0.33);
        float st2 = hash11(k * 5.1 + 2.0);
        float win2 = sdBox(w2, vec2(0.018, 0.03));
        if (st2 < 0.45) c = mix(c, shut * (0.78 + 0.22 * sat(sin(w2.y * 300.0) * 2.0)), aa(win2, PX));
        else {
            c = mix(c, vec3(0.025, 0.02, 0.018), aa(win2, PX));
            c = mix(c, shut * 0.85, aa(sdBox(vec2(abs(w2.x) - 0.027, w2.y), vec2(0.009, 0.03)), PX));
        }
        if (f.x > 0.1 && f.x < 0.23) {
            float u = (f.x - 0.1) / 0.13;
            float ly = 0.3 - 0.014 * 4.0 * u * (1.0 - u);
            c = mix(c, vec3(0.05), aa(abs(f.y - ly) - 0.0008, PX));
            float pc = floor(u * 4.0);
            float pu = fract(u * 4.0);
            float sw = 0.004 * sin(T * 1.6 + pc * 1.3);
            float cloth = sdBox(vec2((pu - 0.5) * 0.0325 + sw * (ly - f.y) * 20.0, f.y - (ly - 0.018 - 0.006 * hash11(pc))),
                                vec2(0.012, 0.016 + 0.006 * hash11(pc)));
            vec3 cc = (hash11(pc + 7.0) > 0.4) ? vec3(0.85, 0.83, 0.78) : vec3(0.25, 0.35, 0.55);
            c = mix(c, cc, aa(cloth, PX) * step(0.5, hash11(pc * 3.0 + 1.0) + 0.3));
        }
        c *= 1.0 - 0.45 * smoothstep(0.03, 0.0, 0.40 - f.y);   // eave shadow
        c = mix(c, wall * 1.15, aa(abs(f.y - 0.388) - 0.004, PX));   // cornice
        return c * L;
    }
    // the left house
    if (r.y > 0.36) return roofTiles(r, 2.4) * L;
    vec2 f = vec2(r.x + 1.4, r.y);
    vec3 wall = vec3(0.74, 0.46, 0.36);
    vec3 a = facade(f, 0.78, 0.36, 5.0, 2.0, 0.13, 9.1, wall, 2.4);
    a = groundFloor(f, 0.78, 0.13, 5.0, false, a);
    return a * L;
}

// ---- the market stalls
const vec3 STALL[2] = vec3[2](vec3(-0.56, -0.25, 0.0), vec3(0.23, 0.54, 1.0));
float stallSil(vec2 q) {
    vec2 r = vec2(q.x, q.y - yBase(ZS));
    if (r.y > 0.31) return r.y - 0.291;
    float d = 1e3;
    for (int i = 0; i < 2; i++) {
        vec3 s = STALL[i];
        float cx = 0.5 * (s.x + s.y), hw = 0.5 * (s.y - s.x);
        float lx = r.x - cx;
        if (abs(lx) > hw + 0.05) continue;
        d = min(d, sdBox(vec2(abs(lx) - (hw - 0.006), r.y - 0.12), vec2(0.0035, 0.12)));   // poles
        float aw = sdTrap(vec2(lx, r.y - 0.255), hw + 0.016, hw + 0.002, 0.035);          // awning
        float sc = 0.018;
        float ux = lx + hw + 0.016;
        float k = floor(ux / sc);
        float wave = 0.003 * sin(T * 2.2 - k * 0.9 + float(i) * 2.0);
        vec2 sq = vec2(ux - (k + 0.5) * sc, r.y - (0.221 + wave));
        float scal = max(max(length(sq) - sc * 0.5, sq.y), abs(lx) - (hw + 0.016));
        d = min(d, min(aw, scal));
        d = min(d, sdBox(vec2(lx, r.y - 0.062), vec2(hw - 0.018, 0.034)));                  // table and cloth
        d = min(d, sdBox(vec2(abs(lx) - (hw - 0.03), r.y - 0.014), vec2(0.003, 0.014)));    // legs
        float bump = abs(sin(lx * ((i == 0) ? 95.0 : 160.0) + 1.0));
        float top = 0.095 + ((i == 0) ? 0.019 : 0.012) * sqrt(bump) + 0.008 * smoothstep(hw, 0.0, abs(lx));
        d = min(d, max(r.y - top, max(0.09 - r.y, abs(lx) - (hw - 0.026))));                 // produce
        // garlic plaits and a hanging scale on the front beam
        vec2 g = vec2(lx - ((i == 0) ? -0.08 : 0.07), r.y - 0.19);
        float garl = (i == 0) ? sdCapsule(g, vec2(0.0, -0.04), vec2(0.0, 0.03), 0.006)
                              : min(sdSeg(g, vec2(0.0, -0.025), vec2(0.0, 0.03)) - 0.0008, sdEllipse(g - vec2(0.0, -0.028), vec2(0.016, 0.004)));
        d = min(d, garl);
    }
    return d;
}

vec3 stallColour(vec2 q) {
    vec2 r = vec2(q.x, q.y - yBase(ZS));
    int i = (r.x < 0.0) ? 0 : 1;
    vec3 s = STALL[i];
    float cx = 0.5 * (s.x + s.y), hw = 0.5 * (s.y - s.x);
    float lx = r.x - cx;
    vec3 L = shadeLight(r.y * ZS);
    vec3 sa = (i == 0) ? vec3(0.80, 0.12, 0.08) : vec3(0.10, 0.45, 0.20);
    vec3 sb = vec3(0.96, 0.89, 0.72);
    if (r.y > 0.205) {      // the awning: the sun shines through the canvas
        float st = step(0.5, fract((lx + 0.011) / 0.044));
        vec3 cl = mix(sa, sb, st);
        float gl = 0.6 + 0.4 * smoothstep(0.29, 0.215, r.y);
        return cl * (L * 0.6 + SUNC * 0.3 * gl) * paper(q, 5.0);
    }
    if (abs(abs(lx) - (hw - 0.006)) < 0.0045 && r.y > 0.095) return vec3(0.10, 0.07, 0.05) * L;
    if (r.y > 0.095 && r.y < 0.205 && abs(lx) < hw - 0.026) {    // produce
        float b = sin(lx * ((i == 0) ? 95.0 : 160.0) + 1.0);
        vec3 pr = (i == 0) ? mix(vec3(0.12, 0.25, 0.08), vec3(0.2, 0.38, 0.12), step(0.0, b))
                           : mix(vec3(0.75, 0.3, 0.1), vec3(0.7, 0.12, 0.06), step(0.0, b));
        return pr * (L * 1.1 + SUNC * 0.12 * smoothstep(0.1, 0.13, r.y));
    }
    if (r.y > 0.095) return ((i == 0) ? vec3(0.85, 0.8, 0.65) : vec3(0.55, 0.45, 0.2)) * L;   // garlic, brass
    if (r.y > 0.027) {      // the table cloth, deep in the awning's shade
        vec3 cl = (i == 0) ? vec3(0.42, 0.36, 0.26) : vec3(0.30, 0.26, 0.2);
        cl = mix(cl, sa * 0.7, aa(abs(r.y - 0.034) - 0.004, PX));
        cl *= 0.85 + 0.15 * sin(lx * 300.0) * 0.5;
        return cl * L * 0.7;
    }
    return vec3(0.06, 0.045, 0.03) * L;
}

// ---- bunting strung across the square: tricolour pennants, glowing with the sun behind them
float buntY(float u) { return mix(0.295, 0.28, u) - 0.11 * 4.0 * u * (1.0 - u) + 0.004 * sin(T * 0.9 + u * 2.5); }
vec4 bunting(vec2 q, out float dist) {
    dist = 1e3;
    const float xa = -0.62, xb = 0.57;
    if (q.x < xa - 0.02 || q.x > xb + 0.02 || q.y < 0.1 || q.y > 0.32) return vec4(0.0);
    float u = sat((q.x - xa) / (xb - xa));
    float dl = abs(q.y - buntY(u)) - 0.0008;
    float sp = 0.036;
    float k = floor((q.x - xa) / sp);
    float xc = xa + (k + 0.5) * sp;
    float uc = (xc - xa) / (xb - xa);
    float slope = (buntY(uc + 0.01) - buntY(uc - 0.01)) / (0.02 * (xb - xa));
    vec2 r = rot(atan(slope) + 0.1 * sin(T * 1.9 + k * 1.7)) * (q - vec2(xc, buntY(uc)));
    float len = 0.02 * (0.85 + 0.15 * sin(T * 2.3 + k));          // swinging towards and away from us
    float tri = sdTrap(r - vec2(0.0, -len), 0.0008, 0.0125, len);
    dist = min(dl, tri);
    float m = mod(k, 3.0);
    vec3 tint = (m < 0.5) ? vec3(0.08, 0.5, 0.15) : ((m < 1.5) ? vec3(0.95, 0.92, 0.85) : vec3(0.85, 0.06, 0.06));
    vec3 c = tint * (SKYA * 0.6 + SUNC * 0.35);
    float a = aa(tri, PX);
    vec3 col = c * a;
    float al = aa(dl, PX * 0.7) * 0.8;
    col = col * (1.0 - al) + vec3(0.04) * al;
    return vec4(col, max(a, al));
}

// ---- the portico arch in the foreground
float archSil(vec2 q) {
    const float R = 0.98;
    vec2 c = vec2(-0.80 + R, 0.03);
    float open = (q.y < c.y) ? (-0.80 - q.x) : (length(q - c) - R);
    float d = -open;
    d = min(d, sdBox(q - vec2(-0.83, 0.03), vec2(0.04, 0.011)));   // impost moulding
    return d;
}

// sun on the paving of the square, with the shadows of everything standing on it
float squareShadow(vec2 g) {
    float lit = 1.0, t;
    if (g.y < ZB) {
        vec2 s = sunHit(g, ZB, t);
        float soft = (0.003 + 0.012 * t) / ZB;
        lit *= smoothstep(-soft, soft, backSil(vec2(X0 + s.x / ZB, YH + (s.y - CAMH) / ZB)));
    }
    if (g.y < ZM) {
        vec2 s = sunHit(g, ZM, t);
        float soft = (0.003 + 0.012 * t) / ZM;
        lit *= smoothstep(-soft, soft, midSil(vec2(X0 + s.x / ZM, YH + (s.y - CAMH) / ZM)));
    }
    if (g.y < ZBT) {
        vec2 s = sunHit(g, ZBT, t);
        float dd;
        vec4 b = bunting(vec2(X0 + s.x / ZBT, YH + (s.y - CAMH) / ZBT), dd);
        float soft = (0.003 + 0.01 * t) / ZBT;
        lit *= mix(1.0, 0.55, 1.0 - smoothstep(-soft, soft, dd));
    }
    if (g.y < ZS) {
        vec2 s = sunHit(g, ZS, t);
        float soft = (0.003 + 0.012 * t) / ZS;
        lit *= smoothstep(-soft, soft, stallSil(vec2(X0 + s.x / ZS, YH + (s.y - CAMH) / ZS)));
    }
    for (int i = 0; i < 16; i++) lit *= villagerShadow(g, i);
    lit *= loverShadow(g, uP[1], POSE_E, 1.0);
    lit *= loverShadow(g, uP[2], POSE_M, 0.0);
    return lit;
}

vec3 squareGround(vec2 p) {
    float Z = groundZ(p.y);
    float X = (p.x - X0) * Z + PAN;
    // worn trachyte slabs in running bond
    const vec2 SL = vec2(0.19, 0.125);
    vec2 sl = vec2(X, Z) / SL;
    sl.x += 0.5 * mod(floor(sl.y), 2.0);
    vec2 id = floor(sl), f = fract(sl);
    float fwz = Z * Z * PX / (CAMH * SL.y);
    float fwx = (Z * PX + abs(p.x - X0) * Z * Z * PX / CAMH) / SL.x;   // includes the slant of the joints
    float jx = min(f.x, 1.0 - f.x), jz = min(f.y, 1.0 - f.y);
    float joint = max(1.0 - smoothstep(0.015, 0.015 + fwx * 1.5, jx), 1.0 - smoothstep(0.022, 0.022 + fwz * 1.5, jz));
    joint *= exp(-max(fwx, fwz) * 4.0);
    float fade = exp(-fwz * 1.5);
    vec3 alb = mix(vec3(0.27, 0.23, 0.19), vec3(0.34, 0.28, 0.21), hash21(id + 0.5) * fade + 0.5 * (1.0 - fade));
    alb *= 0.85 + 0.3 * mix(0.5, vnoise(vec2(X, Z) * 9.0), fade);
    alb *= 0.9 + 0.2 * vnoise(vec2(X, Z) * 1.3);                       // dust and wear
    alb = mix(alb, alb * 0.55, joint * 0.8);
    float lit = squareShadow(vec2(X, Z));
    vec3 c = alb * (SUNC * SINE * 1.05 * lit + SKYA * 1.15);
    return mix(c, air(p), fogF(Z));
}

// open sky behind the set: the source of the shafts of light
float skyOpen(vec2 p) {
    if (p.y < YH) return 0.0;
    float d = backSil(flatP(p, ZB));
    d = min(d, midSil(flatP(p, ZM)));
    d = min(d, farSil(flatP(p, ZFAR)) + 0.002);
    return smoothstep(-0.003, 0.003, d);
}
// light scattered in the haze: march towards the sun gathering the open sky near it, so the
// silhouettes between cast dark streaks and the gaps between them pour out beams
float shafts(vec2 p) {
    vec2 dv = SUN - p;
    float L = length(dv);
    float len = min(L, 1.2) / max(L, 1e-4);
    float j = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
    float acc = 0.0;
    for (int i = 0; i < 24; i++) {
        float s = (float(i) + j) / 24.0;
        vec2 q = p + dv * s * len;
        acc += skyOpen(q) * exp(-length(q - SUN) * 3.2);
    }
    return acc / 24.0;
}

vec3 square(vec2 p) {
    float zf = 1e4;
    vec3 col = skyCol(p);
    vec2 ts = toSun(p);
    // roofs and cypresses beyond the square
    {
        vec2 q = flatP(p, ZFAR);
        float d = farSil(q);
        if (d < 0.01) {
            vec3 c = vec3(0.34, 0.26, 0.2) * shadeLight(1.0) * 2.2 * paper(q, 1.0);
            lay(col, zf, p, d, c, 13.0, rimBand(d, farSil(q + ts * 0.003), 0.003) * 0.6);   // haze capped
        }
    }
    // the paving
    if (p.y < YH + 0.002) {
        vec3 g = squareGround(p);
        float a = aa(p.y - YH, PX);
        col = mix(col, g, a);
        if (a > 0.5) zf = groundZ(p.y);
    }
    // the church, campanile and houses across the square
    {
        vec2 q = flatP(p, ZB);
        float d = backSil(q);
        if (d < 0.01) {
            vec3 c = backColour(q) * paper(q, 2.0);
            lay(col, zf, p, d, c, ZB, rimBand(d, backSil(q + ts * 0.0035), 0.0035) * 0.9);
        }
    }
    // swifts screaming round the tower
    float sw = swifts(p, uP[3].y);
    col = mix(col, mix(vec3(0.02, 0.016, 0.014), air(p), 0.25), sw);
    // the arcaded houses at the sides
    {
        vec2 q = flatP(p, ZM);
        float d = midSil(q);
        if (d < 0.01) {
            vec3 c = midColour(q) * paper(q, 3.0);
            lay(col, zf, p, d, c, ZM, rimBand(d, midSil(q + ts * 0.005), 0.005));
        }
    }
    // villagers beyond the stalls
    for (int i = 0; i < 10; i++) col = over(col, drawVillager(p, i));
    // the stalls
    {
        vec2 q = flatP(p, ZS);
        float d = stallSil(q);
        if (d < 0.01) {
            vec3 c = stallColour(q) * paper(q, 4.0);
            lay(col, zf, p, d, c, ZS, rimBand(d, stallSil(q + ts * 0.004), 0.004) * 0.8);
        }
    }
    // bunting
    {
        float dd;
        vec4 b = bunting(flatP(p, ZBT), dd);
        if (b.a > 0.0) col = col * (1.0 - b.a) + mix(b.rgb, air(p) * b.a, fogF(ZBT));
    }
    // villagers in front of the stalls
    for (int i = 10; i < 16; i++) col = over(col, drawVillager(p, i));
    // the lovers
    drawLovers(col, p);
    // shafts of sunlight through the dusty air, and the motes that drift in them
    float sh = shafts(p);
    float depthW = (zf > 1e3) ? 0.5 : 0.1 + 0.9 * fogF(zf);
    col += SUNC * sh * depthW * mix(0.36, 0.46, MODE);
    float mote = dust(p + vec2(PAN * 0.6, 0.0), T, 0.14, 0.09);
    col += SUNC * mote * (0.05 + 1.2 * sh) * 0.3 * (0.25 + depthW);
    // the portico arch in the foreground
    {
        vec2 q = flatP(p, ZFG);
        float d = archSil(q);
        if (d < 0.01) {
            vec3 c = vec3(0.09, 0.065, 0.05) * paper(q, 6.0);
            c *= 1.0 + 0.25 * aa(abs(q.x + 0.80 + 0.012) - 0.012, PX) * step(q.y, 0.03);   // the pillar's face
            c += BNC * 0.25 * exp(-(q.y + 0.5) * 3.0);
            float a = aa(d, PX);
            col = mix(col, c + SUNC * 0.4 * rimBand(d, archSil(q + ts * 0.006), 0.006), a);
        }
    }
    return col;
}

// ================================================================== THE WHITE ROAD (mode 2)
const float RX = 0.2, RW = 0.75;                          // road centre and half-width (world)
const float PROW = 1.75, PSP = 2.4, PZ0 = 1.6;            // the poplar row: x, spacing, first depth
const vec4 STACK[4] = vec4[4](vec4(-6.6, 12.5, 0.62, 1.3), vec4(-7.8, 19.0, 0.58, 1.2),
                              vec4(-3.4, 27.0, 0.6, 1.25), vec4(-12.0, 31.0, 0.55, 1.15));

float poplarR(float t) {   // a Lombardy poplar: bare trunk, a narrow column of crown, a soft spire
    float base = sqrt(sat((t - 0.045) / 0.22));
    float crown = base * (3.0 - 2.0 * base) * pow(sat(1.0 - t), 0.42);
    return 0.022 + 0.4 * crown;
}
// the crown's outline: small upswept tufts and looser clumps, irregular from tree to tree
float poplarEdge(float lx, float yw, float fn) {
    float tuft = fract(yw * 3.4 + 2.0 * abs(lx) + hash11(fn * 5.7) + 0.3 * vnoise(vec2(yw * 2.0, fn)));
    return 0.9 + 0.07 * smoothstep(0.0, 0.85, tuft) + 0.16 * (vnoise(vec2(yw * 1.6, fn * 3.1)) - 0.5)
         + 0.14 * (vnoise(vec2(lx * 18.0, yw * 9.0) + fn * 7.0) - 0.5);
}
void poplarAt(float fn, out float zn, out float xn, out float hn) {
    zn = PZ0 + fn * PSP + 0.6 * (hash11(fn * 1.7) - 0.5);
    xn = PROW + 0.25 * (hash11(fn * 2.9) - 0.5);
    hn = 6.0 + 1.3 * hash11(fn * 4.3);
}

// the row of poplars on the right of the road, front to back; premultiplied colour and alpha
vec4 poplars(vec2 p) {
    float dx = p.x - X0;
    if (dx <= 0.0004) return vec4(0.0);
    float xr = PROW - PAN;
    float zlo = (xr - 0.75) / dx, zhi = (xr + 0.75) / dx;
    float n0 = max(floor((zlo - PZ0) / PSP) - 1.0, 0.0);
    float n1 = ceil((zhi - PZ0) / PSP) + 1.0;
    vec3 C = vec3(0.0);
    float A = 0.0;
    for (int k = 0; k < 16; k++) {
        float fn = n0 + float(k);
        if (fn > n1 || A > 0.995) break;
        float zn, xn, hn;
        poplarAt(fn, zn, xn, hn);
        float yw = CAMH + (p.y - YH) * zn;
        float t = yw / hn;
        if (t < -0.01 || t > 1.02) continue;
        float sway = 0.09 * t * t * sin(T * 0.7 + fn * 1.3) + 0.02 * t * sin(T * 1.9 + fn);
        float lx = dx * zn + PAN - xn - sway;
        float r = poplarR(t) * poplarEdge(lx, yw, fn);
        float d = (abs(lx) - r) / zn;
        d = max(d, (-yw) / zn);
        float a = aa(d, PX);
        if (a <= 0.0) continue;
        // dark green in shade; the leaves along the sunward edge tremble with light
        float rw = 0.05 + 0.6 * PX * zn;
        float edge = smoothstep(r - rw, r - 0.2 * rw, -lx) * step(lx, 0.0) * step(0.05, t);
        float flick = 0.4 + 1.2 * pow(vnoise(vec2(yw * 9.0, T * 3.0 + fn * 5.0) + lx * 6.0), 2.0);
        float leaf = vnoise(vec2(lx * 22.0, yw * 7.0) + fn * 13.0);
        vec3 c = vec3(0.035, 0.05, 0.026) * (0.7 + 0.6 * leaf) + SKYA * 0.05 * (0.5 + leaf);
        if (t < 0.05) c = vec3(0.035, 0.028, 0.022);
        c += SUNC * edge * flick * 0.45;
        c = mix(c, air(p), fogF(zn));
        C += (1.0 - A) * a * c;
        A += (1.0 - A) * a;
    }
    // the far end of the row, too fine to resolve tree by tree
    float zc = xr / dx;
    if (A < 0.995 && zc > PZ0 + (n0 + 16.0) * PSP) {
        float top = YH + (6.6 - CAMH) / zc, bot = yBase(zc);
        float a = aa(p.y - top, PX) * (1.0 - aa(p.y - bot, PX)) * 0.85;
        vec3 c = mix(vec3(0.035, 0.05, 0.026), air(p), fogF(zc));
        C += (1.0 - A) * a * c;
        A += (1.0 - A) * a;
    }
    return vec4(C, A);
}

// haystacks, a farmhouse with its dovecote tower, cypresses and mulberries across the fields
float sdStack(vec2 r, float rad, float h) {   // a pagliaio: a domed beehive of hay about its pole
    float t = sat(r.y / h);
    float w = rad * sqrt(sat(1.0 - t * t * t)) * (1.0 - 0.12 * t);
    float d = max(abs(r.x) - w, max(-r.y, r.y - h)) * 0.7;
    return min(d, sdBox(r - vec2(0.0, h * 1.06), vec2(0.025, h * 0.1)));
}
float fieldsSil(vec2 p, out vec3 c, out float zhit) {
    float best = 1e3;
    c = vec3(0.0);
    zhit = 1e3;
    // the farmhouse (z 56): house, barn with arches, dovecote tower
    {
        const float z = 56.0;
        vec2 r = vec2((p.x - X0) * z + PAN, CAMH + (p.y - YH) * z);
        float d = sdBox(r - vec2(-30.0, 1.25), vec2(3.4, 1.25));
        d = min(d, sdTrap(r - vec2(-30.0, 2.9), 3.7, 2.2, 0.4));
        d = min(d, sdBox(r - vec2(-25.2, 0.95), vec2(1.6, 0.95)));
        d = min(d, sdTrap(r - vec2(-25.2, 2.1), 1.8, 1.2, 0.2));
        d = min(d, sdBox(r - vec2(-33.9, 2.05), vec2(0.85, 2.05)));
        d = min(d, sdTrap(r - vec2(-33.9, 4.45), 1.0, 0.05, 0.35));
        d = min(d, sdCypress(r - vec2(-36.5, 0.0), 5.2, 0.55) * 1.2);
        d = min(d, sdCypress(r - vec2(-37.6, 0.0), 4.2, 0.5) * 1.2);
        d /= z;
        if (d < best) {
            best = d;
            zhit = z;
            float win = max(abs(mod(r.x, 1.4) - 0.7) - 0.18, abs(r.y - 1.6) - 0.28) / z;
            c = vec3(0.42, 0.3, 0.22) * (1.0 - 0.6 * aa(win, PX) * step(abs(r.x + 30.0), 3.0));
        }
    }
    // a hedgerow of pollarded mulberries along a field boundary (z 38)
    {
        const float z = 38.0;
        vec2 r = vec2((p.x - X0) * z + PAN, CAMH + (p.y - YH) * z);
        float k = floor((r.x + 1.75) / 3.5);
        if (k < -1.0 && k > -8.0) {
            float lx = r.x - (k * 3.5);
            float hh = 2.4 + 0.4 * hash11(k);
            float d = min(sdBox(vec2(lx, r.y - hh * 0.3), vec2(0.07, hh * 0.3)),
                          sdCircle(vec2(lx * 0.85, r.y - hh * 0.72), hh * 0.32) + 0.08 * vnoise(r * 4.0));
            d /= z;
            if (d < best) { best = d; zhit = z; c = vec3(0.07, 0.08, 0.04); }
        }
    }
    // haystacks
    for (int i = 0; i < 4; i++) {
        vec4 s = STACK[i];
        float x = X0 + (s.x - PAN) / s.y;
        if (abs(p.x - x) > s.z * 1.3 / s.y) continue;
        vec2 r = vec2((p.x - X0) * s.y + PAN - s.x, CAMH + (p.y - YH) * s.y);
        float d = sdStack(r, s.z, s.w) / s.y;
        if (d < best || (d < 0.0 && s.y < zhit)) {
            best = d;
            zhit = s.y;
            float edge = smoothstep(s.z * 0.5, s.z, -r.x) * step(r.x, 0.0);
            c = vec3(0.32, 0.22, 0.1) * (0.8 + 0.4 * vnoise(r * vec2(12.0, 30.0))) + SUNC * edge * 0.3;
        }
    }
    return best;
}

float stackShadow(vec2 g) {
    float lit = 1.0, t;
    for (int i = 0; i < 4; i++) {
        vec4 s = STACK[i];
        if (g.y >= s.y) continue;
        vec2 h = sunHit(g, s.y, t);
        float soft = 0.01 + 0.02 * t;
        lit *= smoothstep(-soft, soft, sdStack(vec2(h.x - s.x, h.y), s.z, s.w));
    }
    return lit;
}

float poplarShadow(vec2 g) {   // only the fields beyond the row lie in their shadow
    if (g.x < PROW - 0.6) return 1.0;
    float t0 = (g.x - PROW) / -SH.x;
    float lit = 1.0;
    float zc = g.y + t0 * SH.y;
    float nc = floor((zc - PZ0) / PSP + 0.5);
    for (int k = -1; k <= 1; k++) {
        float fn = nc + float(k);
        if (fn < 0.0) continue;
        float zn, xn, hn;
        poplarAt(fn, zn, xn, hn);
        float tt;
        vec2 h = sunHit(g, zn, tt);
        if (tt <= 0.0) continue;
        float lx = h.x - xn;
        float tr = h.y / hn;
        if (tr > 1.0) continue;
        float soft = 0.03 + 0.008 * tt;
        lit *= smoothstep(-soft, soft, abs(lx) - poplarR(tr) * 0.9);
    }
    return lit;
}

vec3 roadGround(vec2 p) {
    float Z = groundZ(p.y);
    float X = (p.x - X0) * Z + PAN;
    float fz = Z * Z * PX / CAMH;
    float fw = Z * PX + abs(p.x - X0) * fz;              // a pixel's footprint across, including the slant
    float rd = abs(X - RX);
    float fadeZ = exp(-fz * 1.2);                        // texture along the view dissolves with distance
    float fadeX = exp(-fw * 9.0);
    float n1 = mix(0.5, vnoise(vec2(X * 2.0, Z * 0.6)), fadeZ);
    // stubble fields: drill rows running away from us, gold going to straw
    vec3 field = mix(vec3(0.46, 0.31, 0.12), vec3(0.58, 0.41, 0.19), n1);
    float rows = 0.5 + 0.5 * cos(X * TAU / 0.3);
    field *= 1.0 - 0.3 * rows * sat(1.0 - fw / 0.07);
    field *= 0.9 + 0.2 * mix(0.5, vnoise(vec2(X * 9.0, Z * 2.5)), fadeZ * fadeX);
    vec3 alb = field;
    if (X > PROW - 1.0) alb = mix(field, vec3(0.30, 0.31, 0.12), 0.55);    // meadow beyond the poplars
    // grass verges and ditches
    float verge = smoothstep(RW + 0.5, RW + 0.42, rd);
    alb = mix(alb, vec3(0.2, 0.2, 0.08) * (0.8 + 0.4 * n1), verge);
    alb *= 1.0 - 0.5 * smoothstep(0.08 + fw, 0.0, abs(rd - RW - 0.55));
    // the white road: pale gravel, two cart ruts and a grassy crown
    float road = smoothstep(RW + 0.02 + fw, RW - 0.02, rd);
    vec3 grav = vec3(0.86, 0.76, 0.60) * (0.9 + 0.2 * mix(0.5, vnoise(vec2(X, Z) * 22.0), fadeZ * fadeX) + 0.05 * n1);
    float rut = exp(-pow((rd - 0.38) / 0.09, 2.0));
    grav *= 1.0 - 0.14 * rut;
    grav = mix(grav, vec3(0.36, 0.34, 0.16), 0.35 * exp(-pow(rd / 0.08, 2.0)) * fadeX);
    alb = mix(alb, grav, road);
    // sunlight and shadows
    vec2 g = vec2(X, Z);
    float lit = loverShadow(g, uP[1], POSE_E, 1.0) * loverShadow(g, uP[2], POSE_M, 0.0);
    lit *= poplarShadow(g) * stackShadow(g);
    vec3 c = alb * (SUNC * (0.3 + SINE) * lit + SKYA * 1.3);
    // the dust of the road glares back towards the low sun
    float glare = exp(-abs(p.x - SUN.x) * 2.2) * exp(-(YH - p.y) * 4.0);
    c += SUNC * glare * (0.15 + 0.5 * road) * lit;
    return mix(c, air(p), fogF(Z));
}

float hillsFar(float x) {   // the Euganean hills: volcanic cones in the haze
    return YH + 0.012 + 0.032 * exp(-pow((x + 0.62) / 0.085, 2.0)) + 0.05 * exp(-pow((x + 0.77) / 0.07, 2.0))
         + 0.022 * exp(-pow((x + 0.47) / 0.07, 2.0)) + 0.03 * exp(-pow((x + 0.88) / 0.06, 2.0))
         + 0.012 * exp(-pow((x - 0.5) / 0.35, 2.0)) + 0.004 * vnoise(vec2(x * 30.0, 2.0));
}
float treeline(float x) {   // a ribbon of distant trees along the edge of the plain
    return YH + 0.004 + 0.005 * vnoise(vec2(x * 70.0, 1.0)) + 0.003 * vnoise(vec2(x * 190.0, 5.0));
}

vec3 road(vec2 p) {
    float zf = 1e4;
    vec3 col = skyCol(p);
    // rays fanning up from the sun through gaps in unseen cloud
    vec2 dv = p - SUN;
    float ang = atan(dv.y, dv.x);
    float rays = fbm(vec2(ang * 13.0 + 0.3 * sin(T * 0.05), T * 0.02));
    col += SUNC * smoothstep(0.42, 0.85, rays) * 0.045 * exp(-length(dv) * 1.6) * smoothstep(YH - 0.01, YH + 0.04, p.y);
    // the far hills, then the treeline of the plain
    float hy = hillsFar(p.x + PAN * 0.002);
    col = mix(col, mix(vec3(0.3, 0.2, 0.2), air(p), 0.86), aa(p.y - hy, PX));
    float ty = treeline(p.x + PAN * 0.006);
    col = mix(col, mix(vec3(0.1, 0.08, 0.05), air(p), 0.72), aa(p.y - ty, PX));
    // the ground
    if (p.y < YH + 0.001) col = mix(col, roadGround(p), aa(p.y - YH, PX));
    // fields' furniture
    {
        vec3 c;
        float zh;
        float d = fieldsSil(p, c, zh);
        if (d < 0.01) lay(col, zf, p, d, c * shadeLight(0.5) * 2.0, zh, 0.0);
    }
    // the poplar row
    vec4 pr = poplars(p);
    col = col * (1.0 - pr.a) + pr.rgb;
    // swifts over the fields
    float sw = swifts(p, uP[3].y);
    col = mix(col, mix(vec3(0.02, 0.016, 0.014), air(p), 0.3), sw);
    // the lovers: he walks into the sun, she stays
    drawLovers(col, p);
    // dust motes in the low light
    float mote = dust(p + vec2(PAN * 0.6, 0.0), T, 0.12, 0.08);
    col += SUNC * mote * 0.3 * (0.3 + exp(-length(p - SUN) * 1.5));
    return col;
}

// ================================================================== main
void main() {
    vec2 p = screen();
    MODE = uP[0].x;
    PAN = uP[0].y;
    CROWD = sat(uP[0].z);
    WARM = sat(uP[0].w);
    T = uTime;
    PX = PIXEL;

    SUNC = mix(vec3(1.0, 0.80, 0.52), vec3(1.0, 0.48, 0.18), WARM) * 2.4;
    AIRC = mix(vec3(0.88, 0.66, 0.40), vec3(0.95, 0.45, 0.20), WARM) * 0.8;
    SKYA = mix(vec3(0.14, 0.18, 0.27), vec3(0.16, 0.13, 0.21), WARM);

    if (MODE < 1.5) {
        YH = -0.06; CAMH = YH + 0.42; DENS = 0.076; FOGP = 2.0; X0 = 0.0;
        SUN = mix(vec2(-0.30, 0.52), vec2(-0.45, 0.25), WARM);   // sinking behind the belfry
    } else {
        YH = -0.08; CAMH = YH + 0.42; DENS = 1.0 / 34.0; FOGP = 1.5; X0 = 0.05;
        SUN = vec2(-0.30, mix(0.15, -0.03, WARM));
    }
    vec2 sd = vec2(SUN.x - X0, 1.0);
    SH = normalize(sd);
    TANE = (SUN.y - YH) / length(sd);
    SINE = TANE / sqrt(1.0 + TANE * TANE);
    BNC = SUNC * 0.11 * max(SINE, 0.15);

    // the lovers' poses: breathing, the breeze in her skirt; reaching for one another at the farewell
    vec4 E = uP[1], Mp = uP[2];
    float side = (Mp.x >= E.x) ? 1.0 : -1.0;
    POSE_E = vec4(0.12, 0.12, 0.35 + 0.03 * sin(T * 1.3), 0.01 * sin(T * 0.7));
    POSE_M = vec4(0.10, 0.10, 0.0, 0.006 * sin(T * 0.6 + 1.0));
    if (MODE > 0.5 && MODE < 1.5) {
        float reach = 0.36 + 0.06 * sin(T * 0.5);          // reaching, not quite touching
        if (side > 0.0) { POSE_E.y = reach; POSE_M.x = reach * 0.85; }
        else { POSE_E.x = reach; POSE_M.y = reach * 0.85; }
        POSE_E.w += 0.02 * side;
        POSE_M.w -= 0.015 * side;
    } else if (MODE > 1.5) {
        float wk = sin(T * 4.2);
        POSE_M = vec4(0.28 * wk, -0.28 * wk, 0.0, 0.0);
        POSE_E = vec4(0.06, 0.08, 0.36 + 0.05 * sin(T * 0.9), -0.012 + 0.01 * sin(T * 0.6));
    }

    // slow drifts of thicker and thinner haze, like smoke across a stage
    HAZEN = 0.82 + 0.36 * fbm(vec2(p.x * 2.2 + PAN * 0.1 - T * 0.025, p.y * 3.5 + 0.3 * sin(T * 0.05)));

    vec3 col = (MODE < 1.5) ? square(p) : road(p);
    fragColor = vec4(col, 1.0);
}
