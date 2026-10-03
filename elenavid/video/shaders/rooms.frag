#version 430
// =============================================================================================
// ROOMS  -  the interiors of ELENA as lit stage sets ("teatro di luce")
// ---------------------------------------------------------------------------------------------
// One shader, eight rooms (uP[0].x). Each room is a shallow box (back wall, floor, side walls,
// ceiling) seen by an off-axis camera whose figure plane (depth Z0) maps exactly onto screen
// coordinates, so the timeline places characters in screen space and they stay put while the
// set parallaxes around them as the camera drifts. Furniture and set pieces are flat paper-cut
// silhouettes at their own depths. Light enters through windows and doorways and is integrated
// through the haze in three depth bands, so shafts pass both behind and in front of the flats.
// Output is linear HDR scene light: midtones 0.1-0.6, windows and lamps 2-8.
// =============================================================================================
#include common

// ---------------------------------------------------------------------------- conventions
// uP[0]  x mode 0..7
//        y camera drift: lateral camera offset (0.01 = 0.25 m; clamped to +-1.2 m). Animate it
//          slowly; figures stay put, the set behind moves with it, foreground flats against it
//        z amber "home" glow 0..1 (Davide's warmth pooling low in the room)
//        w walls fly away 0..1 (mode 6)
// uP[1]  Elena                 x, y (feet), height, alpha   (screen space: y in [-0.5, 0.5])
// uP[2]  second character      mode 0 the Mother, 1 Vittorio in person, 3..7 Davide;
//                              mode 2: x, y (feet), height of Vittorio's vision (z = 0 keeps
//                              the default by the foot of the bed; never drawn solid there)
// uP[3]  third character       mode 1 the servant, otherwise Nives
// uP[4]  x Tommaso's glow 0..1   y Vittorio 0..1 (mode 1 shadow, mode 2 vision)
//        z portrait glow 0..1 (mode 0)   w door light 0..1 (modes 1 and 7)
// uP[5]  x Elena pose, y second pose, z third pose, w lamp flicker 0..1 (modes 4 and 5)
//        pose codes, shared by everyone: 0 standing, 0..1 arms rising, 1 arms lifted
//        (holding Tommaso in modes 1, 3 and 5), 2 kneeling, 3 lying, 4 seated
// uP[6]  x mode extra: mode 3 sea sparkle 0..1, mode 4 the door bursting open 0..1
// Characters standing higher up the frame are read as further away: they parallax with the
// floor at that depth and their cast shadows land correctly.

// ---------------------------------------------------------------------------- globals
const float Z0 = 3.0;      // depth of the figure plane (m); one screen unit there = 3 m
const float CAMY = 1.26;   // camera height (m): the floor at Z0 sits at screen y = -0.42

vec2 SP;                   // screen coordinates
vec3 RO, RD;               // camera ray P(t) = RO + RD t, with P.z = Z0 t
float RDL;                 // world length of the ray per metre of depth
float PX;                  // one pixel in screen units
float T;                   // film time
float DRIFT;               // lateral camera offset (m)
int MODE;

vec2 at(float z) { return RO.xy + RD.xy * (z / Z0); }
vec3 at3(float z) { return RO + RD * (z / Z0); }
vec2 toScreen(vec3 p) { return vec2((p.x - DRIFT * (1.0 - p.z / Z0)) / p.z, (p.y - CAMY) / p.z); }
float ign(vec2 p) { return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }
float aaw(float d, float w) { return 1.0 - smoothstep(-w, w, d); }
float band01(float x, float a, float b, float w) { return smoothstep(a - w, a + w, x) * (1.0 - smoothstep(b - w, b + w, x)); }

// a layer of colour c and coverage a over a base
vec3 lay(vec3 base, vec3 c, float a) { return base * (1.0 - a) + c * a; }

// ---------------------------------------------------------------------------- room box
struct Hit { float t; int s; vec3 p; };   // s: 0 back, 1 floor, 2 ceiling, 3 left, 4 right, 5 void

float FLOORPAD = 1e3;     // how far the floor runs past the side walls (mode 6 bounds it)

// lift: x back wall, y left wall, z right wall, w ceiling (metres flown upwards, mode 6)
Hit roomHit(float zb, float xl, float xr, float hc, vec4 lift, float floorEnd) {
    Hit h; h.t = 1e5; h.s = 5;
    float t;
    vec3 p;
    t = zb / Z0; p = RO + RD * t;
    if (p.y > lift.x && p.y < hc + lift.x && p.x > xl && p.x < xr) { h.t = t; h.s = 0; }
    if (RD.y < 0.0) {
        t = -RO.y / RD.y; p = RO + RD * t;
        if (t < h.t && p.z < floorEnd && p.x > xl - FLOORPAD && p.x < xr + FLOORPAD) { h.t = t; h.s = 1; }
    }
    if (RD.y > 0.0) {
        t = (hc + lift.w - RO.y) / RD.y; p = RO + RD * t;
        if (t < h.t && p.z < zb && p.x > xl && p.x < xr) { h.t = t; h.s = 2; }
    }
    if (RD.x < 0.0) {
        t = (xl - RO.x) / RD.x; p = RO + RD * t;
        if (t < h.t && p.y > lift.y && p.y < hc + lift.y && p.z < zb) { h.t = t; h.s = 3; }
    }
    if (RD.x > 0.0) {
        t = (xr - RO.x) / RD.x; p = RO + RD * t;
        if (t < h.t && p.y > lift.z && p.y < hc + lift.z && p.z < zb) { h.t = t; h.s = 4; }
    }
    h.p = RO + RD * min(h.t, 1e3);
    return h;
}

// distance (m) to the nearest room edge, for soft corner shading
float cornerDist(Hit h, float zb, float xl, float xr, float hc) {
    vec3 p = h.p;
    if (h.s == 0) return min(min(p.y, hc - p.y), min(p.x - xl, xr - p.x));
    if (h.s == 1) return min(zb - p.z, min(p.x - xl, xr - p.x));
    if (h.s == 2) return min(zb - p.z, min(p.x - xl, xr - p.x));
    return min(min(p.y, hc - p.y), zb - p.z);
}

// ---------------------------------------------------------------------------- materials
vec3 plaster(vec2 uv, vec3 base) {
    float n = fbm(uv * 1.1 + 3.7);
    float s = vnoise(uv * vec2(4.0, 0.7) + 11.0);
    return base * (0.76 + 0.34 * n + 0.1 * s);
}
// floorboards running in depth (z); fw = pixel footprint in metres
vec3 boards(vec2 xz, vec3 base, float w, float fw) {
    float id = floor(xz.x / w);
    float along = xz.y + hash11(id * 1.7) * 9.0;
    float pid = floor(along / 1.9);
    float h = hash21(vec2(id, pid));
    float gx = abs(fract(xz.x / w) - 0.5) * 2.0;
    float fade = 1.0 - smoothstep(0.15 * w, 0.5 * w, fw);
    float seam = smoothstep(1.0 - 2.5 * fw / w - 0.04, 1.0, gx) * fade;
    float butt = smoothstep(0.985, 1.0, abs(fract(along / 1.9) - 0.5) * 2.0) * fade;
    float grain = vnoise(vec2(xz.x * 38.0, along * 1.6 + id * 3.0));
    vec3 c = base * (0.72 + 0.4 * h) * (0.86 + 0.22 * mix(0.5, grain, fade));
    return c * (1.0 - 0.55 * max(seam, butt));
}
vec3 tiles(vec2 xz, vec3 base, float s, float fw) {
    vec2 g = xz / s;
    vec2 id = floor(g);
    vec2 f = abs(fract(g) - 0.5);
    float e = max(f.x, f.y);
    float fade = 1.0 - smoothstep(0.1 * s, 0.4 * s, fw);
    float grout = smoothstep(0.47 - fw / s, 0.47 + fw / s, e) * fade;
    float h = hash21(id);
    vec3 c = base * (0.75 + 0.35 * h) * (0.9 + 0.2 * vnoise(xz * 9.0));
    return mix(c, base * 0.4, grout * 0.8);
}
vec3 giltCol(vec2 uv, float cold) {
    float orn = 0.55 + 0.45 * vnoise(uv * 38.0) * vnoise(uv * 11.0 + 3.0);
    return mix(vec3(0.85, 0.6, 0.26), vec3(0.42, 0.5, 0.64), cold) * orn;
}

// ---------------------------------------------------------------------------- characters
vec4 CP[3];       // x, y (feet), height, alpha in screen space, drift-corrected
vec4 CPOSE[3];    // sdFigure pose
float CV[3];      // variant: 0 standing, 1 arms lifted, 2 kneeling, 3 lying, 4 seated
float CHR[3];     // hair
float CZ[3];      // implied depth (m)
float CHOLD[3];   // 1 when holding Tommaso
vec3 CB[3], CR[3];

// asleep on the back, head to the left; origin at the hips on the mattress (units of height)
float sdLying(vec2 q, float hair) {
    float d = sdCircle(q - vec2(-0.43, 0.09), 0.064);
    d = smin(d, sdCircle(q - vec2(-0.40, 0.112), 0.022), 0.02);
    if (hair > 0.5) d = smin(d, sdEllipse(q - vec2(-0.49, 0.072), vec2(0.055, 0.045)), 0.03);
    d = smin(d, sdCapsule(q, vec2(-0.385, 0.06), vec2(-0.33, 0.06), 0.03), 0.03);
    d = smin(d, sdRBox(q - vec2(-0.1, 0.065), vec2(0.24, 0.07), 0.06), 0.04);
    d = smin(d, sdCapsule(q, vec2(0.1, 0.05), vec2(0.5, 0.035), 0.05), 0.05);
    return d;
}

// common sdFigure, with a jacket and collar for the men (trousers) so they read as clothed
float figSD(vec2 q, vec4 pose, float hair) {
    float d = sdFigure(q, pose, hair);
    if (pose.z > 0.0) d += 0.004 * sin(q.x * 45.0 + T * 1.3) * smoothstep(0.1, 0.0, q.y);
    if (pose.z <= 0.0) {
        vec2 j = q;
        j.x -= j.y * pose.w;
        d = smin(d, sdTrap(j - vec2(0.0, 0.6), 0.098, 0.121, 0.17), 0.02);
        d = smin(d, sdTrap(j - vec2(0.0, 0.795), 0.06, 0.034, 0.03), 0.015);
    }
    return d;
}

float actorSD(vec2 q, vec4 pose, float hair, float v) {
    if (v < 1.5) return figSD(q, pose, hair);
    if (v < 2.5) {                                   // kneeling: shins folded beneath
        float d = max(figSD(q + vec2(0.0, 0.25), pose, hair), -q.y);
        if (pose.z > 0.0) d = smin(d, sdEllipse(q - vec2(0.0, 0.012), vec2(0.2 + 0.1 * pose.z, 0.04)), 0.05);
        else d = smin(d, sdEllipse(q - vec2(0.0, 0.02), vec2(0.115, 0.03)), 0.03);
        return d;
    }
    if (v < 3.5) return sdLying(q, hair);
    // seated, facing us: the upper body lowered onto the lap, shins down to the floor
    float d = max(figSD(q + vec2(0.0, 0.2), pose, hair), 0.25 - q.y);
    d = smin(d, sdRBox(q - vec2(0.0, 0.27), vec2(0.115, 0.04), 0.03), 0.03);
    if (pose.z > 0.0) {
        d = smin(d, sdTrap(q - vec2(0.0, 0.17), 0.125 + 0.06 * pose.z, 0.115, 0.1), 0.02);
        d = min(d, sdCapsule(q, vec2(-0.045, 0.1), vec2(-0.05, 0.015), 0.025));
        d = min(d, sdCapsule(q, vec2(0.045, 0.1), vec2(0.05, 0.015), 0.025));
    } else {
        d = min(d, sdCapsule(q, vec2(-0.055, 0.27), vec2(-0.058, 0.02), 0.034));
        d = min(d, sdCapsule(q, vec2(0.055, 0.27), vec2(0.058, 0.02), 0.034));
    }
    return d;
}

// rim band of character i towards direction dir (emboss test, see actor)
float rimBand(int i, vec2 q, float a, vec2 dir, float e) {
    float dl = actorSD(q + dir * (e / CP[i].z), CPOSE[i], CHR[i], CV[i]) * CP[i].z;
    return a * smoothstep(-0.25 * e, e, dl);
}

float WRAP = 0.0;   // > 0: the key light is behind the figure and wraps round both sides

// Shades a character exactly as common figure() does (body, rim band, halo), extended with the
// stage variants above and a second, positional light (Tommaso's glow, a candle, a door).
// tint scales the body (scene exposure), rimK the rim; L1 = 2D direction towards the key light.
vec4 actor(int i, vec2 L1, float rimK, vec3 tint, vec3 l2col, vec2 l2pos) {
    vec4 P = CP[i];
    if (P.w <= 0.001 || P.z <= 0.001) return vec4(0.0);
    vec2 q = (SP - P.xy) / P.z;
    if (length(q - vec2(0.0, 0.5)) > 0.86) return vec4(0.0);
    float v = CV[i];
    float d = actorSD(q, CPOSE[i], CHR[i], v) * P.z;
    float px = 1.5 * PIXEL;
    float a = aa(d, px);
    float halo = glow(d, 0.008 * P.z) * (1.0 - a) * 0.24;
    if (a <= 0.0 && halo < 0.002) return vec4(0.0);
    // The rim is an emboss test: inside here but outside one rim-width towards the light. Unlike
    // exp(-|d|) it ignores the internal seams of the union (waist, shoulders, arms). 'facing'
    // (for the outer halo) is the same sample read as a directional derivative of the field.
    float e = 0.0045 + 0.004 * P.z;
    vec2 l1 = normalize(L1 + vec2(1e-5, 2e-5));
    float dL1 = actorSD(q + l1 * (e / P.z), CPOSE[i], CHR[i], v) * P.z;
    float facing = sat((dL1 - d) / e * 0.8 + 0.2), facing2 = 0.0;
    float band = a * smoothstep(-0.25 * e, e, dL1), band2 = 0.0;
    if (WRAP > 0.0 && a > 0.0) {
        vec2 pp = vec2(-l1.y, l1.x);
        float bw = max(rimBand(i, q, a, normalize(pp + l1 * 0.35), e), rimBand(i, q, a, normalize(-pp + l1 * 0.35), e));
        band = max(band, bw * WRAP);
    }
    if (dot(l2col, l2col) > 1e-6) {
        vec2 to2 = l2pos - SP;
        vec2 l2 = to2 / (length(to2) + 1e-4);
        float dL2 = actorSD(q + l2 * (e / P.z), CPOSE[i], CHR[i], v) * P.z;
        facing2 = sat((dL2 - d) / e * 0.9 + 0.1);
        band2 = a * smoothstep(-0.25 * e, e, dL2);
    }
    vec3 rim = CR[i] * rimK;
    vec3 c = vec3(0.0);
    if (a > 0.0) {
        float shade = 0.85 + 0.15 * fbm(q * 18.0);
        // folds fanning from the waist of a skirt
        if (CPOSE[i].z > 0.0 && q.y < 0.5 && v < 1.5)
            shade *= 0.9 + 0.1 * sin(atan(q.x, 0.62 - q.y) * 34.0 + q.y * 3.0);
        // soft side modelling towards each light, smooth across the body (no creases)
        vec2 qc = q - vec2(0.0, 0.6);
        float side1 = sat(dot(qc, l1) * 3.0 + 0.3);
        vec2 l2d = normalize(l2pos - P.xy - vec2(0.0, 0.6 * P.z) + 1e-5);
        float side2 = sat(dot(qc, l2d) * 3.0 + 0.3);
        c = CB[i] * tint * shade * (0.5 + 0.6 * sat(q.y * 1.1));
        c += (rim * side1 + l2col * side2) * 0.025;
        c += rim * band * 1.6 + l2col * band2 * 1.6;
        c += CB[i] * l2col * 0.09;   // a little of the second light on the body itself
        c += (CB[i] * 0.5 + vec3(0.06, 0.035, 0.012)) * vec3(1.0, 0.58, 0.24) * uP[0].z * 0.35 * sat(0.55 - q.y);
    }
    vec3 hc = rim * halo * facing + l2col * halo * facing2;
    float alpha = max(a, halo * 0.5 * max(facing, facing2));
    return vec4(c * a + hc, alpha) * P.w;
}

// soft coverage of character i at screen point s (for cast shadows)
float actorOcc(int i, vec2 s, float blur) {
    vec4 P = CP[i];
    if (P.w <= 0.001 || P.z <= 0.001) return 0.0;
    vec2 q = (s - P.xy) / P.z;
    if (length(q - vec2(0.0, 0.5)) > 0.95) return 0.0;
    float d = actorSD(q, CPOSE[i], CHR[i], CV[i]) * P.z;
    return (1.0 - smoothstep(-blur, blur, d)) * P.w;
}

// shadow of all characters on a floor point p, light travelling along L (directional)
float castDir(vec3 p, vec3 L, float soft) {
    float sh = 0.0;
    for (int i = 0; i < 3; i++) {
        if (CP[i].w <= 0.001 || CV[i] > 2.5 && CV[i] < 3.5) continue;
        float s = (p.z - CZ[i]) / L.z;
        if (s <= 0.0) continue;
        vec3 f = p - L * s;
        vec2 sc = vec2((f.x - DRIFT * (1.0 - CZ[i] / Z0)) / CZ[i], (f.y - CAMY) / CZ[i]);
        sh = max(sh, actorOcc(i, sc, 0.004 + soft * s));
    }
    return sh;
}
// the same for a point light at S
float castPoint(vec3 p, vec3 S, float soft) {
    float sh = 0.0;
    for (int i = 0; i < 3; i++) {
        if (CP[i].w <= 0.001 || CV[i] > 2.5 && CV[i] < 3.5) continue;
        float u = (CZ[i] - p.z) / (S.z - p.z);
        if (u <= 0.0 || u >= 1.0) continue;
        vec3 f = p + (S - p) * u;
        vec2 sc = vec2((f.x - DRIFT * (1.0 - CZ[i] / Z0)) / CZ[i], (f.y - CAMY) / CZ[i]);
        sh = max(sh, actorOcc(i, sc, 0.004 + soft * (1.0 - u)));
    }
    return sh;
}

// ---------------------------------------------------------------------------- Tommaso
const vec3 SILVER = vec3(0.85, 0.9, 1.0);
// kind 0 lying (head to the left, origin at the hips), 1 seated (origin on the seat), 2 a bundle
float sdChild(vec2 q, float kind) {
    if (kind < 0.5) {
        float d = sdCircle(q - vec2(-0.36, 0.11), 0.13);
        return smin(d, sdEllipse(q - vec2(0.02, 0.06), vec2(0.32, 0.1)), 0.07);
    }
    if (kind < 1.5) {
        float d = sdCircle(q - vec2(0.0, 0.64), 0.14);
        d = smin(d, sdTrap(q - vec2(0.0, 0.3), 0.17, 0.12, 0.2), 0.07);
        d = smin(d, sdRBox(q - vec2(0.0, 0.07), vec2(0.17, 0.06), 0.05), 0.05);
        d = min(d, sdCapsule(q, vec2(-0.07, 0.04), vec2(-0.08, -0.26), 0.042));
        d = min(d, sdCapsule(q, vec2(0.07, 0.04), vec2(0.08, -0.26), 0.042));
        d = min(d, sdCapsule(q, vec2(-0.16, 0.44), vec2(-0.13, 0.13), 0.036));
        d = min(d, sdCapsule(q, vec2(0.16, 0.44), vec2(0.13, 0.13), 0.036));
        return d;
    }
    float d = sdEllipse(q - vec2(0.04, 0.0), vec2(0.34, 0.16));
    return smin(d, sdCircle(q - vec2(-0.3, 0.05), 0.13), 0.06);
}
// emission (premultiplied) and coverage of the child of light
vec4 childGlow(vec2 p, vec2 pos, float s, float lvl, float kind) {
    vec2 q = (p - pos) / s;
    if (length(q) > 2.6) return vec4(0.0);
    float d = sdChild(q, kind) * s;
    float inside = aaw(d, PX * 1.2 + 0.006 * s);
    float sh = 0.93 + 0.05 * sin(T * 2.3) + 0.03 * sin(T * 5.7);
    // light gathered most strongly in the head and heart, softer at the edges
    vec2 hc = kind < 0.5 ? vec2(-0.36, 0.11) : (kind < 1.5 ? vec2(0.0, 0.64) : vec2(-0.3, 0.05));
    float heart = exp(-length(q - hc) * 4.0) + 0.6 * exp(-length(q - hc * 0.35) * 3.0);
    float core = inside * (0.35 + 0.35 * smoothstep(0.0, 0.07 * s, -d) + 0.6 * heart);
    float breath = 0.8 + 0.2 * fbm(q * 5.0 + vec2(0.0, T * 0.3));
    vec3 e = SILVER * lvl * sh * (core * 1.05 * breath + glow(d, 0.06 * s) * 0.5 + glow(d, 0.25 * s) * 0.16);
    // without his light only a faint, still shape remains
    e += vec3(0.05, 0.06, 0.08) * inside * (1.0 - smoothstep(0.0, 0.3, lvl));
    return vec4(e, inside * 0.92);
}

// Elena holding Tommaso against her breast (pose 1 in modes 1, 3, 5): the swaddled child of
// light, tilted with his head at her shoulder, cradled by both forearms
vec3 heldChild(vec3 col, float lvl, vec3 tint) {
    vec4 P = CP[0];
    if (CHOLD[0] < 0.5 || P.w <= 0.0) return col;
    vec2 q = (SP - P.xy) / P.z;
    q.x -= q.y * CPOSE[0].w;
    if (length(q - vec2(0.0, 0.62)) > 0.35) return col;
    vec2 bc = vec2(0.005, 0.635);
    vec2 bq = rot(0.32) * (q - bc);
    vec4 g = childGlow(bq * P.z + P.xy, P.xy, 0.3 * P.z, lvl * 1.15, 2.0);
    col = col * (1.0 - g.a * 0.95 * P.w) + g.rgb * P.w;
    float arms = sdCapsule(q, vec2(0.124, 0.592), vec2(-0.075, 0.585), 0.027);         // under him
    arms = min(arms, sdCapsule(q, vec2(-0.124, 0.6), vec2(-0.035, 0.668), 0.024));     // over him
    arms = min(arms, sdCapsule(q, vec2(0.11, 0.76), vec2(0.124, 0.592), 0.025));       // upper arms
    arms = min(arms, sdCapsule(q, vec2(-0.11, 0.76), vec2(-0.124, 0.6), 0.025));
    arms = min(arms, sdEllipse(q - vec2(-0.03, 0.672), vec2(0.03, 0.022)));             // her hand
    float a = aaw(arms * P.z, PX) * P.w;
    float near = exp(-length((q - bc) * vec2(0.8, 1.6)) * 9.0);
    vec3 c = CB[0] * tint * 0.9 + SILVER * lvl * 0.8 * exp(max(arms, -0.03) / 0.005) * (0.25 + 0.75 * near);
    return lay(col, c, a);
}

