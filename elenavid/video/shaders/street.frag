#version 430
// THE STREET - Act II, scene 3: Trieste, 1957. A street of Habsburg palazzi runs down to the sea;
// where it ends lie the Riva, the long stone finger of the Molo Audace in grey-blue water, and the
// Karst hills across the bay with the Faro della Vittoria. A bora sky streams out to sea. Elena,
// on an errand, meets Marco again.
// The palazzi are true perspective planes (window reveals and balcony soffits widen with depth);
// everything else is a paper flat or billboard standing on the ground, faded into the cool air.
#include common

// uP[0].x camera pan (screen units at the figures' depth; everything parallaxes by depth)
// uP[1] Elena (feet x, feet y, height, alpha)     uP[2] Marco (feet x, feet y, height, alpha)
// uP[3].x passers-by 0..1                          uP[3].y daylight 0..1 (1 = brighter, softer)
// Figure positions are given at pan 0; figures stand on the street and pan with it.

// ------------------------------------------------------------------ scene state (set in main)
float PAN, LIGHT, T, PX, GUST;
float YH, CAMH, DENS, FOGP, X0;
vec2 SUN, SH;
float TANE, SINE, SUNVIS;
vec3 SUNC, AIRC, SKYC;
vec4 POSE_E, POSE_M;

const float W = 3.2;        // half-width of the street between the facades (world units ~ 3.3 m)
const float ZEND = 11.0;    // the palazzi end here and the Riva opens
const float ZQ = 12.6;      // the quay's edge
const float YW = -0.5;      // the sea, below the level of the street
const float YCL = 9.0;      // the cloud deck
const float HW = 5.8;       // the top of the palazzi's roof balustrades

// ------------------------------------------------------------------ projection and air
float groundZ(float y) { return CAMH / max(YH - y, 1e-4); }
float yBase(float z) { return YH - CAMH / z; }
float fogF(float z) { return 1.0 - exp(-pow(max(z, 0.0) * DENS, FOGP)); }

vec3 air(vec2 p) {
    float r = length((p - SUN) * vec2(0.8, 1.0));
    float up = sat((p.y - YH) * 2.0);
    return AIRC * (1.0 - 0.25 * up) + SUNC * (0.05 * exp(-r * 2.5) + 0.08 * exp(-r * 8.0));
}

float band1(float x, float lo, float hi, float fw) {
    return smoothstep(lo - fw, lo + fw, x) - smoothstep(hi - fw, hi + fw, x);
}
float rectC(vec2 q, vec2 lo, vec2 hi, vec2 fw) { return band1(q.x, lo.x, hi.x, fw.x) * band1(q.y, lo.y, hi.y, fw.y); }

// ------------------------------------------------------------------ sky: bora cloud streaming out to sea
vec3 skyBase(vec2 p) {
    float h = p.y - YH;
    vec3 hor = vec3(0.80, 0.84, 0.82), mid = vec3(0.50, 0.60, 0.64), zen = vec3(0.19, 0.29, 0.35);
    vec3 c = mix(hor, mid, smoothstep(0.0, 0.16, h));
    c = mix(c, zen, smoothstep(0.12, 0.62, h));
    return c * mix(0.6, 1.05, LIGHT);
}
float cloudAt(vec2 p) {
    float h = p.y - YH;
    if (h <= 0.0) return 0.0;
    float zc = (YCL - CAMH) / max(h, 0.004);              // distance to the deck along this line of sight
    vec2 cq = vec2((p.x - X0) * zc + PAN, zc);
    cq += vec2(T * 0.4, -T * 1.6);                        // racing away from us and a little leftwards
    // streets of cloud drawn out along the wind, so they converge on the horizon
    float n = fbm(cq * vec2(0.11, 0.022) + vec2(0.0, 0.25 * sin(cq.x * 0.05)));
    n = 0.75 * n + 0.25 * vnoise(cq * vec2(0.3, 0.08));
    float far = smoothstep(0.015, 0.1, h);                // detail dissolves towards the horizon
    n = mix(0.52, n, far);
    float cover = mix(0.42, 0.55, LIGHT);
    return smoothstep(cover - 0.1, cover + 0.12, n);
}
vec3 sky(vec2 p) {
    vec3 c = skyBase(p);
    float rs = length(p - SUN);
    float d0 = cloudAt(p);
    float d1 = cloudAt(p + normalize(SUN - p + 1e-5) * 0.025);
    vec3 under = mix(vec3(0.72, 0.76, 0.76), vec3(0.38, 0.43, 0.46), d0) * mix(0.62, 1.0, LIGHT);
    float lining = sat((d0 - d1) * 4.0) + 0.3 * (1.0 - d0);
    under += SUNC * lining * (0.14 + 1.1 * exp(-rs * 3.0));
    c += SUNC * (0.12 * exp(-rs * 3.0) + 0.4 * exp(-rs * 12.0));
    c = mix(c, under, d0 * 0.95);
    c += SUNC * 1.6 * smoothstep(0.02, 0.016, rs) * (1.0 - d0) * SUNVIS;   // a veiled disc
    // the haze of the horizon over everything low
    return mix(c, air(p), 0.6 * exp(-max(p.y - YH, 0.0) * 18.0));
}

// light falling through gaps in the cloud onto the sea
float seaBeams(vec2 p) {
    vec2 dv = p - SUN;
    float a = atan(dv.x, -dv.y);
    float n = fbm(vec2(a * 9.0 + T * 0.03, T * 0.05));
    return smoothstep(0.5, 0.8, n) * exp(-length(dv) * 1.2) * step(p.y, SUN.y);
}

