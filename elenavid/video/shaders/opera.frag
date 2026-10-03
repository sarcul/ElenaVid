#version 430
// THE OPERA HOUSE - ray-marched. Teatro all'italiana: horseshoe of five tiers, frescoed dome,
// crystal chandelier, gilded proscenium, velvet drapes, pit with stand lamps, conductor, stalls.
// Used for the required shot: dolly-in (mode 0), wide hall (mode 1), pull-back/curtain (mode 2).
#include common

// uP[0].xyz camera position, uP[1].xyz target, uP[1].w focal length
// uP[2].x arm lift (0..1)   uP[2].y breathing   uP[2].z head tilt  uP[2].w gown sway
// uP[3].x spot tightness   uP[3].y stage wash   uP[3].z house level  uP[3].w curtain drop (0..1)
// uP[4].x chandelier sparkle (voice)   uP[4].y cold intrusion (Vittorio)   uP[4].z dome echo ripple
// uP[5].x mode   uP[5].y focus distance   uP[5].z aperture
// uP[6].xyz conductor baton hand offset   uP[6].w conductor intensity
// uP[7].x conductor's left hand raised to cue (0 rests at the chest, 1 lifted)
// uP[7].y 1 = no singer on the stage (the curtain rising on an empty set; 0 in the film)

#define M_FLOOR 1.0
#define M_STAGE 2.0
#define M_WALL 3.0
#define M_GILT 4.0
#define M_VELVET 5.0
#define M_GOWN 6.0
#define M_SKIN 7.0
#define M_HAIR 8.0
#define M_BLACK 9.0
#define M_SEAT 10.0
#define M_HEAD 11.0
#define M_BOXIN 12.0
#define M_DOME 13.0
#define M_PIT 14.0
#define M_CURTAIN 15.0
#define M_WALLFRAG 16.0
#define M_CYC 17.0
#define M_SHIRT 18.0

const vec3 SINGER = vec3(0.0, 1.2, 4.0);
const vec3 COND = vec3(0.0, -0.32, -3.6);
const vec3 DESK_LAMP = vec3(0.0, 1.07, -3.02);
const float CYC_Z = 13.0;       // the painted cloth upstage
const float WALL_Z = 10.0;      // the free-standing wall fragment with her window

// ---------------------------------------------------------------- the set for N. 22:
// "La finestra. Il mare." A fragment of a room's wall with one arched window, and beyond it a
// painted cloth of the sea at sunset with the village headland and its campanile.
float window2D(vec2 q) {        // < 0 inside the arched opening
    float rect = max(abs(q.x) - 1.45, abs(q.y - 4.15) - 1.85);
    float disc = length(q - vec2(0.0, 6.0)) - 1.45;
    return min(rect, disc);
}

vec3 cycPaint(vec2 q) {
    float hz = 3.6;
    float y = q.y - hz;
    vec3 sky = mix(vec3(1.0, 0.70, 0.36), vec3(0.86, 0.47, 0.27), smoothstep(0.0, 3.0, y));
    sky = mix(sky, vec3(0.30, 0.15, 0.14), smoothstep(2.5, 9.5, y));
    // long horizontal brushstrokes of cloud, their undersides lit by the low sun
    float cl = fbm(vec2(q.x * 0.16, q.y * 0.85) + vec2(3.1, 0.0));
    float band = smoothstep(0.5, 0.74, cl) * smoothstep(0.4, 2.2, y) * (1.0 - smoothstep(6.5, 9.5, y));
    sky = mix(sky, sky * vec3(0.6, 0.44, 0.42) + vec3(0.12, 0.05, 0.02), band * 0.75);
    sky += vec3(0.5, 0.28, 0.1) * band * smoothstep(0.62, 0.5, cl) * 0.35;
    // the sun low over the water, stage right of the window
    vec2 sd = q - vec2(1.15, hz + 0.95);
    float sun = smoothstep(0.62, 0.5, length(sd));
    sky += vec3(1.0, 0.84, 0.58) * sun * 1.5 + vec3(1.0, 0.6, 0.28) * exp(-dot(sd, sd) * 0.22) * 0.5;
    // the sea: umber below, molten near the horizon, a broken glitter path under the sun
    float d = -y;
    vec3 sea = mix(vec3(0.64, 0.4, 0.2), vec3(0.15, 0.075, 0.055), smoothstep(0.0, 2.4, d));
    float path = exp(-pow((q.x - 1.15) * (1.5 - 0.4 * smoothstep(0.0, 2.4, d)), 2.0));
    float glint = smoothstep(0.5, 0.85, vnoise(vec2(q.x * 3.2 + uTime * 0.12, d * 30.0 / (0.25 + d))));
    sea += vec3(1.0, 0.76, 0.42) * path * (0.2 + 0.9 * glint) * (1.0 - 0.6 * smoothstep(0.0, 2.4, d));
    vec3 c = y > 0.0 ? sky : sea;
    c = mix(c, vec3(0.3, 0.15, 0.1), smoothstep(0.04, 0.0, abs(y)) * 0.35);
    // the headland, stage left, with the campanile of the church where she married
    float hill = hz + 0.75 * exp(-pow((q.x + 6.2) / 2.3, 2.0)) + 0.05 * vnoise(vec2(q.x * 3.0, 1.7)) - 0.03;
    float tb = hz + 0.6;                                     // the tower stands on the hill's shoulder
    float tower = step(abs(q.x + 5.7), 0.07) * step(tb - 0.1, q.y) * step(q.y, tb + 0.62);
    float spire = step(abs(q.x + 5.7), 0.075 * (1.0 - (q.y - tb - 0.62) / 0.24)) * step(tb + 0.62, q.y);
    float land = max(step(q.y, hill) * step(-0.02, y), max(tower, spire));
    c = mix(c, mix(vec3(0.2, 0.095, 0.075), sky, 0.25), land * 0.9);
    // the weave of the cloth and the painter's hand
    c *= 0.9 + 0.1 * vnoise(q * vec2(36.0, 3.0)) ;
    return c;
}

float cycLight() { return 0.03 + 0.75 * uP[3].y; }
const vec2 HC = vec2(0.0, -11.0);   // horseshoe centre (x, z)
const vec2 HR = vec2(12.0, 14.0);   // horseshoe radii

vec2 opU(vec2 a, vec2 b) { return a.x < b.x ? a : b; }
float sdBox3(vec3 p, vec3 b) { vec3 d = abs(p) - b; return length(max(d, 0.0)) + min(max(d.x, max(d.y, d.z)), 0.0); }
float sdCap3(vec3 p, vec3 a, vec3 b, float r) { vec3 pa = p - a, ba = b - a;
    float h = sat(dot(pa, ba) / dot(ba, ba)); return length(pa - ba * h) - r; }
float sdEll3(vec3 p, vec3 r) { float k0 = length(p / r); float k1 = length(p / (r * r)); return k0 * (k0 - 1.0) / k1; }
float sdSph(vec3 p, float r) { return length(p) - r; }
float smin3(float a, float b, float k) { float h = sat(0.5 + 0.5 * (b - a) / k); return mix(b, a, h) - k * h * (1.0 - h); }

// elliptical "radius" of the horseshoe (1 = parapet line)
float hsR(vec3 p) { return length((p.xz - HC) / HR); }

// ---------------------------------------------------------------- the singer
float sdRoundCone(vec3 p, vec3 a, vec3 b, float r1, float r2) {
    vec3 ba = b - a; float l2 = dot(ba, ba); float rr = r1 - r2; float a2 = l2 - rr * rr; float il2 = 1.0 / l2;
    vec3 pa = p - a; float y = dot(pa, ba); float z = y - l2;
    vec3 xv = pa * l2 - ba * y; float x2 = dot(xv, xv); float y2 = y * y * l2; float z2 = z * z * l2;
    float k = sign(rr) * rr * rr * x2;
    if (sign(z) * a2 * z2 > k) return sqrt(x2 + z2) * il2 - r2;
    if (sign(y) * a2 * y2 < k) return sqrt(x2 + y2) * il2 - r1;
    return (sqrt(x2 * a2 * il2) + y * rr) * il2 - r1;
}

