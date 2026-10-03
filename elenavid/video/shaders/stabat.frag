#version 430
// ---------------------------------------------------------------------------------------------
// stabat.frag  -  STABAT MATER (Act III, scene 1). The lovers are together offstage; an unseen
// chorus sings. Darkness, and in it hundreds of small flames held in rows that curve away like the
// tiers of a theatre into a vast dark space: the unseen witnesses. Their light lies on a black
// polished floor. Colossal pillars stand far off, barely there.
// uP[0]  x candle field intensity 0..1
//        y the lovers in a lit doorway (alpha 0..1); as it falls the door swings shut
//        z final mode 0..1: the flames go out one by one until a single held point remains
//        w camera drift (a slow dolly forward and to the side; the shot list feeds 0..~0.2)
// uP[1]  x 'gladius': a cold-white shimmer travelling out through the field (an envelope 0..1)
//        y 'desolatum': the field darkens, the farthest rows first (envelope 0..1)
// ---------------------------------------------------------------------------------------------
#include common

const float HOR = 0.16;         // horizon on screen
const float EYE = 0.5;          // eye height above the floor (world): we look down on the field
const float FLAME_H = 0.3;      // the flames are held this high above the floor
const float SPACING = 0.32;     // between flames in a row (world)
const float Z0 = 0.62, ZG = 1.12; // row depths: Z0 * ZG^i
const int ROWS = 36;
const float CURVE = 0.018;      // rows bend away at the sides, like the tiers of a horseshoe
const vec3 FLAME = vec3(1.0, 0.6, 0.28);
const vec3 COLDW = vec3(0.82, 0.9, 1.0);

float gT, gPx, gCamX, gCamZ, gField, gFinal, gGlad, gDeso;
vec2 gSp;

// light of one flame (and its reflection in the floor) at a screen position
vec3 flameLight(vec2 sp, vec2 pos, float r, float I, vec3 c, float near) {
    vec2 d = sp - pos;
    // the flame: a small upright teardrop, a hot core and a soft halo
    vec2 fq = vec2(d.x * (1.0 + 0.6 * sat(d.y / r)), (d.y - r * 0.45) * 0.5);
    float core = exp(-dot(fq, fq) / (r * r * 0.22));
    float halo = r * r / (dot(d, d) * 1.6 + r * r) * 0.3;
    vec3 L = c * I * (core * 3.0 + halo + exp(-dot(d, d) / (r * r * 0.05)) * 1.5);
    return L;
}

vec3 field(vec2 sp) {
    vec3 acc = vec3(0.0);
    float logMax = log(Z0 * pow(ZG, float(ROWS - 1)));
    for (int i = 0; i < ROWS; i++) {
        float fi = float(i);
        float zr = Z0 * pow(ZG, fi) - gCamZ;
        if (zr < 0.25) continue;
        float nearFade = smoothstep(0.3, 0.75, zr);
        float depth01 = log(zr + gCamZ) / logMax;
        float off = (mod(fi, 2.0) * 0.5 + 0.08 * (hash11(fi * 7.31) - 0.5)) * SPACING;   // staggered rows
        float yRow = -EYE + FLAME_H + 0.012 * (hash11(fi * 3.7) - 0.5);
        // which flames in this row are nearest the pixel (one refinement for the curve)
        float x0 = sp.x * zr + gCamX;
        x0 = sp.x * (zr + CURVE * x0 * x0) + gCamX;
        // a flame's light is local: skip rows far from both their flames and their reflections here
        float zp = zr + CURVE * x0 * x0;
        float rowY = HOR + yRow / zp, refY = HOR + (-2.0 * EYE - yRow) / zp;
        float reach = 0.09 + 0.06 / zr;
        if (sp.y > rowY + reach || (sp.y < rowY - reach && abs(sp.y - refY) > reach)) continue;
        float k0 = floor((x0 - off) / SPACING + 0.5);
        // per-row screen size of a flame, never below a pixel
        float r = max(0.009 / zr, gPx * 0.75);
        // dimmer and steadier with distance; the farthest rows fade into a glowing band
        float rowI = (0.55 + 0.45 * exp(-zr * 0.04)) * nearFade;
        rowI *= 1.0 - gDeso * (0.35 + 0.6 * depth01);
        for (int m = -1; m <= 1; m++) {
            float k = k0 + float(m);
            float h = hash21(vec2(k, fi));
            if (h < 0.03) continue;                                // a few gaps in the rows
            float x = (k * SPACING + off) + (hash11(h * 91.0) - 0.5) * 0.025;
            float z = zr + CURVE * x * x;
            float y = yRow + 0.022 * (hash11(h * 17.0) - 0.5);
            vec2 pos = vec2((x - gCamX) / z, HOR + y / z);
            if (abs(sp.y - pos.y) > 0.12 && sp.y > pos.y) continue;
            // gentle flicker, calmer far away; the final flames go out one by one
            float fl = 0.82 + 0.18 * sin(gT * (2.0 + 3.0 * h) + h * 40.0) * sin(gT * (1.3 + 2.0 * fract(h * 7.0)) + h * 9.0);
            fl = mix(fl, 0.92, depth01 * 0.6);
            float alive = 1.0 - smoothstep(h - 0.06, h + 0.02, gFinal * 1.08);
            float I = rowI * fl * alive;
            if (I <= 0.001) continue;
            // the gladius: a cold-white shimmer passing out through the rows
            float wave = smoothstep(0.2, 1.0, sin(depth01 * 14.0 - gT * 5.0 + x * 0.25));
            float cold = gGlad * (0.25 + 0.75 * wave);
            vec3 c = mix(FLAME * (0.9 + 0.2 * hash11(h * 5.0)), COLDW, cold);
            I *= 1.0 + 0.7 * cold * wave;
            acc += flameLight(sp, pos, r, I, c, nearFade);
            // the reflection in the black floor: long, dim and rippling
            float yr = -2.0 * EYE - y;
            vec2 rpos = vec2(pos.x + 0.002 * sin(gT * 1.3 + h * 20.0) / z, HOR + yr / z);
            vec2 rd = (sp - rpos) * vec2(1.0, 0.42);
            acc += c * I * 0.16 * exp(-dot(rd, rd) / (r * r * 0.6)) * (0.85 + 0.15 * sin(sp.y * 450.0 * z + gT * 2.0 + h * 9.0));
            // the nearest flames show the candle beneath, faintly lit from above
            if (zr < 1.4) {
                vec2 cq = sp - pos - vec2(0.0, -0.026 / z);
                float wax = sdBox(cq, vec2(0.0028 / z, 0.024 / z));
                acc += vec3(0.9, 0.72, 0.5) * 0.05 * I * smoothstep(gPx, -gPx, wax) * smoothstep(-0.024 / z, 0.024 / z, cq.y);
            }
        }
    }
    return acc;
}