// ------------------------------------------------------------------ far coast, the Faro, Miramare
float coast(float x) {   // the Karst falling to the sea on the right; a low line of Istria on the left
    float right = 0.05 * smoothstep(-0.05, 0.45, x) + 0.012 * vnoise(vec2(x * 22.0, 3.0)) * smoothstep(-0.05, 0.1, x)
                + 0.01 * exp(-pow((x - 0.235) / 0.04, 2.0));      // the knoll at Gretta that carries the Faro
    float left = 0.006 + 0.004 * vnoise(vec2(x * 30.0, 7.0));
    return YH + max(right, left) + 0.002;
}
float sdFaro(vec2 r) {   // the Faro della Vittoria: rusticated base, fluted column, lantern and Victory
    float d = sdBox(r - vec2(0.0, 0.007), vec2(0.009, 0.007));
    d = min(d, sdTrap(r - vec2(0.0, 0.038), 0.0042, 0.0032, 0.024));
    d = min(d, sdBox(r - vec2(0.0, 0.064), vec2(0.0055, 0.0025)));
    d = min(d, sdBox(r - vec2(0.0, 0.071), vec2(0.0038, 0.0045)));
    d = min(d, sdTrap(r - vec2(0.0, 0.0785), 0.004, 0.001, 0.003));
    d = min(d, sdCapsule(r, vec2(0.0, 0.081), vec2(0.0, 0.089), 0.0012));
    d = min(d, sdSeg(r, vec2(0.0, 0.087), vec2(0.004, 0.091)) - 0.0007);   // the wings
    d = min(d, sdSeg(r, vec2(0.0, 0.087), vec2(-0.0035, 0.0905)) - 0.0007);
    return d;
}
float sdCastle(vec2 r) {   // Miramare: a white castle on its point, a square tower at one end
    float d = sdBox(r - vec2(0.0, 0.004), vec2(0.011, 0.004));
    d = min(d, sdBox(r - vec2(0.008, 0.008), vec2(0.0032, 0.008)));
    d = min(d, sdBox(r - vec2(-0.006, 0.0095), vec2(0.0045, 0.0015)));
    return d;
}
float sdShip(vec2 r) {   // a steamer hull down on the horizon
    float d = sdTrap(r - vec2(0.0, 0.002), 0.012, 0.016, 0.002);
    d = min(d, sdBox(r - vec2(-0.002, 0.0055), vec2(0.006, 0.0015)));
    d = min(d, sdBox(r - vec2(0.0005, 0.0085), vec2(0.0012, 0.0025)));
    return d;
}

// ------------------------------------------------------------------ the sea and the Molo Audace
const float MX0 = -1.3, MX1 = -0.45, MZ1 = 95.0, MY = -0.12;    // pier extent, its top below the street

vec3 seaCol(vec2 p) {
    float Zw = (CAMH - YW) / max(YH - p.y, 1e-4);
    float Xw = (p.x - X0) * Zw + PAN;
    float fz = Zw * Zw * PX / (CAMH - YW);
    float detail = exp(-fz * 0.6);
    // wind-driven chop: streaks across our view, whitecaps whipped up by the bora
    vec2 wq = vec2(Xw * 0.9 + T * 0.15, Zw * 2.2 - T * 0.9);
    float n = vnoise(wq) * 0.6 + vnoise(wq * 2.7 + 4.0) * 0.4;
    n = mix(0.5, n, detail);
    float grazing = sat((YH - p.y) * 30.0);
    vec3 deep = vec3(0.05, 0.12, 0.15) * mix(0.6, 1.0, LIGHT);
    vec3 refl = skyBase(vec2(p.x, YH + (YH - p.y) * 2.0)) * 0.9;
    float fres = mix(0.9, 0.18, pow(grazing, 0.5));
    vec3 c = mix(deep, refl, sat(fres + (n - 0.5) * 0.6));
    c += SKYC * 0.5 * exp(-(YH - p.y) * 260.0);           // the bright line of the horizon
    float cap = smoothstep(0.72, 0.82, vnoise(wq * 1.7 + 9.0)) * detail * grazing;
    c = mix(c, vec3(0.75, 0.8, 0.8) * mix(0.6, 1.0, LIGHT), cap * 0.6);
    // the sun's glitter, a broken column beneath it
    float gx = (p.x - SUN.x) / (0.04 + 0.25 * (YH - p.y));
    float col = exp(-gx * gx);
    float spark = pow(vnoise(vec2(Xw * 7.0, Zw * 3.0 - T * 2.5)), 6.0) * 6.0;
    c += SUNC * col * (0.15 + spark * detail + 0.6 * (1.0 - detail)) * SUNVIS * 0.6;
    c += SUNC * seaBeams(p) * 0.25 * SUNVIS;
    return mix(c, air(p), min(fogF(Zw), 0.45));           // the sea stays darker than the sky over it
}

// the pier: its top and the side facing us; premultiplied colour and alpha
vec4 molo(vec2 p) {
    if (p.y > YH) return vec4(0.0);
    vec4 res = vec4(0.0);
    float dy = YH - p.y;
    // the top surface
    float Zt = (CAMH - MY) / dy;
    float Xt = (p.x - X0) * Zt + PAN;
    float fzt = Zt * Zt * PX / (CAMH - MY);
    float fwt = Zt * PX + abs(p.x - X0) * fzt;
    float onTop = band1(Xt, MX0, MX1, fwt) * band1(Zt, ZQ, MZ1, fzt);
    if (onTop > 0.0) {
        vec3 c = vec3(0.42, 0.42, 0.40) * (SKYC * 1.2 + SUNC * SINE * 0.6);
        c *= 0.85 + 0.15 * vnoise(vec2(Xt * 4.0, Zt * 0.8));
        // bollards along its edges
        float bz = fract(Zt / 3.0);
        float boll = band1(bz, 0.47, 0.53, fzt / 3.0) * band1(abs(Xt - 0.5 * (MX0 + MX1)), 0.23, 0.26, fwt);
        c *= 1.0 - 0.6 * boll;
        res = vec4(mix(c, air(p), min(fogF(Zt), 0.5)) * onTop, onTop);
    }
    // the side face towards the street-side (x = MX1), down to the water
    float Zs = (MX1 - PAN) / (p.x - X0);
    if (MX1 - PAN < 0.0 && Zs > ZQ && Zs < MZ1) {        // only while the pier lies to our left
        float Ys = CAMH + (p.y - YH) * Zs;
        float fy = Zs * PX;
        float side = band1(Ys, YW, MY, fy);
        if (side > 0.0) {
            vec3 c = vec3(0.30, 0.31, 0.30) * SKYC * (0.9 + 0.2 * vnoise(vec2(Zs, Ys * 12.0)));
            c *= 1.0 - 0.3 * band1(fract(Ys / 0.09), 0.0, 0.1, fy / 0.09);   // courses of stone
            c *= mix(0.65, 1.0, smoothstep(YW, YW + 0.15, Ys));             // wet at the waterline
            c = mix(c, air(p), min(fogF(Zs), 0.5));
            res.rgb = res.rgb + c * side * (1.0 - res.a);
            res.a = res.a + side * (1.0 - res.a);
        }
    }
    return res;
}