// the head in its own frame (facing -z): cranium, jaw, chin, nose, brows, lips, ears
float headSDF(vec3 h, out float lipMask) {
    float cran = sdEll3(h - vec3(0.0, 0.02, 0.008), vec3(0.078, 0.095, 0.092));
    float jaw = sdEll3(h - vec3(0.0, -0.045, -0.02), vec3(0.06, 0.06, 0.07));
    float d = smin3(cran, jaw, 0.04);
    float chin = sdEll3(h - vec3(0.0, -0.088, -0.062), vec3(0.025, 0.022, 0.02));
    d = smin3(d, chin, 0.02);
    float cheek = min(sdEll3(h - vec3(0.038, -0.012, -0.055), vec3(0.025, 0.02, 0.02)),
                      sdEll3(h - vec3(-0.038, -0.012, -0.055), vec3(0.025, 0.02, 0.02)));
    d = smin3(d, cheek, 0.02);
    vec3 nq = h - vec3(0.0, -0.006, -0.088);
    float nose = sdRoundCone(nq, vec3(0.0, 0.03, 0.006), vec3(0.0, -0.012, -0.012), 0.008, 0.011);
    d = smin3(d, nose, 0.012);
    float brow = sdEll3(h - vec3(0.0, 0.034, -0.07), vec3(0.06, 0.012, 0.02));
    d = smin3(d, brow, 0.015);
    // eye sockets
    float eyes = min(sdEll3(h - vec3(0.03, 0.016, -0.083), vec3(0.018, 0.009, 0.012)),
                     sdEll3(h - vec3(-0.03, 0.016, -0.083), vec3(0.018, 0.009, 0.012)));
    d = max(d, -eyes + 0.002);
    float lids = min(sdEll3(h - vec3(0.03, 0.0145, -0.0795), vec3(0.0165, 0.0085, 0.0085)),
                     sdEll3(h - vec3(-0.03, 0.0145, -0.0795), vec3(0.0165, 0.0085, 0.0085)));
    d = smin3(d, lids, 0.004);                          // eyes closed, lost in the music
    // lips: open a little as she sings
    float open = 0.004 + 0.012 * uVoice;
    float lipU = sdEll3(h - vec3(0.0, -0.046, -0.082), vec3(0.021, 0.006, 0.009));
    float lipL = sdEll3(h - vec3(0.0, -0.058 - open, -0.08), vec3(0.019, 0.007, 0.009));
    float mouth = sdEll3(h - vec3(0.0, -0.052 - open * 0.5, -0.086), vec3(0.016, open * 0.6 + 0.001, 0.02));
    float lips = min(lipU, lipL);
    d = smin3(d, lips, 0.006);
    d = max(d, -mouth);
    lipMask = step(lips, d + 0.003);
    float ears = min(sdEll3(h - vec3(0.079, 0.0, 0.01), vec3(0.01, 0.026, 0.016)),
                     sdEll3(h - vec3(-0.079, 0.0, 0.01), vec3(0.01, 0.026, 0.016)));
    return smin3(d, ears, 0.008);
}

vec2 singer(vec3 p) {
    vec3 q = p - SINGER;
    float bnd = length(q - vec3(0, 0.9, 0)) - 1.15;
    if (bnd > 0.3) return vec2(bnd, M_GOWN);
    float lift = uP[2].x;
    float br = uP[2].y;
    // ---- the gown: fitted bodice, narrow waist, A-line satin skirt with deepening folds
    float h = q.y;
    float ang = atan(q.x, -q.z);
    float hem = 1.0 - smoothstep(0.0, 0.98, h);
    float folds = (0.022 * sin(ang * 7.0 + 0.6 + uP[2].w) + 0.012 * sin(ang * 13.0 + 2.0)) * hem * hem;
    float rad = mix(0.135, 0.6, pow(hem, 1.35)) + folds;
    vec2 xz = q.xz * vec2(1.0, 1.12) - vec2(0.0, 0.07 * pow(hem, 3.0));      // fuller behind (train)
    float skirt = max(length(xz) - rad, max(-h, h - 1.02));
    float waist = sdEll3(q - vec3(0.0, 1.03, 0.0), vec3(0.118, 0.07, 0.095));
    float ribs = sdEll3(q - vec3(0.0, 1.2 + br * 0.004, 0.0), vec3(0.135, 0.15, 0.105));
    float bust = min(sdEll3(q - vec3(0.058, 1.27, -0.055), vec3(0.07, 0.068, 0.062)),
                     sdEll3(q - vec3(-0.058, 1.27, -0.055), vec3(0.07, 0.068, 0.062)));
    float bodice = smin3(smin3(waist, ribs, 0.06), bust, 0.03);
    bodice = max(bodice, q.y - (1.335 - 0.02 * abs(q.x) * 10.0 * 0.0) - 0.012 * sin(q.x * 40.0) * 0.0);
    float gown = smin3(skirt, bodice, 0.07);
    vec2 res = vec2(gown, M_GOWN);
    // ---- skin: chest, shoulders, collarbones, neck
    float chest = sdEll3(q - vec3(0.0, 1.36, -0.005), vec3(0.15, 0.06, 0.085));
    float delt = min(sdEll3(q - vec3(0.172, 1.395, 0.0), vec3(0.055, 0.05, 0.055)),
                     sdEll3(q - vec3(-0.172, 1.395, 0.0), vec3(0.055, 0.05, 0.055)));
    float clav = min(sdRoundCone(q, vec3(0.012, 1.402, -0.066), vec3(0.15, 1.427, -0.018), 0.006, 0.005),
                     sdRoundCone(q, vec3(-0.012, 1.402, -0.066), vec3(-0.15, 1.427, -0.018), 0.006, 0.005));
    float neck = sdRoundCone(q, vec3(0.0, 1.4, 0.008), vec3(0.0, 1.53, -0.002), 0.054, 0.043);
    float trap = min(sdRoundCone(q, vec3(0.035, 1.47, 0.02), vec3(0.16, 1.425, 0.01), 0.035, 0.03),
                     sdRoundCone(q, vec3(-0.035, 1.47, 0.02), vec3(-0.16, 1.425, 0.01), 0.035, 0.03));
    float skin = smin3(smin3(chest, delt, 0.04), smin3(neck, trap, 0.03), 0.03);
    skin = smin3(skin, clav, 0.018);
    // ---- head, tilted back a little as she sings
    float tilt = uP[2].z;
    vec3 hq = q - vec3(0.0, 1.618, -0.016);
    hq.yz = mat2(cos(tilt), -sin(tilt), sin(tilt), cos(tilt)) * hq.yz;
    float lipMask;
    float head = headSDF(hq, lipMask);
    skin = smin3(skin, head, 0.025);
    // ---- arms: tapered, raised; hands open, palms up
    for (int s = -1; s <= 1; s += 2) {
        float sx = float(s);
        vec3 shp = vec3(0.178 * sx, 1.405, 0.0);
        vec3 du = normalize(mix(vec3(0.14 * sx, -1.0, 0.04), vec3(0.52 * sx, -0.3, -0.62), lift));
        vec3 el = shp + 0.285 * du;
        vec3 df = normalize(mix(vec3(0.04 * sx, -1.0, -0.14), vec3(0.42 * sx, 0.42, -0.72), lift));
        vec3 wr = el + 0.245 * df;
        skin = smin3(skin, sdRoundCone(q, shp, el, 0.041, 0.031), 0.02);
        skin = min(skin, sdRoundCone(q, el, wr, 0.03, 0.022));
        vec3 hd = normalize(df + vec3(0.25 * sx, 0.05, -0.1) * lift);
        // an open hand, palm turned up: palm, four fingers fanning slightly, and the thumb
        vec3 pn = normalize(vec3(0.0, 1.0, 0.0) - hd * hd.y);
        vec3 pw = normalize(cross(hd, pn));
        pw *= sign(dot(pw, vec3(sx, 0.0, 0.0)) + 1e-4);              // +pw points away from her body
        vec3 palm = wr + hd * 0.045;
        vec3 lq = q - palm;
        lq = vec3(dot(lq, pw), dot(lq, pn), dot(lq, hd));
        skin = smin3(skin, sdEll3(lq, vec3(0.036, 0.013, 0.044)), 0.012);
        float fingers = 1e9;
        for (int f = 0; f < 4; f++) {
            float ff = float(f);
            vec3 fb = palm + hd * 0.036 + pw * (0.022 - 0.0145 * ff);
            vec3 fdir = normalize(hd + pn * 0.12 + pw * (0.08 - 0.05 * ff));
            fingers = min(fingers, sdRoundCone(q, fb, fb + fdir * (0.066 - 0.012 * abs(ff - 1.2)), 0.0082, 0.0062));
        }
        vec3 tb = palm + pw * 0.03 - hd * 0.012;
        fingers = min(fingers, sdRoundCone(q, tb, tb + normalize(pw * 0.75 + hd * 0.55 + pn * 0.25) * 0.05, 0.0098, 0.0072));
        skin = smin3(skin, fingers, 0.006);
    }
    lipMask *= step(length(hq), 0.12) * step(head, skin + 0.002);   // lips only on the face
    res = opU(res, vec2(skin, M_SKIN + 0.5 * lipMask));
    // ---- hair: swept up from the face into a chignon
    float hair = sdEll3(hq - vec3(0.0, 0.03, 0.018), vec3(0.086, 0.094, 0.094));
    hair = smin3(hair, sdEll3(hq - vec3(0.0, 0.06, 0.098), vec3(0.055, 0.05, 0.045)), 0.03);
    hair = max(hair, -(-hq.z - 0.035 + 0.55 * (hq.y - 0.04)));      // hairline clears the face
    hair = max(hair, -(hq.y + 0.035 - 0.25 * hq.z));                // and the nape
    res = opU(res, vec2(hair, M_HAIR));
    return res;
}

