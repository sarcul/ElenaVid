#version 430
// ---------------------------------------------------------------------------------------------
// church.frag  -  THE CHURCH: a nave built like a paper theatre. Nested pointed arches recede in
// luminous haze towards the apse; the rose window, the altar and its candles glow at the far end;
// pews and villagers are layered cut-outs; the characters are rim-lit silhouettes.
// One set, five looks (uP[0].x):
//   0 the vow        warm and candlelit, night beyond the glass
//   1 the wedding    golden daylight; the rose window blooms into a mandala that breathes with the
//                    orchestra; the bells ring as rings of light; petals and rice; the village
//   2 cooling        as 1, but the gold drains to cold blue-grey with uP[0].w; she turns to him
//   3 dusk vision    violet light through the windows, empty pews, Elena alone, Vittorio as a
//                    figure of cold light (uP[4].z)
//   4 funeral        grey daylight, a bank of candles, the congregation, a small white coffin,
//                    Tommaso's silver line dissolving into rising motes (uP[4].w)
// uP[0]  x mode   y camera rise 0..1   z rose bloom 0..1   w warm-to-cold 0..1
// uP[1]  Elena    (x, feet y, height, alpha)       uP[2]  Vittorio (x, feet y, height, alpha)
// uP[3]  x crowd visibility 0..1
// uP[4]  x petals 0..1   y bell swing phase (rad)   z vision intensity 0..1   w line -> motes 0..1
// World units: the couple's plane is depth 1 (world = screen there when the camera is level). A
// layer at depth z is scaled by 1/z about the eye, so the floor at depth z meets the screen at
// y = -EYE / z. The camera rise is a crane: a tilt (all layers) plus a pedestal (divided by depth).
// ---------------------------------------------------------------------------------------------
#include common

const float EYE = 0.43;       // eye height above the floor
const float TILT = 0.21;      // rise: screen shift common to every layer
const float PED = 0.09;       // rise: pedestal, parallax by depth
const float Z_BACK = 2.3;     // the apse wall
const float Z_ALTAR = 1.85;
const float AISLE = 0.2;      // half-width of the central aisle (world)
const vec2 ROSE_C = vec2(0.0, 1.0);
const float ROSE_R = 0.5;
const vec3 SILVER = vec3(0.85, 0.9, 1.0);

int gMode;
float gRise, gCold, gBloom, gT, gPx, gCamX, gCrowd;
vec2 gSp;
vec3 gKey, gHaze, gStone, gGlassTint;
float gAmb, gGlass, gCandle, gDesat;
vec2 gLight;      // screen position of the main light (for haze and rim direction)

// screen -> world coordinates of a layer at depth z
vec2 lay(float z) {
    vec2 p = gSp + vec2(gCamX / z, gRise * (TILT + PED / z));
    return p * z;
}
// world point at depth z -> screen
vec2 toScreen(vec2 w, float z) {
    return w / z - vec2(gCamX / z, gRise * (TILT + PED / z));
}

float sdOpening(vec2 q, float w, float ys, float r) {      // pointed arch, negative inside
    float ax = abs(q.x);
    if (q.y < ys) return ax - w;
    return length(vec2(ax + (r - w), q.y - ys)) - r;
}

// lit haze at a screen position: brightest about the main light
vec3 hazeLight(vec2 sp) {
    vec2 d = sp - gLight;
    float g = exp(-dot(d, d * vec2(1.6, 2.6)) * 3.2);
    float wisp = 0.75 + 0.5 * fbm(sp * 2.4 + vec2(gT * 0.012, -gT * 0.02));
    return gHaze * (0.22 + 1.5 * g) * wisp;
}

// ------------------------------------------------------------------ stained glass
vec3 glassColour(float zone, float sid) {
    float alt = mod(sid, 2.0);
    if (zone < 0.5) return vec3(1.0, 0.68, 0.18);                                    // centre: gold
    if (zone < 1.5) return alt < 0.5 ? vec3(0.9, 0.1, 0.07) : vec3(0.12, 0.24, 0.9);  // lancets
    if (zone < 2.5) return vec3(1.0, 0.72, 0.25);                                     // roundels
    if (zone < 3.5) return alt < 0.5 ? vec3(0.1, 0.5, 0.3) : vec3(0.55, 0.18, 0.7);   // spandrels
    return vec3(0.15, 0.3, 0.95);
}

// the rose window: emission through the glass; 'stone' returns tracery coverage
vec3 roseWindow(vec2 q, out float stone, float px) {
    vec2 d = (q - ROSE_C) / ROSE_R;
    float e = px / ROSE_R;
    float r = length(d);
    stone = 0.0;
    if (r > 1.13) return vec3(0.0);
    float a = atan(d.x, d.y);                       // 0 at the top, so a lancet points straight up
    float sec = TAU / 16.0;
    float sid = floor(a / sec + 0.5);
    float as = a - sid * sec;                       // angle from the lancet's centre line
    vec2 lp = r * vec2(cos(as), sin(as));           // sector frame: x along the lancet
    // tracery distance field: stone where negative
    float dS = abs(r - 0.155) - 0.022;
    dS = min(dS, abs(r - 0.64) - 0.016);
    dS = min(dS, abs(r - 0.985) - 0.028);
    float bar = (0.5 * sec - abs(as)) * r;          // distance to the radial bar between lancets
    if (r > 0.155 && r < 0.64) dS = min(dS, bar - 0.014 - 0.012 * r);
    // lancet heads: cusped arches and a small oculus in each lancet
    dS = min(dS, abs(length(lp - vec2(0.47, 0.0)) - 0.075) - 0.012);
    float head = length(vec2(abs(lp.y) + 0.05, lp.x - 0.56)) - 0.09;
    if (lp.x > 0.56 && r < 0.64) dS = min(dS, -head);
    // roundels in the outer zone, each with a quatrefoil
    vec2 rc = lp - vec2(0.81, 0.0);
    float dR = length(rc) - 0.135;
    dS = min(dS, abs(dR) - 0.016);
    float qa = atan(rc.y, rc.x);
    float quat = length(rc) - (0.06 + 0.035 * abs(cos(2.0 * qa)));
    dS = min(dS, abs(quat) - 0.008);
    // a flower in the centre
    float ca = atan(d.y, d.x);
    float fl = r - (0.08 + 0.04 * abs(cos(4.0 * ca)));
    dS = min(dS, abs(fl) - 0.007);
    // moulding beyond the glass
    float mould = r - 0.985;
    stone = smoothstep(e, -e, dS);
    stone = max(stone, smoothstep(-e, e, mould));
    // glass zones
    float zone = (r < 0.155) ? 0.0 : (r < 0.64 ? 1.0 : (dR < 0.0 ? 2.0 : 3.0));
    if (zone == 1.0 && length(lp - vec2(0.47, 0.0)) < 0.075) zone = 2.0;
    vec3 g = glassColour(zone, sid);
    if (zone == 2.0 && quat < 0.0) g = vec3(0.9, 0.12, 0.1);
    // glass texture: uneven panes and fine leading
    float pane = 0.65 + 0.55 * vnoise(q * 90.0) * vnoise(q * 23.0 + 3.0);
    float lead = smoothstep(0.0, 0.25, abs(fract(r * 18.0) - 0.5)) * smoothstep(0.0, 0.2, abs(fract(as * 40.0) - 0.5));
    g = mix(g, vec3(lum(g)) * 1.6, gDesat) * gGlassTint;
    vec3 em = g * pane * (0.55 + 0.45 * lead) * gGlass;
    // the bloom: the glass turns to gold and burns brighter
    em = mix(em, vec3(1.0, 0.72, 0.32) * (1.2 + 1.2 * uScore) * (0.7 + 0.3 * pane), gBloom * 0.18);
    em *= 1.0 + 0.35 * gBloom * uScore;
    em *= 1.0 - stone;
    // the tracery catches a little light at its edges
    float trim = exp(-abs(dS) / (0.012 + e)) * (1.0 - smoothstep(0.95, 1.0, r));
    em += gKey * trim * 0.12 * gGlass * (1.0 - stone * 0.5);
    return em;
}