// ------------------------------------------------------------------ the palazzi: perspective facades
// left wall at x = -W faces +x, right wall at x = +W faces -x; u = depth along the street, v = height.
// A recess of depth dd at depth u shows its far reveal over a width u * dd / W; a projection of dd
// shows its near side over the same width, and an overhang above the eye shows its soffit.
vec3 palette(float b) {
    if (b < 0.5) return vec3(0.64, 0.63, 0.59);   // grey Istrian stone
    if (b < 1.5) return vec3(0.80, 0.71, 0.54);   // Trieste cream
    if (b < 2.5) return vec3(0.82, 0.68, 0.46);   // pale ochre
    return vec3(0.76, 0.62, 0.56);                 // dusty rose
}

// a recessed opening [lo, hi] x [b, t] in a bay: returns coverage; rev = how much of it is far reveal
float opening(float lu, float v, float hw, float b, float t, float depth, float rf, vec2 fw, out float rev) {
    float cov = rectC(vec2(lu, v), vec2(-hw, b), vec2(hw, t), fw);
    float rw = min(rf * depth, hw * 1.8);
    rev = smoothstep(hw - rw - fw.x, hw - rw + fw.x, lu);
    return cov;
}

// the colour of a facade at (u, v); a = coverage (0 above the roofline and between balusters)
vec3 facade(float u, float v, float side, vec2 fw, out float glass, out float a) {
    glass = 0.0;
    float b, u0;
    if (side < 0.0) { b = (u < 5.6) ? 0.0 : 1.0; u0 = (u < 5.6) ? 0.0 : 5.6; }
    else { b = (u < 4.8) ? 2.0 : 3.0; u0 = (u < 4.8) ? 0.0 : 4.8; }
    vec3 stone = palette(b);
    float bw = (b == 0.0 || b == 2.0) ? 1.2 : 1.1;
    float k = floor((u - u0) / bw);
    float lu = u - u0 - (k + 0.5) * bw;                 // across the bay, + is further from us
    float rf = u / W;                                    // how much depth reads as width here
    vec3 c = stone * (0.94 + 0.12 * vnoise(vec2(u * 9.0, v * 7.0) + b * 5.0));
    vec3 dark = vec3(0.025, 0.03, 0.035);
    float rev;
    // ---- the roofline: main cornice, its deep soffit seen from below, a balustrade with statues
    float CR = 5.15;
    float csoff = (CR - CAMH) * 0.3 / W;
    a = band1(v, 0.0, HW, fw.y);                         // from the pavement to the roofline
    float statue = 0.0;
    if (v > CR - csoff - 0.1) {
        float inSoff = band1(v, CR - csoff, CR, fw.y);
        float modil = band1(fract((u - u0) / 0.3), 0.3, 0.7, fw.x / 0.3);
        c = mix(c, stone * mix(0.3, 0.55, modil), inSoff);                 // modillions under the cornice
        c = mix(c, stone * 1.15, band1(v, CR, CR + 0.12, fw.y));          // the cornice's lit lip
        c = mix(c, stone * 0.85, band1(v, CR + 0.12, CR + 0.22, fw.y));
        // balustrade: balusters with the sky between them, pedestals over the pilasters
        float bz = band1(v, CR + 0.22, HW, fw.y);
        float post = band1(fract(lu / 0.11 + 0.5), 0.22, 0.78, fw.x / 0.11);
        float rail = max(band1(v, HW - 0.08, HW, fw.y), band1(v, CR + 0.22, CR + 0.3, fw.y));
        float ped = band1(abs(lu), bw * 0.5 - 0.1, bw * 0.5 + 0.1, fw.x);
        float solid = max(max(post, rail), ped);
        a *= mix(1.0, solid, bz);
        // statues on alternate pedestals, dark against the sky
        float sk = floor((u - u0) / bw + 0.5);
        if (mod(sk, 2.0) < 0.5) {
            vec2 sq = vec2(abs(lu) - bw * 0.5, v - HW);
            float sd = min(sdCapsule(sq, vec2(0.0, 0.05), vec2(0.0, 0.42), 0.055), sdCircle(sq - vec2(0.0, 0.5), 0.06));
            sd = min(sd, sdSeg(sq, vec2(0.0, 0.32), vec2(0.12, 0.44)) - 0.02);
            statue = 1.0 - smoothstep(-fw.y, fw.y, sd);
        }
    }
    // ---- the joint between two palazzi: a broad pilaster strip
    float seam = band1(u - u0, -0.08, 0.08, fw.x) * step(0.5, u0);
    c *= 1.0 - 0.22 * band1(v, -1.0, 0.13, fw.y);                         // plinth
    float GF = 1.55;
    if (v < GF) {
        // rustication: horizontal grooves and staggered vertical joints
        float gy = fract(v / 0.16), row = floor(v / 0.16);
        float gx = fract((u - u0) / 0.42 + 0.5 * mod(row, 2.0));
        c *= 1.0 - 0.22 * band1(gy, 0.0, 0.08, fw.y / 0.16) - 0.1 * band1(gx, 0.0, 0.04, fw.x / 0.42);
        // a round-arched opening in every bay: shop glass in a deep reveal, a keystone above
        float aw = 0.3, sp = 0.92;
        float inArch = band1(lu, -aw, aw, fw.x) * band1(v, 0.13, sp, fw.y);
        float ra = length(vec2(lu, v - sp)) - aw;
        inArch = max(inArch, (1.0 - smoothstep(-max(fw.x, fw.y), max(fw.x, fw.y), ra)) * step(sp, v));
        float rw = min(rf * 0.2, aw * 1.8);
        float inRev = smoothstep(aw - rw - fw.x, aw - rw + fw.x, lu);
        vec3 gl = mix(vec3(0.05, 0.06, 0.07), SKYC * 0.5, smoothstep(0.2, 1.1, v) * 0.55);
        gl += SKYC * 0.22 * band1(fract(lu * 3.0 + v * 0.7), 0.0, 0.15, fw.x * 3.0);
        c = mix(c, mix(gl, stone * 0.62, inRev), inArch);
        glass = inArch * (1.0 - inRev);
        c = mix(c, stone * 1.1, rectC(vec2(lu, v), vec2(-0.05, sp + aw - 0.02), vec2(0.05, sp + aw + 0.1), fw) * (1.0 - inArch));
    } else {
        // cornice over the ground floor
        c = mix(c, stone * 0.5, band1(v, GF, GF + (GF - CAMH) * 0.12 / W, fw.y));
        c = mix(c, stone * 1.14, band1(v, GF + (GF - CAMH) * 0.12 / W, GF + (GF - CAMH) * 0.12 / W + 0.08, fw.y));
        // mezzanine
        float mz = opening(lu, v, 0.18, 1.8, 2.08, 0.12, rf, fw, rev);
        c = mix(c, mix(dark, stone * 0.62, rev), mz);
        glass = max(glass, mz * (1.0 - rev));
        // piano nobile: balcony on brackets, tall windows under pediments, a balustrade in front
        float bal = 2.22;
        float bsoff = (bal - CAMH) * 0.3 / W;
        c = mix(c, stone * 0.42, band1(v, bal - bsoff - 0.04, bal - 0.04, fw.y));
        float brk = band1(fract((u - u0) / bw * 2.0), 0.44, 0.56, fw.x / bw * 2.0) * band1(v, bal - bsoff - 0.18, bal - bsoff - 0.04, fw.y);
        c = mix(c, stone * 0.68, brk);
        c = mix(c, stone * 1.12, band1(v, bal - 0.04, bal + 0.03, fw.y));
        float win = opening(lu, v, 0.21, bal + 0.06, 3.12, 0.15, rf, fw, rev);
        c = mix(c, mix(dark + SKYC * 0.1 * smoothstep(bal, 3.1, v), stone * 0.58, rev), win);
        glass = max(glass, win * (1.0 - rev));
        vec2 pq = vec2(lu, v - 3.2);
        float ped = 1.0 - smoothstep(-fw.y, fw.y, max(abs(pq.x) * 0.3 + pq.y - 0.075, -pq.y));
        c = mix(c, stone * 1.14, ped * step(abs(lu), 0.28));
        c = mix(c, stone * 0.5, band1(v, 3.16, 3.2, fw.y) * step(abs(lu), 0.28));
        float bus = band1(v, bal + 0.03, bal + 0.36, fw.y) * step(abs(lu), 0.38);
        float post = band1(fract(lu / 0.065), 0.25, 0.75, fw.x / 0.065);
        float rail = band1(v, bal + 0.31, bal + 0.36, fw.y);
        c = mix(c, stone * 1.02, bus * max(post, rail));
        c = mix(c, c * 0.75, bus * (1.0 - max(post, rail)) * 0.5);
        // second floor and the attic
        c = mix(c, stone * 1.12, band1(v, 3.48, 3.56, fw.y));
        c = mix(c, stone * 0.55, band1(v, 3.44, 3.48, fw.y));
        float w2 = opening(lu, v, 0.19, 3.64, 4.3, 0.13, rf, fw, rev);
        c = mix(c, mix(dark, stone * 0.6, rev), w2);
        glass = max(glass, w2 * (1.0 - rev));
        c = mix(c, stone * 1.1, rectC(vec2(lu, v), vec2(-0.24, 4.32), vec2(0.24, 4.38), fw));
        c = mix(c, stone * 1.1, band1(v, 4.46, 4.52, fw.y));
        float w3 = opening(lu, v, 0.16, 4.62, 4.98, 0.1, rf, fw, rev);
        c = mix(c, mix(dark, stone * 0.6, rev), w3);
        glass = max(glass, w3 * (1.0 - rev));
        // pilasters between the bays of the upper floors, their near sides in shade
        float pil = band1(abs(lu), bw * 0.5 - 0.075, bw * 0.5 + 0.075, fw.x) * step(v, CR - csoff);
        float pside = band1(lu, bw * 0.5 - 0.075 - min(rf * 0.05, 0.14), bw * 0.5 - 0.075, fw.x) * step(v, CR - csoff);
        c = mix(c, stone * 1.06, pil);
        c = mix(c, stone * 0.72, pside);
    }
    c = mix(c, stone * 0.8, seam);
    c = mix(c, stone * 0.35, statue);
    a = max(a, statue);
    return c;
}