// A chair behind a seated character (pose 4), in the character's own units, so a seated
// figure is never left sitting on air: a parlour armchair (mode 0), a bentwood chair (mode 4)
// or a plain wooden chair. L is the light falling on it.
vec3 seatBehind(int i, vec3 col, vec3 L) {
    vec4 P = CP[i];
    if (CV[i] < 3.5 || P.w <= 0.0) return col;
    vec2 q = (SP - P.xy) / P.z;
    if (abs(q.x) > 0.36 || q.y > 0.82 || q.y < -0.03) return col;
    vec2 a = vec2(abs(q.x), q.y);
    float d;
    vec3 c;
    if (MODE == 0) {
        d = sdRBox(q - vec2(0.0, 0.47), vec2(0.21, 0.25), 0.09);
        d = min(d, sdRBox(a - vec2(0.205, 0.33), vec2(0.05, 0.075), 0.03));
        d = min(d, sdRBox(q - vec2(0.0, 0.225), vec2(0.235, 0.05), 0.025));
        d = min(d, sdBox(a - vec2(0.19, 0.07), vec2(0.016, 0.09)));
        c = vec3(0.3, 0.12, 0.1) * (0.85 + 0.15 * sin(q.x * 60.0));
    } else if (MODE == 4) {
        float loop = max(abs(sdEllipse(q - vec2(0.0, 0.48), vec2(0.14, 0.17))) - 0.013, 0.3 - q.y);
        d = min(loop, sdBox(a - vec2(0.14, 0.3), vec2(0.013, 0.3)));
        d = min(d, sdRBox(q - vec2(0.0, 0.258), vec2(0.18, 0.02), 0.015));
        d = min(d, sdCapsule(a, vec2(0.15, 0.25), vec2(0.185, 0.0), 0.012));
        c = vec3(0.12, 0.07, 0.04);
    } else {
        d = sdBox(a - vec2(0.16, 0.31), vec2(0.016, 0.31));
        d = min(d, sdBox(q - vec2(0.0, 0.6), vec2(0.17, 0.03)));
        d = min(d, sdBox(q - vec2(0.0, 0.47), vec2(0.16, 0.012)));
        d = min(d, sdRBox(q - vec2(0.0, 0.262), vec2(0.19, 0.02), 0.01));
        d = min(d, sdBox(a - vec2(0.15, 0.13), vec2(0.014, 0.13)));
        c = vec3(0.16, 0.1, 0.06);
    }
    float al = aaw(d * P.z, PX) * P.w;
    float edge = smoothstep(-0.02, 0.0, d);
    return lay(col, c * L * (0.8 + 0.4 * edge), al);
}

// ---------------------------------------------------------------------------- home glow
// Davide's warmth (uP[0].z): a soft amber light pooling low in the room around HOMEC (x, z)
vec2 HOMEC = vec2(0.0, 3.4);
float HOMEK = 1.0;
vec3 homeGlow(vec3 p, vec2 c) {
    float k = uP[0].z * HOMEK;
    if (k <= 0.0) return vec3(0.0);
    vec2 d = p.xz - c;
    return vec3(1.0, 0.58, 0.24) * k * 0.9 * exp(-dot(d, d) * 0.3) * exp(-max(p.y, 0.0) * 1.0);
}
vec3 home(vec3 p) { return homeGlow(p, HOMEC); }

// ---------------------------------------------------------------------------- haze
float hazeDen(vec3 p) {
    return 0.55 + 0.45 * vnoise(vec2(p.x * 1.4 + p.z * 0.6, p.y * 1.4) + T * vec2(0.06, 0.02));
}

// =============================================================================================
// MODE 0: the parlour, spring 1950. Warm daylight through a tall window with lace curtains,
// blossom outside, the portrait of the gentleman on the wall.
// =============================================================================================
const float A_ZB = 5.5, A_XL = -3.2, A_XR = 3.2, A_HC = 3.4;
const vec4 A_WIN = vec4(-1.6, 1.95, 0.62, 1.12);   // window centre, half size (back wall, m)
const vec4 A_POR = vec4(0.22, 2.12, 0.36, 0.47);   // portrait oval centre, radii
const vec3 A_SUNC = vec3(1.0, 0.84, 0.62) * 3.6;
vec3 A_SUN;

float laceThreads(vec2 w) {
    vec2 g = w * 30.0;
    float net = abs(sin(g.x + g.y) * sin(g.x - g.y));
    vec2 cc = w * vec2(3.6, 3.0);
    cc.y += 0.5 * mod(floor(cc.x), 2.0);
    vec2 c = fract(cc) - 0.5;
    float ang = atan(c.y, c.x);
    float r = length(c);
    float petal = smoothstep(0.23, 0.15, r - 0.06 * cos(ang * 5.0)) * smoothstep(0.02, 0.07, r);
    float hem = smoothstep(0.07, 0.0, abs(w.y - (A_WIN.y - A_WIN.w + 0.14)));
    hem += smoothstep(0.04, 0.0, abs(w.y - (A_WIN.y - A_WIN.w + 0.28))) * 0.6;
    return sat(0.2 + 0.32 * net + 0.75 * petal + 0.7 * hem);
}
float aCurtainMask(vec2 l, float b) {
    float eL = -0.08 + 0.025 * sin(T * 0.6 + l.y * 2.0);
    float eR = 0.10 + 0.025 * sin(T * 0.5 + l.y * 2.3 + 1.0);
    return 1.0 - smoothstep(eL - b, eL + b, l.x) * (1.0 - smoothstep(eR - b, eR + b, l.x));
}
float aGlazing(vec2 l, float b) {
    float bars = min(abs(l.x) - 0.022, abs(l.y - 0.5) - 0.024);
    bars = min(bars, min(abs(l.y + 0.32) - 0.014, abs(abs(l.x) - 0.31) - 0.012));
    return smoothstep(-b, b, bars);
}
float aAperture(vec2 w, float s) {
    vec2 l = w - A_WIN.xy;
    float b = 0.006 + 0.03 * s;
    float o = 1.0 - smoothstep(-b, b, sdBox(l, A_WIN.zw));
    if (o <= 0.001) return 0.0;
    o *= aGlazing(l, b);
    float tr = mix(0.6, 1.0 - 0.6 * laceThreads(w), exp(-s * 1.4));
    return o * mix(1.0, tr, aCurtainMask(l, b));
}
float aSunLit(vec3 p) {
    float s = (p.z - A_ZB) / A_SUN.z;
    if (s <= 0.0) return 0.0;
    return aAperture(p.xy - A_SUN.xy * s, s);
}
vec3 aPortraitLight(vec3 p) {     // the picture lamp over the portrait
    vec3 L = vec3(A_POR.x, A_POR.y + 0.62, A_ZB - 0.18);
    vec3 d = p - L;
    return vec3(1.0, 0.72, 0.42) * uP[4].z * 0.35 / (0.15 + dot(d, d));
}
// ambient and bounce light in the parlour
vec3 aAmbient(vec3 p) {
    vec3 a = vec3(0.24, 0.19, 0.14);
    // bounce from the sunlit floor and the window wall
    a += vec3(0.26, 0.18, 0.1) * exp(-length(p.xz - vec2(-0.4, 3.4)) * 0.55) * (0.45 + 0.55 * exp(-p.y * 0.8));
    a += vec3(0.2, 0.16, 0.11) * exp(-length(p.xy - A_WIN.xy) * 0.9) * smoothstep(2.5, A_ZB, p.z);
    return a * (0.72 + 0.28 * smoothstep(0.0, 2.5, p.y)) + home(p);
}

// the spring garden seen through the window
vec3 aOutside(vec2 w) {
    vec2 v = vec2(RD.x / RD.z, RD.y / RD.z);           // far away: direction only
    vec3 sky = mix(vec3(1.0, 0.94, 0.82), vec3(0.62, 0.76, 0.98), sat((v.y + 0.05) * 2.2)) * 4.2;
    vec3 col = sky;
    float hill = -0.02 + 0.025 * sin(v.x * 9.0 + 1.0) + 0.012 * sin(v.x * 23.0);
    col = mix(col, vec3(0.5, 0.62, 0.42) * 2.4, smoothstep(hill + 0.004, hill - 0.004, v.y));
    // the blossom tree just outside
    vec2 b = at(A_ZB + 2.2);
    float br = 1e3;
    br = min(br, sdCapsule(b, vec2(-3.4, 0.6), vec2(-1.9, 2.4), 0.07));
    br = min(br, sdCapsule(b, vec2(-1.9, 2.4), vec2(-0.9, 3.1), 0.05));
    br = min(br, sdCapsule(b, vec2(-1.9, 2.4), vec2(-1.4, 3.6), 0.035));
    br = min(br, sdCapsule(b, vec2(-2.4, 1.8), vec2(-1.2, 1.9), 0.03));
    br = min(br, sdCapsule(b, vec2(-1.2, 1.9), vec2(-0.6, 2.3), 0.02));
    br = min(br, sdCapsule(b, vec2(-0.9, 3.1), vec2(-0.2, 3.0), 0.022));
    br += 0.012 * vnoise(b * 30.0);
    float bl = fbm(b * 4.5 + 2.0);
    float near = exp(-max(br, 0.0) * 3.2);
    float bloss = smoothstep(0.5, 0.62, bl * 0.75 + near * 0.45) * smoothstep(1.2, 2.0, b.y);
    vec3 pink = mix(vec3(1.0, 0.72, 0.8), vec3(1.0, 0.92, 0.94), vnoise(b * 40.0)) * 3.4;
    col = mix(col, vec3(0.16, 0.11, 0.1), aaw(br, 0.01));
    col = mix(col, pink * (0.75 + 0.25 * vnoise(b * 12.0)), bloss);
    // falling petals
    vec2 pq = b * 9.0 + vec2(T * 0.25, T * 0.4);
    vec2 id = floor(pq);
    vec2 f = fract(pq) - 0.5 - (hash22(id) - 0.5) * 0.6;
    col = mix(col, pink, step(0.86, hash21(id)) * smoothstep(0.09, 0.03, length(f)));
    return col;
}

// the gentleman in the portrait (painting coordinates: oval radii ~ (1, 1)), painted in the
// manner of a society portrait: warm key light from the upper left, a dark ground
vec3 aPainting(vec2 u, float glowLvl) {
    u += (vec2(vnoise(u * 18.0), vnoise(u * 18.0 + 7.0)) - 0.5) * 0.025;     // brushwork
    vec3 c = mix(vec3(0.05, 0.04, 0.03), vec3(0.24, 0.17, 0.09), smoothstep(0.9, -0.5, length(u - vec2(-0.35, 0.3))));
    c *= 0.82 + 0.25 * fbm(u * 3.5 + 2.0);
    float key = smoothstep(0.45, -0.35, u.x + 0.15 * u.y);                 // light falls from the left
    // dark suit: shoulders, lapels opening on a white shirt and a deep blue tie
    float coat = sdEllipse(u - vec2(0.0, -1.08), vec2(0.86, 0.6));
    vec3 coatC = vec3(0.035, 0.035, 0.045) + vec3(0.13, 0.11, 0.1) * key * smoothstep(-0.2, -0.6, u.y + 0.1 * u.x);
    c = mix(c, coatC, aaw(coat, 0.02));
    float vee = sdTrap(vec2(u.x, -(u.y + 0.62)), 0.0, 0.2, 0.16);
    c = mix(c, vec3(0.75, 0.72, 0.66) * (0.6 + 0.4 * key), aaw(vee, 0.025) * step(u.y, -0.44));
    float tie = sdTrap(vec2(u.x, -(u.y + 0.66)), 0.035, 0.055, 0.13);
    c = mix(c, vec3(0.08, 0.1, 0.22) * (0.7 + 0.5 * key), aaw(tie, 0.022) * step(u.y, -0.5));
    float lapel = min(sdSeg(u, vec2(-0.2, -0.47), vec2(-0.05, -0.8)), sdSeg(u, vec2(0.2, -0.47), vec2(0.05, -0.8))) - 0.012;
    c = mix(c, vec3(0.015), aaw(lapel, 0.022) * 0.7);
    // neck and an oval face narrowing to the chin
    float neck = sdBox(u - vec2(0.0, -0.36), vec2(0.105, 0.13));
    float head = sdEllipse(u - vec2(0.0, 0.06), vec2(0.25, 0.34));
    head = smin(head, sdEllipse(u - vec2(0.0, -0.13), vec2(0.17, 0.17)), 0.08);
    float ears = min(sdEllipse(u - vec2(-0.25, 0.04), vec2(0.04, 0.07)), sdEllipse(u - vec2(0.25, 0.04), vec2(0.04, 0.07)));
    float skin = min(min(neck, head), ears);
    vec3 skinC = vec3(0.8, 0.55, 0.4) * (0.22 + 0.78 * key);
    skinC *= 1.0 - 0.45 * smoothstep(-0.18, -0.3, u.y) * step(-0.46, u.y) * step(neck, head);   // under the jaw
    c = mix(c, skinC, aaw(skin, 0.025));
    // dark hair, combed back from a side parting on his right (our left)
    float hairMass = sdEllipse(u - vec2(0.01, 0.22), vec2(0.28, 0.25));
    float line = u.y - (0.2 + 0.07 * smoothstep(-0.2, 0.25, u.x) - 0.02 * u.x);    // hairline over the brow
    float hair = max(hairMass, -line);
    hair = max(hair, -(u.y + 0.02 - 0.5 * abs(u.x + 0.0)));                        // clears the temples
    vec3 hairC = vec3(0.045, 0.032, 0.022) + vec3(0.2, 0.14, 0.08) * key * smoothstep(0.35, 0.45, u.y) * 0.8;
    hairC += vec3(0.25, 0.18, 0.1) * 0.25 * smoothstep(0.012, 0.0, abs(u.x + 0.11 - 0.25 * (u.y - 0.3))) * step(0.28, u.y);
    c = mix(c, hairC, aaw(hair, 0.025));
    // features: brows, eyes in soft shadow, the nose lit on one side, a gentle mouth
    vec2 a = vec2(abs(u.x), u.y);
    float brow = sdCapsule(a, vec2(0.05, 0.12), vec2(0.15, 0.125), 0.016);
    float eye = sdEllipse(a - vec2(0.095, 0.06), vec2(0.045, 0.018));
    c = mix(c, skinC * 0.55, smoothstep(0.06, 0.0, length((a - vec2(0.095, 0.075)) * vec2(1.0, 1.6))) * 0.6);
    c = mix(c, vec3(0.07, 0.05, 0.04), aaw(brow, 0.022) * 0.85);
    c = mix(c, vec3(0.1, 0.07, 0.06), aaw(eye, 0.02) * 0.85);
    c += vec3(0.5, 0.45, 0.4) * 0.25 * aaw(length(u - vec2(-0.085, 0.064)) - 0.008, 0.006);
    float nose = sdCapsule(u, vec2(0.0, 0.08), vec2(0.015, -0.05), 0.022);
    c = mix(c, skinC * 0.62, aaw(nose - 0.004, 0.022) * smoothstep(-0.01, 0.03, u.x) * 0.7);
    c = mix(c, skinC * 1.15, aaw(sdCapsule(u, vec2(-0.012, 0.07), vec2(-0.004, -0.03), 0.008), 0.02) * 0.6);
    float mouth = sdArc(u, vec2(0.0, -0.06), 0.085, -2.15, -0.99, 0.01);
    c = mix(c, vec3(0.38, 0.17, 0.13) * (0.5 + 0.5 * key), aaw(mouth, 0.02) * 0.85);
    c = mix(c, skinC * 0.7, aaw(sdEllipse(u - vec2(0.0, -0.205), vec2(0.06, 0.02)), 0.02) * 0.4);
    // varnish and the warm glow of remembrance
    c *= 0.9 + 0.12 * vnoise(u * 60.0);
    return c * (0.5 + 1.35 * glowLvl);
}

vec3 aWall(vec3 p, int s, float fw) {
    // s: 0 back wall (u = x), 3/4 side walls (u = z)
    vec2 uv = s == 0 ? p.xy : vec2(p.z, p.y);
    vec3 c = plaster(uv * 1.3, vec3(0.62, 0.5, 0.36));
    // soft regency stripes above the dado
    float st = 0.5 + 0.5 * sin(uv.x * 9.0);
    c *= 0.94 + 0.08 * smoothstep(0.3, 0.7, st);
    // dado panelling below 0.95 m, rail, skirting and cornice
    if (p.y < 0.95) {
        vec3 wood = vec3(0.32, 0.2, 0.11) * (0.8 + 0.3 * vnoise(vec2(uv.x * 30.0, uv.y * 3.0)));
        float pan = sdRBox(vec2(fract(uv.x / 0.9) - 0.5, p.y - 0.5) * vec2(0.9, 1.0), vec2(0.36, 0.3), 0.02);
        wood *= 1.0 - 0.35 * smoothstep(0.015 + fw, 0.0, abs(pan));
        c = wood;
    }
    c *= 1.0 - 0.5 * band01(p.y, 0.93, 0.98, fw);
    c = mix(c, vec3(0.22, 0.14, 0.08), band01(p.y, 0.0, 0.14, fw));
    c *= 1.0 - 0.3 * band01(p.y, A_HC - 0.25, A_HC, fw);
    return c;
}

vec3 aDrape(vec2 w, out float a) {
    // heavy dusty-rose drapes either side of the window, tied back at 1.1 m
    float side = sign(w.x - A_WIN.x);
    float edge = A_WIN.x + side * (A_WIN.z - 0.05);
    float pinch = 0.12 + 0.3 * smoothstep(1.15, 2.2, w.y) + 0.22 * smoothstep(1.0, 0.1, w.y);
    float x = (w.x - edge) * side;     // positive outwards
    float d = max(max(-x - pinch * 0.55, x - 0.42), max(-w.y, w.y - 3.2));
    a = aaw(d, 0.006);
    float folds = 0.6 + 0.4 * sin(x * 38.0 + sin(w.y * 1.5) * 1.5);
    vec3 c = vec3(0.36, 0.13, 0.12) * folds * (0.85 + 0.2 * fbm(w * 3.0));
    float tie = band01(w.y, 1.06, 1.14, 0.01) * step(-0.2, x);
    c = mix(c, vec3(0.6, 0.45, 0.2), tie);
    return c;
}