// golden mandala: the window's geometry unfolding outwards as rings of light
vec3 mandala(vec2 q, float bloom, float pulse, float px) {
    vec2 d = (q - ROSE_C) / ROSE_R;
    float r = length(d);
    float ext = 1.0 + 2.7 * bloom;
    if (r < 0.95 || r > ext + 0.8) return vec3(0.0);
    float a = atan(d.x, d.y);
    float e = px / ROSE_R;                    // one pixel in window radii
    float lw = 0.0028 + e * 0.75;             // line half-width
    float line = 0.0, soft = 0.0, fill = 0.0;
    for (int i = 0; i < 6; i++) {
        float fi = float(i);
        float ri = 1.24 + 0.4 * fi + 0.025 * pulse * fi;
        float on = smoothstep(ri - 0.15, ri + 0.25, ext) * (1.0 - 0.08 * fi);
        if (on <= 0.0) continue;
        float N = 16.0 * (1.0 + floor(fi * 0.5));
        float sec = TAU / N;
        float dir = mod(fi, 2.0) < 0.5 ? 1.0 : -1.0;
        float aa_ = a + dir * gT * 0.008 + mod(fi, 2.0) * 0.5 * sec;
        float as = aa_ - sec * floor(aa_ / sec + 0.5);
        vec2 lp = vec2(r - ri, as * r);       // radial, tangential
        // a pointed vesica petal: two arcs meeting at both tips
        float L = 0.125 + 0.01 * fi;
        float W = min(0.3 * sec * ri, 0.065);
        float rho = (L * L + W * W) / (2.0 * W);
        float pv = length(vec2(lp.x, abs(lp.y) + rho - W)) - rho;
        float vein = abs(lp.y) + step(L * 0.7, abs(lp.x));
        line += (smoothstep(lw, 0.0, abs(pv)) + 0.45 * smoothstep(lw * 0.7, 0.0, vein)) * on;
        soft += exp(-abs(pv) / 0.03) * on;
        fill += smoothstep(0.0, -0.04, pv) * on;
        // a pearl between each pair of petals, and a fine circle beyond the ring
        float pearl = length(vec2(lp.x - 0.02, (abs(as) - 0.5 * sec) * r)) - 0.011;
        line += smoothstep(e, -e, pearl) * 0.85 * on;
        line += smoothstep(lw, 0.0, abs(r - ri - L - 0.065)) * 0.55 * on;
    }
    // fine rays between the rings, out to the edge of the bloom
    float sec64 = TAU / 64.0;
    float ar = a - sec64 * floor(a / sec64 + 0.5);
    float ray = smoothstep(lw * 0.7, 0.0, abs(ar * r)) * (mod(floor(a / sec64 + 0.5), 2.0) < 0.5 ? 1.0 : 0.5);
    line += ray * 0.3 * smoothstep(1.05, 1.3, r) * smoothstep(ext + 0.15, ext - 0.35, r);
    // the bloom's leading edge and a soft halo
    soft += exp(-abs(r - ext - 0.1) / 0.05) * 0.8 * bloom;
    float halo = exp(-max(r - 1.0, 0.0) / (0.5 + 0.9 * bloom)) * 0.2;
    float lvl = bloom * (0.6 + 0.8 * pulse);
    return vec3(1.0, 0.74, 0.36) * (line * 0.85 + soft * 0.1 + fill * 0.07 + halo) * lvl;
}

// bells, heard as light: each strike at the end of a swing sends out a ring from the belfry
float bellRings(vec2 sp, float phase) {
    float acc = 0.0;
    for (int b = 0; b < 2; b++) {
        float fb = float(b);
        float ph = phase * (1.0 - 0.17 * fb) + fb * 1.9;
        float swing = (ph - PI * 0.5) / PI;
        float since = fract(swing);
        vec2 src = vec2(-0.42 + 0.84 * fb, 0.78) - vec2(0.0, gRise * 0.2);
        float r = length((sp - src) * vec2(1.0, 1.1));
        float R = since * 1.5;
        float w = 0.0025 + 0.006 * since;
        float ring = exp(-pow((r - R) / w, 2.0));
        ring += 0.5 * exp(-pow((r - R * 0.86) / w, 2.0)) + 0.25 * exp(-pow((r - R * 0.74) / w, 2.0));
        ring += 0.15 * exp(-abs(r - R) / 0.04);
        acc += ring * exp(-since * 2.4) * smoothstep(0.0, 0.04, since);
    }
    return acc;
}

// ------------------------------------------------------------------ the far end
vec3 backWall(vec2 sp) {
    vec2 q = lay(Z_BACK);
    float px = gPx * Z_BACK;
    float n = fbm(q * 2.5 + 11.0);
    vec3 col = gStone * (0.55 + 0.5 * n) * gAmb * 1.4;
    // the wall is washed by the candles below and the glass above
    col += gStone * gKey * 0.07 * exp(-pow((q.y + 0.1) / 0.35, 2.0)) * exp(-q.x * q.x / 0.3) * gCandle;
    // blind arcading: shallow painted niches along the wall
    float niche = sdOpening(vec2(mod(q.x + 0.21, 0.42) - 0.21, q.y + 0.06), 0.13, 0.12, 0.2);
    col *= mix(1.0, 0.72, smoothstep(px, -px, niche) * step(abs(q.x), 1.3) * step(0.62, abs(q.x)));
    // side lancets
    for (int s = -1; s <= 1; s += 2) {
        vec2 lq = q - vec2(float(s) * 0.74, 0.0);
        float lan = sdOpening(lq - vec2(0.0, 0.0), 0.075, 0.6, 0.12);
        lan = max(lan, -(lq.y + 0.08));
        float frameD = lan - 0.02;
        col = mix(col, gStone * gAmb * 0.7, smoothstep(px, -px, frameD));
        float inL = smoothstep(px, -px, lan);
        // glass in small diamond panes: blue ground, a few ruby and gold quarries
        vec2 dg = rot(0.785) * (lq * 22.0);
        vec2 di = floor(dg);
        float hq = hash21(di + float(s) * 9.0);
        vec3 lg = hq < 0.62 ? vec3(0.16, 0.28, 0.85) : (hq < 0.82 ? vec3(0.85, 0.16, 0.1) : vec3(1.0, 0.68, 0.22));
        float leadL = smoothstep(0.06, 0.16, min(abs(fract(dg.x) - 0.5), abs(fract(dg.y) - 0.5)) * 2.0);
        if (gMode == 0) lg = mix(lg, vec3(0.1, 0.16, 0.45), 0.7);
        float mull = smoothstep(0.012, 0.004, abs(lq.x)) * step(lq.y, 0.62);
        lg = mix(lg, vec3(lum(lg)) * 1.6, gDesat);
        col = mix(col, lg * gGlassTint * gGlass * 0.24 * (0.75 + 0.35 * vnoise(lq * 60.0)) * (0.35 + 0.65 * leadL) * (1.0 - mull * 0.9), inL);
    }
    // dossal behind the altar: a hanging cloth with soft vertical folds
    vec2 dq = q - vec2(0.0, 0.2);
    float dos = sdBox(dq, vec2(0.33, 0.24));
    vec3 cloth = (gMode == 4) ? vec3(0.06, 0.04, 0.07) : (gMode == 3 ? vec3(0.16, 0.06, 0.2) : vec3(0.32, 0.04, 0.05));
    float folds = 0.6 + 0.4 * sin(dq.x * 60.0 + sin(dq.y * 4.0)) * sin(dq.x * 23.0 + 1.0);
    vec3 dc = cloth * folds * (gAmb * 2.0 + 0.6 * gCandle * exp(-pow((dq.y + 0.2) / 0.25, 2.0)));
    dc += vec3(0.9, 0.65, 0.3) * 0.25 * smoothstep(0.012, 0.0, abs(abs(dq.x) - 0.31)) * step(abs(dq.y), 0.24) * (gMode == 1 || gMode == 2 || gMode == 0 ? 1.0 : 0.3);
    col = mix(col, dc, smoothstep(px, -px, dos));
    // the rose window and its moulding
    float stone;
    vec3 rw = roseWindow(q, stone, px);
    vec2 rd = q - ROSE_C;
    float rr = length(rd) / ROSE_R;
    if (rr < 1.13) {
        vec3 mouldC = gStone * gAmb * (0.9 + 0.5 * smoothstep(1.12, 1.0, rr)) + gKey * 0.05 * gGlass * smoothstep(1.13, 1.0, rr);
        float inside = smoothstep(1.0 + px / ROSE_R, 1.0 - px / ROSE_R, rr);
        col = mix(col, mouldC, smoothstep(1.13, 1.12, rr) * (1.0 - inside) + inside * stone);
        col += rw;
    }
    // glow of the glass in the air around it
    col += gKey * gGlass * 0.05 * exp(-max(rr - 1.0, 0.0) * 2.5) * (gMode == 1 || gMode == 2 ? 1.0 : 0.5);
    return col;
}

