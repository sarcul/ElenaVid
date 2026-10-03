#version 430
// ---------------------------------------------------------------------------------------------
// abstract.frag  -  GRAPHIC INTERLUDES. uP[0].x selects the mode, uP[0].y is progress through the
// shot (0..1) in every mode.
//   0 drift     translucent panels slide over one another: a cafe table (two cups, two figures),
//               a windswept pier, a warm home window; Marco's green thread thickens with uP[1].x
//   1 run       warm streaks of light rushing past: urgency
//   2 letter    a sheet of paper in the dark under a lamp; uLetter (R = ink coverage) is revealed
//               in reading order by uP[1].x with a slow push-in; uP[1].z = number of text lines
//               (0 means 6, as elenavid/video/text.py lays out the letter)
//   3 confess   four crimson-edged frames, Elena in each (with the child's glow, with an amber
//               figure, with a green figure, with a steel-blue shadow) slide together into one
//   4 split     the frame splits on a diagonal: Davide grieving in warm amber on the left; the same
//               silhouette through her fear on the right, cold, cracked, Vittorio's shadow behind;
//               uP[1].x intensity, uP[1].y heartbeat pulse
//   5 withdraw  Marco's green line retracting into the dark (uP[1].x 0..1)
//   6 blow      black, then a gilded picture frame cracking apart in slow motion (uP[1].x 0..1;
//               the first tenth brings it up out of the black)
//   7 end       near-black with a faint warm glow, for the end titles
// ---------------------------------------------------------------------------------------------
#include common
uniform sampler2D uLetter;

const vec3 CRIMSON = vec3(0.45, 0.03, 0.06), CRIMSON_RIM = vec3(1.0, 0.45, 0.35);
const vec3 AMBER = vec3(0.35, 0.2, 0.06), AMBER_RIM = vec3(1.0, 0.7, 0.35);
const vec3 GREEN = vec3(0.06, 0.22, 0.18), GREEN_RIM = vec3(0.5, 1.0, 0.8);
const vec3 STEEL = vec3(0.45, 0.6, 1.0);
const vec3 SILVER = vec3(0.86, 0.9, 1.0);
const vec3 THREAD = vec3(0.45, 1.0, 0.72);

float gT, gPx, gProg, gA, gB;
vec2 gSp;

// ------------------------------------------------------------------ silhouettes with arms by IK
float sdArm(vec2 p, vec2 s, vec2 t, float sg) {
    const float A = 0.17, B = 0.16;
    vec2 d = t - s;
    float L = clamp(length(d), 0.06, A + B - 0.002);
    vec2 u = d / max(length(d), 1e-4);
    float ca = clamp((A * A + L * L - B * B) / (2.0 * A * L), -1.0, 1.0);
    vec2 e = s + A * (ca * u + sg * sqrt(1.0 - ca * ca) * vec2(-u.y, u.x));
    vec2 h = s + u * L;
    return min(sdCapsule(p, s, e, 0.024), sdCapsule(p, e, h, 0.02));
}
// sdFigure's body (common.glsl) with arms reaching for hand targets and a head that can bow
float sdFigX(vec2 p, vec4 pose, float hair, vec4 hands, float bow, vec2 sg) {
    p.x -= p.y * pose.w;
    vec2 hc = vec2(0.008 * bow, 0.905 - 0.06 * bow);
    float d = sdCircle(p - hc, 0.062);
    if (hair > 0.5) d = min(d, sdCircle(p - hc - vec2(0.012, 0.03), 0.06));
    if (hair > 1.5) d = min(d, sdCircle(p - hc - vec2(-0.03, 0.06), 0.035));
    d = smin(d, sdCapsule(p, vec2(0.0, 0.85 - 0.05 * bow), vec2(0.0, 0.79), 0.026), 0.02);
    float drop = 0.015 * bow;
    d = smin(d, sdTrap(p - vec2(0.0, 0.64 - drop * 0.5), 0.075, 0.115 - 0.01 * bow, 0.15), 0.03);
    if (pose.z > 0.0) d = smin(d, sdTrap(p - vec2(0.0, 0.26), 0.13 + 0.17 * pose.z, 0.075, 0.25), 0.02);
    else {
        d = smin(d, sdTrap(p - vec2(0.0, 0.47), 0.085, 0.09, 0.03), 0.02);
        d = min(d, sdCapsule(p, vec2(-0.045, 0.46), vec2(-0.05, 0.02), 0.034));
        d = min(d, sdCapsule(p, vec2(0.045, 0.46), vec2(0.05, 0.02), 0.034));
    }
    d = min(d, sdArm(p, vec2(-0.11, 0.765 - drop), hands.xy, sg.x));
    d = min(d, sdArm(p, vec2(0.11, 0.765 - drop), hands.zw, sg.y));
    return d;
}
// figure()'s shading for a silhouette distance d (screen units) and outward normal n
vec4 shadeSil(float d, vec2 n, vec2 q, float h, vec3 body, vec3 rim, vec2 L) {
    float a = aa(d, gPx);
    float facing = sat(dot(n, normalize(L)) * 0.8 + 0.2);
    float band = exp(-max(-d, 0.0) / (0.006 * h + 0.002)) * a;
    vec3 c = body * (0.85 + 0.15 * fbm(q * 18.0)) + rim * band * facing * 1.6;
    float halo = glow(d, 0.01 * h) * (1.0 - a) * 0.35 * facing;
    return vec4(c * a + rim * halo, max(a, halo * 0.5));
}
vec4 figX(vec2 p, vec2 pos, float h, vec4 pose, float hair, vec4 hands, float bow, vec2 sg, vec3 body, vec3 rim, vec2 L) {
    vec2 q = (p - pos) / h;
    if (abs(q.x - q.y * pose.w) > 0.62 || q.y < -0.08 || q.y > 1.12) return vec4(0.0);
    float d = sdFigX(q, pose, hair, hands, bow, sg) * h;
    vec2 e = vec2(0.002 / h, 0.0);
    vec2 n = normalize(vec2(sdFigX(q + e.xy, pose, hair, hands, bow, sg) - sdFigX(q - e.xy, pose, hair, hands, bow, sg),
                            sdFigX(q + e.yx, pose, hair, hands, bow, sg) - sdFigX(q - e.yx, pose, hair, hands, bow, sg)) + 1e-6);
    return shadeSil(d, n, q, h, body, rim, L);
}
// a smoky shadow-figure (Vittorio as she remembers him)
vec4 shadowFigure(vec2 p, vec2 pos, float h, float I) {
    vec2 q = (p - pos) / h;
    if (abs(q.x) > 0.9 || q.y < -0.2 || q.y > 1.6 || I <= 0.0) return vec4(0.0);
    vec2 w = vec2(fbm(q * 3.0 + vec2(0.0, -gT * 0.3)), fbm(q * 3.0 + vec2(4.0, -gT * 0.25))) - 0.5;
    float d = sdFigure(q + w * 0.09, vec4(0.25, 0.3, 0.0, 0.0), 0.0);
    float body = smoothstep(0.035, -0.05, d);
    float edge = exp(-abs(d + 0.012) / 0.012) * (0.35 + 0.65 * fbm(q * 7.0 - gT * 0.4));
    float smoke = smoothstep(0.5, 0.8, fbm(vec2(q.x * 3.0, q.y * 1.5 - gT * 0.3) + w * 2.0)) * exp(-max(d, 0.0) * 6.0) * smoothstep(0.4, 1.0, q.y);
    vec3 c = vec3(0.002, 0.004, 0.009) * body + STEEL * (edge * 0.1 + smoke * 0.04);
    return vec4(c * I, sat((body * 0.93 + smoke * 0.4) * I));
}