// ------------------------------------------------------------------ street furniture and people
// iron lamp posts: world x, depth (on the pavements and along the quay)
const vec2 LAMP[6] = vec2[6](vec2(-2.75, 4.3), vec2(2.75, 6.2), vec2(-2.75, 8.6),
                            vec2(-5.2, 12.3), vec2(0.9, 12.3), vec2(6.4, 12.3));
float sdLamp(vec2 r) {   // a Trieste candelabrum: base, fluted shaft, scrolled arm, lantern
    float d = sdTrap(r - vec2(0.0, 0.09), 0.075, 0.05, 0.09);
    d = min(d, sdTrap(r - vec2(0.0, 0.72), 0.035, 0.024, 0.55));
    d = min(d, sdBox(r - vec2(0.0, 1.29), vec2(0.04, 0.02)));
    d = min(d, sdArc(r, vec2(0.13, 1.32), 0.13, 3.14159, 1.2, 0.012));
    d = min(d, sdTrap(r - vec2(0.0, 1.38), 0.045, 0.07, 0.07));
    d = min(d, sdTrap(r - vec2(0.0, 1.475), 0.075, 0.015, 0.025));
    d = min(d, sdCircle(r - vec2(0.0, 1.51), 0.014));
    return d;
}

// passers-by: on the Riva (crossing), on the far pavements (walking along), tiny on the pier
void passer(int i, out vec2 wp, out float h, out vec4 pose, out float kind, out float vis) {
    float fi = float(i);
    float hsh = hash11(fi * 7.13 + 1.0);
    vis = smoothstep(0.0, 0.1, uP[3].x - hsh * 0.9);
    float dir = (hash11(fi * 3.1) > 0.5) ? 1.0 : -1.0;
    float spd = 0.22 + 0.16 * hash11(fi * 5.7);
    kind = floor(hash11(fi * 9.3) * 3.0);
    h = 0.5 * (0.92 + 0.12 * hash11(fi * 2.2));
    float ph = T * 4.0 * spd / 0.25 + fi * 2.0;
    float wk = sin(ph);
    pose = vec4(0.22 * wk, -0.22 * wk, (kind > 0.5 && kind < 1.5) ? 0.25 : 0.0, -0.03 * dir);
    if (i < 7) {                                       // along the Riva
        float z = 11.4 + 0.75 * hash11(fi * 4.4);
        float x = mod(fi * 2.3 + dir * spd * T, 12.0) - 6.0;
        wp = vec2(x, z);
        vis *= smoothstep(6.0, 5.0, abs(x));
    } else if (i < 9) {                                // down the far pavements
        float side = (i == 7) ? -1.0 : 1.0;
        float z = 5.5 + mod(fi * 1.7 + dir * spd * T, 8.0);
        wp = vec2(side * 2.55, z);
        vis *= smoothstep(5.5, 6.3, z) * smoothstep(13.5, 12.6, z);
    } else {                                           // strolling on the pier
        float z = 32.0 + mod(fi * 5.1 + dir * spd * 0.6 * T, 30.0);
        wp = vec2(mix(MX0, MX1, 0.35 + 0.3 * hash11(fi)), z);
        vis *= smoothstep(32.0, 34.0, z) * smoothstep(62.0, 58.0, z);
    }
    if (kind > 1.5) pose.y = 2.6;                      // holding his hat on in the wind
}