// stone floor in perspective, with a carpet down the aisle and a soft reflection of the altar
vec3 floorCol(vec2 sp, out float zf) {
    float den = min(sp.y + gRise * TILT, -1e-4);
    zf = -(EYE + gRise * PED) / den;
    float X = sp.x * zf + gCamX;
    vec2 g = vec2(X, zf * 1.0) / 0.32;
    vec2 gf = abs(fract(g + vec2(0.5 * step(0.5, fract(g.y * 0.5)), 0.0)) - 0.5);
    float pxx = gPx * zf / 0.32;
    float pxz = gPx * zf * zf / (EYE + gRise * PED) / 0.32;
    float grout = max(smoothstep(0.5 - 1.5 * pxx, 0.5, gf.x), smoothstep(0.5 - 1.5 * pxz, 0.5, gf.y));
    vec3 stone = gStone * (0.75 + 0.35 * vnoise(g * 3.1 + 5.0)) * (1.0 - 0.35 * grout * smoothstep(3.0, 0.6, zf));
    // light: the far end (altar), a pool round the couple, ambient
    float far = exp(-pow((zf - 1.75) / 0.6, 2.0)) * exp(-X * X / 0.5);
    float pool = exp(-pow((zf - 1.05) / 0.45, 2.0)) * exp(-X * X / 0.25);
    vec3 col = stone * (gAmb * 0.9 + gKey * (0.22 * far + 0.12 * pool) * (0.5 + 0.5 * gCandle));
    // carpet (not at the funeral)
    if (gMode != 4 && zf < 1.58 && abs(X) < 0.13) {
        float edge = smoothstep(0.13, 0.122, abs(X));
        float band = smoothstep(0.004, 0.0, abs(abs(X) - 0.11));
        vec3 cc = vec3(0.2, 0.018, 0.03) * (0.8 + 0.2 * vnoise(vec2(X * 200.0, zf * 40.0)));
        cc = cc * (gAmb * 1.6 + gKey * (0.35 * far + 0.5 * pool)) + vec3(0.8, 0.55, 0.25) * band * 0.2 * (gAmb + far);
        cc += gKey * 0.15 * pow(sat(1.0 - abs(X) / 0.13), 2.0) * smoothstep(0.6, 1.5, zf) * gGlass * 0.3;
        col = mix(col, cc, edge);
    }
    // glossy reflection of the far light, a streak down the aisle
    float refl = exp(-X * X / (0.004 + 0.01 * zf)) * smoothstep(0.4, 1.6, zf) * smoothstep(2.3, 1.7, zf);
    col += gKey * refl * 0.12 * (gCandle * 0.6 + gGlass * 0.15);
    return col;
}

// a lit candle on a candlestick (world coordinates at depth z): wax, flame and its glow
vec3 candleAt(vec3 col, vec2 q, vec2 base, float h, float lvl, float seed, float px) {
    float wax = sdBox(q - base - vec2(0.0, h * 0.5), vec2(0.0075, h * 0.5));
    vec3 waxC = vec3(0.9, 0.82, 0.68) * (gAmb + 0.45 * lvl * smoothstep(base.y, base.y + h, q.y));
    col = mix(col, waxC, smoothstep(px, -px, wax));
    if (lvl > 0.0) col += candle(q, base + vec2(0.0, h), 0.034, gT, seed) * lvl;
    return col;
}

vec3 altar(vec3 col) {
    vec2 q = lay(Z_ALTAR);
    float px = gPx * Z_ALTAR;
    float topStep = -EYE + 0.15;
    // the altar block on its top step, a white cloth and a frontal
    float blk = sdBox(q - vec2(0.0, topStep + 0.15), vec2(0.3, 0.15));
    float cloth = sdBox(q - vec2(0.0, topStep + 0.29), vec2(0.315, 0.016));
    float front = sdBox(q - vec2(0.0, topStep + 0.17), vec2(0.18, 0.11));
    vec3 stoneC = gStone * (gAmb * 1.2 + gKey * 0.18 * gCandle) * (0.85 + 0.3 * fbm(q * 9.0));
    col = mix(col, stoneC, smoothstep(px, -px, blk));
    vec3 fr = (gMode == 4) ? vec3(0.03, 0.025, 0.03) : (gMode == 3 ? vec3(0.12, 0.05, 0.16) : vec3(0.35, 0.05, 0.05));
    fr = fr * (gAmb * 2.0 + gKey * 0.3 * gCandle) + vec3(0.9, 0.65, 0.3) * 0.18 * smoothstep(0.01, 0.0, abs(sdBox(q - vec2(0.0, topStep + 0.17), vec2(0.165, 0.095)))) * (gAmb + 0.3 * gCandle);
    col = mix(col, fr, smoothstep(px, -px, front));
    col = mix(col, vec3(0.85, 0.82, 0.76) * (gAmb * 2.2 + gKey * 0.4 * gCandle), smoothstep(px, -px, cloth));
    // crucifix
    vec2 cq = q - vec2(0.0, topStep + 0.31);
    float cr = min(sdBox(cq - vec2(0.0, 0.11), vec2(0.008, 0.11)), sdBox(cq - vec2(0.0, 0.16), vec2(0.045, 0.007)));
    col = mix(col, vec3(0.75, 0.55, 0.25) * (gAmb + 0.5 * gKey * gCandle) + gKey * 0.1, smoothstep(px, -px, cr));
    // six altar candles
    for (int i = 0; i < 6; i++) {
        float fi = float(i);
        float x = (fi < 3.0 ? -1.0 : 1.0) * (0.09 + 0.07 * mod(fi, 3.0));
        float hh = 0.16 - 0.025 * mod(fi, 3.0);
        float lvl = gCandle;
        if (gMode == 3) lvl = (i == 2 || i == 5) ? 0.55 : 0.0;
        vec2 b = vec2(x, topStep + 0.305);
        float stick = sdTrap(q - b - vec2(0.0, 0.03), 0.018, 0.008, 0.03);
        col = mix(col, vec3(0.7, 0.5, 0.22) * (gAmb + 0.4 * gKey * gCandle), smoothstep(px, -px, stick));
        col = candleAt(col, q, b + vec2(0.0, 0.06), hh * 0.6, lvl, fi * 3.1 + 1.0, px);
    }
    // the steps, nearest last
    for (int k = 2; k >= 0; k--) {
        float fk = float(k);
        float zs = 1.62 + 0.09 * fk;
        vec2 sq = lay(zs);
        float spx = gPx * zs;
        float hs = 0.05 * (fk + 1.0);
        float st = sdBox(sq - vec2(0.0, -EYE + hs * 0.5), vec2(0.62 + 0.06 * (2.0 - fk), hs * 0.5));
        vec3 sc = gStone * (gAmb * 1.1 + gKey * 0.16 * gCandle * exp(-sq.x * sq.x / 0.6)) * (0.85 + 0.25 * vnoise(sq * 30.0));
        if (gMode == 4) sc *= 0.35;     // the steps are draped for the funeral
        sc += gKey * 0.25 * smoothstep(0.006, 0.0, abs(sq.y - (-EYE + hs))) * (0.3 + gCandle) * exp(-sq.x * sq.x / 0.5);
        col = mix(col, sc, smoothstep(spx, -spx, st));
    }
    return col;
}