float sdOpening(vec2 q, float w, float ys, float r) {      // round or pointed arch, negative inside
    float ax = abs(q.x);
    if (q.y < ys) return ax - w;
    return length(vec2(ax + (r - w), q.y - ys)) - r;
}

// ------------------------------------------------------------------ mode 0: the drift montage
// a translucent panel: returns local coordinates and a feathered mask
float panelMask(vec2 lp, vec2 hs, float feather) {
    vec2 d = abs(lp) - hs;
    float sd = length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
    return smoothstep(feather, -feather, sd);
}

vec3 cafe(vec2 lp) {
    // warm wall, an arched window onto the night street, a lamp over the table
    vec3 col = mix(vec3(0.16, 0.08, 0.035), vec3(0.3, 0.15, 0.06), smoothstep(-0.2, 0.2, lp.y));
    col *= 1.0 - 0.35 * step(lp.y, -0.06);                                           // wainscot
    col += vec3(1.0, 0.6, 0.3) * 0.05 * smoothstep(0.004, 0.0, abs(lp.y + 0.06));
    float mir = sdEllipse(lp - vec2(-0.33, 0.07), vec2(0.07, 0.09));                  // a gilt mirror
    col = mix(col, vec3(0.08, 0.06, 0.05) + vec3(1.0, 0.65, 0.3) * 0.12 * exp(-length(lp - vec2(-0.31, 0.11)) / 0.04), smoothstep(gPx, -gPx, mir));
    col = mix(col, vec3(0.5, 0.35, 0.15), smoothstep(gPx, -gPx, abs(mir) - 0.006) * 0.8);
    float t2 = min(sdBox(lp - vec2(-0.52, -0.12), vec2(0.07, 0.005)), sdBox(lp - vec2(-0.52, -0.18), vec2(0.006, 0.06)));
    t2 = min(t2, sdRBox(lp - vec2(-0.42, -0.1), vec2(0.022, 0.07), 0.012));         // an empty table and chair
    col = mix(col, vec3(0.03, 0.015, 0.008), smoothstep(gPx, -gPx, t2));
    float win = sdOpening(lp - vec2(0.36, -0.02), 0.13, 0.05, 0.13);
    col = mix(col, vec3(0.04, 0.06, 0.1) + vec3(1.0, 0.7, 0.4) * 0.3 * exp(-length(lp - vec2(0.42, 0.06)) / 0.03), smoothstep(gPx, -gPx, win));
    col = mix(col, vec3(0.05, 0.025, 0.012), smoothstep(gPx, -gPx, abs(win) - 0.006));
    col += vec3(1.0, 0.65, 0.3) * (exp(-length(lp - vec2(0.0, 0.16)) / 0.025) * 1.5 + exp(-length(lp - vec2(0.0, 0.1)) / 0.2) * 0.25);
    // the table: a round top seen edge on, a pedestal
    float top = sdRBox(lp - vec2(0.0, -0.1), vec2(0.13, 0.006), 0.004);
    float ped = sdBox(lp - vec2(0.0, -0.2), vec2(0.008, 0.1));
    float tbl = min(top, ped);
    col = mix(col, vec3(0.03, 0.015, 0.008) + vec3(1.0, 0.6, 0.3) * 0.12 * smoothstep(-0.105, -0.095, lp.y), smoothstep(gPx, -gPx, tbl));
    // two cups on saucers, steam curling up
    for (int i = 0; i < 2; i++) {
        float s = i == 0 ? -1.0 : 1.0;
        vec2 cq = lp - vec2(0.05 * s, -0.087);
        float cup = sdTrap(cq - vec2(0.0, 0.008), 0.009, 0.012, 0.009);
        float handle = abs(length(cq - vec2(0.015 * s, 0.009)) - 0.005) - 0.0018;
        float saucer = sdEllipse(cq - vec2(0.0, -0.002), vec2(0.022, 0.0035));
        float d = min(min(cup, handle), saucer);
        col = mix(col, vec3(0.75, 0.68, 0.58) * 0.5, smoothstep(gPx, -gPx, d));
        float sx = cq.x - 0.006 * sin(cq.y * 160.0 - gT * 2.0 + float(i) * 2.0);
        float steam = exp(-abs(sx) / 0.0025) * smoothstep(0.02, 0.04, cq.y) * smoothstep(0.12, 0.05, cq.y);
        col += vec3(0.8, 0.7, 0.6) * steam * 0.12;
    }
    // Elena and Marco at the table, leaning in
    vec4 e = figure(lp, vec2(-0.2, -0.25), 0.32, vec4(0.1, 0.5, 0.25, 0.1), 2.0, CRIMSON, CRIMSON_RIM, vec2(0.6, 1.0));
    vec4 m = figure(lp, vec2(0.2, -0.255), 0.335, vec4(0.5, 0.1, 0.0, -0.1), 0.0, GREEN, GREEN_RIM, vec2(-0.6, 1.0));
    col = over(col, e);
    col = over(col, m);
    col = mix(col, col * vec3(1.0, 0.85, 0.7), 0.3);
    return col;
}