float spotCone(vec3 p);
// jewellery: a necklace and drop earrings that catch the spot
vec3 jewels(vec3 ro, vec3 rd, float tmax) {
    vec3 acc = vec3(0.0);
    vec3 c0 = SINGER + vec3(0.0, 1.47, -0.02);
    vec3 oc = c0 - ro;
    float tc = dot(oc, rd);
    if (tc < 0.0 || length(oc - rd * tc) > 0.4) return acc;
    for (int k = 0; k < 24; k++) {
        float a = PI * (0.15 + 0.7 * float(k) / 23.0);
        vec3 b = SINGER + vec3(0.085 * cos(a) * 1.2, 1.455 - 0.035 * sin(a), -0.075 * sin(a) - 0.005);
        vec3 ob = b - ro;
        float t = dot(ob, rd);
        if (t < 0.0 || t > tmax + 0.05) continue;
        float d = length(ob - rd * t);
        float tw = 0.6 + 0.4 * sin(uTime * 4.0 + float(k) * 1.7);
        acc += vec3(1.0, 0.92, 0.8) * tw * 2.5e-7 / (d * d + 1e-8);
    }
    for (int s = -1; s <= 1; s += 2) {
        vec3 b = SINGER + vec3(0.081 * float(s), 1.578, -0.014);
        vec3 ob = b - ro;
        float t = dot(ob, rd);
        if (t < 0.0 || t > tmax + 0.05) continue;
        float d = length(ob - rd * t);
        acc += vec3(1.0, 0.95, 0.85) * 4e-7 / (d * d + 1e-8) * (0.7 + 0.3 * sin(uTime * 3.0 + float(s)));
    }
    return acc * spotCone(c0) * 1.0;
}

// ---------------------------------------------------------------- the conductor
// He faces the stage (+z), so his right hand is at -x. From the stalls he is a silhouette in
// tails against the stage, rimmed by its light and haloed by the lamp on his desk.
vec2 conductor(vec3 p) {
    vec3 q = p - COND;
    float bb = length(q - vec3(0.0, 1.25, 0.15));
    if (bb > 1.75) return vec2(bb - 1.55, M_BLACK);
    vec3 bo = vec3(-uP[6].x, uP[6].y, uP[6].z) * 1.6;          // the beat pattern, his way round
    float body = sdEll3(q - vec3(0.0, 1.25, 0.0), vec3(0.23, 0.4, 0.15));
    body = smin3(body, sdEll3(q - vec3(0.0, 1.52, 0.0), vec3(0.27, 0.1, 0.14)), 0.06);
    body = smin3(body, sdCap3(q, vec3(0.0, -0.1, 0.0), vec3(0.0, 0.9, 0.0), 0.15), 0.08);
    body = smin3(body, sdEll3(q - vec3(0.0, 0.74, -0.07), vec3(0.19, 0.36, 0.07)), 0.05);   // tails
    float neck = sdCap3(q, vec3(0.0, 1.58, 0.0), vec3(0.0, 1.74, 0.012), 0.05);
    float head = sdEll3(q - vec3(0.0, 1.85, 0.02), vec3(0.092, 0.112, 0.104));
    head = min(head, min(sdEll3(q - vec3(0.09, 1.84, 0.03), vec3(0.012, 0.03, 0.02)),
                         sdEll3(q - vec3(-0.09, 1.84, 0.03), vec3(0.012, 0.03, 0.02))));
    float collar = max(abs(length(q.xz - vec2(0.0, 0.006)) - 0.055) - 0.011, abs(q.y - 1.665) - 0.022);
    // right arm: the baton, conducting the swell
    vec3 shr = vec3(-0.25, 1.55, 0.0);
    vec3 hand = shr + vec3(-0.17, 0.1, 0.4) + bo;
    vec3 elr = mix(shr, hand, 0.5) + vec3(-0.15, -0.15, -0.05);
    float arm = min(sdCap3(q, shr, elr, 0.05), sdCap3(q, elr, hand - (hand - elr) * 0.16, 0.042));
    float cuff = sdCap3(q, hand - (hand - elr) * 0.2, hand - (hand - elr) * 0.08, 0.046);
    float palm = sdSph(q - hand, 0.045);
    vec3 bdir = normalize(vec3(-0.12, 0.5, 0.85) + bo * 1.5);
    float baton = sdCap3(q, hand, hand + bdir * 0.45, 0.0065);
    // left arm: lifted, open, to cue her breath; otherwise resting at the chest
    float cue = uP[7].x;
    vec3 shl = vec3(0.25, 1.55, 0.0);
    vec3 lh = shl + vec3(mix(0.12, 0.22, cue), mix(-0.16, 0.22, cue) + 0.04 * sin(uTime * 1.3), mix(0.26, 0.32, cue))
              + vec3(-bo.x * 0.35, bo.y * 0.5, 0.0) * (0.3 + 0.7 * cue);
    vec3 ell = mix(shl, lh, 0.5) + vec3(0.14, -0.14, -0.05);
    arm = min(arm, min(sdCap3(q, shl, ell, 0.05), sdCap3(q, ell, lh - (lh - ell) * 0.16, 0.042)));
    cuff = min(cuff, sdCap3(q, lh - (lh - ell) * 0.2, lh - (lh - ell) * 0.08, 0.046));
    palm = min(palm, sdEll3(q - lh - vec3(0.0, 0.03, 0.0), vec3(0.042, 0.06, 0.02)));
    // the podium and his desk, the score lit by its lamp
    float podium = sdBox3(q - vec3(0.0, -0.6, 0.0), vec3(0.5, 0.5, 0.5));
    vec3 dq = q - vec3(0.0, 1.2, 0.5);
    dq.yz = mat2(0.82, -0.57, 0.57, 0.82) * dq.yz;
    float desk = sdBox3(dq, vec3(0.3, 0.2, 0.012));
    float stem = sdCap3(q, vec3(0.0, -0.1, 0.55), vec3(0.0, 1.1, 0.52), 0.015);
    vec2 r = vec2(smin3(smin3(body, arm, 0.04), neck, 0.03), M_BLACK);
    r = opU(r, vec2(head, M_HAIR));
    r = opU(r, vec2(min(podium, stem), M_BLACK));
    r = opU(r, vec2(min(min(collar, cuff), baton), M_SHIRT));
    r = opU(r, vec2(desk, M_SHIRT + 0.5));
    r = opU(r, vec2(palm, M_SKIN));
    return r;
}