float sdPasser(vec2 q, vec4 pose, float kind) {
    float d = sdFigure(q, pose, (kind > 0.5 && kind < 1.5) ? 1.0 : 0.0);
    vec2 a = vec2(q.x - q.y * pose.w, q.y);
    if (kind < 0.5 || kind > 1.5) {                    // a felt hat
        d = min(d, sdBox(a - vec2(0.0, 0.952), vec2(0.085, 0.009)));
        d = min(d, sdTrap(a - vec2(0.0, 0.982), 0.055, 0.045, 0.026));
    } else d = min(d, sdCircle(a - vec2(0.0, 0.92), 0.075));   // a headscarf
    if (kind < 0.5) d = min(d, sdTrap(a - vec2(0.0, 0.5), 0.15, 0.11, 0.2));   // an overcoat
    return d;
}

vec4 drawPasser(vec2 p, int i, float zClip) {
    vec2 wp; float h; vec4 pose; float kind, vis;
    passer(i, wp, h, pose, kind, vis);
    if (vis <= 0.002 || wp.y > zClip) return vec4(0.0);
    float z = wp.y;
    float ybase = (i >= 9) ? YH + (MY - CAMH) / z : yBase(z);
    float hs = h / z;
    vec2 pos = vec2(X0 + (wp.x - PAN) / z, ybase);
    vec2 q = (p - pos) / hs;
    if (abs(q.x) > 0.5 || q.y < -0.05 || q.y > 1.1) return vec4(0.0);
    float d = sdPasser(q, pose, kind) * hs;
    float a = aa(d, PX);
    if (a <= 0.0) return vec4(0.0);
    vec3 c = vec3(0.09, 0.09, 0.1) * (0.85 + 0.15 * vnoise(q * 12.0 + float(i)));
    float rimv = exp(-max(-d, 0.0) / (0.004 * hs + 0.0005)) * sat(-q.x * 3.0 + 0.5) * smoothstep(0.4, 0.9, q.y);
    c += SUNC * rimv * 0.25 * SUNVIS + SKYC * 0.15 * rimv;
    c = mix(c, air(p), fogF(z));
    return vec4(c * a * vis, a * vis);
}

// sheets of newspaper skittering down the street in the bora, now and then lifting off the stones
vec4 papers(vec2 p) {
    vec4 acc = vec4(0.0);
    for (int i = 0; i < 3; i++) {
        float fi = float(i);
        float per = 9.0 + 4.0 * hash11(fi * 3.7);
        float cyc = T / per + hash11(fi * 5.3);
        float u = fract(cyc), k = floor(cyc);
        // carried away from us towards the sea, drifting across the street
        float z = mix(1.6, 7.5, u);
        float x = mix(-1.6, 1.6, hash11(fi * 2.1 + k)) - 0.8 * u + 0.15 * sin(T * 1.7 + fi);
        float hop = 0.25 * pow(max(sin(u * 18.0 + fi * 2.0), 0.0), 3.0);
        vec2 c = vec2(X0 + (x - PAN) / z, yBase(z) + (0.03 + hop) / z);
        float s = 0.11 / z;
        vec2 r = p - c;
        if (abs(r.x) > s * 1.5 || abs(r.y) > s * 1.5) continue;
        float tum = T * 3.0 + fi * 2.0;
        r = rot(0.6 * sin(tum)) * r;
        r.y /= max(abs(cos(tum * 0.7)), 0.15);           // flipping over as it goes
        float d = sdBox(r, vec2(s, s * 0.7));
        float a = aa(d, PX) * smoothstep(0.0, 0.08, u) * smoothstep(1.0, 0.85, u);
        if (a <= 0.0) continue;
        vec3 pc = vec3(0.78, 0.76, 0.7) * (SKYC * 1.2 + SUNC * 0.25 * SUNVIS);
        pc *= 0.85 + 0.15 * step(0.5, fract(r.y / s * 4.0));   // columns of print
        pc = mix(pc, air(p), fogF(z));
        acc.rgb = acc.rgb * (1.0 - a) + pc * a;
        acc.a = max(acc.a, a);
    }
    return acc;
}