vec3 pier(vec2 lp) {
    // a windy dusk over the gulf: streaming cloud, a warm band at the horizon
    float hor = -0.02;
    vec3 sky = mix(vec3(0.3, 0.2, 0.14), vec3(0.05, 0.08, 0.14), smoothstep(hor, 0.2, lp.y));
    float cl = fbm(vec2(lp.x * 3.0 - gT * 0.25, lp.y * 12.0));
    sky = mix(sky, sky * 1.6 + vec3(0.05, 0.03, 0.02), smoothstep(0.5, 0.75, cl) * 0.6);
    vec3 col = sky;
    if (lp.y < hor) {
        float wav = fbm(vec2(lp.x * 8.0 - gT * 0.6, lp.y * 70.0));
        col = mix(vec3(0.02, 0.035, 0.055), vec3(0.08, 0.1, 0.13), smoothstep(0.55, 0.8, wav) * smoothstep(-0.2, hor, lp.y));
        col += vec3(1.0, 0.6, 0.35) * 0.08 * exp(-pow((lp.x - 0.18) / 0.03, 2.0)) * smoothstep(-0.2, hor, lp.y) * wav;
    }
    // the stone pier running out into the sea, bollards along it, a lamp post
    float pierD = sdBox(lp - vec2(-0.2, -0.105), vec2(0.5, 0.02));
    float boll = 1e3;
    for (int i = 0; i < 6; i++) boll = min(boll, sdRBox(lp - vec2(-0.6 + 0.16 * float(i), -0.078), vec2(0.006, 0.007), 0.004));
    float post = sdBox(lp - vec2(0.18, -0.03), vec2(0.0025, 0.06));
    float d = min(min(pierD, boll), post);
    col = mix(col, vec3(0.025, 0.025, 0.03) + vec3(1.0, 0.6, 0.3) * 0.05 * smoothstep(-0.12, -0.085, lp.y), smoothstep(gPx, -gPx, d));
    col += vec3(1.0, 0.65, 0.35) * (exp(-length(lp - vec2(0.18, 0.035)) / 0.008) * 2.0 + exp(-length(lp - vec2(0.18, 0.035)) / 0.06) * 0.15);
    // two figures at the end, the wind at their backs
    vec4 e = figure(lp, vec2(0.235, -0.085), 0.15, vec4(0.2, 0.6, 0.55, 0.12), 2.0, CRIMSON, CRIMSON_RIM, vec2(-1.0, 0.4));
    vec4 m = figure(lp, vec2(0.272, -0.085), 0.162, vec4(0.5, 0.2, 0.0, 0.06), 0.0, GREEN, GREEN_RIM, vec2(-1.0, 0.4));
    col = over(col, m);
    col = over(col, e);
    // spray and wind streaks
    float streak = smoothstep(0.85, 1.0, vnoise(vec2(lp.x * 30.0 - gT * 6.0, lp.y * 200.0)));
    col += vec3(0.6, 0.65, 0.7) * streak * 0.08;
    return col;
}

vec3 homeWindow(vec2 lp) {
    // a cold wall at night and one warm window
    vec3 col = vec3(0.03, 0.045, 0.075) * (0.75 + 0.4 * fbm(lp * 18.0));
    float win = sdBox(lp - vec2(0.0, 0.0), vec2(0.11, 0.16));
    vec3 room = vec3(1.0, 0.62, 0.32) * (0.6 + 0.5 * exp(-length(lp - vec2(-0.04, 0.05)) / 0.12));
    // inside: Davide, and Tommaso's glow beside him
    vec4 dv = figure(lp, vec2(0.025, -0.2), 0.3, vec4(0.15, 0.7, 0.0, -0.03), 0.0, AMBER * 0.5, AMBER_RIM, vec2(-0.6, 1.0));
    vec3 inside = over(room, dv);
    float tg = length(lp - vec2(-0.045, -0.02));
    inside += SILVER * (exp(-tg / 0.012) * 1.2 + exp(-tg / 0.05) * 0.25) * (0.9 + 0.1 * sin(gT * 1.7));
    // lace curtains gathered at the sides
    float lace = smoothstep(0.06, 0.1, abs(lp.x)) * (0.55 + 0.45 * sin(lp.y * 220.0 + sin(lp.x * 90.0) * 2.0));
    inside = mix(inside, vec3(1.0, 0.8, 0.6) * 0.7, lace * 0.5);
    col = mix(col, inside, smoothstep(gPx, -gPx, win));
    // glazing bars and the frame, the sill catching the light
    float bars = min(abs(lp.x), abs(lp.y - 0.05)) - 0.004;
    col = mix(col, vec3(0.04, 0.025, 0.015), smoothstep(gPx, -gPx, max(bars, win)));
    col = mix(col, vec3(0.06, 0.05, 0.05), smoothstep(gPx, -gPx, abs(win) - 0.009));
    col += vec3(1.0, 0.6, 0.3) * 0.25 * smoothstep(0.012, 0.0, abs(lp.y + 0.172)) * step(abs(lp.x), 0.13);
    col += vec3(1.0, 0.6, 0.3) * 0.08 * exp(-max(win, 0.0) / 0.05);
    return col;
}

vec3 drift(vec2 sp) {
    vec3 col = vec3(0.012, 0.012, 0.02) + vec3(0.02, 0.016, 0.012) * exp(-dot(sp, sp) * 2.0);
    float pr = gProg;
    float tw = 0.015 * sin(gT * 0.13);
    // the pier, furthest back, sliding left
    vec2 c1 = vec2(0.28 - 0.56 * pr - tw, -0.205);
    vec2 l1 = sp - c1;
    float m1 = panelMask(l1, vec2(0.7, 0.23), 0.02);
    if (m1 > 0.0) col = mix(col, pier(l1 * vec2(0.94, 0.87)), m1 * 0.8);
    // the cafe, sliding right
    vec2 c2 = vec2(-0.3 + 0.6 * pr + tw, 0.19);
    vec2 l2 = sp - c2;
    float m2 = panelMask(l2, vec2(0.66, 0.24), 0.02);
    if (m2 > 0.0) col = mix(col, cafe(l2 * vec2(0.94, 0.875)), m2 * 0.76);
    // the home window drifting in from the right, warm
    vec2 c3 = vec2(0.75 - 0.55 * smoothstep(0.0, 1.0, pr), -0.02 + 0.02 * sin(gT * 0.3));
    vec2 l3 = sp - c3;
    float m3 = panelMask(l3, vec2(0.22, 0.28), 0.025) * smoothstep(0.05, 0.4, pr);
    if (m3 > 0.0) col = mix(col, homeWindow(l3), m3 * 0.7);
    // thin bright edges of the panels, like the rims of lantern slides
    vec2 e1 = abs(l1) - vec2(0.7, 0.23), e2 = abs(l2) - vec2(0.66, 0.24);
    float s1 = length(max(e1, 0.0)) + min(max(e1.x, e1.y), 0.0), s2 = length(max(e2, 0.0)) + min(max(e2.x, e2.y), 0.0);
    col += vec3(1.0, 0.85, 0.7) * 0.06 * (smoothstep(0.003, 0.0, abs(s1)) + smoothstep(0.003, 0.0, abs(s2)));
    // Marco's green thread, weaving across and thickening
    float th = gA;
    float y = 0.02 * sin(sp.x * 3.1 + gT * 0.7) + 0.012 * sin(sp.x * 7.3 - gT * 1.1) - 0.015;
    float d = abs(sp.y - y);
    float w = mix(0.0006, 0.0055, th);
    float behind = 1.0 - 0.45 * m2 * step(0.0, sin(sp.x * 2.0 + 1.0));   // it slips behind the cafe now and then
    col += THREAD * (smoothstep(w + gPx, w - gPx * 0.5, d) * (1.2 + 1.2 * th) + exp(-d / (0.01 + 0.03 * th)) * (0.08 + 0.35 * th)) * behind;
    return col;
}