vec3 room0() {
    Hit h = roomHit(A_ZB, A_XL, A_XR, A_HC, vec4(0.0), A_ZB);
    vec3 p = h.p;
    float fw = PX * p.z * 1.2;
    vec3 col;
    float sunOnWall = 0.0;
    if (h.s == 0) {
        vec2 w = p.xy;
        vec2 l = w - A_WIN.xy;
        float win = sdBox(l, A_WIN.zw);
        vec3 wall = aWall(p, 0, fw);
        vec3 L = aAmbient(p) + aPortraitLight(p);
        // the portrait's own warm halo on the wall
        float pr = length((w - A_POR.xy) / A_POR.zw);
        L += vec3(1.0, 0.7, 0.4) * uP[4].z * 0.22 * exp(-max(pr - 1.0, 0.0) * 1.6);
        col = wall * L;
        // window reveal and outside view
        float reveal = sdBox(l, A_WIN.zw + 0.07);
        col = mix(col, vec3(0.75, 0.68, 0.56) * (aAmbient(p) * 1.6 + vec3(0.45, 0.38, 0.28)), aaw(reveal, fw));
        if (win < 0.01) {
            vec3 o = aOutside(w);
            float glaze = aGlazing(l, fw);
            vec3 frame = vec3(0.82, 0.78, 0.7) * 0.9;
            o = mix(frame, o, glaze);
            float cur = aCurtainMask(l, fw * 2.0);
            float th = laceThreads(w);
            vec3 laceC = vec3(1.0, 0.95, 0.86) * (1.1 + 1.8 * th) * (0.9 + 0.1 * sin(l.x * 60.0));
            vec3 through = o * (1.0 - 0.75 * th);
            o = mix(o, through * 0.55 + laceC * 0.5, cur);
            col = mix(col, o, aaw(win, fw));
        }
        // the portrait: an oval gilt frame
        float fr = (pr - 1.0) * min(A_POR.z, A_POR.w);
        float frame = abs(fr - 0.05) - 0.055;
        vec3 shadowed = col * (1.0 - 0.5 * aaw(length((w - A_POR.xy - vec2(0.05, -0.07)) / (A_POR.zw + 0.1)) - 1.0, 0.08));
        col = shadowed;
        vec3 paint = aPainting((w - A_POR.xy) / A_POR.zw * vec2(1.0, 1.0), uP[4].z);
        paint = paint * (L * 1.6 + vec3(0.1));
        col = mix(col, paint, aaw(fr, fw));
        vec3 gold = giltCol(w, 0.0) * (L * 2.2 + vec3(0.12, 0.08, 0.03) + vec3(1.0, 0.7, 0.35) * uP[4].z * 0.5);
        gold *= 0.75 + 0.5 * smoothstep(0.0, 0.06, abs(fr - 0.05) + 0.02) * sat(dot(normalize(w - A_POR.xy), vec2(-0.6, 0.8)) + 0.6);
        col = mix(col, gold, aaw(frame, fw));
        // the little brass picture lamp
        vec2 lq = w - vec2(A_POR.x, A_POR.y + A_POR.w + 0.12);
        float lamp = sdRBox(lq, vec2(0.16, 0.022), 0.02);
        col = mix(col, vec3(0.5, 0.36, 0.15) * (L + 0.05) + vec3(1.0, 0.8, 0.5) * uP[4].z * 1.5 * smoothstep(0.02, -0.02, lq.y), aaw(lamp, fw));
        // a panelled double door on the right
        vec2 dq = w - vec2(2.35, 1.22);
        float door = sdBox(dq, vec2(0.58, 1.22));
        if (door < 0.08) {
            vec3 casing = vec3(0.5, 0.4, 0.28) * L * 1.1;
            col = mix(col, casing, aaw(door - 0.07, fw));
            vec2 pq = vec2(abs(dq.x) - 0.27, dq.y);
            pq.y = (abs(pq.y - 0.35) < 0.5) ? pq.y - 0.35 : pq.y + 0.6;
            float panels = sdRBox(vec2(pq.x, pq.y), vec2(0.18, 0.42), 0.02);
            vec3 wood = vec3(0.24, 0.15, 0.08) * (0.8 + 0.3 * vnoise(dq * vec2(4.0, 30.0)));
            wood *= 1.0 - 0.3 * smoothstep(0.015, 0.0, abs(panels)) - 0.5 * smoothstep(0.01, 0.0, abs(dq.x));
            vec3 dc2 = wood * L * 1.2;
            dc2 += vec3(0.9, 0.7, 0.35) * 0.4 * smoothstep(0.03, 0.0, length(dq - vec2(-0.08, -0.15)));
            col = mix(col, dc2, aaw(door, fw));
        }
        // drapes beside the window
        float da;
        vec3 dc = aDrape(w, da);
        float rimD = smoothstep(0.25, 0.0, abs(abs(w.x - A_WIN.x) - A_WIN.z)) * 0.6;
        col = mix(col, dc * (aAmbient(p) * 1.3 + vec3(0.25, 0.17, 0.1) * rimD), da);
        // pelmet
        float pel = sdBox(w - vec2(A_WIN.x, A_WIN.y + A_WIN.w + 0.2), vec2(A_WIN.z + 0.5, 0.1));
        col = mix(col, vec3(0.3, 0.1, 0.09) * aAmbient(p) * 1.2, aaw(pel, fw));
    } else if (h.s == 1) {
        vec3 base = boards(p.xz, vec3(0.42, 0.27, 0.15), 0.16, fw);
        // the rug
        vec2 rq = p.xz - vec2(0.1, 3.7);
        float rug = sdBox(rq, vec2(1.9, 1.15));
        if (rug < 0.02) {
            vec2 rr = abs(rq);
            float border = smoothstep(1.6, 1.62, rr.x) + smoothstep(0.88, 0.9, rr.y);
            float med = length(rq * vec2(0.6, 1.0));
            float motif = 0.5 + 0.5 * sin(med * 7.0 - 1.0) * (0.6 + 0.4 * sin(atan(rq.y, rq.x) * 8.0));
            vec3 rc = mix(vec3(0.34, 0.1, 0.08), vec3(0.42, 0.24, 0.12), smoothstep(0.2, 0.9, motif) * 0.6);
            rc = mix(rc, vec3(0.16, 0.12, 0.2), min(border, 1.0) * 0.7);
            rc *= 0.8 + 0.3 * vnoise(p.xz * 25.0);
            base = mix(base, rc, aaw(rug, fw));
        }
        float sun = aSunLit(p) * sat(-A_SUN.y);
        sun *= 1.0 - 0.85 * castDir(p, A_SUN, 0.02);
        col = base * (aAmbient(p) + A_SUNC * sun + aPortraitLight(p) * 0.4);
        sunOnWall = sun;
    } else if (h.s == 2) {
        col = plaster(p.xz, vec3(0.5, 0.42, 0.32)) * aAmbient(p) * 0.75;
    } else {
        vec3 L = aAmbient(p) + aPortraitLight(p) * 0.3;
        col = aWall(p, h.s, fw) * L;
        vec2 u = vec2(p.z, p.y);
        if (h.s == 3) {
            // a tall gilt pier mirror holding a blur of the bright window
            vec2 mq = u - vec2(4.15, 1.75);
            float mr = sdBox(mq, vec2(0.42, 0.68));
            vec3 refl = vec3(0.07, 0.055, 0.04) + vec3(1.0, 0.85, 0.6) * 0.22 * exp(-pow((mq.x + 0.1) * 6.0, 2.0) - pow(mq.y * 1.2, 2.0));
            refl += vec3(0.6, 0.55, 0.45) * 0.08 * smoothstep(0.03, 0.0, abs(mq.x - 0.2 + mq.y * 0.3));
            refl *= 0.85 + 0.15 * vnoise(mq * 30.0);
            col = mix(col, giltCol(u, 0.0) * (L * 2.0 + 0.05), aaw(mr - 0.07, fw));
            col = mix(col, refl, aaw(mr, fw));
        } else {
            // two small framed prints
            for (int k = 0; k < 2; k++) {
                vec2 fq = u - vec2(3.75 + 0.85 * float(k), 1.72 + 0.08 * float(k));
                float fr = sdBox(fq, vec2(0.22, 0.28));
                vec3 prn = mix(vec3(0.5, 0.42, 0.3), vec3(0.2, 0.15, 0.1), smoothstep(0.1, -0.1, fq.y + 0.05 * sin(fq.x * 20.0))) * L * 1.4;
                col = mix(col, vec3(0.05, 0.035, 0.025), aaw(fr - 0.035, fw));
                col = mix(col, prn, aaw(fr, fw));
            }
            col += aWall(p, h.s, fw) * vec3(0.14, 0.1, 0.06) * smoothstep(4.5, 2.5, p.z);
        }
    }
    // corners
    col *= 0.55 + 0.45 * smoothstep(0.0, 0.7, cornerDist(h, A_ZB, A_XL, A_XR, A_HC));

    // ---- light in the air, in three depth bands
    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.8, zbb = min(p.z, A_ZB);
        float dz = (zbb - za) / 22.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        vec3 rdn = normalize(RD);
        float ph = 0.35 + 1.4 * pow(sat(dot(-rdn, A_SUN)), 6.0);
        for (int i = 0; i < 22; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            float s = aSunLit(q);
            vec3 c = A_SUNC * s * ph * hazeDen(q) * 0.16;
            c += aPortraitLight(q) * 0.25 + aAmbient(q) * 0.012;
            c *= dz * RDL;
            if (z > 4.6) vF += c; else if (z > Z0) vM += c; else vN += c * 0.45;
        }
    }
    col += vF;

    // ---- flats behind the figure plane: sideboard under the portrait, table with blossom, chair
    {
        // sideboard against the back wall
        float z = A_ZB - 0.28;
        vec2 w = at(z);
        vec2 l = w - vec2(A_POR.x, 0.0);
        float d = sdBox(l - vec2(0.0, 0.46), vec2(0.78, 0.46));
        d = min(d, sdBox(l - vec2(0.0, 0.95), vec2(0.84, 0.035)));
        float cl = min(sdBox(l - vec2(0.45, 1.13), vec2(0.07, 0.15)), sdCircle(l - vec2(0.45, 1.22), 0.08));   // a mantel clock
        d = min(d, cl);
        float cs = min(sdCapsule(l, vec2(-0.5, 0.98), vec2(-0.5, 1.3), 0.012), sdBox(l - vec2(-0.5, 1.0), vec2(0.05, 0.02)));
        d = min(d, cs);
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 L = aAmbient(q3) + aPortraitLight(q3) * 1.5;
            vec3 c = vec3(0.16, 0.09, 0.05) * (0.8 + 0.3 * vnoise(l * vec2(20.0, 3.0)));
            float doors = abs(fract(l.x / 0.52 + 0.5) - 0.5) * 0.52;
            c *= 1.0 - 0.4 * smoothstep(0.012, 0.0, doors) * step(l.y, 0.85);
            c = c * L * 1.3;
            c += vec3(0.9, 0.62, 0.3) * 0.05 * smoothstep(0.03, 0.0, abs(l.y - 0.98));
            col = lay(col, c, a);
        }
    }
    {
        // round table with a lace cloth, a vase of blossom; nothing else on it
        float z = 4.25;
        vec2 w = at(z);
        vec2 l = w - vec2(-0.85, 0.0);
        float hem = 0.04 * sin(l.x * 26.0) + 0.02 * sin(l.x * 61.0);
        float cloth = max(sdTrap(l - vec2(0.0, 0.42), 0.56, 0.47, 0.36), 0.03 + hem - l.y);
        float top = sdRBox(l - vec2(0.0, 0.775), vec2(0.5, 0.02), 0.01);
        float vase = sdEllipse(l - vec2(0.05, 0.9), vec2(0.075, 0.11));
        vase = smin(vase, sdBox(l - vec2(0.05, 1.03), vec2(0.03, 0.05)), 0.03);
        float br = 1e3;
        br = min(br, sdCapsule(l, vec2(0.05, 1.05), vec2(-0.18, 1.55), 0.008));
        br = min(br, sdCapsule(l, vec2(0.05, 1.05), vec2(0.2, 1.62), 0.008));
        br = min(br, sdCapsule(l, vec2(0.06, 1.05), vec2(0.05, 1.7), 0.008));
        br = min(br, sdCapsule(l, vec2(0.14, 1.36), vec2(0.34, 1.48), 0.006));
        // clusters of small blossoms along the twigs
        vec2 bq = l * 46.0;
        vec2 bid = floor(bq);
        vec2 bf = fract(bq) - 0.5 - (hash22(bid) - 0.5) * 0.5;
        float near = exp(-max(br, 0.0) * 34.0);
        float blo = smoothstep(0.42, 0.18, length(bf)) * step(1.0 - near * 1.1, hash21(bid + 3.0));
        blo *= smoothstep(1.18, 1.3, l.y);
        float d = min(min(cloth, top), vase);
        float a = aaw(d, PX * z);
        float ab = max(aaw(br, PX * z), blo);
        if (a > 0.0 || ab > 0.0) {
            vec3 q3 = vec3(w, z);
            float sun = aSunLit(q3);
            vec3 L = aAmbient(q3) * 1.1;
            vec3 clothC = vec3(0.8, 0.76, 0.68) * (0.75 + 0.25 * laceThreads(l * 0.8 + 3.0));
            vec3 c = clothC * (L + A_SUNC * sun * 0.35);
            vec3 vaseC = vec3(0.3, 0.38, 0.45) * (L + A_SUNC * sun * 0.5);
            vaseC += vec3(1.0, 0.95, 0.85) * 1.5 * smoothstep(0.03, 0.0, length(l - vec2(0.02, 0.93))) ;
            c = mix(c, vaseC, step(vase, min(cloth, top)));
            col = lay(col, c, a);
            vec3 pinkC = vec3(1.0, 0.48, 0.58) * (L * 1.2 + A_SUNC * sun * 0.08);
            vec3 brC = vec3(0.12, 0.08, 0.07) * L;
            col = lay(col, mix(brC, pinkC, blo), ab);
        }
    }
    {
        // a side chair in profile by the table
        float z = 4.0;
        vec2 w = at(z);
        vec2 l = w - vec2(-0.1, 0.0);
        float d = sdCapsule(l, vec2(0.0, 0.0), vec2(-0.04, 0.98), 0.02);
        d = min(d, sdBox(l - vec2(0.2, 0.46), vec2(0.22, 0.025)));
        d = min(d, sdCapsule(l, vec2(0.4, 0.0), vec2(0.4, 0.45), 0.017));
        d = min(d, sdBox(l - vec2(-0.025, 0.8), vec2(0.03, 0.14)));
        d = min(d, sdCapsule(l, vec2(0.0, 0.16), vec2(0.4, 0.16), 0.008));
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 c = vec3(0.14, 0.08, 0.045) * (aAmbient(q3) * 1.2 + A_SUNC * aSunLit(q3) * 0.3);
            col = lay(col, c, a);
        }
    }
    col += vM;

    // ---- the figures
    {
        vec2 winS = toScreen(vec3(A_WIN.xy, A_ZB));
        for (int i = 1; i >= 0; i--) {
            vec2 L1 = winS - CP[i].xy - vec2(0.0, CP[i].z * 0.7);
            vec3 c3 = vec3(CP[i].x * Z0, CAMY + (CP[i].y + CP[i].z * 0.75) * CZ[i], CZ[i]);
            float sun = aSunLit(c3);
            vec2 porS = toScreen(vec3(A_POR.xy, A_ZB));
            col = seatBehind(i, col, aAmbient(c3) * 1.2 + A_SUNC * sun * 0.15);
            WRAP = sat(sun * 1.5) * 0.8;
            vec4 f = actor(i, L1, 0.7 + 1.1 * sun, vec3(0.5, 0.46, 0.42), vec3(1.0, 0.7, 0.4) * uP[4].z * 0.25, porS);
            WRAP = 0.0;
            col = over(col, f);
        }
    }
    col += vN;

    // ---- foreground: a potted palm at the right edge, dark against the room
    {
        float z = 2.0;
        vec2 w = at(z);
        vec2 l = w - vec2(1.75, 0.0);
        float soft = PX * z * 3.0;                 // close to the lens: slightly out of focus
        float d = sdTrap(l - vec2(0.0, 0.5), 0.11, 0.15, 0.09);                 // the jardiniere
        d = min(d, sdTrap(l - vec2(0.0, 0.2), 0.12, 0.04, 0.22));               // its stand
        float m = aaw(d, soft);
        float vein = 0.0;
        for (int k = 0; k < 7; k++) {
            float fk = float(k);
            float ang = -1.05 + fk * 0.33 + 0.05 * sin(fk * 2.7) + 0.03 * sin(T * 0.5 + fk * 1.3);
            vec2 dir = vec2(sin(ang), cos(ang));
            vec2 lq = l - vec2(0.02 * (fk - 3.0), 0.58);
            float len = 0.78 + 0.18 * hash11(fk * 3.7);
            float u = dot(lq, dir);
            vec2 lq2 = lq + vec2(0.0, 0.42 * max(u, 0.0) * max(u, 0.0) * sign(ang + 0.001) * sign(ang + 0.001));
            u = dot(lq2, dir);
            float vv = dot(lq2, vec2(-dir.y, dir.x));
            float uu = u / len;
            if (uu < 0.0 || uu > 1.0) continue;
            float wdt = 0.085 * pow(sin(PI * sat((uu - 0.22) / 0.78)), 0.8) * step(0.22, uu) + 0.008;
            float leaf = aaw(abs(vv) - wdt, soft);
            m = max(m, leaf);
            vein = max(vein, leaf * smoothstep(0.9, 0.2, abs(vv) / wdt) * step(0.25, uu));
        }
        if (m > 0.0) {
            vec3 c = vec3(0.02, 0.026, 0.016) + vec3(0.12, 0.13, 0.05) * vein * 0.35;
            col = lay(col, c, m * 0.97);
        }
    }
    // dust in the sunlight
    float beamNear = lum(vN + vM) * 4.0;
    col += vec3(1.0, 0.9, 0.7) * dust(SP, T, 0.18, 0.05) * sat(beamNear) * 0.9;
    return col;
}

// =============================================================================================
// shared set pieces
// =============================================================================================
// a chair in profile, facing +x when f = 1 (local metres, origin on the floor under the seat)
float chairSD(vec2 l, float f) {
    l.x *= f;
    float d = sdCapsule(l, vec2(-0.2, 0.0), vec2(-0.24, 0.96), 0.019);          // back leg and post
    d = min(d, sdBox(l - vec2(0.0, 0.455), vec2(0.215, 0.022)));                 // seat
    d = min(d, sdCapsule(l, vec2(0.19, 0.0), vec2(0.19, 0.44), 0.016));          // front leg
    d = min(d, sdBox(l - vec2(-0.225, 0.78), vec2(0.028, 0.16)));                // back splat
    d = min(d, sdCapsule(l, vec2(-0.2, 0.16), vec2(0.19, 0.16), 0.008));         // stretcher
    d = min(d, sdCapsule(l, vec2(-0.25, 0.95), vec2(-0.2, 0.97), 0.022));        // top rail
    return d;
}
// Tommaso's little armchair, seen from the front (local metres, origin on the floor)
float smallChairSD(vec2 l) {
    vec2 a = vec2(abs(l.x), l.y);
    float d = sdBox(a - vec2(0.24, 0.43), vec2(0.022, 0.43));                    // back posts
    d = min(d, sdBox(l - vec2(0.0, 0.83), vec2(0.25, 0.04)));                   // top rail
    d = min(d, sdBox(l - vec2(0.0, 0.62), vec2(0.25, 0.015)));                  // middle rail
    d = min(d, sdBox(a - vec2(0.205, 0.2), vec2(0.018, 0.2)));                   // front legs
    d = min(d, sdRBox(l - vec2(0.0, 0.405), vec2(0.25, 0.028), 0.01));          // seat
    d = min(d, sdRBox(a - vec2(0.26, 0.58), vec2(0.035, 0.018), 0.01));          // arm rests
    d = min(d, sdBox(a - vec2(0.262, 0.5), vec2(0.012, 0.08)));                  // arm supports
    return d;
}
// thin luminous outline of a shape (for the remembered things of mode 6)
float outline(float d, float w) { return exp(-abs(d) / w); }

// sky and sea seen through a Trieste window, by direction. tod: 0 morning, 1 dawn, 2 dusk, 3 night
vec3 seaView(vec2 v, int tod, float sparkle) {
    vec3 skyLo, skyHi, sea, coast;
    if (tod == 0) { skyLo = vec3(1.0, 0.84, 0.62) * 2.4; skyHi = vec3(0.3, 0.52, 1.0) * 1.5; sea = vec3(0.1, 0.3, 0.55) * 1.5; coast = vec3(0.5, 0.55, 0.75) * 1.5; }
    else if (tod == 1) { skyLo = vec3(0.62, 0.6, 0.66) * 1.0; skyHi = vec3(0.3, 0.38, 0.52) * 0.9; sea = vec3(0.1, 0.14, 0.2) * 0.8; coast = vec3(0.24, 0.27, 0.34) * 0.8; }
    else if (tod == 2) { skyLo = vec3(1.0, 0.45, 0.22) * 1.7; skyHi = vec3(0.12, 0.13, 0.32) * 1.0; sea = vec3(0.05, 0.06, 0.13) * 1.0; coast = vec3(0.07, 0.06, 0.12) * 1.0; }
    else { skyLo = vec3(0.1, 0.13, 0.25) * 0.8; skyHi = vec3(0.03, 0.05, 0.12) * 0.8; sea = vec3(0.02, 0.03, 0.07); coast = vec3(0.02, 0.02, 0.04); }
    float hz = 0.0;
    vec3 col;
    if (v.y > hz) {
        float k = sat(v.y / (tod == 0 ? 0.22 : 0.35));
        col = mix(skyLo, skyHi, pow(k, 0.6));
        float cl = fbm(vec2(v.x * 3.0 + T * 0.004, v.y * 9.0));
        col *= 0.92 + 0.16 * cl;
        if (tod == 2) col += vec3(1.0, 0.55, 0.3) * 0.6 * exp(-v.y * 30.0);
        // the far coast: a soft blue band of hills along part of the horizon
        float ch = 0.012 + 0.008 * sin(v.x * 14.0 + 1.3) + 0.004 * sin(v.x * 41.0);
        ch *= smoothstep(-0.05, 0.25, v.x);
        col = mix(col, coast, smoothstep(ch + 0.002, ch - 0.002, v.y - hz));
        if (tod >= 2) {    // lights along the far coast
            vec2 g = vec2(v.x * 160.0, 0.0);
            float id = floor(g.x);
            float on = step(0.72, hash11(id * 3.1)) * smoothstep(-0.05, 0.25, v.x);
            float lt = smoothstep(0.35, 0.0, length(vec2(fract(g.x) - 0.5, (v.y - hz - 0.004) * 160.0)));
            col += vec3(1.0, 0.75, 0.45) * on * lt * (2.0 + sin(T * 3.0 + id)) * (tod == 3 ? 0.6 : 1.0);
        }
    } else {
        float dep = 1.0 / max(hz - v.y, 0.002);          // distance proxy
        vec2 w = vec2(v.x * dep, dep);
        float wv = vnoise(w * vec2(2.5, 0.8) + vec2(T * 0.15, T * 0.3)) * 0.6 + vnoise(w * vec2(6.0, 2.0) - T * 0.25) * 0.4;
        col = sea * (0.75 + 0.5 * wv);
        col = mix(col, skyLo * 0.35, exp(-(hz - v.y) * 40.0) * 0.6);          // haze at the horizon
        // the glitter path under the sun (upper left) or the afterglow
        float path = exp(-pow((v.x + 0.12 + 0.6 * (hz - v.y)) * 5.0, 2.0));
        if (tod == 0) {
            vec2 g = w * vec2(9.0, 2.5);
            vec2 id = floor(g);
            vec2 f = fract(g) - 0.5;
            float tw = pow(0.5 + 0.5 * sin(T * (4.0 + 6.0 * hash21(id)) + hash21(id + 9.0) * 6.28), 8.0);
            float sp = step(0.7, hash21(id + 1.7)) * tw * smoothstep(0.25, 0.0, length(f));
            col += vec3(1.0, 0.92, 0.75) * (path * 2.5 + 0.3) * (sp * 9.0 * (0.3 + sparkle) + path * 0.7 * wv);
        } else if (tod == 2) {
            col += vec3(1.0, 0.5, 0.25) * 0.35 * path * wv;
        } else if (tod == 1) {
            col += vec3(0.7, 0.68, 0.72) * 0.15 * exp(-(hz - v.y) * 25.0) * wv;
        }
    }
    return col;
}

// night sky over the roofs (direction v), with clouds racing in the bora when wind > 0
vec3 nightSky(vec2 v, float wind) {
    vec3 col = mix(vec3(0.07, 0.1, 0.22), vec3(0.015, 0.025, 0.07), sat(v.y * 2.0 + 0.2)) * 1.4;
    vec2 cq = vec2(v.x * 2.0 - T * 0.04 * (1.0 + 6.0 * wind), v.y * 5.0);
    float cl = fbm(cq);
    col = mix(col, vec3(0.16, 0.2, 0.32) * 1.4, smoothstep(0.5, 0.75, cl) * 0.8);
    col += vec3(0.3, 0.38, 0.6) * 0.5 * exp(-length(v - vec2(0.5, 0.6)) * 3.0);   // moon glow
    vec2 sg = v * 140.0;
    vec2 sid = floor(sg);
    col += vec3(0.8, 0.85, 1.0) * step(0.985, hash21(sid)) * smoothstep(0.3, 0.0, length(fract(sg) - 0.5)) * (1.0 - smoothstep(0.5, 0.7, cl)) * 1.5;
    return col;
}

// =============================================================================================
// MODE 1: the Verona house, autumn 1953, night. A very tall, cold, gilded room; two arched
// windows pour moonlight; Tommaso glows in his cradle; Vittorio's shadow arrives from the door.
// =============================================================================================
const float B_ZB = 7.5, B_XL = -4.2, B_XR = 4.2, B_HC = 9.0;
const vec3 B_MOONC = vec3(0.5, 0.66, 1.0) * 2.8;
const float B_WHW = 0.62, B_WSP = 3.0;          // arched windows: half width, spring line above the sill
const float B_WY = 0.95;                        // sill height
vec3 B_MOON;
vec3 B_S;          // the corridor lamp behind the off-screen door
vec3 B_V;          // Vittorio's feet, in the doorway
float B_OPEN, B_DOOR, B_VI, B_COLD;
const vec3 B_CR = vec3(0.45, 0.0, 3.1);        // the cradle (x, floor, depth)