// floor-standing candelabra flanking the steps
vec3 candelabra(vec3 col, float lvl) {
    float z = 1.55;
    vec2 q = lay(z);
    float px = gPx * z;
    for (int s = -1; s <= 1; s += 2) {
        vec2 lq = q - vec2(float(s) * 0.44, -EYE);
        float stem = sdBox(lq - vec2(0.0, 0.2), vec2(0.008, 0.2));
        float foot = sdTrap(lq - vec2(0.0, 0.025), 0.06, 0.012, 0.025);
        float arms = sdArc(lq, vec2(0.0, 0.42), 0.075, PI * 1.05, PI * 1.95, 0.005);
        float d = min(min(stem, foot), arms);
        col = mix(col, vec3(0.55, 0.4, 0.2) * (gAmb + 0.35 * gKey * lvl) + gKey * 0.05, smoothstep(px, -px, d));
        for (int k = -1; k <= 1; k++) {
            vec2 b = vec2(float(k) * 0.075, k == 0 ? 0.42 : 0.395);
            col = candleAt(col, lq, b, 0.07, lvl, float(s * 3 + k) + 7.0, px);
        }
    }
    return col;
}

// votive stand (the vow): small flames in red glass
vec3 votives(vec3 col) {
    float z = 1.3;
    vec2 q = lay(z);
    float px = gPx * z;
    vec2 lq = q - vec2(-0.66, -EYE);
    float stand = sdTrap(lq - vec2(0.0, 0.16), 0.17, 0.12, 0.16);
    col = mix(col, vec3(0.05, 0.03, 0.02) + gKey * 0.03, smoothstep(px, -px, stand));
    for (int r = 0; r < 3; r++) {
        float fr = float(r);
        float y = 0.1 + 0.07 * fr;
        float w = 0.15 - 0.022 * fr;
        float cell = 0.042;
        float xi = clamp(floor(lq.x / cell + 0.5), -floor(w / cell), floor(w / cell));
        vec2 c = vec2(xi * cell, y);
        vec2 dd = lq - c;
        float cup = sdRBox(dd - vec2(0.0, 0.01), vec2(0.011, 0.012), 0.004);
        col = mix(col, vec3(0.5, 0.04, 0.03) * 0.6, smoothstep(px, -px, cup) * 0.7);
        col += vec3(1.0, 0.25, 0.1) * exp(-length(dd - vec2(0.0, 0.01)) / 0.014) * 0.35;
        col += candle(lq, c + vec2(0.0, 0.016), 0.016, gT, xi * 1.7 + fr * 5.0) * 0.6;
    }
    return col;
}

// a transverse arch at depth z (backlit cut-out) and the haze in front of it
vec3 archLayer(vec3 col, float z, float k, float haze) {
    vec2 q = lay(z);
    float px = gPx * z;
    const float W = 0.84, YS = 0.24, R = 1.45;
    float dOpen = sdOpening(q, W, YS, R);
    vec2 cq = vec2(abs(q.x) - (W + 0.035), q.y - (YS - 0.012));
    float cap = sdTrap(vec2(cq.x, -cq.y), 0.04, 0.062, 0.022);
    float base = sdBox(vec2(abs(q.x) - (W + 0.035), q.y + EYE - 0.025), vec2(0.06, 0.025));
    float dBody = max(-dOpen, -(q.y + EYE));
    dBody = min(dBody, min(cap, base));
    float a = smoothstep(px, -px, dBody);
    if (a > 0.0) {
        float edge = max(-dBody, 0.0);
        vec3 stone = gStone * (0.75 + 0.45 * fbm(q * 5.0 + k * 7.3));
        vec3 c = stone * gAmb * (0.55 + 0.45 * smoothstep(1.0, -0.3, q.y));
        // engaged shaft below the spring line, a cylinder catching light from the nave
        float shaft = step(q.y, YS - 0.03) * step(edge, 0.085) * step(-dOpen, 0.085);
        float u = sat(-dOpen / 0.085);
        c += stone * gKey * 0.2 * pow(1.0 - u, 2.5) * shaft;
        c += stone * gKey * 0.05 * smoothstep(0.003, 0.0, abs(u - 0.98)) * shaft;
        // archivolt mouldings above the spring
        float mould = step(YS, q.y) * smoothstep(0.13, 0.0, -dOpen) * (0.5 + 0.5 * sin(-dOpen * 150.0));
        c += stone * gKey * 0.06 * mould;
        // capitals catch the light on their upper faces
        c += stone * gKey * 0.25 * smoothstep(px * 2.0, 0.0, abs(cap)) * step(abs(cq.y + 0.0), 0.03);
        // the paper edge glowing with the light beyond
        float rim = exp(-edge / (0.0035 + 0.7 * px));
        c += gKey * rim * 0.75 * smoothstep(-EYE, -EYE + 0.08, q.y) * (0.6 + 0.4 * smoothstep(-0.2, 0.8, q.y));
        col = mix(col, c, a);
    }
    col = mix(col, hazeLight(gSp), haze);
    return col;
}

// ------------------------------------------------------------------ pews and people
// a villager seen from behind: an oval head on a slim neck, sloping shoulders, hats and scarves
float sdVillager(vec2 q, float seed, float standing) {
    float hs = hash11(seed * 3.7);
    float top = (standing > 0.5 ? 0.5 : 0.385) * (0.94 + 0.1 * hs);
    float kid = step(hash11(seed * 5.3), 0.07);
    top *= 1.0 - 0.24 * kid;
    float sc = 1.0 - 0.18 * kid;
    vec2 hc = vec2(0.004 * (hs - 0.5), top - 0.04 * sc);
    q.x -= (hash11(seed * 4.1) - 0.5) * 0.06 * (q.y - top + 0.4);   // a slight lean
    float d = sdEllipse(q - hc, vec2(0.03, 0.037) * sc);
    float w = (0.098 + 0.02 * hash11(seed * 1.9)) * sc;
    float shY = top - 0.125 * sc;
    float sh = sdTrap(q - vec2(0.0, shY - 0.012), w, w * 0.5, 0.03 * sc);
    float body = sdBox(q - vec2(0.0, shY - 0.25), vec2(w * 0.96, 0.24));
    float neck = sdBox(q - vec2(0.0, top - 0.09 * sc), vec2(0.014, 0.03) * sc);
    d = min(d, neck);
    d = min(d, smin(sh, body, 0.02));
    d = smin(d, sh, 0.012);
    float k = hash11(seed * 9.1);
    if (kid < 0.5) {
        if (k < 0.24) {            // a man's hat: brim and crown
            d = min(d, sdBox(q - hc - vec2(0.0, 0.016), vec2(0.052, 0.0045)));
            d = min(d, sdRBox(q - hc - vec2(0.0, 0.03), vec2(0.029, 0.014), 0.006));
        } else if (k < 0.5) {      // a headscarf, knotted at the nape
            d = smin(d, sdEllipse(q - hc - vec2(0.0, -0.008), vec2(0.04, 0.045)), 0.012);
            d = min(d, sdTrap(q - hc - vec2(0.0, -0.06), 0.03, 0.012, 0.022));
        } else if (k < 0.62) {     // hair in a bun
            d = min(d, sdCircle(q - hc - vec2(0.0, 0.034), 0.017));
        }
    }
    return d;
}