// ------------------------------------------------------------------ mode 1: the run
// running home through the night streets: lamps and windows stream past on both walls,
// their light smeared on the wet stones; at the end of the street, home
vec3 run(vec2 sp) {
    float lt = uLocal;
    vec2 shake = 0.005 * vec2(vnoise(vec2(lt * 13.0, 1.0)) - 0.5, vnoise(vec2(lt * 11.0, 7.0)) - 0.5) * (0.5 + gProg);
    vec2 vp = vec2(0.16, 0.03) + shake;
    vec2 d = sp - vp;
    float r = length(d);
    float th = atan(d.y, d.x);
    float s = log(max(r, 1e-3));
    float S = lt * (1.0 + 0.55 * lt) * 0.7;                 // ever faster
    float L = mix(0.3, 0.95, gProg);                         // streak length in log-radius
    // the street: dark walls either side, a strip of sky, wet stones underfoot
    float up = sat(d.y / max(r, 1e-3));
    vec3 col = vec3(0.012, 0.009, 0.007) + vec3(0.004, 0.006, 0.014) * smoothstep(0.55, 0.9, up);
    col += vec3(0.1, 0.05, 0.02) * exp(-r * 6.0) + vec3(1.0, 0.6, 0.3) * exp(-r / 0.012) * 0.6;   // home, far off
    const float NS = 60.0;
    float dth = TAU / NS;
    for (int band = 0; band < 2; band++) {
        float fb = float(band);
        float ds = 0.48 + 0.22 * fb;
        float spp = s - S * (1.0 + 0.35 * fb);
        for (int k = -1; k <= 1; k++) {
            float sec = floor(th / dth) + float(k);
            float j = floor(spp / ds);
            for (int jj = 0; jj <= 2; jj++) {
                float cj = j + float(jj);
                vec2 h = hash22(vec2(sec, cj) + fb * 17.0);
                float a0 = (sec + 0.15 + 0.7 * h.x) * dth;
                // lamps and windows live on the walls, few in the sky, reflections below
                float sa = sin(a0), ca = cos(a0);
                float onWall = smoothstep(0.62, 0.35, abs(sa));
                float inSky = smoothstep(0.6, 0.9, sa);
                float onStreet = smoothstep(0.55, 0.85, -sa);
                float keep = onWall * 0.75 + onStreet * 0.35 + inSky * 0.05;
                if (h.x > keep) continue;
                float sl = (cj + h.y) * ds;
                float da = mod(th - a0 + PI, TAU) - PI;
                float along = spp - sl;
                if (along > 0.03 || along < -L) continue;
                float w = (0.0016 + 0.0045 * r) * (0.6 + 0.8 * h.y) * (onStreet > 0.5 ? 1.8 : 1.0);
                float across = abs(da) * r;
                float tail = smoothstep(-L, 0.0, along);
                float head = exp(-max(along, 0.0) * 60.0);
                float I = smoothstep(w, 0.0, across) * tail * tail * head * smoothstep(0.03, 0.18, r);
                I += exp(-length(vec2(across, max(along, 0.0) * r)) / (w * 1.4)) * head * 0.4 * smoothstep(0.03, 0.18, r);
                vec3 c = mix(vec3(1.0, 0.52, 0.18), vec3(1.0, 0.8, 0.52), hash11(h.x * 9.0));
                if (hash11(h.y * 13.0) > 0.92) c = vec3(1.0, 0.25, 0.12);
                float lvl = (0.55 + 1.1 * r) * (1.0 - 0.4 * fb) * (onStreet > 0.5 ? 0.35 : 1.0);
                col += c * I * lvl;
            }
        }
    }
    // a heartbeat in the light, the edges closing in
    float ph = fract(lt * 1.7);
    float hb = exp(-pow((ph - 0.05) / 0.04, 2.0)) + 0.6 * exp(-pow((ph - 0.22) / 0.04, 2.0));
    col *= 0.85 + 0.35 * hb;
    col += vec3(1.0, 0.5, 0.2) * 0.05 * hb * exp(-r * 2.0);
    col *= 1.0 - (0.3 + 0.15 * hb) * smoothstep(0.45, 1.0, length(sp * vec2(0.8, 1.25)));
    return col;
}

// ------------------------------------------------------------------ mode 2: the letter
float inkAt(vec2 uv) { return texture(uLetter, uv).r; }