// ---------------------------------------------------------------- stalls audience
vec2 stalls(vec3 p) {
    float reg = max(max(p.z + 6.0, p.y - 2.6), (hsR(p) - 0.98) * 11.0);
    // the bound must stay above the hit threshold (0.0008 t, i.e. 0.064 at 80 m) or rays stop on it
    if (reg > 0.0) return vec2(reg + 0.08, 0.0);
    // rows follow arcs centred behind the stage
    vec2 c = vec2(0.0, 6.0);
    float r = length(p.xz - c);
    float a = atan(p.x - c.x, -(p.z - c.y));
    float row = floor((r - 12.0) / 0.95);
    float rr = 12.0 + (row + 0.5) * 0.95;
    float seatW = 0.58 / rr;
    float sid = floor(a / seatW);
    float ac = (sid + 0.5) * seatW;
    vec3 seatPos = vec3(c.x + rr * sin(ac), 0.0, c.y - rr * cos(ac));
    float jit = hash21(vec2(row, sid));
    vec3 lp = p - seatPos;
    float seat = sdBox3(lp - vec3(0.0, 0.45, 0.25), vec3(0.25, 0.45, 0.06));
    vec2 res = vec2(seat, M_SEAT);
    if (jit > 0.06) {
        vec3 hp = lp - vec3((jit - 0.5) * 0.08, 1.12 + 0.08 * hash21(vec2(sid, row + 3.0)), 0.12);
        float head = sdEll3(hp, vec3(0.085, 0.11, 0.095));
        float shoulders = sdEll3(lp - vec3(0.0, 0.88, 0.14), vec3(0.2, 0.14, 0.12));
        res = opU(res, vec2(smin3(head, shoulders, 0.06), M_HEAD + jit * 0.9));   // < 0.99: stays a head
    }
    return res;
}

// ---------------------------------------------------------------- tiers of boxes
vec2 tiers(vec3 p) {
    float r = hsR(p);
    float reg = max(max((0.9 - r) * 11.0, 1.8 - p.y), max(p.y - 13.85, p.z - 0.3));
    if (reg > 0.0) return vec2(reg + 0.08, 0.0);
    vec2 d2 = p.xz - HC;
    float phi = atan(-d2.x / HR.x, -d2.y / HR.y);         // 0 at the back; the seam faces the stage
    float boxW = TAU / 34.0;
    float bid = floor(phi / boxW + 0.5);
    float tier = floor((p.y - 1.8) / 2.4);
    float ty = 1.8 + tier * 2.4;
    float ly = p.y - ty;
    float dr = (r - 1.0) * 12.5;                          // metres outwards from the parapet line
    // parapet band (gilded, curved)
    // (each tier also sees the next tier's parapet and floor: a repeated cell that ignores its
    // neighbour lets rays oscillate at the boundary and leave holes)
    float parapet = max(abs(dr - 0.06) - 0.08, min(abs(ly - 0.55), abs(ly - 2.95)) - 0.55);
    // dividing walls between boxes
    float local = (phi / boxW - bid) * boxW * 12.5;
    float divider = max(max(abs(local) - 0.05, -dr), dr - 2.4);
    // floor of the box and back wall (dark)
    float shell = max(max(min(abs(ly), abs(ly - 2.4)) - 0.06, -dr), dr - 2.4);
    float back = 2.45 - dr;                               // solid beyond the back of the box
    vec2 res = vec2(min(parapet, 1e9), M_GILT);
    res = opU(res, vec2(max(divider, abs(ly - 1.2) - 1.2), M_BOXIN));
    res = opU(res, vec2(shell, M_BOXIN));
    res = opU(res, vec2(back, M_BOXIN));
    // occupants: two or three faces at the parapet
    float occ = hash21(vec2(bid, tier));
    if (tier < 5.0 && occ > 0.12) {
        for (int k = -1; k <= 1; k++) {
            float hk = hash21(vec2(bid * 3.0 + float(k), tier + 7.0));
            if (hk < 0.25 && k == 0) continue;
            vec3 hp = vec3(local - float(k) * 0.62 - (hk - 0.5) * 0.1, ly - 1.42 - 0.1 * hk, dr - 0.55);
            float head = sdEll3(hp, vec3(0.09, 0.115, 0.1));
            float body = sdEll3(hp - vec3(0.0, -0.33, 0.06), vec3(0.2, 0.2, 0.13));
            res = opU(res, vec2(smin3(head, body, 0.06), M_HEAD + hk * 0.9));
        }
    }
    return res;
}