// gulls hanging in the wind
float sdGull(vec2 r, float flap) {
    vec2 w = vec2(abs(r.x), r.y);
    float lift = 0.14 + 0.22 * flap;
    float d = sdSeg(w, vec2(0.0), vec2(0.4, lift)) - 0.055;
    d = min(d, sdSeg(w, vec2(0.4, lift), vec2(1.0, lift - 0.16 - 0.22 * flap)) - mix(0.04, 0.012, sat((w.x - 0.4) / 0.6)));
    d = min(d, sdEllipse(r - vec2(0.0, -0.03), vec2(0.08, 0.14)));
    return d;
}
vec4 gulls(vec2 p) {
    vec4 acc = vec4(0.0);
    for (int i = 0; i < 7; i++) {
        float fi = float(i);
        vec2 c = vec2(-0.55 + 1.1 * hash11(fi * 3.3), 0.12 + 0.33 * hash11(fi * 5.9));
        c += vec2(0.04 * sin(T * 0.21 + fi * 1.7) - 0.012 * T * hash11(fi), 0.02 * sin(T * 0.37 + fi * 2.9));
        c.x = mod(c.x + 0.9, 1.8) - 0.9;
        float s = 0.012 + 0.016 * hash11(fi * 8.1);
        vec2 r = p - c;
        if (abs(r.x) > s * 1.2 || abs(r.y) > s * 0.6) continue;
        float tilt = 0.15 * sin(T * 0.5 + fi * 2.0);
        vec2 lr = rot(tilt) * r / s;
        float flap = 0.5 + 0.5 * sin(T * (2.0 + 2.0 * hash11(fi * 4.4)) + fi);
        flap *= smoothstep(0.3, 0.7, sin(T * 0.4 + fi * 1.9) * 0.5 + 0.5);
        float d = sdGull(lr, flap) * s;
        float a = aa(d, PX * 0.8);
        if (a <= 0.0) continue;
        vec3 gc = mix(vec3(0.58, 0.62, 0.63), vec3(0.08, 0.08, 0.09), smoothstep(0.75, 0.95, abs(lr.x))) * mix(0.6, 1.0, LIGHT);
        gc += SUNC * 0.25 * smoothstep(0.0, 0.3, lr.y) * SUNVIS;
        gc = mix(gc, air(p), 0.25);
        acc.rgb = acc.rgb * (1.0 - a) + gc * a;
        acc.a = max(acc.a, a);
    }
    return acc;
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
    f.rgb = mix(f.rgb, air(p) * f.a, fogF(z) * 0.5);
    return f * P.w;
}

// Elena's string shopping bag, hanging from her outer hand (she was on an errand)
vec4 errandBag(vec2 p, vec4 P, vec4 pose, float hand) {   // hand: -1 her left, +1 her right
    if (P.w <= 0.0) return vec4(0.0);
    float z = figDepth(P.xy);
    vec2 pos = vec2(P.x - PAN / z, P.y);
    vec2 q = (p - pos) / P.z;
    if (abs(q.x) > 0.5 || q.y < 0.1 || q.y > 0.6) return vec4(0.0);
    float ang = (hand < 0.0) ? pose.x : pose.y;          // the same arm as sdFigure builds it
    vec2 sh = vec2(0.11 * hand, 0.765);
    vec2 el = sh + 0.17 * vec2(hand * sin(ang), -cos(ang));
    vec2 hl = el + 0.16 * vec2(hand * sin(ang * 1.25), -cos(ang * 1.25));
    hl.x += hl.y * pose.w;
    vec2 b = q - hl;
    float sw = 0.12 * sin(T * 1.3) + 0.08 * GUST;
    b = rot(-sw) * b;
    float d = sdSeg(b, vec2(0.0), vec2(0.0, -0.05)) - 0.006;
    d = min(d, sdRBox(b - vec2(0.0, -0.11), vec2(0.05, 0.06), 0.02));
    d *= P.z;
    float a = aa(d, PX);
    vec3 c = vec3(0.12, 0.1, 0.06) + vec3(1.0, 0.45, 0.35) * 0.4 * exp(-max(-d, 0.0) / 0.002) * sat(-b.x * 20.0);
    float mesh = 0.75 + 0.25 * sin(b.x * 300.0) * sin(b.y * 300.0);
    return vec4(c * mesh * a, a) * P.w;
}

float loverShadow(vec2 g, vec4 P, vec4 pose, float hair) {
    if (P.w <= 0.01 || P.z <= 0.0) return 1.0;
    float z = figDepth(P.xy);
    if (g.y >= z) return 1.0;
    float H = P.z * z;
    float t = (z - g.y) / SH.y;
    vec2 q = vec2(g.x + t * SH.x - (P.x - X0) * z, t * TANE) / H;
    if (abs(q.x) > 0.6 || q.y > 1.1) return 1.0;
    float soft = (0.01 + mix(0.03, 0.07, LIGHT) * t) / H;
    return mix(1.0, smoothstep(-soft, soft, sdFigure(q, pose, hair)), P.w * 0.85);
}

// ------------------------------------------------------------------ the ground: masegni, rails, kerbs, Riva
float wallShadow(vec2 g) {   // the left-hand palazzi between us and the sun
    if (SH.x >= 0.0) return 1.0;
    float t = (g.x + W) / -SH.x;
    float zc = g.y + t * SH.y;
    float soft = 0.04 + mix(0.03, 0.08, LIGHT) * t;
    return mix(1.0, smoothstep(ZEND - soft, ZEND + soft, zc), step(-W, g.x));
}
float lampShadow(vec2 g) {
    float lit = 1.0;
    for (int i = 0; i < 3; i++) {
        vec2 L = LAMP[i];
        if (g.y >= L.y) continue;
        float t = (L.y - g.y) / SH.y;
        vec2 r = vec2(g.x + t * SH.x - L.x, t * TANE);
        if (abs(r.x) > 0.3 || r.y > 1.6) continue;
        float soft = 0.01 + 0.03 * t;
        lit *= smoothstep(-soft, soft, sdLamp(r));
    }
    return lit;
}