float bWinSD(vec2 w, float cx) {
    vec2 l = w - vec2(cx, B_WY);
    float rect = sdBox(l - vec2(0.0, B_WSP * 0.5), vec2(B_WHW, B_WSP * 0.5));
    return min(rect, sdCircle(l - vec2(0.0, B_WSP), B_WHW));
}
float bGlazing(vec2 l, float b) {          // l from the sill centre; 1 = glass
    float bars = abs(l.x) - 0.028;
    bars = min(bars, abs(l.y - 0.85) - 0.018);
    bars = min(bars, abs(l.y - 1.7) - 0.018);
    bars = min(bars, abs(l.y - 2.5) - 0.018);
    if (l.y > B_WSP) {
        vec2 a = l - vec2(0.0, B_WSP);
        float ang = atan(a.y, a.x);
        float seg = PI / 4.0;
        float rad = abs(fract(ang / seg + 0.5) - 0.5) * seg * length(a) - 0.016;
        bars = min(bars, min(rad, abs(length(a) - 0.34) - 0.016));
    }
    return smoothstep(-b, b, bars);
}
float bAperture(vec2 w, float s) {
    float b = 0.008 + 0.028 * s;
    float cx = w.x < 0.0 ? -1.6 : 1.6;
    float o = 1.0 - smoothstep(-b, b, bWinSD(w, cx));
    if (o <= 0.001) return 0.0;
    return o * bGlazing(w - vec2(cx, B_WY), b);
}
float bMoonLit(vec3 p) {
    float s = (p.z - B_ZB) / B_MOON.z;
    if (s <= 0.0) return 0.0;
    return bAperture(p.xy - B_MOON.xy * s, s);
}
// visibility of the corridor lamp through the (off-screen) door in the right wall
float bDoorLit(vec3 p) {
    if (B_DOOR <= 0.0) return 0.0;
    vec3 d = B_S - p;
    if (d.x <= 0.0) return 0.0;
    float u = (B_XR - p.x) / d.x;
    if (u <= 0.0 || u >= 1.0) return 0.0;
    vec3 q = p + d * u;
    float b = 0.03 + 0.25 * (1.0 - u);
    float z0 = 3.15, z1 = 3.15 + 1.85 * B_OPEN;
    return smoothstep(z0 - b, z0 + b, q.z) * (1.0 - smoothstep(z1 - b, z1 + b, q.z)) * (1.0 - smoothstep(3.3 - b, 3.3 + b, q.y));
}
// Vittorio's silhouette between the lamp and p (projective shadow)
float bVShadow(vec3 p) {
    if (B_VI <= 0.0) return 0.0;
    vec3 n = normalize(vec3(B_V.x - B_S.x, 0.0, B_V.z - B_S.z));
    float den = dot(p - B_S, n);
    if (den <= 1e-3) return 0.0;
    float s = dot(B_V - B_S, n) / den;
    if (s <= 0.0 || s >= 1.0) return 0.0;
    vec3 x = B_S + (p - B_S) * s;
    vec3 t = vec3(-n.z, 0.0, n.x);
    vec2 q = vec2(dot(x - B_V, t), x.y - B_V.y) / 1.9;
    if (abs(q.x) > 0.8 || q.y > 1.3 || q.y < -0.2) return 0.0;
    float d = sdFigure(q, vec4(0.18, 0.55 + 0.08 * sin(T * 0.5), 0.0, 0.05 * sin(T * 0.6)), 0.0) * 1.9;
    float pen = 0.006 + 0.012 * (1.0 / s - 1.0);
    return (1.0 - smoothstep(-pen, pen, d)) * B_VI;
}
vec3 bDoorLight(vec3 p) {
    if (B_DOOR <= 0.0 || p.x > B_XR - 0.01) return vec3(0.0);
    vec3 d = B_S - p;
    float lit = bDoorLit(p);
    if (lit <= 0.0) return vec3(0.0);
    lit *= 1.0 - bVShadow(p);
    // a stage lamp: slow falloff so the far wall still takes the light
    return vec3(1.0, 0.68, 0.38) * B_DOOR * lit * 15.0 / (1.0 + 0.07 * dot(d, d));
}
vec3 bGlowLight(vec3 p, float lvl) {
    vec3 d = p - vec3(B_CR.x + 0.02, 0.62, B_CR.z);
    return SILVER * lvl * 0.45 / (0.08 + dot(d, d));
}
vec3 bAmbient(vec3 p) {
    vec3 a = vec3(0.032, 0.04, 0.065);
    a += vec3(0.2, 0.28, 0.5) * 0.14 * (exp(-length(p.xy - vec2(-1.6, 2.4)) * 0.8) + exp(-length(p.xy - vec2(1.6, 2.4)) * 0.8)) * smoothstep(4.0, B_ZB, p.z);
    a += vec3(0.3, 0.4, 0.7) * 0.14 * exp(-p.y * 0.45) * (0.6 + 0.4 * smoothstep(3.0, 7.0, p.z));   // moonlit floor bounce
    return a + home(p);
}
float damask(vec2 uv) {
    vec2 g = uv * vec2(2.4, 1.6);
    vec2 id = floor(g);
    vec2 f = fract(g + vec2(0.0, 0.5 * mod(id.x, 2.0))) - 0.5;
    f.x = abs(f.x);
    float r = length(f * vec2(1.3, 1.0));
    float ang = atan(f.y, f.x);
    float m = smoothstep(0.29, 0.25, r + 0.07 * sin(ang * 5.0 + 1.0)) * smoothstep(0.07, 0.11, r);
    m += smoothstep(0.04, 0.0, abs(r - 0.37 - 0.05 * sin(ang * 3.0))) * 0.5;
    return m;
}
vec3 oldPainting(vec2 u, float seed) {
    vec3 c = mix(vec3(0.05, 0.045, 0.03), vec3(0.17, 0.14, 0.09), smoothstep(-1.0, 1.0, u.y + 0.4 * fbm(u * 2.0 + seed * 5.0)));
    if (fract(seed * 0.5) < 0.25) {
        float head = sdEllipse(u - vec2(0.0, 0.25), vec2(0.17, 0.23));
        float body = sdEllipse(u - vec2(0.0, -0.62), vec2(0.62, 0.56));
        c = mix(c, vec3(0.025, 0.02, 0.018), aaw(body, 0.05));
        c = mix(c, vec3(0.45, 0.32, 0.22), aaw(head, 0.04) * 0.8);
    } else {
        float hz = -0.15 + 0.1 * sin(u.x * 3.0 + seed * 4.0);
        c = mix(c, vec3(0.34, 0.28, 0.18), smoothstep(0.35, -0.1, abs(u.y - 0.25)) * 0.45 * step(hz, u.y));
        c = mix(c, vec3(0.04, 0.05, 0.03), smoothstep(hz + 0.02, hz - 0.02, u.y));
        float tree = fbm(u * 3.0 + seed * 7.0) - 0.42 - 0.3 * (u.x * sign(seed - 1.5) + 0.4);
        c = mix(c, vec3(0.05, 0.06, 0.035), smoothstep(0.0, 0.05, tree) * step(hz - 0.1, u.y));
    }
    return c * (0.85 + 0.2 * vnoise(u * 40.0));
}
// a gilt frame on a wall: returns the colour to lay over 'col'; u = wall coords, c centre, hs half size
vec3 giltFrame(vec3 col, vec2 u, vec2 c, vec2 hs, float seed, vec3 L, float fw, float cold, float glint) {
    vec2 q = u - c;
    float outer = sdBox(q, hs + 0.12);
    if (outer > 0.15) return col;
    col *= 1.0 - 0.45 * aaw(sdBox(q - vec2(0.06, -0.08), hs + 0.14), 0.1);   // drop shadow
    float inner = sdBox(q, hs);
    float prof = sat((inner) / 0.12);
    vec3 g = giltCol(u, cold) * (L * 2.6 + vec3(0.02, 0.018, 0.012));
    g *= 0.55 + 0.65 * (0.5 + 0.5 * sin(prof * 9.0));                      // moulded profile
    g += mix(vec3(1.0, 0.8, 0.45), vec3(0.6, 0.75, 1.0), cold) * glint * pow(0.5 + 0.5 * sin(prof * 9.0 + 1.2), 6.0);
    col = mix(col, g, aaw(outer, fw));
    vec3 pnt = oldPainting(q / hs, seed) * (L * 1.4 + vec3(0.008));
    return mix(col, pnt, aaw(inner, fw));
}

vec3 bWallShade(vec3 p, int s, float fw, float glowLvl) {
    vec2 u = s == 0 ? p.xy : vec2(p.z, p.y);
    float dm = damask(u);
    vec3 base = mix(vec3(0.1, 0.115, 0.13), vec3(0.15, 0.16, 0.17), dm) * (0.85 + 0.25 * fbm(u * 1.5));
    // tall panels framed in thin gilt mouldings
    float px = s == 0 ? p.x : p.z;
    float pw = 1.7;
    float cell = (fract(px / pw + 0.5) - 0.5) * pw;
    float pan = max(abs(cell) - 0.7, abs(p.y - 2.75) - 1.6);
    float dado = max(abs(cell) - 0.7, abs(p.y - 0.5) - 0.32);
    float mould = min(abs(pan), abs(dado)) - 0.018;
    vec3 L = bAmbient(p) + bGlowLight(p, glowLvl) + bDoorLight(p);
    vec3 col = base * L;
    float gm = aaw(mould, fw);
    col = mix(col, giltCol(u, B_COLD) * (L * 2.4 + 0.006), gm);
    col = mix(col, vec3(0.05, 0.04, 0.03) * L * 4.0, band01(p.y, 0.0, 0.16, fw));       // skirting
    col *= 1.0 - 0.5 * band01(p.y, 0.98, 1.04, fw);
    return col;
}

vec3 room1() {
    float glowLvl = uP[4].x * (1.0 - CHOLD[0]);
    float holdLvl = uP[4].x * CHOLD[0];
    B_VI = sat(uP[4].y);
    B_COLD = smoothstep(0.1, 0.9, B_VI);
    B_DOOR = max(uP[4].w, smoothstep(0.0, 0.55, B_VI));
    B_OPEN = max(0.35, max(uP[4].w, smoothstep(0.0, 0.5, B_VI)));
    B_S = mix(vec3(6.8, 0.8, 1.8), vec3(5.85, 0.75, 2.55), B_VI);
    B_V = vec3(4.0, 0.0, 4.1);
    Hit h = roomHit(B_ZB, B_XL, B_XR, B_HC, vec4(0.0), B_ZB);
    vec3 p = h.p;
    float fw = PX * p.z * 1.2;
    vec3 col;
    if (h.s == 0) {
        col = bWallShade(p, 0, fw, glowLvl);
        vec2 w = p.xy;
        vec3 L = bAmbient(p) + bGlowLight(p, glowLvl) + bDoorLight(p);
        // the arched windows: deep reveals, then glass full of moonlit sky
        for (int k = 0; k < 2; k++) {
            float cx = k == 0 ? -1.6 : 1.6;
            float wd = bWinSD(w, cx);
            if (wd > 0.25) continue;
            col = mix(col, vec3(0.16, 0.18, 0.22) * (L * 1.5 + vec3(0.18, 0.24, 0.4) * 0.6 * smoothstep(0.2, 0.0, wd)), aaw(wd - 0.16, fw));
            col = mix(col, giltCol(w, B_COLD) * (L * 2.0 + 0.05), aaw(abs(wd - 0.16) - 0.02, fw));
            vec2 v = vec2(RD.x / RD.z, RD.y / RD.z);
            vec3 sky = nightSky(v + vec2(0.0, 0.1), 0.0) * 1.6;
            vec2 b = at(B_ZB + 6.0);
            float trees = b.y - (0.8 + 1.4 * fbm(vec2(b.x * 1.3, 1.0)) + 2.2 * smoothstep(0.35, 0.0, abs(fract(b.x * 0.35) - 0.5)));
            sky = mix(sky, vec3(0.01, 0.015, 0.03), smoothstep(0.03, -0.03, trees));
            vec3 gl = mix(vec3(0.05, 0.06, 0.08), sky, bGlazing(w - vec2(cx, B_WY), fw));
            col = mix(col, gl, aaw(wd, fw));
        }
        // gilt frames with dark old paintings
        float gl = 0.12 + 0.5 * (1.0 - B_COLD);
        col = giltFrame(col, w, vec2(0.0, 2.75), vec2(0.62, 0.85), 0.2, L, fw, B_COLD, gl);
        col = giltFrame(col, w, vec2(-3.15, 2.3), vec2(0.42, 0.56), 1.1, L, fw, B_COLD, gl);
        col = giltFrame(col, w, vec2(3.15, 2.3), vec2(0.42, 0.56), 2.4, L, fw, B_COLD, gl);
        col = giltFrame(col, w, vec2(-3.15, 3.85), vec2(0.3, 0.24), 3.3, L, fw, B_COLD, gl);
        col = giltFrame(col, w, vec2(3.15, 3.85), vec2(0.3, 0.24), 0.7, L, fw, B_COLD, gl);
        // the wall rises into darkness
        col *= 1.0 - 0.75 * smoothstep(3.4, 5.2, p.y);
    } else if (h.s == 1) {
        vec3 base = boards(vec2(p.x + p.z, p.z - p.x) * 0.7071, vec3(0.13, 0.08, 0.05), 0.11, fw);
        float moon = bMoonLit(p) * sat(-B_MOON.y);
        moon *= 1.0 - 0.85 * castDir(p, B_MOON, 0.02);
        vec3 dl = bDoorLight(p);
        dl *= 1.0 - 0.8 * castPoint(p, B_S, 0.03);
        col = base * (bAmbient(p) + B_MOONC * moon + dl + bGlowLight(p, glowLvl));
        // polish: the tall windows reflected in the floor
        vec3 rr = vec3(RD.x, -RD.y, RD.z);
        float tr = (B_ZB - p.z) / rr.z;
        vec3 q = p + rr * tr;
        float rb = 0.04 + 0.05 * tr;
        float ref = 0.0;
        for (int k = 0; k < 2; k++) {
            float cx = k == 0 ? -1.6 : 1.6;
            ref += 1.0 - smoothstep(-rb, rb, bWinSD(q.xy, cx));
        }
        ref *= 0.6 + 0.4 * vnoise(vec2(p.x * 3.0, p.z * 0.5));
        col += vec3(0.4, 0.52, 0.85) * ref * 0.22;
    } else {
        col = bWallShade(p, h.s, fw, glowLvl);
        vec3 L = bAmbient(p) + bDoorLight(p);
        if (h.s == 3) col = giltFrame(col, vec2(p.z, p.y), vec2(5.6, 2.5), vec2(0.5, 0.7), 1.7, L, fw, B_COLD, 0.2);
        col *= 1.0 - 0.75 * smoothstep(3.4, 5.2, p.y);
    }
    col *= 0.6 + 0.4 * smoothstep(0.0, 0.8, cornerDist(h, B_ZB, B_XL, B_XR, B_HC));

    // ---- light in the air
    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.6, zb = min(p.z, B_ZB);
        float dz = (zb - za) / 24.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        vec3 rdn = normalize(RD);
        float ph = 0.4 + 0.7 * pow(sat(dot(-rdn, B_MOON)), 4.0);
        for (int i = 0; i < 24; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            float hd = hazeDen(q);
            vec3 c = B_MOONC * bMoonLit(q) * ph * hd * 0.12;
            c += bDoorLight(q) * hd * 0.022;
            c += bGlowLight(q, glowLvl) * 0.06 + bAmbient(q) * 0.02;
            c *= dz * RDL;
            if (z > 4.6) vF += c; else if (z > Z0 + 0.3) vM += c; else vN += c * 0.6;
        }
    }
    col += vF;

    // ---- far flats: a gilded console under the great painting, a tall chair
    {
        float z = B_ZB - 0.35;
        vec2 w = at(z);
        vec2 l = w - vec2(0.0, 0.0);
        float d = sdBox(l - vec2(0.0, 0.86), vec2(0.75, 0.05));
        d = min(d, sdCapsule(l, vec2(-0.6, 0.82), vec2(-0.5, 0.05), 0.035));
        d = min(d, sdCapsule(l, vec2(0.6, 0.82), vec2(0.5, 0.05), 0.035));
        d = min(d, sdTrap(l - vec2(0.0, 0.72), 0.5, 0.7, 0.08));
        // a silver candelabrum, unlit
        d = min(d, sdBox(l - vec2(0.0, 1.15), vec2(0.02, 0.25)));
        d = min(d, sdArc(l, vec2(0.0, 1.38), 0.2, PI, TAU, 0.012));
        d = min(d, min(sdBox(l - vec2(-0.2, 1.44), vec2(0.012, 0.07)), sdBox(l - vec2(0.2, 1.44), vec2(0.012, 0.07))));
        d = min(d, sdBox(l - vec2(0.0, 1.47), vec2(0.012, 0.08)));
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 L = bAmbient(q3) + bDoorLight(q3) + B_MOONC * bMoonLit(q3) * 0.3;
            vec3 c = giltCol(l, B_COLD) * 0.6 * (L * 2.0 + 0.01);
            col = lay(col, c, a);
        }
    }
    {
        float z = 5.3;
        vec2 w = at(z);
        vec2 l = w - vec2(-2.7, 0.0);
        // a high-backed gilded chair of state
        float back = sdRBox(l - vec2(0.0, 1.15), vec2(0.27, 0.55), 0.1);
        back = min(back, sdCircle(l - vec2(0.0, 1.78), 0.07));
        back = min(back, min(sdCircle(l - vec2(-0.27, 1.66), 0.045), sdCircle(l - vec2(0.27, 1.66), 0.045)));
        float d = min(back, sdRBox(l - vec2(0.0, 0.5), vec2(0.36, 0.05), 0.03));
        d = min(d, sdBox(vec2(abs(l.x) - 0.31, l.y - 0.24), vec2(0.025, 0.24)));
        d = min(d, sdRBox(vec2(abs(l.x) - 0.37, l.y - 0.72), vec2(0.035, 0.17), 0.03));
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 L = bAmbient(q3);
            float edge = smoothstep(-0.04, 0.0, d);
            vec3 c = vec3(0.07, 0.02, 0.03) * L * 1.5;
            c = mix(c, giltCol(l, B_COLD) * (L * 2.5 + 0.01), max(edge, smoothstep(0.03, 0.0, abs(back + 0.06))) * 0.85);
            col = lay(col, c, a);
        }
    }
    col += vM;

    // ---- the cradle with Tommaso, and the characters
    vec2 crS = toScreen(vec3(B_CR.x, 0.0, B_CR.z));
    float czs = B_CR.z;
    vec2 cw = at(czs) - B_CR.xy;                          // cradle-local metres
    float rock = 0.035 * sin(T * 1.1);
    vec2 cl = rot(rock) * (cw - vec2(0.0, 0.12)) + vec2(0.0, 0.12);
    vec3 cq3 = vec3(at(czs), czs);
    vec3 cL = bAmbient(cq3) + bDoorLight(cq3);          // its face is turned from the moon
    vec3 wood = vec3(0.13, 0.075, 0.045);
    {
        // inner far side of the basket, lit by the child
        float inner = sdRBox(cl - vec2(0.0, 0.52), vec2(0.46, 0.2), 0.06);
        float a = aaw(inner, PX * czs);
        vec3 c = wood * 0.7 * (cL + SILVER * glowLvl * 1.6 * exp(-length((cl - vec2(-0.14, 0.52)) * vec2(1.0, 1.5)) * 3.6));
        col = lay(col, c, a);
        // the child of light
        vec2 tp = toScreen(vec3(B_CR.x + 0.04, 0.47, czs));
        vec4 tg = childGlow(SP, tp, 0.3, glowLvl, 0.0);
        col = col * (1.0 - tg.a * step(0.02, glowLvl)) + tg.rgb;
        // the spindled front side, rails, rockers and hood
        float rail = min(sdRBox(cl - vec2(0.0, 0.7), vec2(0.5, 0.022), 0.01), sdRBox(cl - vec2(0.0, 0.33), vec2(0.5, 0.03), 0.01));
        float sp = abs(fract(cl.x / 0.07) - 0.5) * 0.07 - 0.0105;
        float spind = max(sp, max(abs(cl.x) - 0.48, abs(cl.y - 0.52) - 0.19));
        float posts = sdBox(vec2(abs(cl.x) - 0.5, cl.y - 0.42), vec2(0.025, 0.36));
        posts = min(posts, sdCircle(vec2(abs(cl.x) - 0.5, cl.y - 0.8), 0.04));
        float rk = max(abs(length(cl - vec2(0.0, 1.6)) - 1.53) - 0.025, abs(cl.x) - 0.62);
        float hood = sdEllipse(cl - vec2(-0.44, 0.7), vec2(0.21, 0.36));
        hood = max(max(hood, -cl.y + 0.66), cl.x + 0.3);
        float dfront = min(min(rail, spind), min(posts, rk));
        float af = aaw(dfront, PX * czs);
        vec3 fc = wood * (cL * 1.5 + 0.003);
        // silver light catching the inner edges of the spindles; moonlight on the top edges
        fc += SILVER * glowLvl * 0.5 * smoothstep(-0.012, 0.0, dfront) * exp(-length(cl - vec2(0.0, 0.5)) * 2.0);
        fc += B_MOONC * 0.12 * smoothstep(-0.01, 0.0, rail) * step(0.69, cl.y);
        col = lay(col, fc, af);
        float ah = aaw(hood, PX * czs);
        vec3 hcol = vec3(0.3, 0.32, 0.38) * (cL * 1.3 + SILVER * glowLvl * 0.55 * smoothstep(0.8, 0.62, cl.y));
        hcol *= 0.82 + 0.18 * sin(cl.x * 95.0 + 1.5 * sin(cl.y * 20.0));
        float trim = smoothstep(0.02, 0.0, abs(hood + 0.012)) * smoothstep(0.73, 0.78, cl.y);
        hcol = mix(hcol, vec3(0.7, 0.72, 0.78) * (cL * 1.6 + SILVER * glowLvl * 0.4), trim * (0.6 + 0.4 * sin(atan(cl.y - 0.7, cl.x + 0.44) * 40.0)));
        hcol += B_MOONC * 0.08 * smoothstep(-0.015, 0.0, hood);
        col = lay(col, hcol, ah * 0.94);
        // light rising from the cradle
        col += SILVER * glowLvl * 0.3 * exp(-length((cl - vec2(0.02, 0.78)) * vec2(1.0, 0.55)) * 3.0) * smoothstep(0.6, 0.76, cl.y);
    }
    {
        vec2 moonS = toScreen(vec3(1.6 - B_MOON.x * 4.0, B_WY + 2.4, B_ZB));
        vec2 glowS = crS + vec2(0.0, 0.17);
        vec3 l2 = SILVER * (glowLvl + holdLvl) * 0.9 + vec3(1.0, 0.7, 0.4) * B_DOOR * 0.5;
        vec2 l2p = mix(glowS, vec2(1.2, -0.1), B_DOOR * 0.5 / (B_DOOR * 0.5 + glowLvl + holdLvl + 0.01));
        for (int i = 2; i >= 0; i--) {
            vec2 L1 = moonS - CP[i].xy - vec2(0.0, CP[i].z * 0.7);
            vec3 c3 = vec3(CP[i].x * CZ[i], CAMY + (CP[i].y + CP[i].z * 0.7) * CZ[i], CZ[i]);
            float m = bMoonLit(c3);
            col = seatBehind(i, col, bAmbient(c3) * 1.5 + bDoorLight(c3) * 0.5);
            WRAP = 0.6;
            vec4 f = actor(i, L1, 0.5 + 0.8 * m, vec3(0.13, 0.14, 0.2), l2, l2p);
            WRAP = 0.0;
            col = over(col, f);
        }
        col = heldChild(col, holdLvl, vec3(0.13, 0.14, 0.2));
    }
    col += vN;
    // ---- foreground: a heavy drape at the left edge
    {
        float z = 1.9;
        vec2 w = at(z);
        float edge = -1.42 + 0.06 * sin(w.y * 2.0) + 0.1 * smoothstep(0.6, -0.4, w.y);
        float d = w.x - edge;
        float a = aaw(d, PX * z * 2.5);
        if (a > 0.0) {
            float folds = 0.5 + 0.5 * sin((w.x - edge) * 26.0 + w.y * 0.6);
            vec3 c = vec3(0.025, 0.04, 0.05) * (0.5 + 0.8 * folds);
            c += vec3(0.35, 0.45, 0.7) * 0.18 * smoothstep(-0.06, 0.0, d);
            col = lay(col, c, a);
        }
    }
    col += vec3(0.6, 0.7, 1.0) * dust(SP, T, 0.15, 0.05) * sat(lum(vN + vM) * 5.0) * 0.6;
    // Vittorio's coldness creeps in
    col = mix(col, col * vec3(0.8, 0.9, 1.15), B_COLD * 0.5);
    return col;
}

// =============================================================================================
// The Trieste apartment (modes 2, 3, 5, 6, 7): one small room, low ceiling with a beam,
// terracotta floor, a window on the sea. Shared walls, window and floor.
// =============================================================================================
const float C_ZB = 5.0, C_XL = -2.7, C_XR = 2.7, C_HC = 2.95;
const vec4 C_WIN = vec4(0.95, 1.5, 0.72, 0.82);
float C_SHL, C_SHR;      // shutter leaves: fraction open (1 = folded right back)
float C_CASE;            // inner casements: 0 closed, 1 swung open
float C_ZBk;             // back wall depth used by the current mode
vec4 C_WINk;             // window used by the current mode