// ---------------------------------------------------------------- the house shell and stage
vec2 map(vec3 p) {
    vec2 res = vec2(1e9, 0.0);
    // floors
    // the stage as a solid block (with its front face), and the stalls floor with the pit cut out
    // of it as a box, so every face of the step between them exists in the field
    float stageBlock = max(p.y - 1.2, -0.55 - p.z);
    float pitBox = sdBox3(p - vec3(0.0, -0.25, -3.275), vec3(8.0, 1.25, 2.725));
    float stallsFloor = max(p.y, -pitBox);
    if (stageBlock < stallsFloor) res = opU(res, vec2(stageBlock, p.y > 1.18 ? M_STAGE : M_WALL));
    else res = opU(res, vec2(stallsFloor, (p.y < -0.01 && pitBox < 0.05) ? M_PIT : M_FLOOR));
    // stage apron face and pit rail
    res = opU(res, vec2(sdBox3(p - vec3(0.0, -0.15, -0.62), vec3(9.0, 1.35, 0.07)), M_WALL));
    res = opU(res, vec2(sdBox3(p - vec3(0.0, 0.45, -6.05), vec3(8.0, 0.45, 0.05)), M_WALL + 0.25));
    // stage box: back and side walls (black), fly tower
    res = opU(res, vec2(16.5 - p.z, M_BLACK));
    res = opU(res, vec2(max(10.5 - abs(p.x), 0.45 - p.z), M_BLACK));   // stage-house walls behind the frame
    // the painted cloth, hung a little slack, and the wall fragment with her window
    if (p.z > 6.0) {
        float sway = 0.04 * sin(p.x * 0.9 + uTime * 0.35) * smoothstep(1.2, 6.0, p.y);
        res = opU(res, vec2(CYC_Z + sway - p.z, M_CYC));
        float slab = sdBox3(p - vec3(0.0, 4.7, WALL_Z), vec3(2.5, 3.5, 0.11));
        float wo = window2D(p.xy);
        float bars = min(max(abs(p.x) - 0.04, abs(p.z - WALL_Z) - 0.035),
                         min(max(abs(p.y - 6.0) - 0.04, abs(p.z - WALL_Z) - 0.035),
                             max(min(abs(p.y - 3.55), abs(p.y - 4.8)) - 0.022, abs(p.z - WALL_Z) - 0.03)));
        float sill = sdBox3(p - vec3(0.0, 2.27, WALL_Z - 0.12), vec3(1.62, 0.05, 0.12));
        float wall = max(slab, -wo);
        wall = min(wall, max(bars, wo));
        res = opU(res, vec2(min(wall, sill), M_WALLFRAG));
    }
    // proscenium: a gilded frame around the opening (x in +-7, y up to 10.8)
    // (the opening runs below the boards: a frame face coplanar with the stage floor z-fights)
    float open = sdBox3(p - vec3(0.0, 4.4, 0.0), vec3(7.0, 6.4, 2.0));
    float frame = max(sdBox3(p - vec3(0.0, 7.5, 0.0), vec3(9.5, 7.5, 0.45)), -open);
    res = opU(res, vec2(frame, M_GILT));
    // the auditorium wall beyond the boxes and the dome
    if (p.z < 0.3) {
        float wall = (1.2 - hsR(p)) * 12.0;
        res = opU(res, vec2(-wall + 0.0 > 0.0 ? 1e9 : abs(wall) - 0.1 + max(0.0, -wall), M_BOXIN));
        float rr = hsR(p);
        float ceilY = 15.4 + 2.4 * (1.0 - min(rr * rr, 1.44));       // a shallow painted dome
        res = opU(res, vec2((ceilY - p.y) * 0.75, M_DOME));
    }
    // drapes: velvet swags at the sides of the opening and a valance
    float folds = 0.06 * sin(p.x * 9.0 + 1.3) + 0.04 * sin(p.x * 23.0);
    for (int s = -1; s <= 1; s += 2) {
        float sx = float(s);
        float tie = smoothstep(4.5, 2.5, p.y);
        float w = 1.35 + 0.6 * tie;
        float drape = sdBox3(p - vec3(sx * (7.0 - w * 0.5 + 0.02), 5.9, 0.55 + folds),
                             vec3(w * 0.5, 4.7, 0.12));
        res = opU(res, vec2(drape, M_VELVET));
    }
    float scallop = 0.25 * abs(sin(p.x * 0.9));
    float valance = sdBox3(p - vec3(0.0, 10.25 + scallop * 0.5, 0.45 + folds), vec3(7.2, 0.62 - scallop * 0.5, 0.12));
    res = opU(res, vec2(valance, M_VELVET));
    // the main curtain, descending at the end
    float drop = uP[3].w;
    if (drop > 0.0) {
        float bottom = 10.8 - drop * 9.6;
        float cz = 0.35 + 0.08 * sin(p.x * 6.0) + 0.05 * sin(p.x * 15.0);
        float curtain = max(sdBox3(p - vec3(0.0, 6.0, cz), vec3(7.2, 4.9, 0.06)), bottom - p.y);
        res = opU(res, vec2(curtain, M_CURTAIN));
    }
    if (uP[7].y < 0.5) res = opU(res, singer(p));     // uP[7].y = 1: the stage is empty (full opera's act curtains)
    res = opU(res, conductor(p));
    // pit musicians: heads and shoulders below the stage edge
    float preg = max(max(p.y - 0.4, p.z + 0.6), -6.0 - p.z);
    if (preg > 0.0) res = opU(res, vec2(preg + 0.08, 0.0));
    else {
        vec2 cell = vec2(1.1, 1.0);
        vec2 id = floor(vec2(p.x, p.z + 0.6) / cell);
        vec3 lp = vec3(mod(p.x, cell.x) - 0.55, p.y + 0.55, mod(p.z + 0.6, cell.y) - 0.5);
        float hj = hash21(id);
        if (abs(id.x) < 7.0 && id.y > -5.0 && hj > 0.15 && !(abs(id.x) < 1.0 && id.y < -2.0 && id.y > -4.0)) {
            float mus = sdEll3(lp - vec3(0.0, 0.0, 0.0), vec3(0.2, 0.32, 0.15));
            mus = smin3(mus, sdSph(lp - vec3(0.0, 0.42, 0.0), 0.1), 0.05);
            res = opU(res, vec2(mus, M_BLACK + 0.3));
        }
    }
    vec2 st = stalls(p);
    vec2 ti = tiers(p);
    res = opU(res, st);
    res = opU(res, ti);
    // domain repetition makes these fields discontinuous at cell edges: never stride across a cell
    float inStalls = max(max(p.z + 6.0, p.y - 2.6), (hsR(p) - 0.98) * 11.0);
    float inTiers = max(max((0.9 - hsR(p)) * 11.0, 1.8 - p.y), max(p.y - 13.85, p.z - 0.3));
    if (inStalls < 0.0) res.x = min(res.x, 0.22);
    if (inTiers < 0.0) res.x = min(res.x, 0.3);
    return res;
}

vec3 normal(vec3 p) {
    vec2 e = vec2(0.0015, 0.0);
    return normalize(vec3(map(p + e.xyy).x - map(p - e.xyy).x, map(p + e.yxy).x - map(p - e.yxy).x,
                          map(p + e.yyx).x - map(p - e.yyx).x));
}

// ---------------------------------------------------------------- lights
const vec3 SPOT_POS = vec3(0.0, 13.5, -23.0);
vec3 spotDir() { return normalize(SINGER + vec3(0.0, 1.1, 0.0) - SPOT_POS); }
float spotCone(vec3 p) {
    float c = dot(normalize(p - SPOT_POS), spotDir());
    float inner = mix(0.9975, 0.99935, uP[3].x);
    float outer = mix(0.9935, 0.9986, uP[3].x);
    return smoothstep(outer, inner, c);
}
vec3 SPOT_COL = vec3(1.0, 0.78, 0.46) * 1.45;

vec3 headSpace(vec3 p) {
    vec3 hq = p - SINGER - vec3(0.0, 1.618, -0.016);
    float tilt = uP[2].z;
    hq.yz = mat2(cos(tilt), -sin(tilt), sin(tilt), cos(tilt)) * hq.yz;
    return hq;
}