vec3 letter(vec2 sp) {
    // the sheet: the texture's text block sits a little above the centre; the camera pushes in
    float push = 1.0 + 0.12 * smoothstep(0.0, 1.0, gProg);
    vec2 focus = vec2(0.0, 0.03);
    vec2 p = focus + (sp - focus) / push;
    p = rot(0.025) * (p - focus) + focus;
    const float PW = 1.56;                        // paper width on screen at push 1
    const float ASPECT = 760.0 / 1100.0;
    float PH = PW * ASPECT;
    vec2 tc = vec2(0.49, 0.296);                  // text block centre in the texture (from the top)
    vec2 uv = vec2((p.x - focus.x) / PW + tc.x, tc.y - (p.y - focus.y) / PH);   // uv.y from the top
    // the lamp: a warm pool over the writing, falling away into the dark
    vec2 L = sp - vec2(-0.2, 0.22);
    float lamp = 0.06 + 1.0 * exp(-dot(L, L * vec2(0.8, 1.1)) * 1.6);
    // the paper's edge and its shadow on the dark desk
    vec2 e = min(uv, 1.0 - uv);
    float inside = smoothstep(0.0, 0.0012, min(e.x, e.y));
    vec2 su = uv - vec2(-0.006, 0.012);
    vec2 se = min(su, 1.0 - su);
    float shadow = smoothstep(-0.025, 0.01, min(se.x, se.y));
    vec3 desk = vec3(0.022, 0.012, 0.007) * lamp * (0.8 + 0.4 * fbm(sp * vec2(3.0, 40.0))) * (1.0 - 0.7 * shadow);
    if (inside <= 0.0) return desk;
    // paper: warm ivory, fibres, faint laid lines, a gentle cockle, folds in thirds, foxing
    vec2 px = uv * vec2(1100.0, 760.0);
    float fib = fbm(vec2(px.x * 0.06, px.y * 0.018)) * 0.55 + fbm(px * 0.04 + 7.0) * 0.45;
    float laid = 0.5 + 0.5 * sin(px.y * 1.05);
    vec3 paper = vec3(0.9, 0.81, 0.64) * (0.88 + 0.16 * fib) * (0.99 + 0.01 * laid);
    float cockle = fbm(uv * vec2(2.5, 3.5) + 4.0);
    float cx = fbm(uv * vec2(2.5, 3.5) + vec2(4.03, 4.0)) - cockle;
    paper *= 1.0 + 2.2 * cx;                                                       // lit unevenly as it buckles
    float fold1 = uv.y - 1.0 / 3.0, fold2 = uv.y - 2.0 / 3.0;
    paper *= uv.y < 1.0 / 3.0 ? 1.0 : (uv.y < 2.0 / 3.0 ? 0.9 : 0.95);             // the panels tilt differently
    paper *= 1.0 - 0.22 * exp(-abs(fold1) * 1200.0) - 0.18 * exp(-abs(fold2) * 1200.0);
    paper *= 1.0 + 0.07 * exp(-abs(fold1 + 0.0025) * 600.0) + 0.06 * exp(-abs(fold2 + 0.0025) * 600.0);
    float fox = smoothstep(0.68, 0.85, fbm(uv * 8.0 + 3.0)) * smoothstep(0.55, 0.8, vnoise(uv * 36.0));
    paper = mix(paper, paper * vec3(0.82, 0.66, 0.46), fox * 0.4);
    paper *= 1.0 - 0.3 * (1.0 - smoothstep(0.0, 0.035, min(e.x, e.y)));          // handled, darker edges
    // the ink: iron-gall blue-black, pooling at the edges of strokes, uneven with the nib's flow,
    // a faint bleed into the fibres
    vec2 tx = 1.0 / vec2(1100.0, 760.0);
    vec2 tuv = vec2(uv.x, 1.0 - uv.y);
    float c0 = inkAt(tuv);
    float cb = 0.0, cw = 0.0;
    for (int i = 0; i < 8; i++) {
        float a = float(i) * TAU / 8.0;
        vec2 o = vec2(cos(a), sin(a)) * tx;
        cb += inkAt(tuv + o * 1.5);
        cw += inkAt(tuv + o * 3.2);
    }
    cb /= 8.0; cw /= 8.0;
    float lines = uP[1].z > 0.5 ? uP[1].z : 6.0;
    float lineK = floor((px.y - 70.0) / 52.0);
    float f = sat((px.x - 60.0) / 960.0);
    float pos = lineK + f;
    float reveal = uP[1].x * lines;
    float shown = sat((reveal - pos) / 0.12);
    float wet = exp(-max(reveal - pos, 0.0) / 0.35) * shown;
    float flow = 0.7 + 0.45 * vnoise(px * vec2(0.035, 0.07) + 3.0);              // the nib running drier and wetter
    float pool = sat(c0 - cb) * 0.6;                                              // ink gathers at the stroke edges
    float density = sat(c0 * flow + pool) * shown;
    float bleed = sat(cw - c0) * 0.22 * (0.5 + fib) * shown;
    vec3 inkC = mix(vec3(0.05, 0.055, 0.12), vec3(0.02, 0.03, 0.1), wet);
    vec3 col = mix(paper, paper * vec3(0.6, 0.64, 0.78), bleed);
    col = mix(col, inkC, density * 0.94);
    col += vec3(0.3, 0.33, 0.45) * wet * c0 * 0.12;                               // fresh ink still glistens
    col *= lamp * vec3(1.08, 0.97, 0.82);
    return mix(desk, col, inside);
}

// ------------------------------------------------------------------ mode 3: four frames, one confession
vec3 framedScene(vec2 lp, int k) {
    // dark interior with a soft backlight; Elena centred, the same in every frame
    vec3 tint = k == 0 ? SILVER : (k == 1 ? AMBER_RIM : (k == 2 ? GREEN_RIM : STEEL));
    vec2 g = lp - vec2(0.03, 0.1);
    vec3 col = vec3(0.01, 0.007, 0.008) + tint * 0.16 * exp(-dot(g, g * vec2(1.4, 0.7)) * 12.0);
    col += tint * 0.03 * fbm(lp * 6.0 + float(k) * 3.0 - vec2(0.0, gT * 0.05));
    vec2 base = vec2(0.0, -0.3);
    float h = 0.5;
    if (k == 3) {   // the steel-blue shadow looming behind her
        vec4 s = shadowFigure(lp, base + vec2(0.08, 0.0), h * 1.28, 1.0);
        col = over(col, s);
    }
    if (k == 1) col = over(col, figure(lp, base + vec2(0.11, 0.0), h * 1.06, vec4(0.55, 0.1, 0.0, -0.05), 0.0, AMBER, AMBER_RIM, vec2(-0.6, 1.0)));
    if (k == 2) col = over(col, figure(lp, base + vec2(-0.11, 0.0), h * 1.06, vec4(0.1, 0.55, 0.0, 0.05), 0.0, GREEN, GREEN_RIM, vec2(0.6, 1.0)));
    vec2 L = k == 1 ? vec2(0.7, 1.0) : (k == 2 ? vec2(-0.7, 1.0) : vec2(0.0, 1.0));
    vec4 e = figX(lp, base, h, vec4(0.0, 0.0, 0.25, 0.0), 2.0, vec4(-0.2, 0.47, 0.06, 0.62), 0.0, vec2(-1.0, 1.0), CRIMSON, mix(CRIMSON_RIM, tint, 0.25), L);
    col = over(col, e);
    if (k == 0) {   // the child's glow at her breast
        float g = length((lp - base - vec2(0.012, 0.655 * h)) * vec2(0.8, 1.2));
        col += SILVER * (exp(-g / 0.012) * 1.1 + exp(-g / 0.05) * 0.3) * (0.9 + 0.1 * sin(gT * 1.7));
    }
    return col;
}

vec3 confess(vec2 sp) {
    vec3 col = vec3(0.006, 0.004, 0.005);
    float pr = gProg;
    float gather = smoothstep(0.0, 0.85, pr);
    float scale = 1.0 + 0.18 * smoothstep(0.6, 1.0, pr);
    vec2 hs = vec2(0.19, 0.335) * scale;
    vec3 acc = vec3(0.0);
    float cover = 0.0;
    float edgeGlow = 0.0;
    for (int k = 0; k < 4; k++) {
        float fk = float(k);
        float x0 = (fk - 1.5) * 0.44;
        vec2 c = vec2(x0 * (1.0 - gather), 0.0) + vec2(0.0, 0.008 * sin(gT * 0.6 + fk * 1.7)) * (1.0 - gather);
        vec2 lp = (sp - c) / scale;
        float m = panelMask(sp - c, hs, gPx);
        float alpha = mix(1.0, 0.42, gather);
        if (m > 0.0) {
            acc += framedScene(lp, k) * m * alpha;
            cover += m * alpha;
        }
        // the crimson edge: a fine double line that glows
        vec2 dd = abs(sp - c) - hs;
        float sd = length(max(dd, 0.0)) + min(max(dd.x, dd.y), 0.0);
        edgeGlow += smoothstep(0.0025 + gPx, 0.0015, abs(sd)) + 0.6 * smoothstep(0.0015 + gPx, 0.0008, abs(sd + 0.012));
        edgeGlow += exp(-abs(sd) / 0.012) * 0.25;
    }
    col = mix(col, acc / max(cover, 1e-3), sat(cover));
    vec3 crim = vec3(0.95, 0.1, 0.12);
    float merge = smoothstep(0.75, 1.0, pr);
    col += crim * edgeGlow * mix(0.55, 0.32, gather) * (1.0 + 1.5 * merge);
    return col;
}