float cWinSD(vec2 w) { return sdBox(w - C_WINk.xy, C_WINk.zw); }
// a timber beam across the low ceiling at depth zc: ray distance and face (0 underside, 1 front)
float beamHit(float zc, float hc, float tMax, out int face, out vec3 bp) {
    face = -1;
    float best = 1e5;
    float y0 = hc - 0.2;
    bp = vec3(0.0);
    if (RD.y > 0.0) {
        float t = (y0 - RO.y) / RD.y;
        vec3 p = RO + RD * t;
        if (t < tMax && abs(p.z - zc) < 0.12) { best = t; face = 0; bp = p; }
    }
    float tf = (zc - 0.12) / Z0;
    vec3 pf = RO + RD * tf;
    if (tf < best && tf < tMax && pf.y > y0 && pf.y < hc) { best = tf; face = 1; bp = pf; }
    return best;
}
vec3 beamShade(int face, vec3 bp, vec3 L) {
    vec3 wood = vec3(0.24, 0.15, 0.09) * (0.8 + 0.3 * vnoise(vec2(bp.x * 3.0, bp.y * 40.0 + bp.z * 40.0)));
    return wood * L * (face == 0 ? 1.15 : 0.75);
}
// transmission of the window: casement bars and the louvred shutters
float cAperture(vec2 w, float s) {
    vec2 l = w - C_WINk.xy;
    float b = 0.008 + 0.03 * s;
    float o = 1.0 - smoothstep(-b, b, sdBox(l, C_WINk.zw));
    if (o <= 0.001) return 0.0;
    float hw = C_WINk.z;
    // casement bars (closed casements show a cross; open ones leave only a sliver at the sides)
    float cb = min(abs(l.x) - 0.025, abs(l.y - 0.22) - 0.02);
    float side = abs(abs(l.x) - hw) - 0.06 - 0.12 * C_CASE;
    float bars = mix(cb, side, C_CASE);
    o *= smoothstep(-b, b, bars);
    // louvred shutters outside: leaves fold in from each side
    float eL = -hw + 2.0 * hw * 0.5 * (1.0 - C_SHL);
    float eR = hw - 2.0 * hw * 0.5 * (1.0 - C_SHR);
    float inLeaf = max(1.0 - smoothstep(eL - b, eL + b, l.x), smoothstep(eR - b, eR + b, l.x));
    float slat = mix(0.18, 0.62, smoothstep(0.55, 0.85, fract(l.y * 16.0)));
    slat = mix(slat, 0.3, 1.0 - exp(-s * 2.0));
    return o * mix(1.0, slat, inLeaf);
}
float cLitDir(vec3 p, vec3 L) {
    float s = (p.z - C_ZBk) / L.z;
    if (s <= 0.0) return 0.0;
    return cAperture(p.xy - L.xy * s, s);
}
vec3 cWall(vec3 p, int s, vec3 base, float fw) {
    vec2 u = s == 0 ? p.xy : vec2(p.z, p.y);
    vec3 c = plaster(u * 1.4, base);
    c *= 1.0 - 0.12 * smoothstep(0.4, 0.0, p.y);                                   // grime low down
    c = mix(c, base * 0.45, band01(p.y, 0.0, 0.1, fw));                          // skirting
    return c;
}
vec3 cFloor(vec3 p, float fw) {
    return tiles(p.xz, vec3(0.42, 0.2, 0.12), 0.3, fw);
}
// the window seen from inside: reveal, frame, casements, shutters, the view (tod as seaView)
vec3 cWindow(vec3 col, vec2 w, vec3 L, float fw, int tod, float sparkle, vec3 frameLit) {
    vec2 l = w - C_WINk.xy;
    float wd = sdBox(l, C_WINk.zw);
    if (wd > 0.2) return col;
    // the deep reveal of an old wall, shaded towards the glass, and a painted architrave
    vec3 reveal = vec3(0.6, 0.55, 0.48) * (L * 1.2 + frameLit * 0.6 * smoothstep(0.06, 0.0, wd));
    reveal *= 0.7 + 0.3 * smoothstep(0.0, 0.06, wd);
    col = mix(col, reveal, aaw(wd - 0.06, fw));
    col = mix(col, vec3(0.72, 0.69, 0.63) * (L * 1.15 + frameLit * 0.25), aaw(abs(wd - 0.07) - 0.014, fw));
    float sill = sdBox(l - vec2(0.0, -C_WINk.w - 0.05), vec2(C_WINk.z + 0.12, 0.03));
    col = mix(col, vec3(0.7, 0.67, 0.6) * (L * 1.3 + frameLit * 0.4), aaw(sill, fw));
    if (wd < 0.01) {
        vec2 v = vec2(RD.x / RD.z, RD.y / RD.z);
        vec3 view = tod == 3 ? nightSky(v + vec2(0.0, 0.08), 1.0) : seaView(v + vec2(0.0, 0.02), tod, sparkle);
        if (tod == 3) {    // roofs of the old town under the night sky
            vec2 b = at(C_ZBk + 14.0);
            float roof = b.y - (0.2 + 0.6 * abs(fract(b.x * 0.18) - 0.5) + 0.25 * step(0.8, fract(b.x * 0.9)));
            view = mix(view, vec3(0.012, 0.016, 0.03), smoothstep(0.03, -0.03, roof));
            vec2 g = floor(b * vec2(3.0, 4.0));
            view += vec3(1.0, 0.7, 0.4) * 0.8 * step(0.93, hash21(g)) * step(roof, -0.1) * step(0.2, fract(b.x * 3.0)) * step(0.3, fract(b.y * 4.0));
        }
        float hw = C_WINk.z;
        // shutters outside (dark louvres with light between the slats)
        float eL = -hw + hw * (1.0 - C_SHL);
        float eR = hw - hw * (1.0 - C_SHR);
        float inLeaf = max(1.0 - smoothstep(eL - fw, eL + fw, l.x), smoothstep(eR - fw, eR + fw, l.x));
        float slat = smoothstep(0.55, 0.8, fract(l.y * 16.0));
        vec3 sh = mix(vec3(0.05, 0.06, 0.05) * (L * 2.0 + frameLit * 0.2), view * 0.5, slat * 0.55);
        view = mix(view, sh, inLeaf);
        // casements: white-painted frames and glass
        float cb = min(abs(l.x) - 0.025, abs(l.y - 0.22) - 0.02);
        float side = abs(abs(l.x) - hw) - 0.06 - 0.12 * C_CASE;
        float bars = mix(cb, side, C_CASE);
        view *= mix(1.0, 0.85, 1.0 - C_CASE);
        view = mix(vec3(0.7, 0.68, 0.62) * (L * 1.2 + frameLit * 0.4), view, smoothstep(-fw, fw, bars));
        col = mix(col, view, aaw(wd, fw));
    }
    return col;
}

// =============================================================================================
// MODE 2: Trieste at night, the nightmare. The bora rattles the shutters; Elena asleep;
// Vittorio as a tall figure of cold light and smoke by the bed.
// =============================================================================================
vec3 C_MOON;
const vec3 C_MOONC = vec3(0.45, 0.58, 1.0) * 3.0;
vec3 C_VPOS;     // the vision: screen x, y (feet), height
float C_VI;

vec3 cVisionLight(vec3 p) {
    vec3 c = vec3(C_VPOS.x * Z0, CAMY + (C_VPOS.y + C_VPOS.z * 0.6) * Z0, Z0);
    vec3 d = p - c;
    return vec3(0.45, 0.6, 1.0) * C_VI * 0.9 / (0.25 + dot(d, d));
}
vec3 cNightAmb(vec3 p) {
    return vec3(0.034, 0.045, 0.085) + vec3(0.1, 0.13, 0.25) * 0.22 * exp(-length(p.xy - C_WINk.xy) * 0.9)
         + vec3(0.06, 0.08, 0.16) * 0.25 * exp(-length(p.xz - vec2(0.2, 2.8)) * 0.8) * exp(-p.y * 0.6) + home(p);
}
// the vision: emission (premultiplied) and coverage
vec4 vision(vec2 sp) {
    if (C_VI <= 0.001) return vec4(0.0);
    float h = C_VPOS.z;
    vec2 q = (sp - C_VPOS.xy) / h;
    if (abs(q.x) > 0.9 || q.y < -0.15 || q.y > 1.9) return vec4(0.0);
    float tt = T * 0.35;
    vec2 disp = vec2(fbm(q * 3.0 + vec2(0.0, -tt * 2.0)) - 0.5, fbm(q * 3.0 + vec2(5.2, -tt * 2.0)) - 0.5);
    vec2 qd = q + disp * (0.04 + 0.1 * sat(q.y - 0.2) + 0.12 * sat(0.3 - q.y)) * (1.7 - C_VI);
    float d = figSD(qd, vec4(0.1, 0.32, 0.0, 0.02 * sin(T * 0.4)), 0.0) * h;
    d += (fbm(q * 9.0 + vec2(0.0, -T * 0.6)) - 0.5) * 0.02 * h;             // edges eaten by smoke
    float form = smoothstep(0.15, 0.75, C_VI);
    float solid = smoothstep(0.02, 0.45, q.y);                              // he dissolves towards the floor
    float inside = aaw(d, 0.004);
    float edge = exp(-abs(d) / (0.004 + 0.006 * h));
    float flick = 0.6 + 0.4 * fbm(q * 7.0 + vec2(0.0, -T * 0.8));
    vec3 steel = vec3(0.45, 0.62, 1.0);
    vec3 e = steel * form * solid * (inside * 0.22 * flick + edge * 0.85 * flick) * C_VI;
    e += steel * glow(d, 0.03 * h) * 0.25 * C_VI * (0.4 + 0.6 * solid);
    // smoke rising off him, and pooling where his feet should be
    vec2 sq = vec2(q.x * 3.0 + 0.4 * sin(q.y * 2.0 + T * 0.3), q.y * 1.4 - T * 0.25);
    float sm = fbm(sq) * fbm(sq * 2.1 + 3.0);
    float plume = exp(-max(d, 0.0) / (0.06 + 0.14 * sat(q.y - 0.7))) * smoothstep(-0.15, 0.5, q.y);
    plume += exp(-length((q - vec2(0.0, 0.05)) * vec2(1.6, 4.0)) * 2.0) * 0.8;
    e += vec3(0.3, 0.42, 0.7) * smoothstep(0.1, 0.42, sm) * plume * 0.45 * C_VI;
    // a few gold flecks drifting inside the form
    vec2 g = q * vec2(14.0, 9.0) + vec2(0.0, T * 0.15);
    vec2 id = floor(g);
    vec2 f = fract(g) - 0.5 - (hash22(id) - 0.5) * 0.7;
    float tw = pow(0.5 + 0.5 * sin(T * (2.0 + 3.0 * hash21(id)) + hash21(id + 4.0) * 6.28), 4.0);
    float fl = step(0.8, hash21(id + 2.3)) * smoothstep(0.14, 0.0, length(f)) * tw * max(inside, 0.5 * exp(-max(d, 0.0) / 0.03));
    e += vec3(1.0, 0.75, 0.32) * fl * 3.5 * form * C_VI;
    return vec4(e, inside * form * 0.35 * C_VI);
}

// bed in profile along the back wall, headboard to the left (local metres, origin floor centre)
float bedFrameSD(vec2 l, float len, float headH, float footH) {
    float hx = -len * 0.5;
    float head = sdRBox(l - vec2(hx, headH * 0.5), vec2(0.045, headH * 0.5), 0.02);
    head = min(head, sdEllipse(l - vec2(hx + 0.03, headH - 0.05), vec2(0.07, 0.11)));
    float foot = sdRBox(l - vec2(-hx, footH * 0.5), vec2(0.045, footH * 0.5), 0.02);
    float rail = sdBox(l - vec2(0.0, 0.33), vec2(len * 0.5, 0.045));
    return min(min(head, foot), rail);
}

vec3 room2() {
    C_ZBk = C_ZB; C_WINk = C_WIN;
    C_CASE = 0.0;
    float gust = 0.12 * smoothstep(0.55, 1.0, 0.5 + 0.5 * sin(T * 0.63)) * sin(T * 7.3);
    C_SHL = 0.42 + 0.12 * sin(T * 1.9) + 0.05 * sin(T * 5.3 + 1.0) + gust;
    C_SHR = 0.3 + 0.1 * sin(T * 2.3 + 2.0) + 0.04 * sin(T * 6.1) - gust * 0.7;
    C_VI = sat(uP[4].y);
    C_VPOS = uP[2].z > 0.01 ? uP[2].xyz : vec3(0.36, -0.4, 0.64);
    Hit h = roomHit(C_ZB, C_XL, C_XR, C_HC, vec4(0.0), C_ZB);
    vec3 p = h.p;
    float fw = PX * p.z * 1.2;
    vec3 col;
    vec3 wallBase = vec3(0.42, 0.42, 0.45);
    if (h.s == 0 || h.s >= 3) {
        vec3 L = cNightAmb(p) + cVisionLight(p);
        col = cWall(p, h.s, wallBase, fw) * L;
        if (h.s == 0) {
            vec2 w = p.xy;
            // moon stripes through the slats fall on the reveal
            col = cWindow(col, w, L, fw, 3, 0.0, C_MOONC * 0.05);
            // a small crucifix over the bed and a framed photograph
            vec2 cq = w - vec2(-1.0, 1.75);
            float cr = min(sdBox(cq, vec2(0.012, 0.11)), sdBox(cq - vec2(0.0, 0.04), vec2(0.055, 0.012)));
            col = mix(col, vec3(0.02, 0.018, 0.02), aaw(cr, fw));
            vec2 fq = w - vec2(-1.95, 1.6);
            col = mix(col, vec3(0.03, 0.025, 0.02), aaw(sdBox(fq, vec2(0.14, 0.18)), fw));
            col = mix(col, vec3(0.2, 0.2, 0.22) * L * 2.0, aaw(sdBox(fq, vec2(0.1, 0.14)), fw));
        }
    } else if (h.s == 1) {
        float moon = cLitDir(p, C_MOON) * sat(-C_MOON.y);
        vec3 fl = cFloor(p, fw);
        fl = mix(fl, vec3(lum(fl)) * 1.2, 0.6);                 // colour drains away at night
        col = fl * (cNightAmb(p) + C_MOONC * moon + cVisionLight(p));
    } else {
        col = cWall(p, 0, wallBase * 0.8, fw) * (cNightAmb(p) * 0.7 + cVisionLight(p) * 0.5);
    }
    col *= 0.55 + 0.45 * smoothstep(0.0, 0.6, cornerDist(h, C_ZB, C_XL, C_XR, C_HC));
    {
        int bf; vec3 bp;
        float tb = beamHit(3.9, C_HC, h.t, bf, bp);
        if (bf >= 0) col = beamShade(bf, bp, cNightAmb(bp) * 0.8 + cVisionLight(bp));
    }

    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.6, zb = min(p.z, C_ZB);
        float dz = (zb - za) / 22.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        vec3 rdn = normalize(RD);
        float ph = 0.3 + 1.5 * pow(sat(dot(-rdn, C_MOON)), 5.0);
        for (int i = 0; i < 22; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            float hd = hazeDen(q);
            vec3 c = C_MOONC * cLitDir(q, C_MOON) * ph * hd * 0.13 + cVisionLight(q) * 0.05 + cNightAmb(q) * 0.02;
            c *= dz * RDL;
            if (z > 4.2) vF += c; else if (z > Z0 + 0.25) vM += c; else vN += c * 0.6;
        }
    }
    col += vF;
    // ---- far flats: a wardrobe and a chair with her dress over it
    {
        float z = 4.7;
        vec2 w = at(z);
        vec2 l = w - vec2(-2.25, 0.0);
        float d = sdBox(l - vec2(0.0, 1.0), vec2(0.42, 1.0));
        d = min(d, sdBox(l - vec2(0.0, 2.02), vec2(0.46, 0.04)));
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 c = vec3(0.12, 0.08, 0.06) * (cNightAmb(q3) * 1.3 + cVisionLight(q3));
            c *= 1.0 - 0.5 * smoothstep(0.012, 0.0, abs(l.x));
            col = lay(col, c, a);
        }
        z = 4.3;
        w = at(z);
        l = w - vec2(1.75, 0.0);
        d = chairSD(l, -1.0);
        float dress = sdTrap(l - vec2(-0.05, 0.62), 0.12, 0.2, 0.3) ;
        dress = max(dress, -(l.y - 0.32 + 0.04 * sin(l.x * 30.0)));
        d = min(d, dress);
        a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 L = cNightAmb(q3) * 1.3 + cVisionLight(q3) + C_MOONC * cLitDir(q3, C_MOON) * 0.3;
            vec3 c = mix(vec3(0.1, 0.07, 0.05), vec3(0.4, 0.04, 0.06), step(dress, chairSD(l, -1.0))) * L;
            col = lay(col, c, a);
        }
    }
    col += vM;

    // ---- the bed, Elena asleep, the vision
    {
        float z = Z0;
        vec2 bw = at(z);
        vec2 l = bw - vec2(-0.66, 0.0);
        float len = 2.0;
        vec3 q3 = vec3(bw, z);
        vec3 L = cNightAmb(q3) * 1.4 + cVisionLight(q3) + C_MOONC * cLitDir(q3, C_MOON) * 0.4;
        float frameD = bedFrameSD(l, len, 1.15, 0.8);
        vec3 wood = vec3(0.13, 0.08, 0.05);
        // headboard and pillow behind the sleeper
        float head = min(sdRBox(l - vec2(-len * 0.5, 0.575), vec2(0.045, 0.575), 0.02), sdEllipse(l - vec2(-len * 0.5 + 0.03, 1.1), vec2(0.07, 0.11)));
        col = lay(col, wood * L, aaw(head, PX * z));
        float mattress = sdRBox(l - vec2(0.0, 0.47), vec2(len * 0.5 - 0.02, 0.09), 0.04);
        vec3 sheet = vec3(0.55, 0.58, 0.68);
        col = lay(col, sheet * L, aaw(mattress, PX * z));
        float pillow = sdEllipse(l - vec2(-0.78, 0.6), vec2(0.2, 0.075));
        col = lay(col, sheet * 1.1 * L, aaw(pillow, PX * z));
        // Elena, asleep (pose 3 is laid in this bed whatever uP[1].xy says)
        vec4 f = actor(0, vec2(0.8, 0.6), 0.6, vec3(0.16, 0.16, 0.24), vec3(0.45, 0.6, 1.0) * C_VI * 0.8, C_VPOS.xy + vec2(0.0, C_VPOS.z * 0.6));
        col = over(col, f);
        // the blanket over her, hanging down the side of the bed
        bool asleep = CV[0] > 2.5 && CV[0] < 3.5 && CP[0].w > 0.0;
        float hh = CP[0].z;
        float bx = (SP.x - CP[0].x) / max(hh, 0.01);
        float footX = toScreen(vec3(-0.66 + len * 0.5 - 0.03, 0.0, z)).x;
        float top = -0.232 + 0.016;
        float bl = toScreen(vec3(-0.66 - 0.6, 0.0, z)).x;
        if (asleep) {
            // over her body: up to the shoulder, following the shape of her beneath
            float prof = 0.165 * smoothstep(-0.375, -0.3, bx) - 0.05 * smoothstep(0.0, 0.42, bx);
            prof += 0.01 * sin(bx * 22.0 + 1.0) * smoothstep(-0.3, 0.0, bx);
            top = -0.235 + hh * prof + 0.01;
            bl = CP[0].x - 0.375 * hh;
        }
        float hang = -0.335 + 0.01 * sin(SP.x * 70.0) + 0.006 * sin(SP.x * 151.0);
        float blanket = max(max(SP.y - top, hang - SP.y), max(bl - SP.x, SP.x - footX));
        float folds = 0.75 + 0.25 * sin(SP.x * 75.0 + 2.5 * sin(SP.y * 30.0 + SP.x * 9.0)) * smoothstep(-0.2, -0.3, SP.y);
        vec3 bc = vec3(0.17, 0.18, 0.3) * folds * L * (0.85 + 0.25 * fbm(SP * 30.0));
        float turn = smoothstep(0.016, 0.0, abs(SP.y - top + 0.012)) * step(bl, SP.x) * (asleep ? 1.0 : 0.0);
        bc = mix(bc, sheet * L * 1.15, turn);
        col = lay(col, bc, aaw(blanket, PX * 1.2));
        float foot = sdRBox(l - vec2(len * 0.5, 0.4), vec2(0.045, 0.4), 0.02);
        foot = min(foot, sdBox(l - vec2(0.0, 0.3), vec2(len * 0.5, 0.04)));
        foot = min(foot, min(sdBox(l - vec2(-len * 0.5 + 0.04, 0.15), vec2(0.03, 0.15)), sdBox(l - vec2(len * 0.5 - 0.04, 0.15), vec2(0.03, 0.15))));
        col = lay(col, wood * L * 1.2, aaw(foot, PX * z));
        // a bedside table with a glass of water catching the moon
        vec2 tl = bw - vec2(-1.95, 0.0);
        float tb = min(sdBox(tl - vec2(0.0, 0.3), vec2(0.2, 0.3)), sdBox(tl - vec2(0.0, 0.62), vec2(0.23, 0.02)));
        col = lay(col, wood * 0.8 * L, aaw(tb, PX * z));
        float glass = sdBox(tl - vec2(0.06, 0.72), vec2(0.03, 0.08));
        col = lay(col, vec3(0.3, 0.4, 0.6) * L * 2.0 + vec3(0.5, 0.65, 1.0) * 0.4 * smoothstep(0.012, 0.0, abs(tl.x - 0.08)), aaw(glass, PX * z) * 0.8);
        // Vittorio is only ever the vision here (uP[2] places it); a third character may enter
        {
            vec2 L1 = toScreen(vec3(C_WIN.xy, C_ZB)) - CP[2].xy;
            vec4 g = actor(2, L1, 0.6, vec3(0.16, 0.15, 0.2), vec3(0.45, 0.6, 1.0) * C_VI * 0.5, C_VPOS.xy);
            col = over(col, g);
        }
        vec4 vs = vision(SP);
        col = col * (1.0 - vs.a) + vs.rgb;
    }
    col += vN;
    col += vec3(0.6, 0.7, 1.0) * dust(SP, T, 0.12, 0.05) * sat(lum(vN + vM) * 6.0) * 0.5;
    col = mix(col, col * vec3(0.8, 0.9, 1.2), C_VI * 0.35);
    return col;
}

// =============================================================================================
// MODE 3: Trieste, morning. The window open on the sea; warm light; the table; Tommaso in his
// chair with Davide's paper boat; Davide and Elena; the amber home glow.
// =============================================================================================
vec3 C_SUN;
const vec3 C_SUNC = vec3(1.0, 0.83, 0.58) * 3.8;
const vec3 C_TCH = vec3(0.02, 0.0, 3.25);    // Tommaso's chair (x, floor, depth)

vec3 cMornAmb(vec3 p) {
    vec3 a = vec3(0.27, 0.22, 0.17);
    a += vec3(0.4, 0.28, 0.15) * exp(-length(p.xz - vec2(-0.3, 2.9)) * 0.6) * (0.45 + 0.55 * exp(-p.y * 0.8));
    a += vec3(0.24, 0.26, 0.3) * 0.7 * exp(-length(p.xy - C_WIN.xy) * 0.75) * smoothstep(2.5, C_ZB, p.z);
    return a * (0.75 + 0.25 * smoothstep(0.0, 2.0, p.y)) + home(p) * 1.6;
}