vec3 shade(vec3 p, vec3 n, vec3 rd, float mat) {
    vec3 L = normalize(SPOT_POS - p);
    float spot = spotCone(p) * sat(dot(n, L));
    // stage wash from overhead battens (warm), only over the stage
    vec3 W = normalize(vec3(0.0, 1.0, -0.35));
    float washArea = smoothstep(-1.0, 0.5, p.z) * smoothstep(12.0, 6.0, abs(p.x)) * (1.0 - smoothstep(14.0, 16.0, p.z));
    float wash = uP[3].y * washArea * sat(dot(n, W) * 0.7 + 0.3);
    // spill from the lit stage onto the house (faces turned to the stage)
    vec3 toStage = normalize(vec3(0.0, 3.0, 4.0) - p);
    float spill = sat(dot(n, toStage) * 0.8 + 0.2) * (p.z < -0.5 ? 1.0 : 0.0) * 1.1 / (1.0 + 0.003 * dot(p.xz - vec2(0, 4), p.xz - vec2(0, 4)));
    float house = uP[3].z;
    vec3 albedo;
    float spec = 0.0, shin = 16.0;
    vec3 emis = vec3(0.0);
    if (mat < 1.5) albedo = vec3(0.10, 0.05, 0.04);
    else if (mat < 2.5) { albedo = vec3(0.22, 0.13, 0.08) * (0.85 + 0.15 * vnoise(p.xz * vec2(0.8, 5.0))); spec = 0.1; }
    else if (mat < 3.5) albedo = vec3(0.05, 0.035, 0.03);
    else if (mat < 4.5) {
        float orn = 0.6 + 0.4 * fbm(p.xy * 3.0 + p.z) ;
        albedo = vec3(0.72, 0.52, 0.22) * orn; spec = 0.9; shin = 28.0;
    } else if (mat < 5.5) {
        albedo = vec3(0.36, 0.025, 0.04) * (0.65 + 0.35 * abs(sin(p.x * 9.0)));
        spec = 0.08;
    } else if (mat < 6.5) {
        float ang2 = atan(p.x - SINGER.x, -(p.z - SINGER.z));
        float hem2 = 1.0 - smoothstep(1.2, 2.2, p.y);
        float valley = 0.5 + 0.5 * sin(ang2 * 7.0 + 0.6 + uP[2].w);
        albedo = vec3(0.46, 0.016, 0.038) * mix(1.0, 0.55 + 0.45 * valley, hem2);
        spec = 0.16; shin = 10.0;
    } else if (mat < 7.75) {                         // skin, and lips at 7.5
        albedo = mat > 7.25 ? vec3(0.5, 0.07, 0.09) : vec3(0.66, 0.44, 0.33);
        spec = mat > 7.25 ? 0.45 : 0.22; shin = 26.0;
        vec3 hq = headSpace(p);
        if (length(hq) < 0.13 && hq.z < -0.03) {
            float ax = abs(hq.x);
            float lash = smoothstep(0.0028, 0.0006, abs(hq.y - (0.0085 - 1.4 * (ax - 0.028) * (ax - 0.028))))
                         * smoothstep(0.019, 0.014, abs(ax - 0.03)) * step(hq.z, -0.07);
            float brow = smoothstep(0.0038, 0.001, abs(hq.y - (0.034 - 4.0 * (ax - 0.026) * (ax - 0.026))))
                         * smoothstep(0.024, 0.016, abs(ax - 0.03)) * step(hq.z, -0.062);
            float blush = exp(-pow((ax - 0.042) / 0.017, 2.0) - pow((hq.y + 0.014) / 0.014, 2.0));
            albedo = mix(albedo, vec3(0.07, 0.045, 0.04), max(lash, brow * 0.65));
            albedo = mix(albedo, vec3(0.72, 0.34, 0.3), blush * 0.28);
            // inside the open mouth only (the cavity carved in headSDF, slightly enlarged)
            float open = 0.004 + 0.012 * uVoice;
            vec3 mc = vec3(0.0, -0.052 - open * 0.5, -0.086);
            float cav = sdEll3(hq - mc, vec3(0.016, open * 0.6 + 0.001, 0.02) * 1.12);
            float inMouth = smoothstep(0.0015, -0.0005, cav);
            float teeth = inMouth * smoothstep(0.35, 0.75, (hq.y - mc.y) / (open * 0.6 + 0.001)) * step(0.0, open - 0.006);
            albedo = mix(albedo, vec3(0.2, 0.03, 0.04), inMouth);
            albedo = mix(albedo, vec3(0.55, 0.5, 0.45), teeth * 0.45);
        }
        float wrapd = sat((dot(n, normalize(SPOT_POS - p)) + 0.45) / 1.45);
        emis += albedo * vec3(1.0, 0.5, 0.35) * SPOT_COL * spotCone(p) * 0.06 * wrapd;
    }
    else if (mat < 8.5) { albedo = vec3(0.05, 0.035, 0.03); spec = 0.3; }
    else if (mat < 9.5) { albedo = vec3(mat > 9.2 ? 0.045 : 0.018); spec = 0.2; }
    else if (mat < 10.5) albedo = vec3(0.28, 0.03, 0.04);
    else if (mat < 11.99) {
        float k = fract(mat);
        vec3 skin = mix(vec3(0.62, 0.42, 0.32), vec3(0.42, 0.28, 0.2), k);
        float hairCap = smoothstep(0.02, 0.06, n.y) * step(0.5, fract(k * 7.0));
        albedo = mix(skin, vec3(0.06, 0.045, 0.035), hairCap * 0.8);
        spec = 0.15;
        // faces in the stalls, turned to the stage: brows, eyes and a mouth as soft dark marks
        if (p.z < -6.0 && p.y < 2.6) {
            vec2 c = vec2(0.0, 6.0);
            float r = length(p.xz - c);
            float a = atan(p.x - c.x, -(p.z - c.y));
            float row = floor((r - 12.0) / 0.95);
            float rr = 12.0 + (row + 0.5) * 0.95;
            float seatW = 0.58 / rr;
            float sid = floor(a / seatW);
            float ac = (sid + 0.5) * seatW;
            vec3 seatPos = vec3(c.x + rr * sin(ac), 0.0, c.y - rr * cos(ac));
            float jit = hash21(vec2(row, sid));
            vec3 hq = p - seatPos - vec3((jit - 0.5) * 0.08, 1.12 + 0.08 * hash21(vec2(sid, row + 3.0)), 0.12);
            vec2 fwd = normalize(c - seatPos.xz);
            float fz = dot(hq.xz, fwd), sx = dot(hq.xz, vec2(fwd.y, -fwd.x)), uy = hq.y;
            if (fz > 0.04) {
                float eyes = smoothstep(0.016, 0.008, length(vec2(abs(sx) - 0.031, (uy - 0.012) * 1.6)));
                float brows = smoothstep(0.007, 0.002, abs(uy - 0.034 + 0.25 * (abs(sx) - 0.03) * (abs(sx) - 0.03) * 40.0))
                              * smoothstep(0.05, 0.035, abs(sx)) * step(0.012, abs(sx));
                float mouth = smoothstep(0.006, 0.002, abs(uy + 0.048)) * smoothstep(0.022, 0.012, abs(sx));
                albedo = mix(albedo, vec3(0.05, 0.03, 0.025), max(eyes * 0.85, max(brows * 0.6, mouth * 0.45)));
            }
        }
    } else if (mat < 12.5) albedo = vec3(0.12, 0.025, 0.03);
    else if (mat < 13.5) {
        // the fresco: radial panels of painted sky between gilded ribs
        vec2 d2 = (p.xz - HC) / HR;
        float a = atan(d2.y, d2.x);
        float rr = length(d2);
        float rib = smoothstep(0.035, 0.0, abs(fract(a / TAU * 16.0) - 0.5) * 0.25 * rr - 0.0);
        float ring = smoothstep(0.03, 0.0, abs(rr - 0.18)) + smoothstep(0.03, 0.0, abs(rr - 0.92));
        vec3 sky = mix(vec3(0.20, 0.27, 0.36), vec3(0.55, 0.42, 0.28), fbm(d2 * 6.0 + 3.0));
        albedo = mix(sky, vec3(0.75, 0.55, 0.25), sat(rib + ring));
        spec = (rib + ring) * 0.6;
        float ripple = uP[4].z * exp(-pow((rr - fract(uTime * 0.35)) * 9.0, 2.0)) * 0.6;
        emis += vec3(1.0, 0.75, 0.4) * ripple * (0.6 + 0.4 * (rib + ring));
        emis += mix(vec3(0.0), vec3(0.25, 0.4, 0.85), uP[4].y) * 0.15 * (1.0 - rr);
    } else if (mat < 14.5) albedo = vec3(0.03, 0.02, 0.015);
    else if (mat < 15.5) {
        albedo = vec3(0.42, 0.03, 0.045) * (0.6 + 0.4 * abs(sin(p.x * 6.0)));
        spec = 0.1;
    } else if (mat < 16.5) {
        // old plaster, sun-faded: kept darker than her so the window and the singer carry the eye
        float stain = fbm(p.xy * 1.3 + 4.0);
        albedo = vec3(0.2, 0.15, 0.11) * (0.75 + 0.35 * stain);
        float reveal = smoothstep(0.12, 0.0, abs(window2D(p.xy)));          // the reveal catches the sea light
        emis += cycPaint(vec2(p.x * 0.6, 4.6)) * cycLight() * reveal * 0.2;
    } else if (mat < 17.5) {
        // the cloth is lit by its own battens and groundrow: return it unshaded
        vec3 c = cycPaint(p.xy) * cycLight();
        c += vec3(1.0, 0.55, 0.25) * exp(-(p.y - 1.2) * 1.1) * 0.25 * uP[3].y;
        return c;
    } else if (mat < 18.25) {
        albedo = vec3(0.75, 0.73, 0.68); spec = 0.3;                      // shirt collar, cuffs, baton
    } else {
        albedo = vec3(0.8, 0.76, 0.66);                                   // the score on his desk
        float dl = length(p - DESK_LAMP);
        emis += vec3(1.0, 0.8, 0.5) * 0.35 / (1.0 + dl * dl * 40.0);
    }
    // soft front fill from the front-of-house positions, and a golden upstage backlight
    vec3 Fd = normalize(vec3(0.0, 0.35, -1.0));
    float fill = smoothstep(-1.5, 0.5, p.z) * uP[3].y * sat(dot(n, Fd) * 0.6 + 0.4);
    vec3 Bk = normalize(vec3(0.0, 12.0, 13.0) - p);
    float onStage = smoothstep(-0.6, 0.6, p.z) * (1.0 - smoothstep(9.0, 12.0, p.z));
    float backRim = pow(1.0 - sat(dot(n, -rd)), 3.0) * sat(dot(n, Bk)) * onStage;
    vec3 H = normalize(L - rd);
    vec3 col = albedo * vec3(1.0, 0.8, 0.58) * 0.55 * fill;
    wash *= 0.7;
    float rimK = (mat > 5.5 && mat < 6.5) ? 0.5 : (mat > 6.5 && mat < 7.5) ? 0.35 : (mat > 7.5 && mat < 8.5) ? 0.22 : 0.08;
    col += vec3(1.0, 0.72, 0.38) * backRim * rimK * (0.4 + uP[3].y);
    col += albedo * (SPOT_COL * spot + vec3(1.0, 0.72, 0.42) * 1.6 * wash + vec3(1.0, 0.75, 0.5) * spill * (0.4 + house)
                         + vec3(0.9, 0.6, 0.35) * 0.05 * house);
    col += SPOT_COL * spot * spec * pow(sat(dot(n, H)), shin) * 0.6;
    // gown sheen and rim from the wash
    if (mat > 5.5 && mat < 7.5) col += vec3(1.0, 0.6, 0.35) * pow(1.0 - sat(dot(n, -rd)), 3.0) * 0.6 * (spot + 0.4 * wash);
    // a side light from the stage-left boom models her face and arms against the frontal spot
    if (mat > 5.5 && mat < 8.5 && p.z > 2.0 && p.z < 6.0) {
        vec3 Ls = normalize(vec3(1.0, 0.45, -0.25));
        col += albedo * vec3(1.0, 0.8, 0.6) * 0.55 * pow(sat(dot(n, Ls)), 1.5) * (0.3 + uP[3].y);
        col *= 1.0 - 0.18 * sat(dot(n, vec3(-1.0, 0.0, 0.0)));      // and the far side falls away
    }
    // box sconces: a small warm lamp on the back wall of every box
    if (mat > 11.99 && mat < 12.5 && p.z < 0.3) {
        vec2 d2 = p.xz - HC;
        float phi = atan(-d2.x / HR.x, -d2.y / HR.y);
        float boxW = TAU / 34.0;
        float local = (phi / boxW - floor(phi / boxW + 0.5)) * boxW * 12.5;
        float ly = p.y - (1.8 + floor((p.y - 1.8) / 2.4) * 2.4);
        float lamp = exp(-(local * local) / 0.02 - pow(ly - 1.75, 2.0) / 0.01);
        float halo = exp(-(local * local) / 0.35 - pow(ly - 1.6, 2.0) / 0.4);
        col += vec3(1.0, 0.6, 0.28) * (lamp * 3.0 + halo * 0.18) * (0.25 + house);
    }
    if (mat > 3.5 && mat < 4.5) col += vec3(0.85, 0.6, 0.28) * (spill * 0.5 + 0.05 + 0.12 * house) * (0.5 + 0.5 * fbm(p.xy * 9.0 + p.z * 3.0));
    // footlights wash the singer from below
    if (p.z > 2.0 && p.z < 6.0) col += albedo * vec3(1.0, 0.6, 0.3) * 0.5 * uP[3].y * sat(-n.y * 0.5 + 0.5) * smoothstep(3.0, 0.5, p.y - 1.2);
    // the conductor and the pit: dark figures rimmed by light spilling from the stage behind them
    if ((mat > 8.5 && mat < 9.5 || mat > 7.5 && mat < 8.5) && p.z < -0.6 && p.z > -6.0) {
        vec3 toS = normalize(vec3(0.0, 2.4, 4.0) - p);
        float rimS = pow(1.0 - sat(dot(n, -rd)), 2.4) * sat(dot(n, toS) + 0.1);
        col += vec3(1.0, 0.68, 0.36) * rimS * 0.9 * (0.4 + uP[3].y);
    }
    // the audience in the stalls: the backs of heads, edged by the light from the stage
    if (mat > 10.99 && mat < 11.95 && p.z < -6.0) {
        vec3 toS = normalize(vec3(0.0, 3.0, 4.0) - p);
        float rimS = pow(1.0 - sat(dot(n, -rd)), 3.0) * sat(dot(n, toS) + 0.15);
        col += vec3(1.0, 0.7, 0.4) * rimS * 0.22 * (0.3 + uP[3].y);
    }
    // the desk lamp: a small warm source in the pit that finds his hands, cuffs and baton
    {
        vec3 dl = DESK_LAMP - p;
        float d2 = dot(dl, dl);
        if (d2 < 4.0) col += albedo * vec3(1.0, 0.75, 0.45) * sat(dot(n, dl * inversesqrt(d2))) * 0.05 / (d2 + 0.05);
    }
    // the boards are semi-gloss: a soft reflection of the lit cloth, and of the dark wall fragment
    if (mat > 1.5 && mat < 2.5) {
        vec3 rr = reflect(rd, n);
        if (rr.z > 0.02) {
            float tw = (WALL_Z - p.z) / rr.z;
            vec3 hw = p + rr * tw;
            vec3 hc = p + rr * ((CYC_Z - p.z) / rr.z);
            vec3 refl = 0.5 * (cycPaint(hc.xy) + cycPaint(hc.xy + vec2(0.0, 0.7))) * cycLight();
            float wm = step(0.0, tw) * smoothstep(2.9, 2.1, abs(hw.x)) * smoothstep(8.6, 7.6, hw.y)
                       * smoothstep(-0.35, 0.35, window2D(hw.xy));
            refl = mix(refl, vec3(0.03, 0.022, 0.016), wm);
            float fres = 0.015 + 0.22 * pow(1.0 - sat(dot(n, -rd)), 5.0);
            col += refl * fres * (0.7 + 0.3 * vnoise(p.xz * vec2(0.8, 5.0)));
        }
    }
    // her shadow on the boards
    if (mat > 1.5 && mat < 2.5) {
        vec2 off = (p.xz - SINGER.xz) - vec2(0.0, 0.9);
        col *= 1.0 - 0.7 * exp(-dot(off * vec2(2.2, 0.9), off * vec2(2.2, 0.9))) * smoothstep(0.0, 0.5, uP[3].y + uP[3].x);
    }
    return col + emis;
}