// ------------------------------------------------------------------ mode 4: the split
// fine cracks as in struck glass: rays from a point, kinking as they run, joined by short chords
float rayAngle(float ki, float rho, float N) {
    float km = mod(ki, N);
    float u = rho * 7.0 + hash11(km);
    float s0 = floor(u);
    float off = mix(hash11(km * 17.0 + s0), hash11(km * 17.0 + s0 + 1.0), fract(u)) - 0.5;
    return (ki + 0.5 * hash11(km * 3.1)) * (TAU / N) + 0.07 * off / (1.0 + rho * 4.0);
}
float glassCracks(vec2 p, vec2 P, float reach) {
    const float N = 13.0;
    vec2 d = p - P;
    float r = length(d);
    float a = atan(d.y, d.x);
    float k0 = floor(a / (TAU / N));
    float best = 1e3;
    for (int i = -1; i <= 1; i++) {
        float ki = k0 + float(i);
        float km = mod(ki, N);
        float ai = rayAngle(ki, r, N);
        float len = reach * (0.45 + 0.55 * hash11(km * 7.7));
        if (cos(a - ai) > 0.0 && r < len) best = min(best, r * abs(sin(a - ai)));
        float lenNext = reach * (0.45 + 0.55 * hash11(mod(ki + 1.0, N) * 7.7));
        for (int j = 1; j <= 3; j++) {
            float fj = float(j);
            if (hash11(km * 11.0 + fj * 3.0) < 0.5) continue;      // not every ring is broken through
            float r1 = reach * (0.1 + 0.17 * fj + 0.05 * hash11(km * 5.0 + fj));
            float r2 = r1 * (0.88 + 0.24 * hash11(km * 9.0 + fj));
            if (r1 > len || r2 > lenNext) continue;
            float a1 = rayAngle(ki, r1, N), a2 = rayAngle(ki + 1.0, r2, N);
            best = min(best, sdSeg(p, P + r1 * vec2(cos(a1), sin(a1)), P + r2 * vec2(cos(a2), sin(a2))));
        }
    }
    return best;
}

vec3 split(vec2 sp) {
    float I = gA;                                   // intensity
    float hb = pow(sat(gB), 3.0);                   // heartbeat, sharpened into a thump
    float open = smoothstep(0.0, 0.2, gProg);
    // the diagonal: steep, through the centre, opening as the shot begins
    vec2 n = normalize(vec2(1.0, -0.42));
    float sd = dot(sp, n);
    float gap = 0.004 * open * (1.0 + hb);
    float right = smoothstep(-gPx, gPx, sd - gap) * open;
    float left = smoothstep(gPx, -gPx, sd + gap) + (1.0 - open) * smoothstep(-gPx, gPx, sd - gap);
    // Davide grieving: head bowed, one hand pressed to his brow, the other arm hanging
    vec4 pose = vec4(0.0, 0.0, 0.0, 0.035);
    vec4 hands = vec4(-0.15, 0.45, 0.03, 0.835);
    vec2 sg = vec2(-1.0, -1.0);                     // left elbow down at his side, right elbow lifted out
    float h = 0.66;
    vec2 posL = vec2(-0.42, -0.42), posR = vec2(0.44, -0.42);
    vec3 col = vec3(0.0);
    if (left > 0.0) {
        // amber light behind him, warm dust in the air
        vec2 g = sp - posL - vec2(0.06, 0.5);
        vec3 c = vec3(0.035, 0.016, 0.006) + vec3(0.55, 0.28, 0.08) * 0.42 * exp(-dot(g, g * vec2(1.0, 0.6)) * 4.0);
        c += vec3(0.5, 0.25, 0.07) * 0.06 * beam(sp, posL + vec2(-0.5, 1.0), vec2(0.45, -1.0), 0.3, 2.0);
        c *= 1.0 + 0.3 * hb;
        vec4 d = figX(sp, posL, h, pose, 0.0, hands, 1.0, sg, AMBER * 0.75, AMBER_RIM, vec2(0.3, 1.0));
        c = over(c, d);
        c += AMBER_RIM * 0.05 * dust(sp, gT, 0.08, 0.05);
        col += c * left;
    }
    if (right > 0.0) {
        // the same man through her fear: cold light, Vittorio's shadow rising behind him
        vec2 g = sp - posR - vec2(0.12, 0.6);
        vec3 c = vec3(0.006, 0.01, 0.022) + STEEL * 0.32 * exp(-dot(g, g * vec2(1.0, 0.5)) * 2.6);
        c += STEEL * 0.05 * fbm(sp * 4.0 + vec2(0.0, -gT * 0.08));
        vec4 s = shadowFigure(sp, posR + vec2(0.12, -0.05), h * (1.45 + 0.05 * hb), 0.5 + 0.5 * I);
        c = over(c, s);
        vec4 d = figX(sp, posR, h, pose, 0.0, hands, 1.0, sg, vec3(0.018, 0.026, 0.05), STEEL * 0.85, vec2(-0.3, 1.0));
        c = over(c, d);
        // fine cracks, spreading with the intensity
        float cr = glassCracks(sp, vec2(0.62, 0.22), 0.25 + 0.9 * I);
        float crack = smoothstep(gPx * 1.2, 0.0, cr) * (0.35 + 0.65 * I);
        float sparkle = 0.5 + 0.5 * vnoise(sp * 60.0);
        c = mix(c, c * 0.3, smoothstep(gPx * 3.0, 0.0, cr) * 0.4 * I);
        c += vec3(0.75, 0.88, 1.0) * crack * 0.2 * sparkle * (1.0 + 0.8 * hb);
        c += vec3(0.75, 0.88, 1.0) * exp(-cr / 0.006) * 0.02 * I;
        c *= 1.0 + 0.25 * hb;
        col += c * right;
    }
    // the seam itself
    float seam = exp(-abs(sd) / (0.0025 + 0.004 * hb)) * open;
    col += mix(AMBER_RIM, STEEL, smoothstep(-0.02, 0.02, sd)) * seam * (0.35 + 0.65 * hb) * (0.5 + 0.5 * I);
    return col;
}