vec3 groundCol(vec2 p) {
    float Z = groundZ(p.y);
    float X = (p.x - X0) * Z + PAN;
    float fz = Z * Z * PX / CAMH;
    float fw = Z * PX + abs(p.x - X0) * fz;
    float ax = abs(X);
    vec3 alb;
    if (Z > ZEND + 0.3) {
        // the Riva: broad slabs, the quay's edge with its bollards
        vec2 sl = vec2(X / 0.5, Z / 0.34);
        sl.x += 0.5 * mod(floor(sl.y), 2.0);
        float j = max(band1(fract(sl.x), -0.03, 0.03, fw / 0.5) + band1(fract(sl.x), 0.97, 1.03, fw / 0.5),
                      band1(fract(sl.y), -0.04, 0.04, fz / 0.34) + band1(fract(sl.y), 0.96, 1.04, fz / 0.34));
        alb = vec3(0.44, 0.44, 0.42) * (0.88 + 0.24 * hash21(floor(sl))) * (1.0 - 0.35 * j * exp(-fz * 2.0));
        alb = mix(alb, vec3(0.75, 0.75, 0.72), band1(Z, ZQ - 0.35, ZQ, fz));          // the quay's pale kerb
        // bollards along the edge
        float bx = fract(X / 1.6 + 0.5);
        alb = mix(alb, vec3(0.05), band1(bx, 0.47, 0.53, fw / 1.6) * band1(Z, ZQ - 0.6, ZQ - 0.35, fz));
    } else {
        // masegni: big slabs of grey sandstone in running bond; tram rails glinting down the middle
        vec2 sq = vec2(X / 0.3, Z / 0.2);
        sq.x += 0.5 * mod(floor(sq.y), 2.0);
        float jt = max(band1(fract(sq.x), -0.03, 0.03, fw / 0.3), band1(fract(sq.y), -0.045, 0.045, fz / 0.2));
        float fadeS = exp(-max(fw / 0.3, fz / 0.2) * 3.0);
        alb = vec3(0.30, 0.31, 0.31) * (0.86 + 0.28 * mix(0.5, hash21(floor(sq)), fadeS));
        alb *= 0.92 + 0.16 * vnoise(vec2(X, Z) * 3.0);
        alb *= 1.0 - 0.35 * jt * fadeS;
        float pave = smoothstep(2.42 - fw, 2.42 + fw, ax);
        vec2 pq = vec2(X / 0.45, Z / 0.45);
        float pj = max(band1(fract(pq.y), -0.03, 0.03, fz / 0.45), band1(fract(pq.x), -0.03, 0.03, fw / 0.45));
        vec3 pav = vec3(0.42, 0.41, 0.38) * (0.9 + 0.2 * hash21(floor(pq) + 3.0)) * (1.0 - 0.3 * pj * exp(-max(fz, fw) * 3.0));
        alb = mix(alb, pav, pave);
        alb = mix(alb, vec3(0.55, 0.54, 0.5), band1(ax, 2.38, 2.46, fw));            // kerbstones
        float rails = band1(abs(X - 0.18), 0.135, 0.165, fw) + band1(abs(X - 0.18), 0.585, 0.615, fw);
        alb = mix(alb, vec3(0.06), rails * 0.6);
        alb += SKYC * rails * 0.9 * (0.4 + exp(-abs(p.x - SUN.x) * 1.5));            // steel catching the sky
    }
    vec2 g = vec2(X, Z);
    float lit = wallShadow(g) * lampShadow(g);
    lit *= loverShadow(g, uP[1], POSE_E, 2.0) * loverShadow(g, uP[2], POSE_M, 0.0);
    vec3 c = alb * (SKYC * 1.05 + SUNC * SINE * 0.85 * lit * SUNVIS);
    // polished masegni mirror the bright opening at the street's end, softly and blurred
    float open = smoothstep(0.42, 0.12, abs(p.x)) * exp(-(YH - p.y) * 2.6);
    c += SKYC * open * (0.22 + 0.1 * LIGHT) * (0.75 + 0.25 * vnoise(vec2(X * 2.0, Z * 0.5)));
    return mix(c, air(p), fogF(Z));
}