// chandelier: emissive bulbs and twinkling crystals, by closest approach of the ray
vec3 chandelier(vec3 ro, vec3 rd, float tmax) {
    vec3 C = vec3(HC.x, 12.4, HC.y);
    vec3 oc = C - ro;
    float tc = dot(oc, rd);
    if (tc < 0.0) return vec3(0.0);
    float miss = length(oc - rd * tc);
    if (miss > 3.2) return vec3(0.0);
    vec3 acc = vec3(0.0);
    for (int ring = 0; ring < 3; ring++) {
        float rr = 1.5 - 0.42 * float(ring);
        float yy = -0.2 + 0.55 * float(ring);
        int nb = 18 - ring * 4;
        for (int k = 0; k < 18; k++) {
            if (k >= nb) break;
            float a = TAU * float(k) / float(nb) + float(ring) * 0.3;
            vec3 b = C + vec3(rr * cos(a), yy, rr * sin(a));
            vec3 ob = b - ro;
            float t = dot(ob, rd);
            if (t < 0.0 || t > tmax) continue;
            float d = length(ob - rd * t);
            float px = t * 0.0012;
            acc += vec3(1.0, 0.8, 0.55) * (0.0009 / (d * d + px * px * 0.5)) * (0.25 + uP[3].z * 0.5);
        }
    }
    // crystals catching the light: they sparkle with her voice
    for (int k = 0; k < 90; k++) {
        float fk = float(k);
        float a = fk * 2.39996;
        float yy = -0.9 + 1.9 * hash11(fk * 1.7);
        float rr = (1.65 - 0.55 * (yy + 0.9) / 1.9) * sqrt(hash11(fk * 3.1));
        vec3 b = C + vec3(rr * cos(a), yy, rr * sin(a));
        vec3 ob = b - ro;
        float t = dot(ob, rd);
        if (t < 0.0 || t > tmax) continue;
        float d = length(ob - rd * t);
        float tw = pow(0.5 + 0.5 * sin(uTime * (3.0 + 5.0 * hash11(fk)) + fk), 6.0);
        float spark = (0.15 + 1.4 * uP[4].x * tw) * 0.00025 / (d * d + 1e-6 + t * t * 1e-6);
        acc += mix(vec3(1.0, 0.9, 0.75), vec3(0.7, 0.85, 1.0), hash11(fk * 9.0)) * spark;
    }
    return acc;
}