// ------------------------------------------------------------------ mode 5: Marco withdraws
vec3 withdraw(vec2 sp) {
    float a = gA;
    vec3 col = vec3(0.005, 0.007, 0.008);
    // the line holds from the right edge to a left end that slides away to the right
    float xl = mix(-0.95, 0.98, pow(a, 0.85));
    float y = 0.0 + 0.015 * sin(sp.x * 4.0 + gT * 0.8) * (1.0 - a * 0.5) + 0.006 * sin(sp.x * 11.0 - gT * 1.6);
    float d = abs(sp.y - y);
    float on = smoothstep(xl - 0.01, xl + 0.03, sp.x);
    float w = mix(0.0035, 0.0012, a);
    float lvl = 1.0 - 0.55 * a;
    col += THREAD * (smoothstep(w + gPx, w - gPx * 0.5, d) * 1.6 + exp(-d / 0.02) * 0.25 + exp(-d / 0.12) * 0.03) * on * lvl;
    float dr = abs(sp.y + 0.16 - (y - 0.0) * -0.4);                    // a dim, wavering reflection below
    col += THREAD * exp(-dr / 0.006) * 0.1 * on * lvl * (0.6 + 0.4 * sin(sp.x * 60.0 + gT * 2.0));
    // the retreating end glows; behind it, a faint wake and a few motes left in the dark
    vec2 tip = vec2(xl, 0.015 * sin(xl * 4.0 + gT * 0.8) * (1.0 - a * 0.5) + 0.006 * sin(xl * 11.0 - gT * 1.6));
    float dt = length(sp - tip);
    col += THREAD * (exp(-dt / 0.006) * 1.6 + exp(-dt / 0.05) * 0.2) * lvl * step(a, 0.995);
    float wake = exp(-d / 0.006) * smoothstep(xl, xl - 0.6, sp.x) * smoothstep(xl - 0.8, xl, sp.x) * 0.25 * (1.0 - a);
    col += THREAD * wake;
    for (int i = 0; i < 14; i++) {
        float fi = float(i);
        float bx = -0.9 + fi * 0.13 + 0.05 * hash11(fi);
        float age = a * 1.9 - (bx + 0.95) / 1.93 * 1.7;
        if (age <= 0.0) continue;
        vec2 mp = vec2(bx + 0.02 * sin(age * 5.0 + fi), 0.006 * sin(bx * 4.0) + age * 0.06 * (hash11(fi * 3.0) - 0.3));
        float dm = length(sp - mp);
        col += THREAD * exp(-dm / 0.0025) * exp(-age * 2.5) * 0.8;
    }
    return col;
}

// ------------------------------------------------------------------ mode 6: the blow
// the moulding's height across the border (t: 0 outer edge -> 1 sight edge) and along it
float mouldH(float t, float along) {
    float bead = sqrt(max(0.0, 1.0 - pow((t - 0.07) / 0.07, 2.0)));                 // outer bead
    float cove = 0.55 - 0.45 * sqrt(max(0.0, 1.0 - pow((t - 0.24) / 0.1, 2.0)));    // hollow
    float eg = length(vec2((fract(along / 0.028) - 0.5) * 0.028 / 0.0105, (t - 0.5) / 0.13));
    float eggs = sqrt(max(0.0, 1.0 - eg * eg)) * 0.8 + 0.25;                          // egg-and-dart
    float pearl = length(vec2((fract(along / 0.011) - 0.5) * 0.011 / 0.0045, (t - 0.76) / 0.04));
    float pearls = sqrt(max(0.0, 1.0 - pearl * pearl)) * 0.55 + 0.2;
    float h = t < 0.14 ? bead : (t < 0.36 ? cove : (t < 0.66 ? eggs : (t < 0.84 ? pearls : 0.12)));
    return h;
}

// the gilded frame and the portrait it holds, in the frame's own coordinates
vec3 gildedPicture(vec2 q, float lit, out float mask) {
    const vec2 OUTER = vec2(0.44, 0.32), INNER = vec2(0.345, 0.225);
    vec2 dO = abs(q) - OUTER, dI = abs(q) - INNER;
    float so = length(max(dO, 0.0)) + min(max(dO.x, dO.y), 0.0);
    float si = length(max(dI, 0.0)) + min(max(dI.x, dI.y), 0.0);
    mask = smoothstep(gPx, -gPx, so);
    vec3 col;
    if (si > 0.0) {
        // which side of the frame (mitred at the corners), the position along it, the depth across it
        bool side = (abs(q.x) - OUTER.x) > (abs(q.y) - OUTER.y);
        vec2 outN = side ? vec2(sign(q.x), 0.0) : vec2(0.0, sign(q.y));
        float along = side ? q.y : q.x;
        float t = sat(-so / (OUTER.x - INNER.x));
        float e = 0.004;
        float h0 = mouldH(t, along);
        float ht = (mouldH(t + e, along) - mouldH(t - e, along)) / (2.0 * e);
        float ha = (mouldH(t, along + 0.002) - mouldH(t, along - 0.002)) / 0.004 * 0.004;
        vec2 slope = outN * ht * 0.09 + (side ? vec2(0.0, 1.0) : vec2(1.0, 0.0)) * ha * 1.5;
        vec3 n = normalize(vec3(slope, 1.0));
        vec3 L = normalize(vec3(-0.55, 0.65, 0.55));
        float diff = sat(dot(n, L));
        float spec = pow(sat(dot(reflect(-L, n), vec3(0.0, 0.0, 1.0))), 22.0);
        vec3 gold = vec3(0.72, 0.5, 0.2) * (0.25 + 0.9 * diff) * (0.55 + 0.45 * h0);
        gold += vec3(1.0, 0.86, 0.55) * spec * 1.1;
        gold *= 0.82 + 0.3 * fbm(q * 70.0);                          // worn gilding
        gold = mix(gold, vec3(0.12, 0.07, 0.03), smoothstep(0.86, 0.9, t) * 0.7);   // dark slip at the sight edge
        col = gold;
    } else {
        // the wedding portrait behind glass: dark, the couple faint, a streak of reflection
        vec3 c = vec3(0.04, 0.03, 0.025) * (0.8 + 0.4 * fbm(q * 9.0));
        c += vec3(0.25, 0.16, 0.08) * 0.25 * exp(-dot(q - vec2(0.0, 0.08), q - vec2(0.0, 0.08)) * 18.0);
        vec4 e = figure(q, vec2(-0.05, -0.2), 0.36, vec4(0.1, 0.35, 0.32, 0.0), 2.0, CRIMSON * 0.6, CRIMSON_RIM * 0.6, vec2(0.3, 1.0));
        vec4 v = figure(q, vec2(0.06, -0.2), 0.39, vec4(0.35, 0.1, 0.0, 0.0), 0.0, vec3(0.03), vec3(1.0, 0.8, 0.4) * 0.6, vec2(-0.3, 1.0));
        c = over(c, v);
        c = over(c, e);
        float refl = exp(-pow((q.x + q.y * 0.8 + 0.1) / 0.05, 2.0)) * 0.07 + exp(-pow((q.x + q.y * 0.8 - 0.05) / 0.012, 2.0)) * 0.04;
        col = c + vec3(0.9, 0.85, 0.75) * refl;
        col *= 1.0 - 0.5 * smoothstep(0.012, 0.0, -si);              // the rebate's shadow on the picture
    }
    return col * lit;
}