vec3 room3() {
    C_ZBk = C_ZB; C_WINk = C_WIN;
    C_CASE = 1.0; C_SHL = 1.0; C_SHR = 1.0;
    float tl = uP[4].x;
    float glowLvl = tl * (1.0 - CHOLD[0]);
    float holdLvl = tl * CHOLD[0];
    Hit h = roomHit(C_ZB, C_XL, C_XR, C_HC, vec4(0.0), C_ZB);
    vec3 p = h.p;
    float fw = PX * p.z * 1.2;
    vec3 col;
    vec3 wallBase = vec3(0.7, 0.55, 0.4);
    if (h.s == 0 || h.s >= 3) {
        vec3 L = cMornAmb(p);
        col = cWall(p, h.s, wallBase, fw) * L;
        if (h.s == 0) {
            vec2 w = p.xy;
            col = cWindow(col, w, L, fw, 0, uP[6].x, vec3(1.0, 0.9, 0.7) * 1.2);
            // geraniums on the sill
            vec2 gq = w - vec2(C_WIN.x - 0.35, C_WIN.y - C_WIN.w);
            float pot = sdTrap(gq - vec2(0.0, 0.07), 0.06, 0.08, 0.07);
            float leaves = sdCircle(gq - vec2(0.0, 0.2), 0.12) + 0.03 * vnoise(gq * 40.0);
            col = mix(col, vec3(0.5, 0.22, 0.12) * (L + 0.4), aaw(pot, fw));
            col = mix(col, vec3(0.05, 0.12, 0.04) * (L + 0.3), aaw(leaves, fw));
            float fl = smoothstep(0.62, 0.7, vnoise(gq * 30.0)) * aaw(leaves + 0.02, fw);
            col = mix(col, vec3(0.9, 0.1, 0.08) * 1.4, fl);
            // a shelf with plates, and a clock
            vec2 sq = w - vec2(-1.2, 1.85);
            float shelf = sdBox(sq, vec2(0.55, 0.02));
            col *= 1.0 - 0.4 * aaw(sdBox(sq - vec2(0.03, -0.06), vec2(0.55, 0.04)), 0.04);
            col = mix(col, vec3(0.3, 0.2, 0.12) * L, aaw(shelf, fw));
            for (int k = 0; k < 3; k++) {
                vec2 pq = sq - vec2(-0.32 + 0.32 * float(k), 0.17);
                float plate = sdCircle(pq, 0.14);
                vec3 pc = vec3(0.85, 0.82, 0.75) * L * 1.2;
                pc = mix(pc, vec3(0.2, 0.3, 0.6) * L, smoothstep(0.015, 0.0, abs(length(pq) - 0.1)));
                col = mix(col, pc, aaw(plate, fw));
            }
            vec2 kq = w - vec2(-1.95, 2.25);
            col = mix(col, vec3(0.3, 0.2, 0.1) * L, aaw(sdCircle(kq, 0.13), fw));
            col = mix(col, vec3(0.85, 0.82, 0.72) * L * 1.2, aaw(sdCircle(kq, 0.105), fw));
            float hands = min(sdSeg(kq, vec2(0.0), vec2(0.0, 0.08)), sdSeg(kq, vec2(0.0), vec2(0.05, -0.02))) - 0.006;
            col = mix(col, vec3(0.05), aaw(hands, fw));
        }
    } else if (h.s == 1) {
        float sun = cLitDir(p, C_SUN) * sat(-C_SUN.y);
        sun *= 1.0 - 0.85 * castDir(p, C_SUN, 0.02);
        col = cFloor(p, fw) * (cMornAmb(p) + C_SUNC * sun + SILVER * glowLvl * 0.15 * exp(-length(p.xz - C_TCH.xz) * 2.0));
    } else {
        col = plaster(p.xz, vec3(0.62, 0.52, 0.42)) * cMornAmb(p) * 0.8;
    }
    col *= 0.6 + 0.4 * smoothstep(0.0, 0.6, cornerDist(h, C_ZB, C_XL, C_XR, C_HC));
    {
        int bf; vec3 bp;
        float tb = beamHit(3.9, C_HC, h.t, bf, bp);
        if (bf >= 0) col = beamShade(bf, bp, cMornAmb(bp) * 1.3);
    }

    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.6, zb = min(p.z, C_ZB);
        float dz = (zb - za) / 22.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        vec3 rdn = normalize(RD);
        float ph = 0.35 + 1.4 * pow(sat(dot(-rdn, C_SUN)), 6.0);
        for (int i = 0; i < 22; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            vec3 c = C_SUNC * cLitDir(q, C_SUN) * ph * hazeDen(q) * 0.12 + home(q) * 0.1 + cMornAmb(q) * 0.012;
            c *= dz * RDL;
            if (z > 4.0) vF += c; else if (z > Z0 + 0.4) vM += c; else vN += c * 0.5;
        }
    }
    col += vF;
    // ---- the table with a cloth, cups, bread and the milk Davide brought
    {
        float z = 4.15;
        vec2 w = at(z);
        vec2 l = w - vec2(-0.75, 0.0);
        float hem = 0.02 * sin(l.x * 30.0);
        float cloth = max(sdBox(l - vec2(0.0, 0.62), vec2(0.62, 0.16)), 0.46 + hem - l.y);
        float legs = min(sdBox(l - vec2(-0.52, 0.25), vec2(0.03, 0.25)), sdBox(l - vec2(0.52, 0.25), vec2(0.03, 0.25)));
        float jug = sdRBox(l - vec2(0.22, 0.88), vec2(0.06, 0.1), 0.03);
        float cup = sdRBox(l - vec2(-0.2, 0.82), vec2(0.045, 0.04), 0.01);
        float bread = sdEllipse(l - vec2(-0.02, 0.81), vec2(0.13, 0.04));
        float d = min(min(cloth, legs), min(jug, min(cup, bread)));
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            float sun = cLitDir(q3, C_SUN);
            vec3 L = cMornAmb(q3) * 1.1 + C_SUNC * sun * 0.35;
            float check = step(0.5, fract(l.x * 6.0)) + step(0.5, fract(l.y * 6.0));
            vec3 c = mix(vec3(0.82, 0.8, 0.74), vec3(0.62, 0.2, 0.15), mod(check, 2.0) * 0.6);
            if (legs < cloth) c = vec3(0.25, 0.15, 0.08);
            if (jug < min(cloth, legs)) c = vec3(0.9, 0.88, 0.82);
            if (bread < min(cloth, min(legs, jug))) c = vec3(0.65, 0.4, 0.18);
            if (cup < min(cloth, min(legs, min(jug, bread)))) c = vec3(0.85, 0.82, 0.76);
            col = lay(col, c * L, a);
        }
    }
    col += vM;
    // ---- Tommaso in his little chair, then the figures
    {
        float z = C_TCH.z;
        vec2 w = at(z);
        vec2 l = w - C_TCH.xy;
        vec3 q3 = vec3(w, z);
        vec3 L = cMornAmb(q3) + C_SUNC * cLitDir(q3, C_SUN) * 0.3;
        float back = min(sdBox(l - vec2(0.0, 0.73), vec2(0.23, 0.1)), sdBox(vec2(abs(l.x) - 0.24, l.y - 0.43), vec2(0.022, 0.43)));
        col = lay(col, vec3(0.3, 0.18, 0.09) * L, aaw(back, PX * z));
        vec2 tp = toScreen(vec3(C_TCH.x, 0.43, z));
        vec4 tg = childGlow(SP, tp, 0.74 / z, glowLvl, 1.0);
        col = col * (1.0 - tg.a * step(0.02, glowLvl)) + tg.rgb;
        // the paper boat on his lap
        vec2 bq = (SP - tp - vec2(0.0, 0.035)) * z;
        float hull = sdTrap(bq - vec2(0.0, 0.0), 0.07, 0.11, 0.025);
        float sail = sdTrap(bq - vec2(0.0, 0.06), 0.035, 0.0, 0.04);
        float boat = min(hull, sail);
        col = lay(col, vec3(0.95, 0.93, 0.88) * (L * 1.3 + SILVER * glowLvl * 0.6), aaw(boat, PX * z) * step(0.02, glowLvl + 0.05));
        float front = smallChairSD(l);
        front = max(front, -(sdBox(l - vec2(0.0, 0.73), vec2(0.23, 0.1))));
        float fr = min(min(sdBox(vec2(abs(l.x) - 0.205, l.y - 0.2), vec2(0.018, 0.2)), sdRBox(l - vec2(0.0, 0.405), vec2(0.25, 0.028), 0.01)), min(sdRBox(vec2(abs(l.x) - 0.26, l.y - 0.58), vec2(0.035, 0.018), 0.01), sdBox(vec2(abs(l.x) - 0.262, l.y - 0.5), vec2(0.012, 0.08))));
        col = lay(col, vec3(0.32, 0.19, 0.1) * L * 1.1, aaw(fr, PX * z));
    }
    {
        vec2 sunS = toScreen(vec3(C_WIN.xy + vec2(0.1, 0.2), C_ZB));
        vec2 glowS = toScreen(vec3(C_TCH.x, 0.75, C_TCH.z));
        for (int i = 2; i >= 0; i--) {
            vec2 L1 = sunS - CP[i].xy - vec2(0.0, CP[i].z * 0.7);
            vec3 c3 = vec3(CP[i].x * CZ[i], CAMY + (CP[i].y + CP[i].z * 0.7) * CZ[i], CZ[i]);
            float s = cLitDir(c3, C_SUN);
            col = seatBehind(i, col, cMornAmb(c3) * 1.1);
            WRAP = 0.5 * s;
            vec3 tint = vec3(0.32, 0.27, 0.23) + vec3(0.16, 0.09, 0.03) * uP[0].z;
            vec4 f = actor(i, L1, 0.8 + 0.9 * s, tint, SILVER * (glowLvl + holdLvl) * 0.5 + vec3(1.0, 0.6, 0.25) * uP[0].z * 0.15, glowS);
            WRAP = 0.0;
            col = over(col, f);
        }
        col = heldChild(col, holdLvl, vec3(0.32, 0.27, 0.23));
    }
    col += vN;
    // ---- foreground: the edge of a dresser with a jug and a bowl, warm against the room
    {
        float z = 2.15;
        vec2 w = at(z);
        vec2 l = w - vec2(-2.05, 0.0);
        float d = sdBox(l - vec2(0.0, 0.48), vec2(0.42, 0.48));
        d = min(d, sdBox(l - vec2(0.03, 0.98), vec2(0.47, 0.03)));
        float jug = sdRBox(l - vec2(0.22, 1.13), vec2(0.075, 0.12), 0.05);
        jug = min(jug, sdBox(l - vec2(0.22, 1.27), vec2(0.04, 0.03)));
        float bowl = max(sdEllipse(l - vec2(-0.1, 1.04), vec2(0.17, 0.08)), 1.01 - l.y);
        d = min(d, min(jug, bowl));
        float soft = PX * z * 4.0;                       // near the lens: a little out of focus
        float a = aaw(d, soft);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 L = cMornAmb(q3);
            vec3 c = vec3(0.13, 0.085, 0.05) * L * (0.75 + 0.25 * smoothstep(0.0, 1.0, l.y));
            float drawer = abs(fract((l.y - 0.1) / 0.3) - 0.5) * 0.3;
            c *= 1.0 - 0.3 * smoothstep(0.015, 0.0, drawer) * step(l.y, 0.9);
            // window light grazing the edges that face it (up and to the right)
            vec2 toWin = normalize(vec2(1.0, 0.5));
            float lit = sat(a - aaw(min(min(sdBox(l - toWin * 0.025 - vec2(0.0, 0.48), vec2(0.42, 0.48)), sdBox(l - toWin * 0.025 - vec2(0.03, 0.98), vec2(0.47, 0.03))), min(sdRBox(l - toWin * 0.025 - vec2(0.22, 1.13), vec2(0.075, 0.12), 0.05), max(sdEllipse(l - toWin * 0.025 - vec2(-0.1, 1.04), vec2(0.17, 0.08)), 1.01 - l.y + toWin.y * 0.025))), soft));
            c += vec3(1.0, 0.82, 0.58) * 0.22 * lit;
            col = lay(col, c, a);
        }
    }
    col += vec3(1.0, 0.9, 0.7) * dust(SP, T, 0.18, 0.05) * sat(lum(vN + vM) * 4.0) * 0.8;
    return col;
}

// =============================================================================================
// MODE 4: a trattoria in the evening. Hanging lamps, dim diners, a small table with a candle
// and two glasses; Elena and Davide seated. uP[6].x: the door bursts open on cold light.
// =============================================================================================
const float D_ZB = 6.5, D_XL = -3.6, D_XR = 3.6, D_HC = 3.3;
const vec4 D_DOOR = vec4(-2.0, 1.15, 0.5, 1.15);     // door in the back wall: centre, half size
float D_B;           // burst 0..1
vec3 D_LAMP[3];
vec3 D_CS;           // the cold light outside the door
vec3 D_CANDLE;       // candle flame (world)

float dDoorLit(vec3 p) {
    if (D_B <= 0.0) return 0.0;
    vec3 d = D_CS - p;
    if (d.z <= 0.0) return 0.0;
    float u = (D_ZB - p.z) / d.z;
    if (u <= 0.0 || u >= 1.0) return 0.0;
    vec3 q = p + d * u;
    float b = 0.02 + 0.2 * (1.0 - u);
    float open = D_DOOR.z * 2.0 * D_B;
    float x0 = D_DOOR.x - D_DOOR.z, x1 = x0 + open;
    return smoothstep(x0 - b, x0 + b, q.x) * (1.0 - smoothstep(x1 - b, x1 + b, q.x)) * (1.0 - smoothstep(2.3 - b, 2.3 + b, q.y));
}
vec3 dLampLight(vec3 p) {
    vec3 acc = vec3(0.0);
    float fk = 1.0 - uP[5].w * 0.3 * smoothstep(0.55, 1.0, vnoise(vec2(T * 6.0, 3.0)));
    for (int k = 0; k < 3; k++) {
        vec3 d = p - D_LAMP[k];
        float r2 = dot(d, d);
        float cone = smoothstep(0.35, 0.75, -d.y / sqrt(r2 + 1e-4));
        acc += vec3(1.0, 0.68, 0.36) * (0.12 + 2.2 * cone) / (0.3 + r2) * fk;
    }
    vec3 dc = p - D_CANDLE;
    float fl = 0.85 + 0.15 * sin(T * 9.0) * sin(T * 13.7 + 1.0);
    acc += vec3(1.0, 0.6, 0.28) * 0.12 * fl / (0.02 + dot(dc, dc));
    return acc;
}
vec3 dCold(vec3 p) {
    if (D_B <= 0.0) return vec3(0.0);
    vec3 d = D_CS - p;
    return vec3(0.6, 0.78, 1.0) * D_B * dDoorLit(p) * 70.0 / (1.0 + 0.35 * dot(d, d));
}
vec3 dAmb(vec3 p) { return vec3(0.05, 0.032, 0.02) * (1.0 - 0.3 * D_B) + vec3(0.02, 0.03, 0.05) * D_B + home(p); }

vec3 room4() {
    D_B = sat(uP[6].x);
    float sw = D_B * 0.18 * sin(T * 2.6) + 0.015 * sin(T * 0.9);
    D_LAMP[0] = vec3(-1.15 + sw, 2.15, 4.7);
    D_LAMP[1] = vec3(1.55 + sw * 0.8, 2.15, 5.5);
    D_LAMP[2] = vec3(0.0 + sw * 1.2, 2.3, 3.15);
    D_CS = vec3(D_DOOR.x, 2.0, D_ZB + 3.0);
    D_CANDLE = vec3(0.0, 0.98, 2.9);
    Hit h = roomHit(D_ZB, D_XL, D_XR, D_HC, vec4(0.0), D_ZB);
    vec3 p = h.p;
    float fw = PX * p.z * 1.2;
    vec3 col;
    vec3 L = dAmb(p) + dLampLight(p) + dCold(p);
    if (h.s == 0 || h.s >= 3) {
        vec2 u = h.s == 0 ? p.xy : vec2(p.z, p.y);
        vec3 c = plaster(u * 1.3, vec3(0.55, 0.32, 0.18));
        if (p.y < 1.1) {
            vec3 wood = vec3(0.2, 0.11, 0.06) * (0.8 + 0.3 * vnoise(vec2(u.x * 25.0, u.y * 2.0)));
            float pan = abs(fract(u.x / 0.6) - 0.5);
            wood *= 1.0 - 0.3 * smoothstep(0.03, 0.0, abs(pan - 0.47));
            c = wood;
        }
        c *= 1.0 - 0.5 * band01(p.y, 1.08, 1.14, fw);
        col = c * L;
        if (h.s == 0) {
            vec2 w = p.xy;
            // shelves of bottles on the right, catching the lamps
            for (int k = 0; k < 2; k++) {
                float sy = 1.55 + 0.55 * float(k);
                vec2 sq = w - vec2(1.6, sy);
                float shelf = sdBox(sq + vec2(0.0, 0.012), vec2(1.5, 0.03));
                shelf = min(shelf, sdBox(vec2(abs(sq.x) - 1.2, sq.y + 0.1), vec2(0.015, 0.08)));
                col *= 1.0 - 0.35 * aaw(sdBox(sq + vec2(-0.03, 0.08), vec2(1.5, 0.05)), 0.06);
                col = mix(col, vec3(0.2, 0.12, 0.06) * L * 1.3, aaw(shelf, fw));
                if (abs(sq.x) < 1.45 && sq.y > 0.0 && sq.y < 0.45) {
                    float bx = floor(sq.x / 0.13);
                    float hb = hash11(bx + float(k) * 17.0);
                    vec2 bq = vec2(fract(sq.x / 0.13) - 0.5, sq.y) * vec2(0.13, 1.0);
                    float bh = 0.24 + 0.1 * hb;
                    float bottle = min(sdRBox(bq - vec2(0.0, bh * 0.36), vec2(0.042, bh * 0.36), 0.025), sdTrap(bq - vec2(0.0, bh * 0.82), 0.03, 0.012, bh * 0.14));
                    bottle = hb > 0.15 ? bottle : 1.0;
                    vec3 gc = mix(vec3(0.1, 0.28, 0.1), vec3(0.45, 0.16, 0.05), step(0.6, hb));
                    gc = mix(gc, vec3(0.5, 0.06, 0.08), step(0.85, hb));
                    vec3 bc = gc * L * 3.2 * (0.7 + 0.3 * smoothstep(0.04, -0.04, bq.x));
                    bc += vec3(1.0, 0.78, 0.5) * 0.35 * smoothstep(0.007, 0.0, abs(bq.x + 0.02)) * step(0.03, bq.y) * step(bq.y, bh * 0.68);
                    bc = mix(bc, vec3(0.75, 0.68, 0.55) * L * 2.0, step(abs(bq.y - bh * 0.4), bh * 0.12) * step(0.3, hb) * 0.85);
                    col = mix(col, bc, aaw(bottle, fw));
                }
            }
            // the door: glazed upper panels, frosted, glowing faintly with the street; it bursts open
            vec2 dq = w - D_DOOR.xy;
            float frame = sdBox(dq, D_DOOR.zw + 0.08);
            col = mix(col, vec3(0.18, 0.1, 0.05) * L, aaw(frame, fw));
            float opening = sdBox(dq, D_DOOR.zw);
            if (opening < 0.0) {
                float open = D_DOOR.z * 2.0 * D_B;
                float xr = dq.x + D_DOOR.z;
                vec3 street = mix(vec3(0.5, 0.65, 0.95) * 5.0, vec3(0.2, 0.28, 0.45) * 2.0, smoothstep(0.0, 2.0, dq.y + 1.15));
                street *= 0.8 + 0.2 * fbm(vec2(dq.x * 3.0, dq.y * 2.0 + T));
                vec3 pnl = vec3(0.2, 0.11, 0.055) * L * 1.2;
                float glassP = sdBox(vec2(fract((xr - open) / max(2.0 * D_DOOR.z - open, 0.01) * 2.0) - 0.5, dq.y - 0.45), vec2(0.38, 0.55));
                pnl = mix(pnl, vec3(0.35, 0.4, 0.5) * (0.6 + 1.5 * D_B) + vec3(0.12, 0.1, 0.09), aaw(glassP, 0.02) * 0.8);
                vec3 dc = xr < open ? street * D_B : pnl;
                col = mix(col, dc, aaw(opening, fw));
            }
            // a framed print of the harbour and a mirror
            col = mix(col, vec3(0.05, 0.035, 0.02), aaw(sdBox(w - vec2(-0.6, 1.85), vec2(0.38, 0.27)), fw));
            col = mix(col, vec3(0.3, 0.26, 0.2) * L * 1.5, aaw(sdBox(w - vec2(-0.6, 1.85), vec2(0.33, 0.22)), fw));
        }
    } else if (h.s == 1) {
        col = tiles(p.xz * vec2(1.0, 1.0), vec3(0.32, 0.26, 0.2), 0.25, fw);
        float chk = mod(floor(p.x / 0.25) + floor(p.z / 0.25), 2.0);
        col *= 0.75 + 0.35 * chk;
        vec3 cl = dCold(p) * (1.0 - 0.8 * castPoint(p, D_CS, 0.03));
        col *= dAmb(p) + dLampLight(p) + cl;
    } else {
        col = vec3(0.3, 0.2, 0.12) * L * 0.6;
        float beams = smoothstep(0.04, 0.0, abs(fract(p.z / 0.9) - 0.5) - 0.42);
        col = mix(col, vec3(0.08, 0.05, 0.03) * L, beams);
    }
    col *= 0.6 + 0.4 * smoothstep(0.0, 0.6, cornerDist(h, D_ZB, D_XL, D_XR, D_HC));

    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.6, zb = min(p.z, D_ZB);
        float dz = (zb - za) / 22.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        vec3 rdn = normalize(RD);
        for (int i = 0; i < 22; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            float hd = hazeDen(q);
            vec3 c = dLampLight(q) * hd * 0.06 + dCold(q) * hd * 0.05 + dAmb(q) * 0.05;
            c *= dz * RDL;
            if (z > 4.9) vF += c; else if (z > Z0 + 0.2) vM += c; else vN += c * 0.6;
        }
    }
    col += vF;
    // ---- the lamps: cords, enamel shades, bright bulbs
    for (int k = 0; k < 3; k++) {
        vec3 lp = D_LAMP[k];
        vec2 w = at(lp.z);
        vec2 l = w - lp.xy;
        float cord = max(abs(l.x) - 0.006, -l.y);
        float shade = sdTrap(l - vec2(0.0, 0.06), 0.24, 0.05, 0.09);
        float a = aaw(min(cord, shade), PX * lp.z);
        vec3 c = vec3(0.04, 0.08, 0.05) * (dAmb(vec3(w, lp.z)) + 0.04);
        c += vec3(1.0, 0.75, 0.45) * 0.5 * smoothstep(0.02, -0.02, l.y + 0.0) * aaw(shade, 0.01);
        col = lay(col, c, a);
        float bulb = length(l - vec2(0.0, -0.04));
        col += vec3(1.0, 0.8, 0.55) * (7.0 * smoothstep(0.045, 0.02, bulb) + 0.5 * exp(-bulb * 9.0));
    }
    // ---- diners in the background: soft silhouettes at their tables
    for (int k = 0; k < 2; k++) {
        float z = k == 0 ? 4.8 : 5.6;
        float cx = k == 0 ? -1.15 : 1.55;
        vec2 w = at(z);
        vec2 l = w - vec2(cx, 0.0);
        float tbl = max(sdBox(l - vec2(0.0, 0.55), vec2(0.45, 0.2)), 0.38 - l.y);
        float tlegs = sdBox(l - vec2(0.0, 0.2), vec2(0.04, 0.2));
        float soft = PX * z * 2.5;
        vec3 q3 = vec3(w, z);
        vec3 Ld = dAmb(q3) + dLampLight(q3) + dCold(q3);
        for (int j = 0; j < 2; j++) {
            float sx = j == 0 ? -0.55 : 0.55;
            float hh = 0.04 * hash11(float(k * 2 + j));
            vec2 dq = l - vec2(sx, 0.0);
            float body = sdRBox(dq - vec2(0.0, 0.75), vec2(0.17, 0.27), 0.12);
            body = smin(body, sdCircle(dq - vec2(0.0, 1.17 + hh), 0.1), 0.05);
            body = min(body, sdBox(dq - vec2(0.0, 0.25), vec2(0.12, 0.25)));
            float arm = sdCapsule(dq, vec2(0.08 * -sign(sx), 0.88), vec2(0.32 * -sign(sx), 0.78 + 0.05 * sin(T * 0.8 + float(k))), 0.04);
            body = min(body, arm);
            float ad = aaw(body, soft);
            vec3 dc = vec3(0.016, 0.011, 0.008) * (1.0 + Ld);
            dc += vec3(1.0, 0.65, 0.35) * 0.16 * smoothstep(-0.04, 0.0, body) * ad;
            col = lay(col, dc, ad);
        }
        float at2 = aaw(min(tbl, tlegs), soft);
        col = lay(col, mix(vec3(0.75, 0.7, 0.62), vec3(0.15, 0.1, 0.06), step(tlegs, tbl)) * Ld, at2);
    }
    col += vM;
    // ---- Elena and Davide, then the little table in front of them
    {
        vec2 cS = toScreen(D_CANDLE);
        vec2 dS = toScreen(vec3(D_DOOR.xy, D_ZB));
        vec3 l2 = vec3(1.0, 0.62, 0.3) * 0.55 * (1.0 - 0.5 * D_B) + vec3(0.6, 0.78, 1.0) * D_B * 1.8;
        vec2 l2p = mix(cS, dS, D_B * 1.8 / (D_B * 1.8 + 0.55 * (1.0 - 0.5 * D_B)));
        vec2 lampS = toScreen(D_LAMP[2]);
        for (int i = 2; i >= 0; i--) {
            vec2 L1 = lampS - CP[i].xy - vec2(0.0, CP[i].z * 0.7);
            vec3 c3 = vec3(CP[i].x * CZ[i], CAMY + (CP[i].y + CP[i].z * 0.3) * CZ[i], CZ[i]);
            col = seatBehind(i, col, dAmb(c3) + dLampLight(c3) * 0.8 + dCold(c3));
            vec3 tint = vec3(0.24, 0.18, 0.14) * (1.0 - 0.35 * D_B) + vec3(0.04, 0.05, 0.08) * D_B;
            vec4 f = actor(i, L1, 0.95 - 0.3 * D_B, tint, l2, l2p);
            col = over(col, f);
        }
    }
    {
        float z = 2.9;
        vec2 w = at(z);
        vec2 l = w - vec2(0.0, 0.0);
        vec3 q3 = vec3(w, z);
        vec3 Lt = dAmb(q3) + dLampLight(q3) + dCold(q3);
        float hem = 0.025 * sin(l.x * 24.0) + 0.012 * sin(l.x * 57.0);
        float cloth = max(sdTrap(l - vec2(0.0, 0.62), 0.42, 0.38, 0.17), 0.45 + hem - l.y);
        float stem = sdBox(l - vec2(0.0, 0.25), vec2(0.035, 0.22));
        float base = sdEllipse(l - vec2(0.0, 0.02), vec2(0.2, 0.025));
        float d = min(cloth, min(stem, base));
        float folds = 0.75 + 0.25 * sin(l.x * 40.0 + 3.0 * sat(0.8 - l.y));
        vec3 c = vec3(0.82, 0.78, 0.7) * folds * Lt;
        c = mix(c, vec3(0.08, 0.05, 0.03) * Lt, step(stem, cloth) * step(stem, base) + step(base, cloth) * step(base, stem));
        col = lay(col, c, aaw(d, PX * z));
        // a straw-covered bottle holding the candle, and two glasses of red wine
        vec2 bq = l - vec2(0.0, 0.8);
        float bottle = min(sdEllipse(bq - vec2(0.0, 0.07), vec2(0.075, 0.08)), sdBox(bq - vec2(0.0, 0.17), vec2(0.016, 0.06)));
        vec3 bc = mix(vec3(0.5, 0.36, 0.16), vec3(0.05, 0.12, 0.05), step(0.12, bq.y)) * Lt * (0.8 + 0.3 * sin(bq.y * 120.0) * step(bq.y, 0.12));
        col = lay(col, bc, aaw(bottle, PX * z));
        float wax = sdBox(bq - vec2(0.0, 0.25), vec2(0.013, 0.035));
        col = lay(col, vec3(0.9, 0.85, 0.75) * Lt * 1.3, aaw(wax, PX * z));
        float lean = D_B * 0.6 * sin(T * 3.0) * 0.5 + D_B * 0.5;
        col += candle(SP + vec2(lean * 0.006, 0.0), toScreen(D_CANDLE + vec3(0.0, -0.01, 0.0)), 0.035, T, 1.0) * (1.0 - 0.6 * D_B * (0.5 + 0.5 * sin(T * 11.0)));
        for (int k = 0; k < 2; k++) {
            float sx = k == 0 ? -0.2 : 0.21;
            vec2 gq = l - vec2(sx, 0.8);
            float bowl = max(sdEllipse(gq - vec2(0.0, 0.13), vec2(0.045, 0.06)), gq.y - 0.16);
            float gs = min(sdBox(gq - vec2(0.0, 0.04), vec2(0.005, 0.045)), sdEllipse(gq - vec2(0.0, 0.0), vec2(0.035, 0.008)));
            float wine = max(bowl, gq.y - 0.12);
            vec3 gc = vec3(0.4, 0.38, 0.35) * Lt;
            col = lay(col, gc, aaw(min(bowl, gs), PX * z) * 0.35);
            col = lay(col, vec3(0.3, 0.02, 0.03) * (Lt * 1.5 + 0.05) + vec3(1.0, 0.4, 0.3) * 0.25 * smoothstep(0.015, 0.0, abs(gq.y - 0.12)), aaw(wine, PX * z) * 0.95);
            col += vec3(1.0, 0.85, 0.65) * 0.9 * aaw(length(gq - vec2(-0.022 * sign(sx), 0.15)) - 0.006, PX * z * 1.5);
        }
    }
    col += vN;
    // ---- foreground: the back of an empty bentwood chair at the next table, out of focus
    {
        float z = 1.9;
        vec2 w = at(z);
        vec2 l = w - vec2(1.5, 0.0);
        float soft = PX * z * 4.5;
        float loop = abs(sdEllipse(l - vec2(0.0, 0.78), vec2(0.17, 0.3))) - 0.016;     // the bent loop
        loop = max(loop, 0.5 - l.y);
        float inner = abs(sdEllipse(l - vec2(0.0, 0.72), vec2(0.09, 0.2))) - 0.011;
        inner = max(inner, 0.52 - l.y);
        float posts = sdBox(vec2(abs(l.x) - 0.17, l.y - 0.5), vec2(0.016, 0.5));
        float seat = sdRBox(l - vec2(0.0, 0.46), vec2(0.22, 0.025), 0.02);
        float legs = min(sdCapsule(l, vec2(-0.15, 0.44), vec2(-0.19, 0.0), 0.015), sdCapsule(l, vec2(0.15, 0.44), vec2(0.19, 0.0), 0.015));
        float ring = max(abs(sdEllipse(l - vec2(0.0, 0.2), vec2(0.17, 0.035))) - 0.008, 0.0);
        float d = min(min(loop, inner), min(min(posts, seat), min(legs, ring)));
        float a = aaw(d, soft);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            vec3 c = vec3(0.05, 0.03, 0.018) * (1.0 + dLampLight(q3) * 0.5);
            float lit = sat(a - aaw(d + 0.012, soft));
            c += mix(vec3(1.0, 0.65, 0.35), vec3(0.6, 0.78, 1.0), D_B) * lit * 0.1;
            col = lay(col, c, a * 0.97);
        }
    }
    col += vec3(0.7, 0.8, 1.0) * dust(SP, T * (1.0 + 3.0 * D_B), 0.12 + 0.2 * D_B, 0.05) * D_B * sat(lum(vN + vM) * 3.0);
    return col;
}