// volumetric light: the follow spot through the haze, the stage wash, the pit lamps
vec3 volume(vec3 ro, vec3 rd, float tmax) {
    vec3 acc = vec3(0.0);
    float steps = 28.0;
    float tEnd = min(tmax, 60.0);
    float dt = tEnd / steps;
    float jit = hash21(gl_FragCoord.xy + fract(uTime) * 100.0);
    for (int i = 0; i < 28; i++) {
        float t = (float(i) + jit) * dt;
        vec3 p = ro + rd * t;
        float cone = spotCone(p);
        float dust = 0.55 + 0.45 * fbm3(p * 0.6 + vec3(0.0, uTime * 0.04, uTime * 0.02));
        float g = 0.3 + 0.9 * pow(sat(dot(rd, -spotDir())), 8.0);
        acc += SPOT_COL * cone * dust * g * 0.0035 * dt;
        float washArea = smoothstep(-0.5, 1.5, p.z) * smoothstep(9.0, 4.0, abs(p.x)) * smoothstep(13.0, 4.0, p.y) * smoothstep(1.0, 2.5, p.y) * (1.0 - smoothstep(10.0, 15.0, p.z));
        acc += vec3(1.0, 0.7, 0.4) * washArea * uP[3].y * dust * 0.0016 * dt;
    }
    return acc;
}

// the warm haze over the pit, integrated only across the stretch of ray inside the pit: the old
// jittered march put one or two samples there and turned it into glitter along the stage edge
vec3 pitHaze(vec3 ro, vec3 rd, float tmax) {
    vec3 sr = sign(rd) * max(abs(rd), vec3(1e-5));
    vec3 t0 = (vec3(-8.0, -1.5, -6.0) - ro) / sr, t1 = (vec3(8.0, 0.6, -0.6) - ro) / sr;
    vec3 tn = min(t0, t1), tf = max(t0, t1);
    float a = max(max(tn.x, tn.y), max(tn.z, 0.0));
    float b = min(min(tf.x, tf.y), min(tf.z, tmax));
    if (b <= a) return vec3(0.0);
    float dt = (b - a) / 10.0;
    float acc = 0.0;
    for (int i = 0; i < 10; i++) {
        vec3 p = ro + rd * (a + (float(i) + 0.5) * dt);
        acc += smoothstep(-6.0, -1.0, p.z) * smoothstep(-0.5, -1.5, p.z) * smoothstep(0.6, -1.0, p.y) * smoothstep(-2.0, -1.0, p.y);
    }
    return vec3(1.0, 0.6, 0.3) * acc * dt * 0.012 * (0.6 + 0.4 * uP[6].w);
}

void main() {
    vec2 sp = screen();
    vec3 ro = uP[0].xyz;
    vec3 ta = uP[1].xyz;
    float fl = uP[1].w;
    vec3 ww = normalize(ta - ro);
    vec3 uu = normalize(cross(ww, vec3(0.0, 1.0, 0.0)));
    vec3 vv = cross(uu, ww);
    vec3 rd = normalize(sp.x * uu + sp.y * vv + fl * ww);
    float t = 0.02;
    vec2 h = vec2(0.0);
    bool hit = false;
    for (int i = 0; i < 320; i++) {
        vec3 p = ro + rd * t;
        h = map(p);
        if (abs(h.x) < 0.0008 * t) { hit = true; break; }
        t += h.x * 0.9;
        if (t > 80.0) break;
    }
    // rays that ran out of steps grazing a surface are hits, not holes
    if (!hit && t < 80.0 && abs(h.x) < 0.02) hit = true;
    vec3 col = vec3(0.004, 0.003, 0.003);
    if (hit) {
        vec3 p = ro + rd * t;
        vec3 n = normal(p);
        col = shade(p, n, rd, h.y);
        col *= exp(-t * 0.012);
    }
    col += volume(ro, rd, hit ? t : 80.0);
    col += pitHaze(ro, rd, hit ? t : 80.0);
    col += chandelier(ro, rd, hit ? t : 80.0);
    col += jewels(ro, rd, hit ? t : 80.0);
    // pit stand lamps: small warm glows
    for (int k = 0; k < 12; k++) {
        vec3 lp = vec3(-6.0 + float(k) * 1.1 + 0.3 * hash11(float(k)), -0.05, -1.4 - 1.6 * hash11(float(k) * 3.0));
        vec3 ob = lp - ro;
        float tt = dot(ob, rd);
        if (tt < 0.0 || (hit && tt > t + 0.5)) continue;
        float d = length(ob - rd * tt);
        col += vec3(1.0, 0.7, 0.35) * 0.00012 / (d * d + 4e-5) * uP[6].w;
    }
    // the conductor's desk lamp, hidden by his body when we are behind him
    {
        vec3 ob = DESK_LAMP - ro;
        float tt = dot(ob, rd);
        if (tt > 0.0 && !(hit && tt > t + 0.03)) {
            float d = length(ob - rd * tt);
            col += vec3(1.0, 0.74, 0.42) * (0.00008 / (d * d + 2e-5) + 0.004 / (d * d * 30.0 + 0.04)) * uP[6].w;
        }
    }
    // Vittorio: a cold breath through the dark of the hall
    col = mix(col, col * vec3(0.75, 0.85, 1.2) + vec3(0.0, 0.004, 0.012) * uP[4].y, uP[4].y * 0.6);
    fragColor = vec4(col, 1.0);
}