vec3 rows(vec3 col, vec3 bodyC, vec3 rimC, bool far) {
    const float ROWZ[6] = float[6](1.06, 0.96, 0.87, 0.79, 0.72, 0.66);
    float standing = (gMode == 1 || gMode == 2 || gMode == 0) ? 1.0 : 0.0;
    for (int j = 0; j < 6; j++) {
        float z = ROWZ[j];
        if (far != (z > 1.0)) continue;
        vec2 q = lay(z);
        float px = gPx * z;
        float ax = abs(q.x);
        float side = q.x < 0.0 ? 0.0 : 1.0;
        // people in this pew
        if (gCrowd > 0.001) {
            float spc = 0.19;
            float u = (ax - AISLE - 0.075) / spc;
            float k0 = floor(u + 0.5);
            for (int m = -1; m <= 1; m++) {
                float kk = k0 + float(m);
                if (kk < 0.0) continue;
                float seed = kk * 7.13 + float(j) * 31.7 + side * 101.3;
                float hv = hash11(seed * 2.3);
                float vis = smoothstep(0.55 * hv, 0.55 * hv + 0.45, gCrowd);
                if (vis <= 0.0) continue;
                float xc = AISLE + 0.075 + kk * spc + (hash11(seed) - 0.5) * 0.07;
                vec2 lq = vec2(ax - xc, q.y + EYE);
                float d = sdVillager(lq, seed, standing);
                float a = smoothstep(px, -px, d) * vis;
                if (a <= 0.0) continue;
                // backlit paper: the edges facing the far light catch a thin rim
                float dUp = sdVillager(lq + vec2(0.0, 0.005), seed, standing);
                float dIn = sdVillager(lq + vec2(-0.005, 0.0), seed, standing);
                float facing = sat((dUp - d) / 0.005 * 0.85 + (dIn - d) / 0.005 * 0.4);
                float band = exp(-max(-d, 0.0) / (0.0022 + 0.7 * px));
                vec3 c = bodyC * (0.75 + 0.35 * vnoise(lq * 30.0 + seed)) * (0.7 + 0.3 * smoothstep(-0.2, 0.1, lq.y - 0.4));
                c += rimC * band * (0.15 + facing) * 1.1;
                col = mix(col, c, a);
            }
        }
        // the pew back and its end panel at the aisle
        float top = -EYE + 0.27;
        float back = max(-(ax - AISLE - 0.012), q.y - top);
        back = max(back, -(q.y + EYE));
        float endp = sdRBox(vec2(ax - AISLE - 0.016, q.y - (top - 0.12)), vec2(0.016, 0.15), 0.012);
        float dp = min(back, endp);
        float a = smoothstep(px, -px, dp);
        if (a > 0.0) {
            vec3 wood = vec3(0.075, 0.045, 0.026) * (0.7 + 0.5 * vnoise(vec2(q.x * 30.0, q.y * 6.0)));
            vec3 c = wood * (gAmb * 2.2 + 0.1 * lum(gKey));
            float rim = exp(-max(-dp, 0.0) / (0.0025 + px)) * smoothstep(top - 0.04, top + 0.03, q.y + 0.0) ;
            c += gKey * rim * 0.35;
            c += gKey * 0.12 * exp(-max(-endp, 0.0) / (0.003 + px)) * step(endp, 0.0);
            col = mix(col, c, a);
        }
        col = mix(col, hazeLight(gSp), 0.045);
    }
    return col;
}

// ------------------------------------------------------------------ the characters
vec4 figB(vec2 p, vec2 pos, float h, vec4 pose, float hair, vec3 body, vec3 rim, vec2 L, float sx) {
    vec2 q = (p - pos) / h;
    if (abs(q.x - q.y * pose.w) > 0.62 / sx || q.y < -0.08 || q.y > 1.12) return vec4(0.0);
    vec2 pp = vec2(pos.x + (p.x - pos.x) / sx, p.y);
    return figure(pp, pos, h, pose, hair, body, rim, L);
}

// Vittorio as a figure of cold light, his edges torn into smoke
vec3 lightFigure(vec2 p, vec2 pos, float h, float I) {
    vec2 q = (p - pos) / h;
    if (abs(q.x) > 0.95 || q.y < -0.25 || q.y > 1.9 || I <= 0.0) return vec3(0.0);
    // the outline is pushed about by slow rising noise, more at the edges of the body
    vec2 nq = q * 3.2 + vec2(0.0, -gT * 0.35);
    vec2 w = vec2(fbm(nq), fbm(nq + vec2(5.2, 1.3))) - 0.5;
    float d0 = sdFigure(q, vec4(0.16, 0.2, 0.0, -0.02), 0.0);
    float d = sdFigure(q + w * 0.075, vec4(0.16, 0.2, 0.0, -0.02), 0.0) - 0.006;
    // he is solid nowhere: a veil of light inside, a torn bright edge, smoke where he thins
    float tear = smoothstep(0.35, 0.65, fbm(q * vec2(6.0, 3.0) + vec2(0.0, -gT * 0.6)));
    float feet = smoothstep(-0.05, 0.35, q.y);                 // he dissolves towards the floor
    float inner = smoothstep(0.02, -0.03, d) * (0.18 + 0.3 * fbm(q * 8.0 - vec2(0.0, gT * 0.5)));
    float edge = exp(-abs(d) / 0.009) * (0.45 + 0.75 * tear);
    float halo = exp(-max(d, 0.0) / 0.05) * 0.35 + exp(-max(d0, 0.0) / 0.18) * 0.12;
    // smoke curling up from the head and shoulders and off the edges
    vec2 sq = vec2(q.x * 2.4, q.y * 1.3 - gT * 0.22);
    float sm = fbm(sq + w * 2.5);
    float plume = smoothstep(0.5, 0.82, sm) * exp(-max(d0, 0.0) * 9.0) * smoothstep(0.35, 1.0, q.y) * smoothstep(1.85, 0.95, q.y);
    float mist = smoothstep(0.45, 0.8, fbm(vec2(q.x * 3.0, q.y * 5.0 - gT * 0.1))) * exp(-q.y * q.y * 30.0) * exp(-q.x * q.x * 6.0);
    // tendrils drawn upwards off his edges
    float wisp = smoothstep(0.52, 0.85, fbm(vec2(q.x * 5.0, q.y * 1.1 - gT * 0.45) + w * 3.0));
    wisp *= exp(-max(d0, 0.0) * 12.0) * (1.0 - smoothstep(-0.02, 0.0, -d0) * 0.7) * smoothstep(0.15, 0.8, q.y);
    float flick = 0.9 + 0.1 * sin(gT * 7.3) * sin(gT * 3.1);
    vec3 C = vec3(0.45, 0.6, 1.0);
    return C * I * flick * ((inner * 0.8 + edge * 1.35) * feet + halo * feet + plume * 0.7 + mist * 0.45 + wisp * 0.55);
}