// =============================================================================================
// MODE 5: the deathbed. A very dim night room; Tommaso's small bed and pale glow; a table lamp;
// Elena kneeling on one side, Davide on the other. Without his glow the room empties.
// =============================================================================================
vec3 E_LAMP;
float E_GL;

vec3 eLamp(vec3 p) {
    float fl = 1.0 - uP[5].w * (0.35 * (0.5 + 0.5 * sin(T * 17.0)) * (0.5 + 0.5 * sin(T * 5.3 + 1.0)) + 0.25 * smoothstep(0.7, 1.0, vnoise(vec2(T * 4.0, 0.0))));
    vec3 d = p - E_LAMP;
    float down = smoothstep(-0.4, 0.4, -d.y / (length(d) + 1e-4));
    return vec3(1.0, 0.62, 0.3) * fl * (0.12 + 0.3 * down) / (0.05 + dot(d, d));
}
vec3 eGlow(vec3 p) {
    vec3 d = p - vec3(-0.05, 0.6, Z0);
    return SILVER * E_GL * 0.4 / (0.06 + dot(d, d));
}
vec3 eAmb(vec3 p) { return vec3(0.012, 0.016, 0.03) + vec3(0.06, 0.08, 0.15) * 0.08 * exp(-length(p.xy - C_WINk.xy)) + home(p) * 0.6; }

vec3 room5() {
    C_ZBk = C_ZB; C_WINk = C_WIN;
    C_CASE = 0.0; C_SHL = 0.0; C_SHR = 0.0;
    E_GL = uP[4].x * (1.0 - CHOLD[0]);
    float holdLvl = uP[4].x * CHOLD[0];
    E_LAMP = vec3(-0.6, 0.9, 4.35);
    Hit h = roomHit(C_ZB, C_XL, C_XR, C_HC, vec4(0.0), C_ZB);
    vec3 p = h.p;
    float fw = PX * p.z * 1.2;
    vec3 col;
    vec3 L = eAmb(p) + eLamp(p) + eGlow(p);
    vec3 wallBase = vec3(0.5, 0.42, 0.36);
    if (h.s == 0 || h.s >= 3) {
        col = cWall(p, h.s, wallBase, fw) * L;
        if (h.s == 0) {
            col = cWindow(col, p.xy, L, fw, 3, 0.0, vec3(0.0));
            // a curtain drawn half across the window
            vec2 cq = p.xy - C_WIN.xy;
            float cur = cq.x - (-0.05 + 0.04 * sin(cq.y * 5.0));
            float ca = aaw(-cur, fw) * step(abs(cq.y), C_WIN.w + 0.15) * step(cq.x, C_WIN.z + 0.25);
            float folds = 0.6 + 0.4 * sin(cq.x * 50.0);
            col = mix(col, vec3(0.25, 0.22, 0.3) * folds * (L * 1.3 + 0.004), ca * 0.97);
        }
    } else if (h.s == 1) {
        col = cFloor(p, fw) * L;
    } else {
        col = cWall(p, 0, wallBase * 0.8, fw) * L * 0.8;
    }
    col *= 0.55 + 0.45 * smoothstep(0.0, 0.6, cornerDist(h, C_ZB, C_XL, C_XR, C_HC));

    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.6, zb = min(p.z, C_ZB);
        float dz = (zb - za) / 20.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        for (int i = 0; i < 20; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            float hd = hazeDen(q);
            vec3 c = (eLamp(q) * 0.05 + eGlow(q) * 0.08) * hd + eAmb(q) * 0.03;
            c *= dz * RDL;
            if (z > 4.0) vF += c; else if (z > Z0 + 0.2) vM += c; else vN += c * 0.6;
        }
    }
    col += vF;
    // ---- the bedside table and the lamp
    {
        float z = E_LAMP.z;
        vec2 w = at(z);
        vec2 l = w - vec2(E_LAMP.x, 0.0);
        vec3 q3 = vec3(w, z);
        vec3 Lq = eAmb(q3) + eLamp(q3) * 0.5 + eGlow(q3);
        float tb = min(sdBox(l - vec2(0.0, 0.32), vec2(0.22, 0.32)), sdBox(l - vec2(0.0, 0.65), vec2(0.26, 0.02)));
        col = lay(col, vec3(0.16, 0.1, 0.06) * Lq * 1.4, aaw(tb, PX * z));
        float base = min(sdEllipse(l - vec2(0.0, 0.72), vec2(0.06, 0.05)), sdBox(l - vec2(0.0, 0.8), vec2(0.012, 0.08)));
        col = lay(col, vec3(0.3, 0.22, 0.12) * Lq, aaw(base, PX * z));
        float fl = 1.0 - uP[5].w * (0.35 * (0.5 + 0.5 * sin(T * 17.0)) * (0.5 + 0.5 * sin(T * 5.3 + 1.0)) + 0.25 * smoothstep(0.7, 1.0, vnoise(vec2(T * 4.0, 0.0))));
        vec2 sq = l - vec2(0.0, 0.97);
        float shade = sdTrap(sq, 0.15, 0.09, 0.1);
        vec3 sc = vec3(1.0, 0.68, 0.38) * fl * (1.2 + 1.4 * smoothstep(0.1, -0.1, sq.y)) * (0.85 + 0.15 * sin(sq.x * 90.0));
        col = lay(col, sc, aaw(shade, PX * z));
        col += vec3(1.0, 0.6, 0.3) * fl * 0.5 * exp(-length(sq * vec2(1.0, 1.6)) * 7.0);
    }
    col += vM;
    // ---- the small bed, the child of light, and the parents kneeling either side
    {
        float z = Z0;
        vec2 bw = at(z);
        vec2 l = bw - vec2(0.0, 0.0);
        vec3 q3 = vec3(bw, z);
        vec3 Lb = eAmb(q3) + eLamp(q3) + eGlow(q3);
        float len = 1.4;
        // iron headboard with bars, light passing between them
        vec2 hq = l - vec2(-len * 0.5, 0.0);
        float arch = abs(length(hq - vec2(0.0, 0.62)) - 0.24) - 0.018;
        arch = max(arch, 0.62 - hq.y);
        float posts = min(sdBox(hq - vec2(-0.24, 0.45), vec2(0.022, 0.45)), sdBox(hq - vec2(0.24, 0.45), vec2(0.022, 0.45)));
        float bars = max(abs(fract(hq.x / 0.08) - 0.5) * 0.08 - 0.008, max(abs(hq.x) - 0.24, abs(hq.y - 0.63) - 0.2));
        float hb = min(min(arch, posts), bars);
        hb = min(hb, sdBox(hq - vec2(0.0, 0.42), vec2(0.24, 0.02)));
        vec3 iron = vec3(0.32, 0.32, 0.34) * Lb * 1.2;
        col = lay(col, iron, aaw(hb, PX * z));
        float mattress = sdRBox(l - vec2(0.0, 0.43), vec2(len * 0.5, 0.075), 0.035);
        col = lay(col, vec3(0.5, 0.5, 0.55) * Lb, aaw(mattress, PX * z));
        float pillow = sdEllipse(l - vec2(-0.25, 0.545), vec2(0.18, 0.06));
        col = lay(col, vec3(0.7, 0.7, 0.75) * Lb * 1.1 + SILVER * E_GL * 0.25, aaw(pillow, PX * z));
        // the child under his blanket
        vec2 tp = toScreen(vec3(0.2, 0.5, z));
        vec4 tg = childGlow(SP, tp, 0.36, E_GL, 0.0);
        col = col * (1.0 - tg.a) + tg.rgb;
        // the blanket: translucent where his light is
        float bx = (SP.x - tp.x) / 0.36;
        float top = -0.25 + 0.36 * (0.14 * smoothstep(-0.27, -0.17, bx) - 0.025 * smoothstep(0.1, 0.5, bx) + 0.008 * sin(bx * 18.0));
        float blanket = max(max(SP.y - top, toScreen(vec3(0.0, 0.33, z)).y - SP.y + 0.006 * sin(SP.x * 120.0)), max(tp.x - 0.36 * 0.26 - SP.x, SP.x - toScreen(vec3(len * 0.5, 0.0, z)).x));
        float folds = 0.86 + 0.14 * sin(SP.x * 70.0 + 3.0 * sin(SP.y * 50.0 + SP.x * 13.0)) * (0.6 + 0.4 * vnoise(SP * 40.0));
        vec3 bc = vec3(0.62, 0.62, 0.68) * folds * Lb * 0.9;
        bc += SILVER * E_GL * 0.75 * exp(-length((SP - tp - vec2(0.0, 0.015)) * vec2(0.9, 1.8)) * 8.0);
        bc = mix(bc, vec3(0.75, 0.75, 0.8) * Lb + SILVER * E_GL * 0.5, smoothstep(0.012, 0.0, abs(SP.y - top + 0.008)) * step(tp.x - 0.36 * 0.26, SP.x));
        col = lay(col, bc, aaw(blanket, PX * 1.2));
        float foot = min(sdBox(l - vec2(len * 0.5, 0.33), vec2(0.022, 0.33)), sdBox(l - vec2(0.0, 0.32), vec2(len * 0.5, 0.025)));
        foot = min(foot, sdBox(l - vec2(-len * 0.5 + 0.24, 0.2), vec2(0.02, 0.2)));
        col = lay(col, iron * 0.9, aaw(foot, PX * z));
        // light pooling around the child on the sheet
        col += SILVER * E_GL * 0.12 * exp(-length((SP - tp) * vec2(0.8, 2.0)) * 6.0);
        // the parents
        vec2 glowS = tp + vec2(-0.04, 0.03);
        vec2 lampS = toScreen(E_LAMP + vec3(0.0, 0.1, 0.0));
        for (int i = 2; i >= 0; i--) {
            vec2 L1 = lampS - CP[i].xy - vec2(0.0, CP[i].z * 0.6);
            float lk = 0.45 + 0.4 * exp(-abs(CP[i].x - lampS.x) * 3.0);
            vec3 c3 = vec3(CP[i].x * CZ[i], CAMY + (CP[i].y + CP[i].z * 0.3) * CZ[i], CZ[i]);
            col = seatBehind(i, col, eAmb(c3) + eLamp(c3) + eGlow(c3));
            vec3 tint = vec3(0.07, 0.065, 0.09) + vec3(0.06, 0.06, 0.08) * E_GL;
            vec4 f = actor(i, L1, lk, tint, SILVER * (E_GL + holdLvl) * 0.75, glowS);
            col = over(col, f);
        }
        col = heldChild(col, holdLvl, vec3(0.12, 0.11, 0.15));
    }
    col += vN;
    // ---- foreground: the heavy fold of a curtain at the left edge
    {
        float z = 1.9;
        vec2 w = at(z);
        float edge = -1.5 + 0.05 * sin(w.y * 2.6 + 0.5) + 0.07 * smoothstep(0.4, -0.5, w.y);
        float d = w.x - edge;
        float a = aaw(d, PX * z * 3.5);
        if (a > 0.0) {
            float ph = (w.x - edge) * 22.0 + 0.6 * sin(w.y * 1.7);
            float folds = 0.5 + 0.5 * sin(ph);
            vec3 q3 = vec3(w, z);
            vec3 Lc = eAmb(q3) * 2.0 + eLamp(q3) * 0.35 + eGlow(q3) * 0.5;
            vec3 c = vec3(0.13, 0.08, 0.09) * Lc * (0.35 + 0.9 * folds * folds);
            c += vec3(1.0, 0.62, 0.3) * 0.02 * smoothstep(-0.04, 0.0, d);
            col = lay(col, c, a);
        }
    }
    col += SILVER * dust(SP, T * 0.5, 0.1, 0.05) * E_GL * 0.25;
    // when his light is gone the room grows cold and still
    float empt = 1.0 - smoothstep(0.0, 0.35, uP[4].x);
    col = mix(col, vec3(lum(col)) * vec3(0.75, 0.85, 1.1), empt * 0.45);
    return col;
}

// =============================================================================================
// MODE 6: the empty room at dawn. Grey-blue light; the window and sea dim; Davide's empty chair
// outlined in amber, Tommaso's folded blanket outlined in silver; Elena alone. uP[0].w flies
// the walls and furniture away like stage flats, revealing darkness and a golden light below.
// =============================================================================================
float G_W;
vec4 G_LIFT;
float gLift(float a, float b) { float x = smoothstep(a, b, G_W); return 7.0 * x * x; }
vec3 gAmb(vec3 p) {
    vec3 a = vec3(0.07, 0.085, 0.11) + vec3(0.14, 0.16, 0.2) * 0.35 * exp(-length(p.xy - C_WIN.xy - vec2(0.0, G_LIFT.x)) * 0.7);
    return a * (1.0 - 0.8 * smoothstep(0.2, 0.8, G_W)) + home(p) * 0.7;
}
vec3 gGold(vec3 p) {     // the golden light rising from below as the room flies out
    float k = smoothstep(0.1, 0.9, G_W);
    return vec3(1.0, 0.7, 0.32) * k * (0.25 + 0.9 * exp(-max(p.y, 0.0) * 0.9)) * (0.6 + 0.4 * smoothstep(6.0, 1.5, p.z));
}

vec3 room6() {
    C_ZBk = C_ZB; C_WINk = C_WIN;
    C_CASE = 1.0; C_SHL = 1.0; C_SHR = 1.0;
    G_W = sat(uP[0].w);
    G_LIFT = vec4(gLift(0.12, 0.8), gLift(0.0, 0.62), gLift(0.22, 0.95), gLift(0.05, 0.7));
    float fEnd = C_ZB + 0.25;
    if (G_W > 0.0) FLOORPAD = 0.25;
    Hit h = roomHit(C_ZB, C_XL, C_XR, C_HC, G_LIFT, fEnd);
    FLOORPAD = 1e3;
    vec3 p = h.p;
    float fw = PX * p.z * 1.2;
    vec3 col;
    vec3 wallBase = vec3(0.5, 0.48, 0.47);
    float k = smoothstep(0.05, 0.85, G_W);
    if (h.s == 5) {
        // the void: darkness above, a golden light welling up from far below the stage
        vec2 v = vec2(RD.x / RD.z, RD.y / RD.z);
        col = vec3(0.004, 0.004, 0.007);
        float below = smoothstep(0.08, -0.5, v.y);
        float rays = 0.6 + 0.4 * vnoise(vec2(v.x * 7.0 / (0.6 - v.y), T * 0.06));
        rays *= 0.75 + 0.25 * sin(v.x * 34.0 / (0.7 - v.y) + 2.0 * vnoise(vec2(v.x * 2.0, T * 0.05)));
        col += vec3(1.0, 0.62, 0.25) * k * (2.4 * below * below * rays + 0.08 * exp(-abs(v.y + 0.12) * 5.0));
        vec2 g = vec2(v.x * 36.0, v.y * 36.0 - T * 0.5);
        vec2 id = floor(g);
        float mote = step(0.955, hash21(id)) * smoothstep(0.25, 0.0, length(fract(g) - 0.5 - (hash22(id) - 0.5) * 0.5));
        mote *= 0.5 + 0.5 * sin(T * (1.0 + 2.0 * hash21(id + 5.0)) + hash21(id) * 6.28);
        col += vec3(1.0, 0.78, 0.4) * mote * k * 1.4 * smoothstep(0.4, -0.3, v.y);
    } else if (h.s == 0 || h.s >= 3) {
        vec3 pl = p;
        if (h.s == 0) pl.y -= G_LIFT.x;
        if (h.s == 3) pl.y -= G_LIFT.y;
        if (h.s == 4) pl.y -= G_LIFT.z;
        vec3 L = gAmb(pl) + gGold(p) * 0.5;
        col = cWall(pl, h.s, wallBase, fw) * L;
        if (h.s == 0) col = cWindow(col, pl.xy, L, fw, 1, 0.0, vec3(0.1, 0.12, 0.16));
        // the bottom edge of a flat in flight: its timber frame
        col = mix(col, vec3(0.03, 0.025, 0.02), band01(pl.y, 0.0, 0.05, fw) * step(0.01, G_W));
        if (h.s == 0) col = mix(col, cWindow(col, pl.xy, L, fw, 1, 0.0, vec3(0.1, 0.12, 0.16)), 0.0);
    } else if (h.s == 1) {
        // light spilling over the edges of the stage from below
        float edgeD = min(fEnd - p.z, min(p.x - (C_XL - 0.25), (C_XR + 0.25) - p.x));
        vec3 spill = vec3(1.0, 0.62, 0.25) * k * 1.4 * exp(-max(edgeD, 0.0) * 2.2);
        vec3 fl = cFloor(p, fw);
        fl = mix(fl, vec3(lum(fl)) * vec3(0.95, 0.9, 0.85), 0.45 + 0.35 * k) * (1.0 - 0.45 * k);
        col = fl * (gAmb(p) + gGold(p) * 0.45 + spill);
        col += vec3(1.0, 0.7, 0.35) * k * 0.6 * smoothstep(0.03, 0.0, edgeD);
    } else {
        col = cWall(p, 0, wallBase * 0.8, fw) * gAmb(p) * 0.8;
    }
    if (h.s != 5) col *= 0.6 + 0.4 * smoothstep(0.0, 0.6, cornerDist(h, C_ZB, C_XL, C_XR, C_HC + G_LIFT.w));

    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.6, zb = min(p.z, 9.0);
        float dz = (zb - za) / 18.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        for (int i = 0; i < 18; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            float hd = hazeDen(q);
            vec3 c = (gAmb(q) * 0.05 + gGold(q) * 0.035 * smoothstep(1.5, 0.0, q.y)) * hd;
            c *= dz * RDL;
            if (z > 4.0) vF += c; else if (z > Z0 + 0.4) vM += c; else vN += c * 0.6;
        }
    }
    col += vF;
    // ---- the bare table, flown out with the back wall
    {
        float z = 4.3;
        float lift = gLift(0.18, 0.85);
        vec2 w = at(z);
        vec2 l = w - vec2(-0.25, lift);
        float d = min(sdBox(l - vec2(0.0, 0.74), vec2(0.6, 0.025)), min(sdBox(l - vec2(-0.52, 0.36), vec2(0.03, 0.36)), sdBox(l - vec2(0.52, 0.36), vec2(0.03, 0.36))));
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            col = lay(col, vec3(0.2, 0.15, 0.11) * (gAmb(q3) * 1.3 + gGold(q3) * 0.4), a);
        }
    }
    col += vM;
    // ---- the remembered things: his chair in amber, the folded blanket in silver
    {
        float z = 3.35;
        float lift = gLift(0.32, 1.0);
        vec2 w = at(z);
        vec2 l = w - vec2(1.25, lift);
        l = rot(0.08 * smoothstep(0.32, 1.0, G_W) * sin(T * 0.8)) * (l - vec2(0.0, 1.0)) + vec2(0.0, 1.0);
        float d = chairSD(l, -1.0);
        vec3 q3 = vec3(w, z);
        float a = aaw(d, PX * z);
        vec3 c = vec3(0.06, 0.065, 0.08) * (gAmb(q3) * 2.0 + gGold(q3) * 0.3);
        col = lay(col, c, a);
        col += vec3(1.0, 0.6, 0.25) * 0.3 * outline(d, 0.005 + PX * z) * (0.85 + 0.15 * sin(T * 0.7));
        col += vec3(1.0, 0.6, 0.25) * 0.025 * exp(-max(d, 0.0) * 10.0);

        z = 3.3;
        w = at(z);
        l = w - vec2(-1.6, gLift(0.28, 0.98));
        float sc = smallChairSD(l);
        float blank = sdRBox(l - vec2(0.0, 0.47), vec2(0.2, 0.045), 0.02);
        blank = min(blank, sdRBox(l - vec2(0.0, 0.535), vec2(0.18, 0.03), 0.02));
        q3 = vec3(w, z);
        col = lay(col, vec3(0.08, 0.07, 0.07) * (gAmb(q3) * 2.0 + gGold(q3) * 0.3), aaw(sc, PX * z));
        float ab = aaw(blank, PX * z);
        col = lay(col, vec3(0.42, 0.44, 0.5) * (gAmb(q3) * 1.5 + gGold(q3) * 0.25), ab);
        float folds = smoothstep(0.004, 0.0, abs(l.y - 0.505)) * step(abs(l.x), 0.17) * ab;
        col = mix(col, col * 0.6, folds);
        col += SILVER * 0.36 * outline(blank, 0.004 + PX * z) * (0.85 + 0.15 * sin(T * 0.9 + 1.0));
        col += SILVER * 0.03 * exp(-max(blank, 0.0) * 9.0);
    }
    {
        vec2 winS = toScreen(vec3(C_WIN.xy + vec2(0.0, G_LIFT.x), C_ZB));
        vec2 goldS = vec2(SP.x * 0.3, -0.75);
        for (int i = 2; i >= 0; i--) {
            vec2 L1 = mix(winS - CP[i].xy - vec2(0.0, CP[i].z * 0.7), vec2(0.0, -1.0), smoothstep(0.3, 0.9, G_W));
            float gk = smoothstep(0.1, 0.9, G_W);
            vec3 c3 = vec3(CP[i].x * CZ[i], CAMY + (CP[i].y + CP[i].z * 0.3) * CZ[i], CZ[i]);
            col = seatBehind(i, col, gAmb(c3) * 1.5 + gGold(c3) * 0.3);
            vec4 f = actor(i, L1, 0.45 + 0.6 * gk, vec3(0.28, 0.28, 0.33) * (1.0 - 0.4 * gk) + vec3(0.2, 0.12, 0.04) * gk, vec3(1.0, 0.65, 0.3) * gk * 0.7, vec2(CP[i].x, -0.7));
            col = over(col, f);
        }
    }
    col += vN;
    col += vec3(1.0, 0.75, 0.4) * dust(SP + vec2(0.0, -T * 0.01), T, 0.12, 0.05) * smoothstep(0.2, 0.9, G_W) * 0.5;
    return col;
}