// the colossal pillars far away, barely touched by the light of the field
vec3 pillars(vec2 sp, float lit) {
    vec3 col = vec3(0.0);
    for (int i = 0; i < 6; i++) {
        float fi = float(i);
        float side = mod(fi, 2.0) < 0.5 ? -1.0 : 1.0;
        float z = 14.0 + 9.0 * floor(fi * 0.5);
        float x = side * (3.2 + 0.4 * fi);
        float px = (x - gCamX) / z;
        float w = 0.55 / z;
        float d = abs(sp.x - px) - w;
        float a = smoothstep(gPx, -gPx, d) * step(HOR - EYE / z, sp.y);
        // lit from below by the flames, fading into the dark above
        float up = exp(-max(sp.y - HOR + EYE / z, 0.0) * z * 0.6);
        float rim = exp(-abs(d) / (0.003 + gPx));
        col = mix(col, FLAME * 0.025 * up * lit, a);
        col += FLAME * 0.01 * rim * up * lit * a;
    }
    return col;
}

// the lit doorway with the two lovers, close together, in shadow
vec4 doorway(vec2 sp, float A) {
    if (A <= 0.0) return vec4(0.0);
    float z = 1.7;
    vec2 base = vec2(-0.04 - gCamX / z, HOR - EYE / z);
    float open = smoothstep(0.0, 0.65, A);                     // the door swinging shut
    float W = 0.15 / z * 2.0 * open, H = 0.84 / z;
    vec2 q = sp - base;
    float door = min(sdBox(q - vec2(0.0, H * 0.4), vec2(W * 0.5, H * 0.4)), sdCircle(q - vec2(0.0, H * 0.8), W * 0.5));
    door = max(door, -q.y);
    float inDoor = smoothstep(gPx, -gPx, door);
    // the warm room beyond: brighter at its heart, a lamp somewhere inside
    vec3 room = vec3(1.0, 0.68, 0.38) * (1.2 + 0.6 * exp(-length(q - vec2(0.02, H * 0.55)) / 0.06)) * A;
    vec3 col = room * inDoor;
    // the lovers in the doorway: dark against the light, a crimson and a green edge
    if (inDoor > 0.0) {
        float fh = 0.58 / z;
        vec4 e = figure(sp, base + vec2(-0.03, 0.0), fh, vec4(0.12, 1.05, 0.18, 0.07), 2.0,
                        vec3(0.03, 0.004, 0.007), vec3(1.0, 0.35, 0.3) * 0.55, vec2(0.6, 0.8));
        vec4 m = figure(sp, base + vec2(0.036, 0.0), fh * 1.06, vec4(0.95, 0.12, 0.0, -0.07), 0.0,
                        vec3(0.004, 0.016, 0.012), vec3(0.5, 1.0, 0.8) * 0.5, vec2(-0.6, 0.8));
        col = over(col, m * inDoor);
        col = over(col, e * inDoor);
    }
    // the frame of the door
    float frame = smoothstep(gPx, -gPx, abs(door) - 0.004 / z * 2.0) * step(0.0, q.y);
    col = mix(col, vec3(0.02, 0.012, 0.008), frame * 0.8);
    // light thrown across the floor towards us, and a glow in the air
    float spill = 0.0;
    if (sp.y < base.y) {
        float zf = EYE / max(HOR - sp.y, 1e-3);                 // depth of this floor point
        float X = sp.x * zf + gCamX;
        float dx = X - (base.x * z + gCamX);
        float hw = W * 0.5 * z + (z - zf) * 0.2;                // the wedge widens towards us
        spill = smoothstep(hw, hw * 0.4, abs(dx)) * step(zf, z) * exp(-(z - zf) * 1.6) * 0.3;
    }
    col += vec3(1.0, 0.66, 0.36) * spill * A;
    float glowD = length((sp - base - vec2(0.0, H * 0.45)) * vec2(1.4, 0.9));
    col += vec3(1.0, 0.62, 0.32) * exp(-glowD / 0.12) * 0.12 * A * open * (1.0 - 0.9 * inDoor);
    float a = max(inDoor, frame);
    return vec4(col, a);
}