// ------------------------------------------------------------------ falling petals and rice
vec4 petals(vec2 sp, float amt) {
    vec4 acc = vec4(0.0);
    for (int l = 0; l < 3; l++) {
        float fl = float(l);
        float z = 0.9 - 0.2 * fl;
        float cell = 0.07 + 0.045 * fl;
        vec2 p = sp + vec2(gCamX / z, gRise * (TILT + PED / z));
        p += vec2(0.015 * gT * (1.0 + fl * 0.3), 0.055 * gT * (1.0 + 0.5 * fl));
        vec2 g = p / cell;
        vec2 id = floor(g);
        vec2 f = fract(g);
        float h0 = hash21(id + fl * 17.0);
        if (h0 > amt * (0.55 - 0.2 * fl)) continue;
        vec2 h = hash22(id + fl * 5.3);
        vec2 c = vec2(0.5 + 0.28 * sin(gT * (0.7 + h.x) + h.y * 6.28), 0.25 + 0.5 * h.y);
        vec2 d = (f - c) * cell;
        float rice = step(0.72, hash21(id + 3.3)) * step(fl, 0.5);     // rice only where it is in focus
        float ang = gT * (0.8 + 1.6 * h.x) + h.y * 6.0;
        float flip = 0.25 + 0.75 * abs(sin(gT * (1.1 + h.y) + h.x * 5.0));
        d = rot(ang) * d;
        float size = (0.0065 + 0.004 * h.x) * (1.0 + 0.9 * fl);
        float blur = gPx * (1.0 + 2.5 * fl * fl);
        float sd;
        vec3 c0;
        if (rice > 0.5) {
            sd = sdCapsule(d, vec2(-size * 0.45, 0.0), vec2(size * 0.45, 0.0), size * 0.2);
            c0 = vec3(0.95, 0.9, 0.8) * (0.25 + 0.6 * flip) * (0.6 + 0.6 * lum(gKey));
        } else {
            vec2 e = d / vec2(size, size * 0.62 * flip);
            sd = (length(e + vec2(0.0, 0.25 * e.x * e.x)) - 1.0) * size * 0.62 * flip;
            vec3 tint = mix(vec3(0.6, 0.04, 0.09), vec3(0.85, 0.35, 0.4), hash21(id + 9.1));
            c0 = tint * (0.25 + 0.55 * flip) * (0.5 + 0.7 * lum(gKey)) + gKey * tint * 0.25 * (1.0 - flip);
        }
        float a = smoothstep(blur, -blur, sd) * (1.0 - 0.25 * fl);
        acc.rgb = acc.rgb * (1.0 - a) + c0 * a;
        acc.a = acc.a + a * (1.0 - acc.a);
    }
    return acc;
}

// ------------------------------------------------------------------ funeral: the coffin
vec3 coffin(vec3 col) {
    float z = 1.16;
    vec2 q = lay(z);
    float px = gPx * z;
    vec2 cq = q - vec2(0.13, -EYE);
    // a black pall over the bier, falling in folds to the floor
    float bier = sdRBox(cq - vec2(0.0, 0.07), vec2(0.2, 0.07), 0.01);
    float folds = 0.75 + 0.25 * sin(cq.x * 90.0 + sin(cq.y * 20.0));
    vec3 pall = vec3(0.01, 0.009, 0.011) * folds + gKey * 0.004;
    pall += vec3(1.0, 0.7, 0.4) * 0.05 * exp(-max(-bier, 0.0) / (0.003 + px)) * step(0.1, cq.y);
    col = mix(col, pall, smoothstep(px, -px, bier));
    // the small white coffin: a low casket with a gently peaked lid
    vec2 kq = cq - vec2(0.0, 0.14);
    float box = sdRBox(kq - vec2(0.0, 0.04), vec2(0.15, 0.04), 0.006);
    float lid = sdTrap(kq - vec2(0.0, 0.092), 0.158, 0.125, 0.014);
    float d = min(box, lid);
    float lit = gAmb * 2.4 + 0.5 * gCandle;
    vec3 white = vec3(0.86, 0.84, 0.8) * lit * mix(vec3(1.0), vec3(1.0, 0.82, 0.62), 0.6 * gCandle);
    white *= 0.72 + 0.28 * smoothstep(0.0, 0.08, kq.y);                     // lit from above and behind
    white *= 1.0 - 0.25 * smoothstep(0.003, 0.0, abs(kq.y - 0.08));          // the lid's seam
    white += vec3(1.0, 0.78, 0.5) * 0.35 * gCandle * exp(-max(-d, 0.0) / (0.003 + px)) * smoothstep(0.05, 0.1, kq.y);
    float handles = sdBox(vec2(abs(kq.x) - 0.09, kq.y - 0.04), vec2(0.022, 0.004));
    white = mix(white, vec3(0.7, 0.55, 0.3) * lit * 0.8, smoothstep(px, -px, handles));
    col = mix(col, white, smoothstep(px, -px, d));
    // white flowers and leaves on the lid
    vec2 fq = kq - vec2(-0.03, 0.118);
    float leaf = sdEllipse(fq - vec2(0.0, 0.004), vec2(0.07, 0.012));
    col = mix(col, vec3(0.03, 0.06, 0.03) * lit, smoothstep(px, -px, leaf));
    for (int i = 0; i < 5; i++) {
        float fi = float(i);
        vec2 c = vec2((fi - 2.0) * 0.026, 0.012 + 0.006 * sin(fi * 2.1));
        float r = 0.016 - 0.003 * mod(fi, 2.0);
        vec2 bq = fq - c;
        float bl = sdCircle(bq, r);
        float ang = atan(bq.y, bq.x);
        float swirl = 0.7 + 0.3 * sin(ang * 3.0 + length(bq) / r * 9.0);
        float petalEdge = smoothstep(0.0, r * 0.25, -bl) * 0.25 + 0.75;
        col = mix(col, vec3(0.93, 0.91, 0.87) * lit * 1.15 * swirl * petalEdge, smoothstep(px, -px, bl));
    }
    return col;
}

// funeral: a tiered bank of candles across the steps
vec3 candleBank(vec3 col) {
    float z = 1.7;
    vec2 q = lay(z);
    float px = gPx * z;
    for (int r = 0; r < 3; r++) {
        float fr = float(r);
        float y = -EYE + 0.13 + 0.075 * fr;
        float w = 0.56 - 0.1 * fr;
        float cell = 0.07;
        float off = 0.5 * mod(fr, 2.0);
        float xi = clamp(floor(q.x / cell + 0.5 - off), -floor(w / cell), floor(w / cell));
        float xc = (xi + off) * cell;
        // tier shelf
        float shelf = sdBox(q - vec2(0.0, y - 0.01), vec2(w + 0.04, 0.006));
        col = mix(col, vec3(0.03, 0.025, 0.02) + gKey * 0.02, smoothstep(px, -px, shelf));
        for (int k = -1; k <= 1; k++) {
            float xk = xc + float(k) * cell;
            if (abs(xk) > w + 0.001) continue;
            float hh = 0.035 + 0.025 * hash11(xk * 13.0 + fr);
            col = candleAt(col, q, vec2(xk, y - 0.004), hh, gCandle * 0.85, xk * 9.0 + fr * 4.0, px);
        }
    }
    // the glow of the whole bank in the haze
    vec2 c = toScreen(vec2(0.0, -EYE + 0.2), z);
    vec2 dd = (gSp - c) * vec2(0.7, 1.6);
    col += vec3(1.0, 0.6, 0.28) * 0.16 * exp(-dot(dd, dd) * 9.0) * gCandle;
    return col;
}