// radial fracture about the point of the blow: shards are sectors cut by rings
const vec2 BLOW_P = vec2(0.16, -0.08);
const float NSEC = 11.0;
const float SECW = 0.5711987;     // TAU / NSEC
float secB(float i, float r) {    // angle of the crack between sector i-1 and sector i
    float ii = mod(i, NSEC);
    return (i + 0.38 * (hash11(ii * 3.7 + 1.0) - 0.5)) * SECW + 0.045 * sin(r * 13.0 + ii * 1.7);
}
float ringB(float i, float j) {   // inner radius of ring j in sector i
    if (j <= 0.0) return 0.0;
    float ii = mod(i, NSEC);
    return 0.04 * j * (1.0 + 0.4 * j) * (0.85 + 0.3 * hash11(ii * 7.1 + j * 1.31));
}
vec2 shardOf(vec2 q, out float edge) {
    vec2 d = q - BLOW_P;
    float r = length(d);
    float a = atan(d.y, d.x);
    float i0 = floor(a / SECW);
    float si = i0;
    for (int k = -1; k <= 1; k++) {
        float i = i0 + float(k);
        if (a >= secB(i, r) && a < secB(i + 1.0, r)) si = i;
    }
    float je = floor((-0.04 + sqrt(0.0016 + 0.064 * r)) / 0.032);
    float sj = max(je, 0.0);
    for (int k = -1; k <= 1; k++) {
        float j = max(je + float(k), 0.0);
        if (r >= ringB(si, j) && r < ringB(si, j + 1.0)) sj = j;
    }
    edge = min(min(r * abs(sin(a - secB(si, r))), r * abs(sin(secB(si + 1.0, r) - a))),
               min(sj > 0.0 ? abs(r - ringB(si, sj)) : 1e3, abs(ringB(si, sj + 1.0) - r)));
    return vec2(mod(si, NSEC), sj);
}

vec3 blow(vec2 sp) {
    float a = gA;
    float lit = smoothstep(0.0, 0.1, a) * (0.9 + 0.1 * sin(gT * 3.0));
    float crackR = smoothstep(0.1, 0.34, a) * 0.95;          // how far the cracks have run
    float sep = smoothstep(0.3, 1.0, a);                     // the pieces drifting apart
    vec3 col = vec3(0.0);
    float e0;
    vec2 own = shardOf(sp, e0);
    // find the piece that now covers this pixel: its own, or one moving out from nearer the blow
    for (int dj = 0; dj <= 1; dj++) for (int di = -1; di <= 1; di++) {
        float ci = own.x + float(di);
        float cj = own.y - float(dj);
        if (cj < 0.0) continue;
        float rm = 0.5 * (ringB(ci, cj) + ringB(ci, cj + 1.0));
        float am = 0.5 * (secB(ci, rm) + secB(ci + 1.0, rm));
        vec2 dir = vec2(cos(am), sin(am));
        vec2 pivot = BLOW_P + dir * rm;
        float cracked = smoothstep(crackR, crackR - 0.12, rm);
        float hsh = hash11(mod(ci, NSEC) * 13.7 + cj * 3.1);
        float k = sep * cracked;
        vec2 D = dir * k * (0.025 + 0.04 * hsh) * (1.0 + 0.6 / (1.0 + cj)) + vec2(0.0, -0.035 * k * k);
        float th = (hsh - 0.5) * k * 0.55;
        vec2 q = pivot + rot(-th) * (sp - pivot - D);
        float eq;
        vec2 s = shardOf(q, eq);
        if (abs(s.x - mod(ci, NSEC)) > 0.5 || abs(s.y - cj) > 0.5) continue;
        float m;
        vec3 pc = gildedPicture(q, lit, m);
        if (m <= 0.0) continue;
        // a turning piece catches the light; its broken edges glint
        pc *= 1.0 + th * 1.2;
        float crackLine = smoothstep(0.0035, 0.0, eq) * smoothstep(crackR, crackR - 0.06, length(q - BLOW_P));
        pc = mix(pc, pc * 0.15, crackLine * (1.0 - sep));
        pc += vec3(1.0, 0.88, 0.6) * smoothstep(0.004, 0.0, eq) * cracked * (0.15 + 0.6 * sep) * lit * 0.5;
        float glint = pow(sat(sin(th * 18.0 + hsh * 6.0 + gT * 0.7)), 12.0) * k;
        pc += vec3(1.0, 0.9, 0.7) * glint * 0.25 * lit;
        col = pc * m;
        break;
    }
    // the moment of the blow: a brief flash where it lands
    float flash = exp(-pow((a - 0.13) / 0.03, 2.0));
    col += vec3(1.0, 0.9, 0.7) * flash * exp(-length(sp - BLOW_P) / 0.07) * 1.5;
    // splinters of glass and gilt hanging in the air, drifting
    for (int i = 0; i < 28; i++) {
        float fi = float(i);
        vec2 h = hash22(vec2(fi, 3.0)) - 0.5;
        vec2 dp = BLOW_P + normalize(h + 1e-3) * (0.03 + 0.45 * sep * (0.25 + hash11(fi * 4.0))) + vec2(0.0, -0.08 * sep * sep);
        float dd = length(sp - dp);
        float tw = 0.5 + 0.5 * sin(gT * (4.0 + 6.0 * hash11(fi)) + fi);
        col += mix(vec3(1.0, 0.8, 0.45), vec3(0.85, 0.9, 1.0), step(0.6, hash11(fi * 2.0))) * exp(-dd / 0.0018) * sep * tw * 1.6;
    }
    return col;
}

// ------------------------------------------------------------------ mode 7: the end
vec3 ending(vec2 sp) {
    vec3 col = vec3(0.004, 0.003, 0.0025);
    float breath = 0.9 + 0.1 * sin(gT * 0.5);
    vec2 d = sp - vec2(0.0, -0.06);
    col += vec3(1.0, 0.62, 0.3) * 0.035 * exp(-dot(d * vec2(0.7, 1.2), d * vec2(0.7, 1.2)) * 3.0) * breath;
    col += vec3(1.0, 0.7, 0.4) * dust(sp, gT * 0.5, 0.03, 0.05) * 0.05;
    return col;
}

void main() {
    gSp = screen();
    gT = uTime;
    gPx = 1.5 * PIXEL;
    int mode = int(uP[0].x + 0.5);
    gProg = sat(uP[0].y);
    gA = sat(uP[1].x);
    gB = sat(uP[1].y);
    vec3 col;
    if (mode == 0) col = drift(gSp);
    else if (mode == 1) col = run(gSp);
    else if (mode == 2) col = letter(gSp);
    else if (mode == 3) col = confess(gSp);
    else if (mode == 4) col = split(gSp);
    else if (mode == 5) col = withdraw(gSp);
    else if (mode == 6) col = blow(gSp);
    else col = ending(gSp);
    fragColor = vec4(max(col, 0.0), 1.0);
}