// ================================================================== main
void main() {
    vec2 p = screen();
    PAN = uP[0].x;
    LIGHT = sat(uP[3].y);
    T = uTime;
    PX = PIXEL;
    GUST = 0.5 + 0.5 * sin(T * 0.9) * sin(T * 0.37 + 1.0);

    YH = -0.02; CAMH = YH + 0.42; DENS = 1.0 / 19.0; FOGP = 1.5; X0 = 0.0;
    SUN = vec2(-0.2, 0.40);
    SUNVIS = mix(0.45, 1.0, LIGHT);
    SUNC = vec3(1.0, 0.94, 0.84) * mix(1.1, 1.9, LIGHT);
    SKYC = vec3(0.42, 0.49, 0.53) * mix(0.62, 1.0, LIGHT);
    AIRC = vec3(0.62, 0.69, 0.70) * mix(0.65, 1.0, LIGHT);
    vec2 sd = vec2(SUN.x - X0, 1.0);
    SH = normalize(sd);
    TANE = (SUN.y - YH) / length(sd);
    SINE = TANE / sqrt(1.0 + TANE * TANE);

    // poses: she leans a little into the wind, her skirt lifting with the gusts
    vec4 E = uP[1], M = uP[2];
    float side = (M.x >= E.x) ? 1.0 : -1.0;
    POSE_E = vec4(0.14, 0.14, 0.3 + 0.06 * GUST, 0.012 * side + 0.01 * GUST);
    POSE_M = vec4(0.1, 0.1, 0.0, -0.01 * side + 0.004 * sin(T * 0.6));
    if (side > 0.0) { POSE_E.y = 0.3 + 0.06 * sin(T * 0.7); POSE_M.x = 0.22 + 0.05 * sin(T * 0.5 + 1.0); }
    else { POSE_E.x = 0.3 + 0.06 * sin(T * 0.7); POSE_M.y = 0.22 + 0.05 * sin(T * 0.5 + 1.0); }
    float bagHand = -side;      // the bag hangs from her outer hand, away from him

    // ---- sky, far coast, the Faro, Miramare, a steamer
    vec3 col = sky(p);
    float cy = coast(p.x + PAN * 0.004);
    vec3 coastC = mix(vec3(0.20, 0.25, 0.29), air(p), 0.62 - 0.25 * smoothstep(0.1, 0.45, p.x));
    col = mix(col, coastC, aa(p.y - cy, PX));
    {
        vec2 fp = vec2(p.x + PAN * 0.004 - 0.235, p.y - coast(0.235) + 0.002);
        float fd = sdFaro(fp * 1.35) / 1.35;
        col = mix(col, mix(vec3(0.14, 0.17, 0.2), air(p), 0.55), aa(fd, PX));
        vec2 mp = vec2(p.x + PAN * 0.003 - 0.055, p.y - YH - 0.006);
        col = mix(col, mix(vec3(0.85, 0.86, 0.82) * mix(0.6, 1.0, LIGHT), air(p), 0.45), aa(sdCastle(mp), PX));
        vec2 shp = vec2(p.x + PAN * 0.002 + 0.16 + 0.0015 * T * 0.02, p.y - YH);
        col = mix(col, mix(vec3(0.12, 0.14, 0.16), air(p), 0.6), aa(sdShip(shp), PX));
        // its smoke, torn away by the bora
        vec2 sm = shp - vec2(0.0, 0.011);
        float smoke = exp(-pow((sm.y - 0.012 * sat(-sm.x * 12.0)) / (0.003 + 0.02 * sat(-sm.x)), 2.0)) * step(sm.x, 0.0) * exp(sm.x * 7.0);
        smoke *= 0.5 + 0.5 * vnoise(vec2(sm.x * 80.0 + T * 0.5, sm.y * 60.0));
        col = mix(col, mix(vec3(0.3, 0.32, 0.33), air(p), 0.4), sat(smoke) * 0.6);
    }
    // ---- the sea (above the quay's edge), then the pier
    float yq = yBase(ZQ);
    if (p.y < YH && p.y > yq - 0.002) {
        float a = aa(p.y - YH, PX) * (1.0 - aa(p.y - yq, PX));
        col = mix(col, seaCol(p), a);
        vec4 mo = molo(p);
        col = col * (1.0 - mo.a * a) + mo.rgb * a;
    }
    // ---- the street and the Riva
    if (p.y < yq + 0.001) col = mix(col, groundCol(p), aa(p.y - yq, PX));
    // ---- passers-by on the pier and the Riva, and the quay's lamps
    for (int i = 9; i < 12; i++) { vec4 f = drawPasser(p, i, 1e3); col = col * (1.0 - f.a) + f.rgb; }
    for (int i = 3; i < 6; i++) {
        vec2 L = LAMP[i];
        vec2 r = vec2(((p.x - X0) * L.y + PAN) - L.x, CAMH + (p.y - YH) * L.y);
        if (abs(r.x) > 0.3 || r.y > 1.6) continue;
        float d = sdLamp(r) / L.y;
        float a = aa(d, PX);
        col = mix(col, mix(vec3(0.03, 0.035, 0.04) + SKYC * 0.1, air(p), fogF(L.y)), a);
    }
    for (int i = 0; i < 7; i++) { vec4 f = drawPasser(p, i, 1e3); col = col * (1.0 - f.a) + f.rgb; }
    // ---- the palazzi on either side
    float dx = p.x - X0;
    if (abs(dx) > 1e-4) {
        float sideW = sign(dx);
        float Zf = (sideW * W - PAN) / dx;                // depth where this line of sight meets the wall
        if (Zf > 0.0 && Zf < ZEND * 1.03) {
            float v = CAMH + (p.y - YH) * Zf;
            vec2 fw = vec2(Zf * Zf * PX / W, Zf * PX);
            float gl, wa;
            vec3 alb = facade(Zf, v, sideW, fw, gl, wa);
            vec3 Lw = (sideW < 0.0) ? SKYC * 0.8 : SKYC * 0.95 + SUNC * 0.2 * SUNVIS;
            Lw *= 0.7 + 0.45 * smoothstep(0.0, 4.5, v);    // brighter higher up, open to the sky
            Lw *= 0.75 + 0.25 * smoothstep(3.0, 9.0, Zf);  // the nearest bays in the deepest shade
            vec3 c = alb * Lw;
            c += SKYC * gl * 0.3 * smoothstep(2.0, 9.0, Zf);    // the far windows mirror the bright sky
            c = mix(c, air(p), fogF(Zf));
            // the corner where the palazzo ends: a crisp edge
            float edge = aa((Zf - ZEND) * W / (Zf * Zf), PX);
            col = mix(col, c, edge * wa);
        }
    }
    // ---- lamps on the pavements, figures in the far street
    for (int i = 7; i < 9; i++) { vec4 f = drawPasser(p, i, 1e3); col = col * (1.0 - f.a) + f.rgb; }
    for (int i = 0; i < 3; i++) {
        vec2 L = LAMP[i];
        vec2 r = vec2(((p.x - X0) * L.y + PAN) - L.x, CAMH + (p.y - YH) * L.y);
        if (abs(r.x) > 0.3 || r.y > 1.6) continue;
        float d = sdLamp(r) / L.y;
        float a = aa(d, PX);
        if (a <= 0.0) continue;
        vec3 c = vec3(0.02, 0.022, 0.025) + SKYC * 0.08;
        c += SUNC * 0.35 * SUNVIS * exp(-max(-d * L.y, 0.0) / 0.012) * step(r.x, 0.0);   // rim on the sunward side
        c += vec3(0.7, 0.75, 0.75) * 0.2 * smoothstep(1.32, 1.36, r.y) * smoothstep(1.45, 1.42, r.y);   // lantern glass
        col = mix(col, mix(c, air(p), fogF(L.y)), a);
    }
    // ---- newspapers blowing along the paving
    vec4 pp = papers(p);
    col = col * (1.0 - pp.a) + pp.rgb;
    // ---- the lovers
    vec4 e = lover(p, E, POSE_E, 2.0, vec3(0.45, 0.03, 0.06), vec3(1.0, 0.45, 0.35));
    vec4 m = lover(p, M, POSE_M, 0.0, vec3(0.06, 0.22, 0.18), vec3(0.5, 1.0, 0.8));
    vec4 bag = errandBag(p, E, POSE_E, bagHand);
    if (figDepth(M.xy) > figDepth(E.xy)) { col = over(col, m); col = over(col, e); col = over(col, bag); }
    else { col = over(col, e); col = over(col, bag); col = over(col, m); }
    // ---- soft beams slanting down through the gaps in the cloud
    vec2 bv = p - SUN;
    float ba = atan(bv.x, -bv.y);
    float beams = smoothstep(0.52, 0.78, fbm(vec2(ba * 5.0 + 0.4 * sin(T * 0.04), T * 0.03 + 3.0)));
    beams *= smoothstep(0.0, 0.25, length(bv)) * exp(-length(bv) * 0.9) * step(p.y, SUN.y);
    col += SUNC * beams * 0.09 * SUNVIS;
    // ---- gulls, and the grit the bora carries
    vec4 gu = gulls(p);
    col = col * (1.0 - gu.a) + gu.rgb;
    float grit = dust(p + vec2(T * 0.08, 0.0), T * 2.0, 0.06, 0.06);
    col += SKYC * grit * 0.25;
    fragColor = vec4(col, 1.0);
}