// funeral: Tommaso's line, faint silver at the height of his tone, dissolving into motes
vec3 tommasoLine(vec2 sp, float w) {
    if (w <= 0.0) return vec3(0.0);
    const float Y = 0.085, X0 = -0.8, X1 = 0.8;
    const float NSEG = 48.0;
    float segW = (X1 - X0) / NSEG;
    vec3 acc = vec3(0.0);
    // the line: segments go out one by one, the ends first
    float s = floor((sp.x - X0) / segW);
    if (s >= 0.0 && s < NSEG) {
        float centre = abs((s + 0.5) / NSEG - 0.5) * 2.0;        // 0 middle, 1 ends
        float tau = 0.08 + 0.5 * (1.0 - centre) * 0.8 + 0.25 * hash11(s * 3.1);
        float alive = 1.0 - smoothstep(tau - 0.06, tau + 0.04, w);
        float y = Y + 0.0012 * sin(sp.x * 9.0 + gT * 2.0);
        float d = abs(sp.y - y);
        float fadeIn = smoothstep(0.0, 0.05, w);
        float edge = sat(min(sp.x - X0, X1 - sp.x) / 0.1);
        acc += SILVER * (exp(-d / 0.0016) * 0.9 + exp(-d / 0.012) * 0.18) * alive * fadeIn * edge * 0.9;
    }
    // motes: each segment releases two that rise and fade
    for (int k = -2; k <= 2; k++) {
        float sk = s + float(k);
        if (sk < 0.0 || sk >= NSEG) continue;
        float centre = abs((sk + 0.5) / NSEG - 0.5) * 2.0;
        float tau = 0.08 + 0.5 * (1.0 - centre) * 0.8 + 0.25 * hash11(sk * 3.1);
        for (int m = 0; m < 2; m++) {
            float fm = float(m);
            float age = w - tau + 0.05 * fm;
            if (age <= 0.0) continue;
            float hx = hash11(sk * 7.7 + fm * 3.3);
            vec2 mp = vec2(X0 + (sk + 0.2 + 0.6 * hx) * segW + 0.012 * sin(age * 9.0 + hx * 6.0),
                           Y + age * (0.32 + 0.25 * hash11(sk + fm * 9.0)));
            float tw = 0.65 + 0.35 * sin(gT * (3.0 + 4.0 * hx) + sk);
            float life = exp(-age * 2.6) * smoothstep(0.0, 0.04, age);
            float dd = length(sp - mp);
            acc += SILVER * (exp(-dd / 0.0022) * 1.4 + exp(-dd / 0.014) * 0.12) * life * tw;
        }
    }
    return acc;
}

// light shafts from high windows on the left (dusk), streaked by dust
float shafts(vec2 sp) {
    vec2 dir = normalize(vec2(0.62, -1.0));
    vec2 n = vec2(-dir.y, dir.x);
    float across = dot(sp - vec2(-0.6, 0.6), n);
    float along = dot(sp - vec2(-0.6, 0.6), dir);
    float bands = 0.0;
    for (int i = 0; i < 3; i++) {
        float c = -0.05 + 0.33 * float(i);
        float w = 0.05 + 0.012 * float(i);
        bands += smoothstep(w, w * 0.3, abs(across - c));
    }
    float streak = 0.6 + 0.4 * fbm(vec2(across * 22.0, along * 2.0 - gT * 0.05));
    return bands * streak * smoothstep(-0.1, 0.3, along) * exp(-max(along, 0.0) * 0.9);
}