// =============================================================================================
// MODE 7: the apartment at dusk. On the right, the entrance: a doorway of warm light in the
// wall of the little hall, just behind the threshold, with Davide on it (about (0.42, -0.43)
// at height 0.56); uP[4].w closes the door. Elena on the left in shadow by the window.
// =============================================================================================
const float F_ZB = 4.4, F_XL = -2.6, F_XR = 2.6, F_HC = 2.95;
const vec4 F_WIN = vec4(-1.2, 1.6, 0.5, 0.66);
const float F_PZ = 3.1;                          // the hall wall, just behind the threshold
const float F_PX0 = 0.52;                        // where it ends, on the left
const float F_PT = 0.14;                         // its thickness
const vec3 F_DOORC = vec3(1.28, 2.15, 0.48);     // the doorway in it: centre x, height, half width
vec3 F_S;          // the lamp on the landing
float F_PHI;       // door panel angle (0 shut .. PI/2 wide open)
float F_OPEN;

// the door, hinged on the right jamb, swings into the room, so from the camera the light
// narrows to a slit at the left jamb as it shuts: ray parameter of the hit (or 1e5)
float fPanelHit(vec3 ro, vec3 rd, float tmax, out vec2 uv) {
    vec3 H = vec3(F_DOORC.x + F_DOORC.z, 0.0, F_PZ);
    vec3 u = vec3(-cos(F_PHI), 0.0, -sin(F_PHI));
    vec3 n = vec3(-u.z, 0.0, u.x);
    float den = dot(rd, n);
    uv = vec2(0.0);
    if (abs(den) < 1e-6) return 1e5;
    float t = dot(H - ro, n) / den;
    if (t <= 0.0 || t >= tmax) return 1e5;
    vec3 x = ro + rd * t;
    float uu = dot(x - H, u);
    if (uu < 0.0 || uu > 2.0 * F_DOORC.z || x.y < 0.0 || x.y > F_DOORC.y) return 1e5;
    uv = vec2(uu, x.y);
    return t;
}
// visibility of the landing lamp from a point in the room, through the doorway and past the door
float fDoorLit(vec3 p) {
    if (F_OPEN <= 0.0 || p.z >= F_PZ) return 0.0;
    vec3 d = F_S - p;
    float u = (F_PZ - p.z) / d.z;
    if (u <= 0.0 || u >= 1.0) return 0.0;
    vec3 q = p + d * u;
    float b = 0.01 + 0.08 * (1.0 - u);
    float x0 = F_DOORC.x - F_DOORC.z, x1 = F_DOORC.x + F_DOORC.z;
    float lit = smoothstep(x0 - b, x0 + b, q.x) * (1.0 - smoothstep(x1 - b, x1 + b, q.x)) * (1.0 - smoothstep(F_DOORC.y - b, F_DOORC.y + b, q.y));
    if (lit <= 0.0) return 0.0;
    vec2 uv;
    return fPanelHit(p, d, 1.0, uv) < 1.0 ? 0.0 : lit;
}
vec3 fDoorLight(vec3 p) {
    vec3 d = F_S - p;
    return vec3(1.0, 0.6, 0.28) * fDoorLit(p) * F_OPEN * 7.0 / (0.6 + dot(d, d));
}
vec3 fAmb(vec3 p) {
    vec3 a = vec3(0.022, 0.022, 0.045) + vec3(0.1, 0.08, 0.16) * 0.22 * exp(-length(p.xy - F_WIN.xy) * 0.8) * smoothstep(2.0, F_ZB, p.z);
    // warm bounce from the pool of light on the floor before the door
    a += vec3(1.0, 0.6, 0.28) * F_OPEN * 0.05 * exp(-length(p.xz - vec2(F_DOORC.x - 0.2, 2.4)) * 1.2) * exp(-p.y * 0.8);
    return a + home(p) * 0.6;
}
// the lit landing seen through the doorway
vec3 fLanding() {
    vec2 b = at(F_PZ + 1.7);
    vec3 land = vec3(0.9, 0.55, 0.26) * 1.6 * (0.75 + 0.25 * fbm(b * 2.0));
    land *= 0.55 + 0.6 * exp(-length(b - vec2(F_S.x, 2.4)) * 0.7);
    vec2 b2 = at(F_PZ + 0.8);
    float rail = min(abs(b2.y - 0.95) - 0.025, max(abs(fract(b2.x / 0.14) - 0.5) * 0.14 - 0.01, b2.y - 0.95));
    rail = max(rail, -b2.y);
    land = mix(land, vec3(0.12, 0.06, 0.03), aaw(rail, PX * 4.0) * step(F_DOORC.x - 0.1, b2.x));
    vec2 b3 = at(F_PZ + 1.65);
    land *= 1.0 - 0.6 * smoothstep(0.02, 0.0, b3.y - 0.1);                      // its skirting
    land += vec3(1.0, 0.8, 0.5) * 3.0 * exp(-length(b - vec2(F_S.x, 2.35)) * 6.0);
    // the landing floor, in perspective, under the lamp
    if (RD.y < 0.0) {
        float tf = -RO.y / RD.y;
        vec3 fp = RO + RD * tf;
        if (fp.z < F_PZ + 1.7) {
            vec3 fl = tiles(fp.xz, vec3(0.42, 0.22, 0.12), 0.3, PX * fp.z * 1.2);
            float fall = 1.0 / (0.6 + 0.35 * dot(fp - F_S, fp - F_S));
            land = fl * vec3(1.0, 0.62, 0.3) * 4.0 * fall;
        }
    }
    return land * F_OPEN + vec3(0.01, 0.008, 0.006);
}

vec3 room7() {
    C_ZBk = F_ZB; C_WINk = F_WIN;
    C_CASE = 0.0; C_SHL = 1.0; C_SHR = 1.0;
    F_OPEN = sat(uP[4].w);
    F_PHI = (PI * 0.5) * smoothstep(0.0, 1.0, F_OPEN);
    F_S = vec3(F_DOORC.x + 0.12, 2.35, F_PZ + 1.4);
    Hit h = roomHit(F_ZB, F_XL, F_XR, F_HC, vec4(0.0), F_ZB);
    // the hall wall: 1 its face, 2 the doorway, 3 its end
    int part = 0;
    vec3 pp = RO + RD * (F_PZ / Z0);
    if (F_PZ / Z0 < h.t && pp.x > F_PX0 && pp.x < F_XR && pp.y < F_HC && pp.y > 0.0)
        part = (abs(pp.x - F_DOORC.x) < F_DOORC.z && pp.y < F_DOORC.y) ? 2 : 1;
    vec3 pe = vec3(0.0);
    float te = 1e5;
    if (part == 0 && RD.x > 0.0) {
        te = (F_PX0 - RO.x) / RD.x;
        pe = RO + RD * te;
        if (te < h.t && pe.z > F_PZ && pe.z < F_PZ + F_PT && pe.y > 0.0 && pe.y < F_HC) part = 3;
    }
    vec3 p = part == 0 ? h.p : (part == 3 ? pe : pp);
    float fw = PX * p.z * 1.2;
    vec3 col;
    vec3 wallBase = vec3(0.5, 0.42, 0.38);
    if (part == 1 || part == 2) {
        vec3 L = fAmb(p);
        col = cWall(p, 0, wallBase, fw) * L;
        vec2 dq = p.xy - vec2(F_DOORC.x, F_DOORC.y * 0.5);
        float dd = sdBox(dq, vec2(F_DOORC.z, F_DOORC.y * 0.5));
        float casing = abs(dd - 0.04) - 0.04;
        vec3 cc = vec3(0.32, 0.24, 0.16) * (L * 1.4 + 0.004);
        cc += vec3(1.0, 0.62, 0.3) * F_OPEN * 0.25 * smoothstep(0.0, -0.08, dd - 0.08) * smoothstep(-0.02, 0.06, dd);
        col = mix(col, cc, aaw(casing, fw));
        if (part == 2) col = mix(col, fLanding(), aaw(dd, fw));
    } else if (part == 3) {
        col = cWall(vec3(p.z, p.y, p.x), 0, wallBase * 0.8, fw) * fAmb(p) * 0.6;
    } else if (h.s == 0 || h.s >= 3) {
        vec3 L = fAmb(p) + fDoorLight(p);
        col = cWall(p, h.s, wallBase, fw) * L;
        if (h.s == 0) col = cWindow(col, p.xy, L, fw, 2, 0.0, vec3(0.3, 0.15, 0.1) * 0.3);
    } else if (h.s == 1) {
        vec3 dl = fDoorLight(p) * (1.0 - 0.85 * castPoint(p, F_S, 0.012));
        col = cFloor(p, fw) * (fAmb(p) + dl);
    } else {
        col = cWall(p, 0, wallBase * 0.8, fw) * (fAmb(p) * 0.8 + fDoorLight(p) * 0.3);
    }
    if (part == 0) col *= 0.55 + 0.45 * smoothstep(0.0, 0.6, cornerDist(h, F_ZB, F_XL, F_XR, F_HC));
    float tHit = part == 0 ? h.t : (part == 3 ? te : F_PZ / Z0);
    // the door itself
    {
        vec2 uv;
        float tp = fPanelHit(RO, RD, tHit + 0.001, uv);
        if (tp < 1e4) {
            vec3 q = RO + RD * tp;
            float pan = sdRBox(vec2(uv.x - F_DOORC.z, uv.y - 1.45), vec2(F_DOORC.z - 0.12, 0.5), 0.02);
            pan = min(pan, sdRBox(vec2(uv.x - F_DOORC.z, uv.y - 0.55), vec2(F_DOORC.z - 0.12, 0.3), 0.02));
            vec3 wood = vec3(0.22, 0.13, 0.07) * (0.85 + 0.2 * vnoise(uv * vec2(4.0, 25.0)));
            wood *= 1.0 - 0.35 * smoothstep(0.02, 0.0, abs(pan));
            vec3 Lp = fAmb(q) * 1.5 + vec3(1.0, 0.6, 0.28) * F_OPEN * 0.3 * smoothstep(0.35, 0.0, uv.x);
            col = wood * Lp;
            col += vec3(1.0, 0.65, 0.3) * 0.18 * F_OPEN * smoothstep(0.025, 0.0, abs(uv.x - 2.0 * F_DOORC.z)) * step(0.05, F_PHI);
            tHit = tp;
        }
    }

    vec3 vF = vec3(0.0), vM = vec3(0.0), vN = vec3(0.0);
    {
        float za = 1.6, zb = min(Z0 * tHit, F_ZB);
        float dz = (zb - za) / 24.0;
        float jit = ign(gl_FragCoord.xy + fract(T * 7.0) * 61.0);
        vec3 rdn = normalize(RD);
        for (int i = 0; i < 24; i++) {
            float z = za + (float(i) + jit) * dz;
            vec3 q = at3(z);
            vec3 c = fAmb(q) * 0.03;
            vec3 dl = fDoorLight(q);
            if (dl.r > 0.0) {
                float ph = 0.4 + 1.2 * pow(sat(dot(-rdn, normalize(q - F_S))), 4.0);
                dl *= 1.0 - castPoint(q, F_S, 0.01);
                c += dl * hazeDen(q) * 0.06 * ph;
            }
            c *= dz * RDL;
            if (z > F_PZ + 0.05) vF += c; else if (z > Z0 + 0.05) vM += c; else vN += c * 0.6;
        }
    }
    col += vF;
    // ---- the table and two chairs by the window wall
    if (part == 0) {
        float z = 3.9;
        vec2 w = at(z);
        vec2 l = w - vec2(-0.75, 0.0);
        float d = min(sdBox(l - vec2(0.0, 0.73), vec2(0.5, 0.025)), min(sdBox(l - vec2(-0.44, 0.36), vec2(0.025, 0.36)), sdBox(l - vec2(0.44, 0.36), vec2(0.025, 0.36))));
        d = min(d, chairSD(l - vec2(-0.7, 0.0), 1.0));
        d = min(d, chairSD(l - vec2(0.72, 0.0), -1.0));
        float a = aaw(d, PX * z);
        if (a > 0.0) {
            vec3 q3 = vec3(w, z);
            col = lay(col, vec3(0.14, 0.09, 0.06) * (fAmb(q3) * 1.4 + fDoorLight(q3) * 0.6), a);
        }
    }
    col += vM;
    {
        vec2 doorS = toScreen(vec3(F_DOORC.x, 1.3, F_PZ + 0.4));
        vec2 winS = toScreen(vec3(F_WIN.xy, F_ZB));
        for (int i = 2; i >= 0; i--) {
            float inLight = exp(-abs(CP[i].x - doorS.x) * 6.0) * F_OPEN;
            vec2 L1 = mix(winS, doorS, step(0.0, CP[i].x - (winS.x + doorS.x) * 0.5)) - CP[i].xy - vec2(0.0, CP[i].z * 0.7);
            vec3 c3 = vec3(CP[i].x * CZ[i], CAMY + (CP[i].y + CP[i].z * 0.3) * CZ[i], CZ[i]);
            col = seatBehind(i, col, fAmb(c3) * 1.5 + fDoorLight(c3) * 0.3);
            WRAP = inLight;
            vec3 tint = i == 0 ? vec3(0.085, 0.08, 0.115) : vec3(0.12, 0.1, 0.1);
            float rk = i == 0 ? 0.32 : 0.5 + 1.6 * inLight;
            vec4 f = actor(i, L1, rk, tint, vec3(1.0, 0.6, 0.28) * F_OPEN * 0.22 * (1.0 - inLight), doorS);
            WRAP = 0.0;
            col = over(col, f);
        }
    }
    col += vN;
    col += vec3(1.0, 0.7, 0.4) * dust(SP, T, 0.15, 0.05) * sat(lum(vN + vM) * 5.0) * 0.6;
    return col;
}

// =============================================================================================
void main() {
    SP = screen();
    T = uTime;
    PX = PIXEL;
    MODE = int(uP[0].x + 0.5);
    DRIFT = clamp(uP[0].y * 25.0, -1.2, 1.2);
    RO = vec3(DRIFT, CAMY, 0.0);
    RD = vec3(SP.x * Z0 - DRIFT, SP.y * Z0, Z0);
    RDL = length(RD) / Z0;

    // ---- the company of characters for this room
    vec3 bodyE = vec3(0.45, 0.03, 0.06), rimE = vec3(1.0, 0.45, 0.35);
    vec3 bodyD = vec3(0.35, 0.2, 0.06), rimD = vec3(1.0, 0.7, 0.35);
    vec3 bodyV = vec3(0.04, 0.05, 0.08), rimV = vec3(0.45, 0.6, 1.0);
    vec3 bodyM = vec3(0.12, 0.1, 0.25), rimM = vec3(0.6, 0.55, 1.0);
    vec3 bodyN = vec3(0.2, 0.16, 0.24), rimN = vec3(0.75, 0.62, 0.85);
    CB[0] = bodyE; CR[0] = rimE; CHR[0] = 2.0;
    CB[1] = bodyD; CR[1] = rimD; CHR[1] = 0.0;
    CB[2] = bodyN; CR[2] = rimN; CHR[2] = 1.0;
    float flare[3];
    flare[0] = 0.3; flare[1] = 0.0; flare[2] = 0.25;
    if (MODE == 0) { CB[1] = bodyM; CR[1] = rimM; CHR[1] = 1.0; flare[1] = 0.25; }
    if (MODE == 1) { CB[1] = bodyV; CR[1] = rimV; CB[2] = vec3(0.1, 0.09, 0.08); CR[2] = vec3(0.5, 0.48, 0.45); }
    if (MODE == 2) { CB[1] = bodyV; CR[1] = rimV; }
    // the full opera recasts the third figure: uP[6].y = 1 Vittorio (the proposal in the parlour),
    // 2 Marco (in green, his motif's colour); 0 (the film, always) keeps the room's own company
    if (uP[6].y > 0.5 && uP[6].y < 1.5) { CB[2] = bodyV; CR[2] = rimV; CHR[2] = 0.0; flare[2] = 0.0; }
    if (uP[6].y > 1.5) { CB[2] = vec3(0.05, 0.14, 0.09); CR[2] = vec3(0.55, 1.0, 0.7); CHR[2] = 0.0; flare[2] = 0.0; }
    bool holdMode = (MODE == 1 || MODE == 3 || MODE == 5);
    for (int i = 0; i < 3; i++) {
        vec4 P = uP[1 + i];
        float pose = (i == 0) ? uP[5].x : (i == 1 ? uP[5].y : uP[5].z);
        float v = pose < 1.5 ? (pose < 0.5 ? 0.0 : 1.0) : floor(pose + 0.5);
        float lift = sat(pose);
        float sway = 0.012 * sin(T * 0.6 + float(i) * 2.1);
        vec2 rest = vec2(0.02 + 0.015 * sin(T * 0.45 + float(i)), 0.02 + 0.015 * sin(T * 0.5 + float(i) + 1.0));
        vec4 ps = vec4(rest, flare[i], sway);
        CHOLD[i] = 0.0;
        if (pose < 1.5) {
            if (holdMode && i == 0 && pose > 0.5) {
                ps.xy = mix(rest, vec2(-0.25, -0.25), lift);
                CHOLD[i] = 1.0;
            } else {
                ps.xy = mix(rest, vec2(1.95, 1.35), lift);
            }
        } else if (v < 2.5) {
            ps.xy = vec2(0.3, 0.3);
            ps.w = 0.0;
        } else if (v > 3.5) {
            ps.xy = vec2(-0.12, -0.12);
            ps.w = 0.0;
        }
        // at the deathbed and the trattoria table, kneeling or seated figures reach and lean in
        if ((MODE == 4 || MODE == 5) && ((v > 1.5 && v < 2.5) || v > 3.5)) {
            float side = P.x < 0.0 ? 1.0 : -1.0;
            float reach = v < 2.5 ? 0.85 : 0.5;
            if (side > 0.0) ps.y = reach; else ps.x = reach;
            ps.w = side * (v < 2.5 ? 0.11 : 0.05);
        }
        CV[i] = v;
        CPOSE[i] = ps;
        float z = (v > 2.5 && v < 3.5) ? Z0 : CAMY / max(-P.y, 0.08);
        z = clamp(z, 1.2, 14.0);
        CZ[i] = z;
        P.x += DRIFT * (1.0 / Z0 - 1.0 / z);
        CP[i] = P;
    }

    A_SUN = normalize(vec3(0.3, -0.5, -0.81));
    B_MOON = normalize(vec3(-0.25, -0.5, -0.83));
    C_MOON = normalize(vec3(-0.32, -0.42, -0.85));
    C_SUN = normalize(vec3(-0.38, -0.45, -0.81));

    // mode 2: Vittorio exists only as the vision (uP[2] positions it, see room2)
    if (MODE == 2) CP[1].w = 0.0;
    // mode 2: a sleeper is laid in the bed, wherever the timeline put her
    if (MODE == 2 && CV[0] > 2.5 && CV[0] < 3.5) {
        CP[0].xy = vec2(-0.47 + 0.42 * CP[0].z, -0.235);
        CZ[0] = Z0;
    }

    // where Davide's warmth pools: under the table, the bed, his empty chair, the threshold
    if (MODE == 4 || MODE == 5) HOMEC = vec2(0.0, 3.1);
    if (MODE == 6) HOMEC = vec2(1.2, 3.4);
    if (MODE == 7) HOMEC = vec2(1.2, 4.0);

    vec3 col = vec3(0.0);
    if (MODE == 0) col = room0();
    else if (MODE == 1) col = room1();
    else if (MODE == 2) col = room2();
    else if (MODE == 3) col = room3();
    else if (MODE == 4) col = room4();
    else if (MODE == 5) col = room5();
    else if (MODE == 6) col = room6();
    else col = room7();
    fragColor = vec4(max(col, 0.0), 1.0);
}