void main() {
    gSp = screen();
    gT = uTime;
    gPx = 1.5 * PIXEL;
    gField = sat(uP[0].x);
    float doorA = sat(uP[0].y);
    gFinal = sat(uP[0].z);
    float drift = uP[0].w;
    gGlad = sat(uP[1].x);
    gDeso = sat(uP[1].y);
    gCamX = drift * 3.0 + 0.02 * sin(gT * 0.09);
    gCamZ = drift * 6.0;
    // the dark: a faint warm breath of light low down, black above
    vec3 col = vec3(0.004, 0.003, 0.003) + vec3(0.012, 0.008, 0.005) * exp(-max(gSp.y - HOR, 0.0) * 6.0);
    float lit = gField * (1.0 - gFinal) * (1.0 - 0.6 * gDeso);
    col += pillars(gSp, lit);
    vec3 fl = field(gSp);
    col += fl * gField;
    // the light of the multitude hanging in the air over the far rows
    float band = exp(-abs(gSp.y - HOR + 0.012) / 0.04) * 0.035 + exp(-abs(gSp.y - HOR) / 0.15) * 0.015;
    vec3 bandC = mix(FLAME, COLDW, gGlad * 0.4) * band * lit;
    col += bandC * (1.0 + 0.3 * sin(gSp.x * 3.0 + gT * 0.2));
    col += FLAME * dust(gSp, gT, 0.05, 0.05) * 0.03 * lit;
    // the doorway at the start
    vec4 dr = doorway(gSp, doorA);
    col = mix(col, dr.rgb, dr.a) + dr.rgb * (1.0 - dr.a);
    // the held point: when the others have gone, one flame remains
    vec2 hp = vec2(0.0, HOR - 0.045);
    float held = smoothstep(0.35, 0.95, gFinal);
    float hr = 0.006;
    vec2 hd = gSp - hp;
    vec2 hq = vec2(hd.x, (hd.y - hr * 0.5) * 0.55);
    float hfl = 0.93 + 0.07 * sin(gT * 2.3) * sin(gT * 3.7);
    col += mix(FLAME, vec3(1.0, 0.85, 0.65), 0.5) * held * hfl * (exp(-dot(hq, hq) / (hr * hr * 0.35)) * 3.0 + hr * hr / (dot(hd, hd) * 1.2 + hr * hr) * 0.5);
    col += FLAME * held * (exp(-length(hd) / 0.15) * 0.04 + exp(-length(hd) / 0.04) * 0.08);
    vec2 hrq = (gSp - vec2(hp.x, HOR - 0.06 - 0.045)) * vec2(1.0, 0.3);
    col += FLAME * held * 0.25 * exp(-dot(hrq, hrq) / (hr * hr * 0.5));
    // the gladius also leaves a faint cold sheen in the air
    col += COLDW * gGlad * 0.012 * exp(-abs(gSp.y - HOR) / 0.15);
    col *= 1.0 - 0.25 * gDeso;
    fragColor = vec4(max(col, 0.0), 1.0);
}