// ------------------------------------------------------------------ main
void main() {
    gSp = screen();
    gT = uTime;
    gPx = 1.5 * PIXEL;
    gMode = int(uP[0].x + 0.5);
    gRise = sat(uP[0].y);
    gBloom = sat(uP[0].z);
    gCold = sat(uP[0].w);
    gCrowd = sat(uP[3].x);
    gCamX = 0.012 * sin(uTime * 0.07);
    // ---- the looks
    gKey = vec3(1.0, 0.62, 0.3); gHaze = vec3(0.2, 0.1, 0.042); gStone = vec3(0.55, 0.45, 0.36);
    gGlassTint = vec3(0.35, 0.45, 0.9); gAmb = 0.075; gGlass = 0.22; gCandle = 1.0; gDesat = 0.2;
    if (gMode == 1 || gMode == 2) {
        gKey = vec3(1.0, 0.78, 0.45) * 1.25; gHaze = vec3(0.42, 0.29, 0.14) * 0.7; gStone = vec3(0.62, 0.52, 0.40);
        gGlassTint = vec3(1.0); gAmb = 0.12; gGlass = 2.0; gCandle = 0.8; gDesat = 0.0;
    } else if (gMode == 3) {
        gKey = vec3(0.62, 0.45, 1.0) * 0.85; gHaze = vec3(0.17, 0.11, 0.3) * 0.55; gStone = vec3(0.45, 0.42, 0.5);
        gGlassTint = vec3(0.62, 0.48, 1.0); gAmb = 0.06; gGlass = 0.5; gCandle = 0.0; gDesat = 0.45;
    } else if (gMode == 4) {
        gKey = vec3(0.75, 0.78, 0.85) * 0.75; gHaze = vec3(0.13, 0.13, 0.145) * 0.8; gStone = vec3(0.5, 0.49, 0.49);
        gGlassTint = vec3(0.62, 0.66, 0.72); gAmb = 0.075; gGlass = 0.6; gCandle = 1.0; gDesat = 0.78;
    }
    // the gold drains away (mode 2, or anywhere uP[0].w is raised)
    vec3 coldKey = vec3(0.55, 0.62, 0.75) * 0.8;
    gKey = mix(gKey, coldKey, gCold);
    gHaze = mix(gHaze, vec3(0.1, 0.12, 0.16) * 0.8, gCold);
    gGlassTint = mix(gGlassTint, vec3(0.5, 0.56, 0.68), gCold);
    gGlass *= 1.0 - 0.6 * gCold;
    gDesat = mix(gDesat, 0.85, gCold);
    gCandle *= 1.0 - 0.5 * gCold;
    float roseScreenY = toScreen(ROSE_C, Z_BACK).y;
    gLight = (gMode == 1 || gMode == 2) ? vec2(0.0, roseScreenY - 0.1) :
             (gMode == 3 ? vec2(-0.25, 0.25) : toScreen(vec2(0.0, -0.05), Z_ALTAR));

    // ---- far to near
    vec3 col;
    float zf;
    vec3 fl = floorCol(gSp, zf);
    bool isFloor = (gSp.y + gRise * TILT < 0.0) && zf < Z_BACK;
    col = isFloor ? fl : backWall(gSp);
    col = mix(col, hazeLight(gSp), 0.12);
    // mandala behind the arches: the window's light filling the vault
    if ((gMode == 1 || gMode == 2) && gBloom > 0.0) {
        vec2 qb = lay(Z_BACK);
        col += mandala(qb, gBloom, uScore, gPx * Z_BACK) * (1.0 - 0.75 * gCold);
    }
    col = archLayer(col, 2.0, 0.0, 0.14);
    col = altar(col);
    if (gMode == 0) col = votives(col);
    if (gMode != 3) col = candelabra(col, gCandle);
    if (gMode == 4) col = candleBank(col);
    // beams through the haze
    if (gMode == 1 || gMode == 2) {
        vec2 rs = toScreen(ROSE_C, Z_BACK);
        float b = beam(gSp, rs, vec2(0.0, -1.0), 0.32, 1.4);
        b += 0.5 * beam(gSp, rs + vec2(-0.12, 0.0), vec2(-0.18, -1.0), 0.12, 1.0);
        b += 0.5 * beam(gSp, rs + vec2(0.12, 0.0), vec2(0.18, -1.0), 0.12, 1.0);
        float streak = 0.55 + 0.45 * fbm(vec2(gSp.x * 18.0 / (1.0 + abs(rs.y - gSp.y) * 2.0), gSp.y * 1.5 - gT * 0.03));
        vec3 bc = mix(vec3(1.0, 0.72, 0.35), vec3(0.95, 0.5, 0.45), 0.5 + 0.5 * sin(gSp.x * 14.0));
        col += bc * mix(vec3(1.0), vec3(0.55, 0.62, 0.78), gCold) * b * streak * 0.32 * gGlass * 0.5;
        col += gKey * dust(gSp, gT, 0.18, 0.08) * b * 0.5;
    } else if (gMode == 3) {
        float s = shafts(gSp);
        col += vec3(0.6, 0.42, 1.0) * s * 0.22;
        col += vec3(0.8, 0.7, 1.0) * dust(gSp, gT, 0.15, 0.08) * s * 0.4;
    } else if (gMode == 4) {
        vec2 c0 = toScreen(vec2(-0.74, 0.5), Z_BACK);
        vec2 c1 = toScreen(vec2(0.74, 0.5), Z_BACK);
        float b = beam(gSp, c0, vec2(0.5, -1.0), 0.09, 1.2) + beam(gSp, c1, vec2(-0.5, -1.0), 0.09, 1.2);
        col += gKey * b * 0.1 * (0.6 + 0.4 * fbm(gSp * 6.0 + gT * 0.02));
    }
    col = archLayer(col, 1.5, 1.0, 0.1);
    if (gMode == 4) {
        col = coffin(col);
        // four tall candles at the coffin's corners
        for (int i = 0; i < 4; i++) {
            float zc = i < 2 ? 1.27 : 1.07;
            vec2 q = lay(zc);
            float xs = (mod(float(i), 2.0) < 0.5 ? -1.0 : 1.0) * 0.25 + 0.13;
            float px = gPx * zc;
            float stick = sdBox(q - vec2(xs, -EYE + 0.17), vec2(0.009, 0.17));
            col = mix(col, vec3(0.04, 0.03, 0.025) + gKey * 0.02, smoothstep(px, -px, stick));
            col = candleAt(col, q, vec2(xs, -EYE + 0.34), 0.06, gCandle, float(i) * 5.7 + 2.0, px);
        }
    }
    col = archLayer(col, 1.12, 2.0, 0.07);

    // ---- pews beside the couple, then the characters (depth 1)
    vec3 crowdBody = vec3(0.032, 0.021, 0.013) * (0.6 + 3.0 * gAmb), crowdRim = gKey * 0.85;
    if (gMode == 4) { crowdBody = vec3(0.013, 0.012, 0.014); crowdRim = gKey * 0.5; }
    col = rows(col, crowdBody, crowdRim, true);
    vec2 q1 = lay(1.0);
    vec4 E = uP[1], V = uP[2];
    if (E.z <= 0.0) E = vec4(-0.1, -0.43, 0.5, 0.0);     // an empty slot means she is absent
    if (V.z <= 0.0) V = vec4(0.12, -0.43, 0.55, 0.0);
    vec3 eBody = vec3(0.45, 0.03, 0.06), eRim = vec3(1.0, 0.45, 0.35);
    vec3 vBody = vec3(0.035, 0.03, 0.03), vRim = vec3(1.0, 0.8, 0.4);
    vRim = mix(vRim, vec3(0.6, 0.68, 0.8), gCold);
    eRim = mix(eRim, vec3(0.8, 0.6, 0.62), gCold * 0.6);
    if (gMode == 3) { eBody *= 0.8; eRim = mix(eRim, vec3(0.75, 0.6, 1.0), 0.45); }
    if (gMode == 4) { eBody *= 0.7; eRim = mix(eRim, vec3(0.9, 0.8, 0.75), 0.4); }
    vec2 Le = normalize(gLight - (E.xy + vec2(0.0, E.z * 0.7)));
    vec2 Lv = normalize(gLight - (V.xy + vec2(0.0, V.z * 0.7)));
    // poses: hands joined (vow, wedding); in the cooling she lets go and turns to face him
    vec4 eP = vec4(0.12, 0.35, 0.32, 0.0), vP = vec4(0.35, 0.1, 0.0, 0.0);
    float sx = 1.0;
    if (gMode == 0) { eP = vec4(0.1, 0.45, 0.3, 0.03); vP = vec4(0.3, 0.1, 0.0, -0.02); }
    if (gMode == 2) {
        float turn = smoothstep(0.15, 0.7, gCold);
        eP = vec4(mix(0.12, 0.18, turn), mix(0.35, 0.95, turn), mix(0.32, 0.22, turn), mix(0.0, 0.06, turn));
        sx = mix(1.0, 0.8, turn);
    }
    if (gMode == 3) { eP = vec4(0.12, 0.42, 0.26, 0.035); }
    if (gMode == 4) { eP = vec4(0.06, 0.08, 0.2, 0.0); }
    // Vittorio: a man at the wedding, a figure of cold light in the vision
    if (gMode == 3) {
        float I = sat(uP[4].z) * V.w;
        col += lightFigure(q1, V.xy, V.z, I);
        // his cold light on the floor and on her
        vec2 fd = (q1 - V.xy - vec2(0.0, 0.02)) * vec2(1.0, 4.0);
        col += vec3(0.45, 0.6, 1.0) * 0.12 * I * exp(-dot(fd, fd) * 8.0);
        eRim = mix(eRim, vec3(0.55, 0.7, 1.0), 0.6 * I);
        Le = normalize(mix(Le, normalize(V.xy + vec2(0.0, V.z * 0.6) - E.xy - vec2(0.0, E.z * 0.6)), I));
    } else if (V.w > 0.0) {
        vec4 v = figB(q1, V.xy, V.z, vP, 0.0, vBody, vRim, Lv, 1.0);
        col = over(col, v * V.w);
    }
    if (E.w > 0.0) {
        vec4 e = figB(q1, E.xy, E.z, eP, 2.0, eBody, eRim, Le, sx);
        col = over(col, e * E.w);
    }

    // ---- pews and people, nearer the camera
    col = rows(col, crowdBody, crowdRim, false);
    col = archLayer(col, 0.84, 3.0, 0.03);

    // ---- light in the air, nearest of all
    if (gMode == 1 || gMode == 2) {
        float rings = bellRings(gSp, uP[4].y);
        col += vec3(1.0, 0.78, 0.42) * rings * 0.22 * (1.0 - gCold);
        vec4 pt = petals(gSp, sat(uP[4].x));
        col = col * (1.0 - pt.a) + pt.rgb;
    }
    if (gMode == 4) col += tommasoLine(gSp, sat(uP[4].w));
    col += gKey * dust(gSp + vec2(0.0, gRise * 0.3), gT, 0.06, 0.05) * 0.08 * (gMode == 4 ? 0.5 : 1.0);
    // gold drained: the picture itself goes grey and cold
    float l = lum(col);
    col = mix(col, vec3(l) * vec3(0.82, 0.9, 1.08), gCold * 0.7);
    fragColor = vec4(max(col, 0.0), 1.0);
}
