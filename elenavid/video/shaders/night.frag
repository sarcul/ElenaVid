#version 430
// ---------------------------------------------------------------------------------------------
// night.frag  -  THE STATION AND THE MAP (Act II, scene 1).
//   mode 0  A railway platform at night, 1953: cast-iron columns and arched brackets under the
//           canopy, gas lamps in their halos, lit steam drifting, a dark train with lit windows.
//           Elena with a suitcase and Tommaso's glow in her arms. The train can depart: it slides
//           left, accelerating, its windows smearing into streaks, until the tail lamp has gone.
//   mode 1  A deep-blue paper map of the northern Adriatic (the Venetian lagoon, the Gulf of
//           Trieste, Istria, the Kvarner islands); a crimson route is drawn from Verona through
//           Venice to Trieste with a travelling point of light.
// uP[0]  x mode   y train departure 0..1   z steam density 0..1
// uP[1]  Elena (x, feet y, height, alpha)
// uP[2]  x route progress 0..1   y map zoom (1 = whole map; 0 is treated as 1)
// Map anchors (screen, zoom 1): Verona (-0.5702, 0.0232), Venice (-0.0868, 0.0044),
// Trieste (0.4370, 0.0924): a conformal fit of the real geography to the requested positions.
// World units on the platform: Elena's plane is depth ~1; a layer at depth z is scaled by 1/z about
// the eye, the platform surface lying EYE below it.
// ---------------------------------------------------------------------------------------------
#include common

const float EYE = 0.47;
const float Z_COL = 1.38;      // columns, beam and lamps
const float Z_EDGE = 1.62;     // platform edge
const float Z_TRAIN = 2.1;
const float RAIL = -0.637;     // rail level (world, below the eye)
const vec3 SILVER = vec3(0.86, 0.9, 1.0);
const vec3 GAS = vec3(1.0, 0.72, 0.42);

float gT, gPx, gCamX, gDep, gSteam, gShift, gBlur;
vec2 gSp;

vec2 lay(float z) { return (gSp + vec2(gCamX / z, 0.0)) * z; }
vec2 toScreen(vec2 w, float z) { return w / z - vec2(gCamX / z, 0.0); }

// ------------------------------------------------------------------ silhouettes with arms by IK
// a two-bone arm from shoulder s to hand target t (figure units); sg chooses the elbow side
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
// the body of sdFigure (common.glsl) without its arms
float sdTorso(vec2 p, vec4 pose, float hair) {
    p.x -= p.y * pose.w;
    float d = sdCircle(p - vec2(0.0, 0.905), 0.062);
    if (hair > 0.5) d = min(d, sdCircle(p - vec2(0.012, 0.935), 0.06));
    if (hair > 1.5) d = min(d, sdCircle(p - vec2(-0.03, 0.965), 0.035));
    d = smin(d, sdCapsule(p, vec2(0.0, 0.85), vec2(0.0, 0.79), 0.026), 0.02);
    d = smin(d, sdTrap(p - vec2(0.0, 0.64), 0.075, 0.115, 0.15), 0.03);
    if (pose.z > 0.0) d = smin(d, sdTrap(p - vec2(0.0, 0.26), 0.13 + 0.17 * pose.z, 0.075, 0.25), 0.02);
    else {
        d = smin(d, sdTrap(p - vec2(0.0, 0.47), 0.085, 0.09, 0.03), 0.02);
        d = min(d, sdCapsule(p, vec2(-0.045, 0.46), vec2(-0.05, 0.02), 0.034));
        d = min(d, sdCapsule(p, vec2(0.045, 0.46), vec2(0.05, 0.02), 0.034));
    }
    return d;
}
// figure()'s shading, for a silhouette distance d (screen units) and outward normal n
vec4 shadeSil(float d, vec2 n, vec2 q, float h, vec3 body, vec3 rim, vec2 L) {
    float px = 1.5 * PIXEL;
    float a = aa(d, px);
    float facing = sat(dot(n, normalize(L)) * 0.8 + 0.2);
    float band = exp(-max(-d, 0.0) / (0.006 * h + 0.002)) * a;
    vec3 c = body * (0.85 + 0.15 * fbm(q * 18.0)) + rim * band * facing * 1.6;
    float halo = glow(d, 0.01 * h) * (1.0 - a) * 0.35 * facing;
    return vec4(c * a + rim * halo, max(a, halo * 0.5));
}

// Elena travelling: a coat, the suitcase in her left hand, Tommaso cradled in her right arm
const vec4 E_POSE = vec4(0.0, 0.0, 0.16, 0.0);
const vec2 E_CASE_HAND = vec2(-0.235, 0.455);
const vec2 E_CRADLE_HAND = vec2(-0.07, 0.6);
float sdElenaBody(vec2 q) {
    float d = sdTorso(q, E_POSE, 2.0);
    return min(d, sdArm(q, vec2(-0.11, 0.765), E_CASE_HAND, -1.0));
}
float sdCradleArm(vec2 q) { return sdArm(q, vec2(0.11, 0.765), E_CRADLE_HAND, 1.0); }
float sdCase(vec2 q) {
    vec2 c = q - vec2(-0.235, 0.33);
    float box = sdRBox(c, vec2(0.15, 0.1), 0.012);
    float handle = abs(sdRBox(q - vec2(-0.235, 0.445), vec2(0.035, 0.016), 0.012)) - 0.006;
    return min(box, max(handle, -(q.y - 0.432)));
}

vec4 elena(vec2 p, vec4 E, vec2 L, out float glowAmt) {
    glowAmt = 0.0;
    vec2 q = (p - E.xy) / E.z;
    if (q.x < -0.55 || q.x > 0.45 || q.y < -0.06 || q.y > 1.1) return vec4(0.0);
    float h = E.z;
    vec2 e = vec2(0.002 / h, 0.0);
    vec3 body = vec3(0.45, 0.03, 0.06), rim = vec3(1.0, 0.45, 0.35);
    // Tommaso: a pale silver-white glow held at her breast
    vec2 bq = rot(-0.35) * (q - vec2(0.015, 0.655));
    float bundle = length(bq / vec2(0.085, 0.05)) - 1.0;
    float head = length(q - vec2(0.085, 0.69)) - 0.032;
    float tb = min(bundle * 0.05, head);
    float breath = 0.9 + 0.1 * sin(gT * 1.7);
    glowAmt = exp(-max(tb, 0.0) / 0.05) * breath;
    // the suitcase, behind her hand
    float dc = sdCase(q) * h;
    vec2 nc = normalize(vec2(sdCase(q + e.xy) - sdCase(q - e.xy), sdCase(q + e.yx) - sdCase(q - e.yx)) + 1e-6);
    vec4 cs = shadeSil(dc, nc, q, h, vec3(0.13, 0.07, 0.035), vec3(1.0, 0.65, 0.35) * 0.8, L);
    float strap = smoothstep(0.006, 0.0, abs(abs(q.x + 0.235) - 0.08)) * step(sdCase(q), 0.0) * step(q.y, 0.42);
    cs.rgb += vec3(0.3, 0.18, 0.08) * strap * 0.4 * cs.a;
    // her body (with the suitcase arm), lit a little by the child at her breast
    float d = sdElenaBody(q) * h;
    vec2 n = normalize(vec2(sdElenaBody(q + e.xy) - sdElenaBody(q - e.xy),
                            sdElenaBody(q + e.yx) - sdElenaBody(q - e.yx)) + 1e-6);
    vec3 lit = body + SILVER * 0.35 * exp(-length(q - vec2(0.02, 0.66)) / 0.09) * breath;
    vec4 bd = shadeSil(d, n, q, h, lit, rim, L);
    // the cradling arm passes in front of her body and under the child
    float da = sdCradleArm(q) * h;
    vec2 na = normalize(vec2(sdCradleArm(q + e.xy) - sdCradleArm(q - e.xy),
                             sdCradleArm(q + e.yx) - sdCradleArm(q - e.yx)) + 1e-6);
    vec4 ar = shadeSil(da, na, q, h, lit * 0.92, rim, normalize(L + vec2(-0.6, 0.0)));
    vec4 c = cs;
    c = vec4(c.rgb * (1.0 - bd.a) + bd.rgb, c.a + bd.a * (1.0 - c.a));
    c = vec4(c.rgb * (1.0 - ar.a) + ar.rgb, c.a + ar.a * (1.0 - c.a));
    // the child in the crook of her arm: a soft pale light, brightest at its heart
    float core = smoothstep(0.012, -0.03, tb) * breath;
    float heart = exp(-length(q - vec2(0.03, 0.665)) / 0.035);
    c.rgb += SILVER * (core * 0.55 + heart * 0.6 + glowAmt * 0.22);
    c.a = max(c.a, core * 0.8);
    return c;
}

// ------------------------------------------------------------------ the station
// the lamps hang midway between the columns (columns every 1.1 world units)
float lampX(float x) { return floor((x - 0.55) / 1.1 + 0.5) * 1.1 + 0.55; }   // the nearest lamp

// screen-space light from the gas lamps (for haze and steam)
float lampLight(vec2 sp) {
    float acc = 0.0;
    vec2 q = lay(Z_COL);
    float k = floor((q.x - 0.55) / 1.1 + 0.5);
    for (int i = -1; i <= 1; i++) {
        float lx = (k + float(i)) * 1.1 + 0.55;
        vec2 ls = toScreen(vec2(lx, 0.33), Z_COL);
        float r = length((sp - ls) * vec2(1.0, 1.1));
        acc += exp(-r / 0.07) * 0.6 + exp(-r / 0.25) * 0.4;
    }
    // the far side's lamps
    vec2 fq = lay(4.2);
    float fk = floor(fq.x / 1.4 + 0.5);
    for (int i = -1; i <= 1; i++) {
        vec2 ls = toScreen(vec2((fk + float(i)) * 1.4, 0.3), 4.2);
        acc += exp(-length(sp - ls) / 0.05) * 0.25;
    }
    return acc;
}

vec3 farSide(vec2 sp) {
    // night beyond the shed: blue-black, a glow from the city, the far platform's lamps and roof
    vec3 col = mix(vec3(0.006, 0.009, 0.02), vec3(0.025, 0.03, 0.055), smoothstep(0.5, -0.1, sp.y));
    vec2 q = lay(4.2);
    float px = gPx * 4.2;
    // far canopy: a band of roof with its own columns
    float roof = sdBox(q - vec2(0.0, 0.95), vec2(50.0, 0.12));
    float cols = abs(mod(q.x + 0.7, 1.4) - 0.7) - 0.03;
    cols = max(cols, -(q.y + 0.47 - 0.0));
    float far = min(roof, max(cols, q.y - 0.9));
    col = mix(col, vec3(0.012, 0.014, 0.022), smoothstep(px, -px, far));
    float fk = floor(q.x / 1.4 + 0.5);
    vec2 lq = q - vec2(fk * 1.4, 0.3);
    col += GAS * (exp(-length(lq) / 0.012) * 2.5 + exp(-length(lq) / 0.12) * 0.12);
    // the far platform edge and an empty track, seen when the train has gone
    vec2 tq = lay(3.0);
    col += vec3(0.6, 0.55, 0.5) * 0.04 * smoothstep(0.006, 0.0, abs(tq.y - (RAIL + 0.01)));
    col += vec3(0.6, 0.55, 0.5) * 0.05 * smoothstep(0.008, 0.0, abs(tq.y + 0.47));
    col = mix(col, vec3(0.02, 0.022, 0.03), smoothstep(-0.47 + px, -0.47 - px, tq.y) * 0.8);
    return col;
}

// a carriage seen side on; q in train coordinates (world at depth Z_TRAIN, x along the train)
const float CAR_L = 6.0, GAP = 0.18;
const float TRAIN_REAR = 4.4;      // x of the rear buffer at rest
const float WIN_P = 0.47, WIN_W = 0.17, WIN_Y = 0.17, WIN_H = 0.13, WIN_0 = 0.55;

// the reflection of a platform lamp on the varnished side of the carriage (screen x)
float sheenAt(float sx) {
    float acc = 0.0;
    float k = floor((sx * 2.82 - 0.55) / 1.1 + 0.5);
    for (int i = -1; i <= 1; i++) {
        float rx = ((k + float(i)) * 1.1 + 0.55) / 2.82;
        acc += exp(-pow((sx - rx) / 0.05, 2.0));
    }
    return acc;
}

vec3 compartment(vec2 wq, float hw, float lit) {
    // warm light inside: the back wall, seat backs, a ceiling lamp, perhaps a traveller
    vec3 wc = mix(vec3(1.0, 0.56, 0.24), vec3(1.0, 0.7, 0.42), hash11(hw * 7.0)) * (0.65 + 0.45 * hash11(hw * 2.0)) * lit;
    wc *= 0.8 + 0.25 * smoothstep(-0.13, 0.13, wq.y);
    wc += vec3(1.0, 0.8, 0.55) * exp(-length((wq - vec2(0.0, 0.11)) * vec2(1.0, 2.5)) / 0.02) * 1.5 * lit;
    float seat = sdRBox(wq - vec2(0.0, -0.12), vec2(0.15, 0.04), 0.02);
    wc *= 1.0 - 0.35 * smoothstep(0.004, -0.004, seat);
    float v = hash11(hw * 3.1);
    float sil = 1e3;
    if (v > 0.35) {                                            // a traveller, in profile or turned away
        float x0 = (hash11(hw * 5.7) - 0.5) * 0.14;
        float face = hash11(hw * 9.1) > 0.5 ? 1.0 : -1.0;
        vec2 hq = wq - vec2(x0, -0.015);
        float head = sdEllipse(hq, vec2(0.033, 0.04));
        head = min(head, sdCircle(hq - vec2(0.03 * face, -0.006), 0.012));      // nose and brow
        float shoulders = sdEllipse(wq - vec2(x0 - 0.01 * face, -0.12), vec2(0.075, 0.06));
        sil = min(head, smin(shoulders, sdBox(hq - vec2(0.0, -0.05), vec2(0.015, 0.03)), 0.02));
        if (hash11(hw * 4.3) > 0.6)                            // a hat
            sil = min(sil, min(sdBox(hq - vec2(0.0, 0.03), vec2(0.048, 0.004)), sdRBox(hq - vec2(0.0, 0.041), vec2(0.028, 0.012), 0.008)));
        if (v > 0.85) {                                        // a second traveller, reading
            vec2 h2 = wq - vec2(-x0 * 0.8 + 0.06, -0.03);
            sil = min(sil, min(sdCircle(h2, 0.03), sdEllipse(wq - vec2(-x0 * 0.8 + 0.06, -0.13), vec2(0.06, 0.055))));
            sil = min(sil, sdBox(rot(0.2) * (wq - vec2(-x0 * 0.8 + 0.02, -0.07)), vec2(0.035, 0.03)));
        }
    }
    wc = mix(wc, wc * 0.18, smoothstep(0.004, -0.004, sil));
    // curtains gathered at the sides, a blind half drawn on some
    float curtain = smoothstep(0.1, 0.135, abs(wq.x)) * (0.6 + 0.4 * sin(wq.x * 160.0));
    wc *= 1.0 - 0.6 * curtain;
    if (hash11(hw * 6.6) > 0.7) wc *= mix(1.0, 0.35, smoothstep(0.05, 0.04, -wq.y + 0.1 * hash11(hw)) * step(0.0, wq.y));
    return wc;
}

vec4 carriage(vec2 q, out float winLight) {
    winLight = 0.0;
    if (q.x > TRAIN_REAR) return vec4(0.0);
    float body = sdRBox(q - vec2(0.0, 0.11), vec2(1e3, 0.43), 0.02);
    float roof = sdEllipse(q - vec2(0.0, 0.52), vec2(1e3, 0.06));
    float cx = mod(q.x - TRAIN_REAR, CAR_L);       // position within a carriage from its rear
    float ci = floor((q.x - TRAIN_REAR) / CAR_L);
    float gapD = min(cx, CAR_L - cx) - GAP * 0.5;  // the gangway between carriages
    float d = min(body, roof);
    float inGap = smoothstep(0.004, -0.004, gapD);
    float local = cx - WIN_0;
    float wi = floor(local / WIN_P);
    float wx = local - (wi + 0.5) * WIN_P;
    float win = sdRBox(vec2(wx, q.y - WIN_Y), vec2(WIN_W, WIN_H), 0.03);
    win = max(win, max(-local, local - 4.7));
    float dxe = min(cx - 0.3, CAR_L - 0.3 - cx);
    float door = sdRBox(vec2(dxe, q.y - 0.12), vec2(0.07, 0.24), 0.02);
    float dwin = sdRBox(vec2(dxe, q.y - 0.23), vec2(0.045, 0.08), 0.015);
    // livery: dark chestnut, varnished, with the lamps reflected along it
    float sx = q.x / Z_TRAIN;
    vec3 c = vec3(0.034, 0.02, 0.016) * (0.8 + 0.4 * vnoise(q * vec2(4.0, 30.0)));
    c *= 0.85 + 0.3 * smoothstep(0.5, -0.3, q.y);
    c += GAS * 0.07 * smoothstep(0.012, 0.0, abs(q.y + 0.02)) + GAS * 0.08 * smoothstep(0.02, 0.0, abs(q.y - 0.5));
    c += GAS * 0.05 * smoothstep(0.006, 0.0, abs(q.y - 0.36));
    float panel = smoothstep(0.006, 0.0, abs(abs(wx) - WIN_P * 0.5)) * step(abs(q.y - 0.17), 0.3) * step(0.0, local) * step(local, 4.7);
    c += GAS * 0.025 * panel;
    c += GAS * 0.06 * smoothstep(0.005, 0.0, abs(door));
    c += GAS * 0.09 * sheenAt(sx - gShift / Z_TRAIN) * smoothstep(-0.35, 0.45, q.y) * (1.0 - 0.6 * gDep);
    float hw = hash11(ci * 13.0 + wi * 1.7);
    float lit = step(0.1, hw);
    vec3 wc = compartment(vec2(wx, q.y - WIN_Y), hw, lit);
    float inWin = smoothstep(0.004, -0.004, win);
    float inDoor = smoothstep(0.004, -0.004, dwin);
    c = mix(c, wc, inWin);
    c = mix(c, vec3(1.0, 0.6, 0.3) * 0.5, inDoor);
    winLight = inWin * lum(wc) + inDoor * 0.3;
    c = mix(c, vec3(0.045, 0.03, 0.02) + GAS * 0.08, smoothstep(0.01, 0.0, abs(win)) * 0.7);
    // the underframe and bogies below the body
    float under = sdBox(q - vec2(0.0, -0.39), vec2(1e3, 0.06));
    vec2 bq = vec2(cx - 0.9, q.y - (RAIL + 0.1));
    vec2 bq2 = vec2(CAR_L - cx - 0.9, q.y - (RAIL + 0.1));
    float bog = min(sdBox(bq, vec2(0.4, 0.07)), sdBox(bq2, vec2(0.4, 0.07)));
    float wheels = min(min(sdCircle(bq - vec2(-0.22, -0.02), 0.08), sdCircle(bq - vec2(0.22, -0.02), 0.08)),
                       min(sdCircle(bq2 - vec2(-0.22, -0.02), 0.08), sdCircle(bq2 - vec2(0.22, -0.02), 0.08)));
    float dU = min(under, min(bog, wheels));
    float aBody = smoothstep(0.004, -0.004, d) * (1.0 - inGap);
    float aU = smoothstep(0.004, -0.004, dU);
    vec3 cu = vec3(0.01, 0.009, 0.009) + GAS * 0.05 * smoothstep(0.02, 0.0, abs(wheels));
    vec4 res = vec4(cu * aU, aU);
    res = vec4(mix(res.rgb, c, aBody), max(res.a, aBody));
    float bel = sdBox(vec2(gapD + GAP * 0.5, q.y - 0.12), vec2(GAP * 0.5, 0.36));
    float ab = smoothstep(0.004, -0.004, bel) * inGap;
    res = vec4(mix(res.rgb, vec3(0.006) + vec3(0.008) * sin(q.y * 200.0), ab), max(res.a, ab));
    if (q.x > TRAIN_REAR - 0.25) {
        vec2 tl = vec2(q.x - (TRAIN_REAR - 0.06), q.y);
        float lamp = min(length(tl - vec2(0.0, -0.22)), length(tl - vec2(0.0, 0.42)));
        res.rgb += vec3(1.0, 0.08, 0.05) * (exp(-lamp / 0.012) * 3.0) * res.a;
    }
    return res;
}

// integral along x of the window mask (exact motion blur for the streaking windows)
float winIntegral(float x) {
    float r = min(x, TRAIN_REAR) - TRAIN_REAR;
    float ci = floor(r / CAR_L);
    float cx = r - ci * CAR_L;
    float acc = 0.0;
    for (int k = 0; k < 10; k++) acc += clamp(cx - (WIN_0 + float(k) * WIN_P + 0.5 * WIN_P - WIN_W), 0.0, 2.0 * WIN_W);
    return ci * 10.0 * 2.0 * WIN_W + acc;
}
float presentIntegral(float x) { return min(x, TRAIN_REAR); }

vec4 train(vec2 sp, out float winLight) {
    vec2 q = lay(Z_TRAIN);
    q.x += gShift;
    winLight = 0.0;
    if (q.y < RAIL - 0.05 || q.y > 0.62) return vec4(0.0);
    if (gBlur < 0.004) return carriage(q, winLight);
    vec4 acc = vec4(0.0);
    if (gBlur < 0.08) {
        // moving off: samples along the motion, jittered with interleaved gradient noise
        float j = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) - 0.5;
        float wl = 0.0;
        for (int i = 0; i < 12; i++) {
            float f = (float(i) + 0.5 + j) / 12.0 - 0.5;
            float w;
            acc += carriage(q + vec2(f * gBlur, 0.0), w);
            wl += w;
        }
        acc /= 12.0;
        winLight = wl / 12.0;
        if (gBlur < 0.06) return acc;
    }
    // at speed: exactly box-filtered streaks of window light over the dark body
    float B = gBlur;
    float x0 = q.x - 0.5 * B, x1 = q.x + 0.5 * B;
    float wm = (winIntegral(x1) - winIntegral(x0)) / B;
    float pres = (presentIntegral(x1) - presentIntegral(x0)) / B;
    float body = smoothstep(0.004, -0.004, sdRBox(q - vec2(0.0, 0.11), vec2(1e3, 0.43), 0.02));
    float under = smoothstep(0.004, -0.004, sdBox(q - vec2(0.0, -0.45), vec2(1e3, 0.14)));
    float rowY = smoothstep(0.006, -0.006, abs(q.y - WIN_Y) - WIN_H + 0.01);
    vec3 bc = vec3(0.03, 0.019, 0.015) + GAS * 0.07 * smoothstep(0.012, 0.0, abs(q.y + 0.02)) + GAS * 0.08 * smoothstep(0.02, 0.0, abs(q.y - 0.5));
    vec3 wc = vec3(1.0, 0.6, 0.3) * 0.95 * (0.85 + 0.25 * smoothstep(-0.13, 0.13, q.y - WIN_Y));
    vec3 c = mix(bc, wc, wm * rowY / max(pres, 1e-3));
    float a = sat(max(body, under * 0.95)) * pres;
    vec4 fast = vec4(c * a, a);
    float tl = TRAIN_REAR - 0.06;
    float lampY = min(abs(q.y + 0.22), abs(q.y - 0.42));
    fast.rgb += vec3(1.0, 0.08, 0.05) * 3.0 * exp(-lampY / 0.012) * sat(0.03 / B) * step(abs(q.x - tl), 0.5 * B + 0.02);
    winLight = wm * rowY * 0.8;
    return mix(acc, fast, smoothstep(0.06, 0.08, gBlur));
}

// the tail lamp's glow in the air as she pulls away
vec3 tailGlow(vec2 sp) {
    float x = TRAIN_REAR - 0.06 - gShift;
    vec2 a = toScreen(vec2(x, -0.22), Z_TRAIN), b = toScreen(vec2(x, 0.42), Z_TRAIN);
    float r = min(length(sp - a), length(sp - b));
    return vec3(1.0, 0.1, 0.06) * (exp(-r / 0.03) * 0.25 + exp(-r / 0.12) * 0.05);
}

vec3 platformFloor(vec2 sp) {
    float den = min(sp.y, -1e-4);
    float zf = -EYE / den;
    float X = sp.x * zf + gCamX;
    vec2 g = vec2(X * 1.6, zf * 3.0);
    vec3 col = vec3(0.03, 0.032, 0.038) * (0.75 + 0.35 * vnoise(g * 2.0) + 0.15 * fbm(vec2(X, zf) * 12.0));
    // paving joints, fainter with distance
    float jz = abs(fract(zf * 2.4) - 0.5);
    col *= 1.0 - 0.3 * smoothstep(0.49 - gPx * zf * zf * 3.0, 0.5, jz);
    // the stone edge and its white line
    float edge = smoothstep(Z_EDGE - 0.05, Z_EDGE - 0.02, zf);
    col = mix(col, vec3(0.16, 0.15, 0.14), edge);
    col += vec3(0.5) * 0.12 * smoothstep(0.03, 0.0, abs(zf - (Z_EDGE - 0.12)));
    // pools of gaslight under the lamps
    float k = floor((X - 0.55) / 1.1 + 0.5);
    float lx = k * 1.1 + 0.55;
    float pool = exp(-pow((X - lx) / 0.35, 2.0)) * exp(-pow((zf - Z_COL) / 0.35, 2.0));
    col += GAS * 0.11 * pool;
    // window light thrown onto the platform by the train
    float wq = mod(X + gShift - TRAIN_REAR - 0.55, 0.47) / 0.47;
    float throwW = smoothstep(0.0, 0.25, wq) * smoothstep(0.95, 0.7, wq);
    float near = smoothstep(Z_EDGE - 0.6, Z_EDGE, zf) * (1.0 - edge);
    float trainHere = step(X + gShift, TRAIN_REAR);
    col += vec3(1.0, 0.66, 0.36) * 0.09 * mix(throwW, 0.55, sat(gBlur * 6.0)) * near * trainHere * (1.0 - 0.6 * gDep);
    // wet sheen: a soft reflection of the lamps' glow
    col += GAS * 0.03 * exp(-pow((X - lx) / 0.15, 2.0)) * smoothstep(0.9, 1.4, zf);
    return col;
}

// a cast-iron column with spandrel brackets, the beam and a fringed valance
vec4 ironwork(vec2 sp) {
    vec2 q = lay(Z_COL);
    float px = gPx * Z_COL;
    float k = floor(q.x / 1.1 + 0.5);
    vec2 c = vec2(q.x - k * 1.1, q.y);
    float shaft = sdBox(c - vec2(0.0, -0.1), vec2(0.016 - 0.003 * sat((c.y + 0.1) / 0.4), 0.37));
    float base = sdTrap(c - vec2(0.0, -0.44), 0.04, 0.022, 0.035);
    float capital = sdTrap(c - vec2(0.0, 0.3), 0.022, 0.045, 0.02);
    float d = min(min(shaft, base), capital);
    // spandrels: quarter-arches from the capital to the beam, pierced with rings
    vec2 sq = vec2(abs(c.x), c.y);
    float arch = abs(length(sq - vec2(0.36, 0.3)) - 0.34) - 0.008;
    arch = max(arch, max(-(sq.y - 0.3), sq.y - 0.6));
    arch = max(arch, sq.x - 0.36);
    float rings = abs(length(sq - vec2(0.06, 0.53)) - 0.032) - 0.005;
    rings = min(rings, abs(length(sq - vec2(0.12, 0.45)) - 0.022) - 0.004);
    float spand = min(arch, rings);
    spand = min(spand, max(abs(sq.y - 0.6) - 0.008, sq.x - 0.36));
    d = min(d, spand);
    // the beam
    float beam = sdBox(q - vec2(0.0, 0.64), vec2(1e3, 0.04));
    d = min(d, beam);
    // a fringed valance hanging from the beam
    float fr = q.y - 0.6 + 0.035 * (0.5 + 0.5 * abs(fract(q.x * 9.0) - 0.5) * 2.0);
    float val = max(-fr, q.y - 0.7);
    val = max(val, -(q.y - 0.56));
    d = min(d, val);
    float a = smoothstep(px, -px, d);
    vec3 iron = vec3(0.012, 0.013, 0.016);
    // gaslight catches the iron: a rim on the side facing the nearest lamp
    float lx = lampX(q.x) - 0.0;
    float rim = exp(-max(-d, 0.0) / (0.003 + px));
    vec3 cc = iron + GAS * rim * 0.35 * exp(-abs(q.x - lx) * 1.5) * (0.6 + 0.4 * smoothstep(-0.4, 0.6, q.y));
    cc += GAS * 0.05 * exp(-length(q - vec2(lx, 0.33)) * 3.0);
    return vec4(cc, a);
}

// the gas lamps: hanging lanterns with glowing mantles
vec3 lamps(vec3 col, vec2 sp) {
    vec2 q = lay(Z_COL);
    float px = gPx * Z_COL;
    float lx = lampX(q.x);
    vec2 l = (q - vec2(lx, 0.33)) / 1.5;            // lanterns drawn half as large again
    float lpx = px / 1.5;
    float rod = sdBox(l - vec2(0.0, 0.14), vec2(0.003, 0.1));
    float cap = sdTrap(l - vec2(0.0, 0.056), 0.044, 0.01, 0.016);
    float glass = sdTrap(l - vec2(0.0, 0.0), 0.024, 0.037, 0.04);
    float fin = sdTrap(l - vec2(0.0, -0.05), 0.004, 0.02, 0.012);
    float collar = sdBox(l - vec2(0.0, 0.041), vec2(0.04, 0.004));
    float base = sdBox(l - vec2(0.0, -0.041), vec2(0.026, 0.004));
    float iron = min(min(min(rod, cap), fin), min(collar, base));
    float flick = 0.94 + 0.06 * sin(gT * 11.0 + lx) * sin(gT * 7.3);
    // amber glass, lit from within: brightest round the mantle, darker at the panes' edges
    float m = length((l - vec2(0.0, -0.005)) * vec2(1.4, 1.0));
    vec3 gl = GAS * (0.45 + 1.6 * exp(-m / 0.022)) * flick;
    float bars = smoothstep(0.0035, 0.001, abs(abs(l.x) - 0.011 - 0.006 * (l.y + 0.04) / 0.08)) * step(abs(l.y), 0.04);
    gl = mix(gl, vec3(0.02), bars * 0.85);
    col = mix(col, gl, smoothstep(lpx, -lpx, glass));
    col += vec3(1.0, 0.88, 0.7) * (exp(-length((l - vec2(0.0, -0.005)) * vec2(1.6, 1.0)) / 0.007) * 7.0) * flick;
    col = mix(col, vec3(0.008) + GAS * 0.25 * exp(-length(l) * 18.0), smoothstep(lpx, -lpx, iron));
    // halos in the damp air and faint cones falling to the platform, from this lamp and its neighbours
    for (int i = -1; i <= 1; i++) {
        float lxi = lx + float(i) * 1.1;
        vec2 ls = toScreen(vec2(lxi, 0.33), Z_COL);
        float r = length(sp - ls);
        col += GAS * (exp(-r / 0.035) * 0.55 + exp(-r / 0.14) * 0.16) * flick;
        col += GAS * beam(sp, ls, vec2(0.0, -1.0), 0.55, 0.9) * 0.05;
    }
    return col;
}

// drifting steam, lit by the lamps and the train's windows
vec3 steamLayer(vec3 col, vec2 sp, float z, float amt, float windowGlow, float lampL) {
    if (amt <= 0.0) return col;
    vec2 q = lay(z);
    float drag = gShift * 0.35 * (2.0 - z);         // the departing train drags the steam
    vec2 p = vec2(q.x * 1.4 + gT * 0.07 + drag, q.y * 2.0 - gT * 0.05);
    vec2 w = vec2(fbm(p * 0.9 + vec2(0.0, gT * 0.03)), fbm(p * 0.9 + vec2(4.0, -gT * 0.02)));
    float n = fbm(p * 1.3 + w * 1.6 + z * 3.0);
    // denser low down (from under the carriages) and in a band along the roof (the engine's plume)
    float low = smoothstep(0.1, -0.5, q.y);
    float plume = exp(-pow((q.y - 0.5) / 0.2, 2.0)) * 0.9;
    float dens = smoothstep(0.36, 0.82, n) * (0.55 * low + plume + 0.3) * amt;
    // steam glows where the gaslight and the windows reach it, a cold blue elsewhere
    vec3 sc = vec3(0.022, 0.028, 0.045) + GAS * (0.9 * lampL) + vec3(1.0, 0.64, 0.36) * 0.4 * windowGlow;
    return mix(col, sc * (0.65 + 0.6 * n), sat(dens) * 0.8);
}

vec3 station(vec2 sp) {
    vec4 E = uP[1];
    if (E.z <= 0.0) E = vec4(-0.2, -0.43, 0.5, 0.0);     // an empty slot means she is absent
    float lampL = lampLight(sp);
    // the far side, then the train
    vec3 col = farSide(sp);
    // the roof of the shed overhead: iron and glass, the night sky through the panes
    vec2 rq = lay(Z_COL);
    if (rq.y > 0.66) {
        vec2 g = vec2(rq.x * 3.0, (rq.y - 0.66) * 9.0);
        vec2 gf = abs(fract(g) - 0.5);
        float bar = max(smoothstep(0.42, 0.47, gf.x), smoothstep(0.38, 0.46, gf.y));
        vec3 sky = vec3(0.012, 0.018, 0.04) + vec3(0.6, 0.65, 0.8) * step(0.995, hash21(floor(sp * 300.0))) * 0.5;
        col = mix(sky, vec3(0.006, 0.006, 0.008) + GAS * 0.04 * lampL, bar);
    }
    float winL;
    vec4 tr = train(sp, winL);
    col = col * (1.0 - tr.a) + tr.rgb;
    col += tailGlow(sp);
    // light spilling from the windows into the air beside the carriages
    float windowGlow = 0.0;
    {
        vec2 q = lay(Z_TRAIN);
        q.x += gShift;
        float onTrain = step(q.x, TRAIN_REAR) * smoothstep(0.62, 0.35, q.y) * smoothstep(-0.5, -0.1, q.y);
        windowGlow = onTrain * (0.6 + 0.4 * smoothstep(0.0, 0.3, gBlur)) * (1.0 - 0.7 * smoothstep(0.7, 1.0, gDep));
    }
    col = steamLayer(col, sp, 1.9, gSteam, windowGlow, lampL);
    // the platform, its edge and the drop to the track
    if (sp.y < -EYE / Z_EDGE + 0.002) col = platformFloor(sp);
    // ironwork and lamps
    vec4 iw = ironwork(sp);
    col = mix(col, iw.rgb, iw.a);
    col = lamps(col, sp);
    col += GAS * lampL * 0.05 + vec3(0.008, 0.011, 0.02);           // damp air, gaslit and night-blue
    col = steamLayer(col, sp, 1.2, gSteam * 0.7, windowGlow * 0.5, lampL);
    // Elena
    float glowAmt;
    vec2 Lr = normalize(vec2(0.25, 1.0));
    vec4 el = elena(sp, E, Lr, glowAmt);
    col = over(col, el * E.w);
    col += SILVER * 0.05 * glowAmt * E.w;
    // a last thin veil of steam drifting past in front of her
    col = steamLayer(col, sp, 0.9, gSteam * 0.3, 0.0, lampL);
    col += GAS * dust(sp, gT, 0.05, 0.05) * 0.1 * (0.3 + lampL);
    return col;
}

// ------------------------------------------------------------------ the map
const vec2 COAST[200] = vec2[200](vec2(-0.1238, -0.6011), vec2(-0.1241, -0.5625), vec2(-0.1247, -0.5260), vec2(-0.1257, -0.4918), vec2(-0.1269, -0.4599), vec2(-0.1285, -0.4302), vec2(-0.1283, -0.4035), vec2(-0.1265, -0.3797), vec2(-0.1230, -0.3589), vec2(-0.1178, -0.3410), vec2(-0.1111, -0.3271), vec2(-0.1031, -0.3171), vec2(-0.0936, -0.3110), vec2(-0.0827, -0.3089), vec2(-0.0719, -0.3054), vec2(-0.0613, -0.3007), vec2(-0.0509, -0.2947), vec2(-0.0407, -0.2873), vec2(-0.0323, -0.2796), vec2(-0.0257, -0.2715), vec2(-0.0208, -0.2630), vec2(-0.0178, -0.2541), vec2(-0.0177, -0.2457), vec2(-0.0205, -0.2378), vec2(-0.0263, -0.2305), vec2(-0.0351, -0.2237), vec2(-0.0434, -0.2167), vec2(-0.0512, -0.2093), vec2(-0.0586, -0.2016), vec2(-0.0655, -0.1936), vec2(-0.0724, -0.1840), vec2(-0.0792, -0.1727), vec2(-0.0859, -0.1599), vec2(-0.0926, -0.1455), vec2(-0.0970, -0.1311), vec2(-0.0991, -0.1169), vec2(-0.0990, -0.1027), vec2(-0.0967, -0.0886), vec2(-0.0935, -0.0749), vec2(-0.0893, -0.0615), vec2(-0.0843, -0.0485), vec2(-0.0784, -0.0358), vec2(-0.0721, -0.0245), vec2(-0.0654, -0.0144), vec2(-0.0582, -0.0057), vec2(-0.0507, 0.0017), vec2(-0.0414, 0.0083), vec2(-0.0304, 0.0140), vec2(-0.0175, 0.0188), vec2(-0.0029, 0.0228), vec2(0.0122, 0.0277), vec2(0.0277, 0.0335), vec2(0.0438, 0.0403), vec2(0.0604, 0.0480), vec2(0.0762, 0.0556), vec2(0.0914, 0.0631), vec2(0.1059, 0.0704), vec2(0.1198, 0.0776), vec2(0.1336, 0.0840), vec2(0.1473, 0.0896), vec2(0.1611, 0.0944), vec2(0.1748, 0.0983), vec2(0.1892, 0.1023), vec2(0.2042, 0.1062), vec2(0.2200, 0.1101), vec2(0.2364, 0.1140), vec2(0.2514, 0.1165), vec2(0.2650, 0.1176), vec2(0.2771, 0.1172), vec2(0.2879, 0.1155), vec2(0.2983, 0.1151), vec2(0.3083, 0.1160), vec2(0.3178, 0.1182), vec2(0.3270, 0.1218), vec2(0.3346, 0.1269), vec2(0.3408, 0.1338), vec2(0.3454, 0.1423), vec2(0.3485, 0.1525), vec2(0.3526, 0.1594), vec2(0.3577, 0.1631), vec2(0.3638, 0.1635), vec2(0.3710, 0.1606), vec2(0.3782, 0.1565), vec2(0.3857, 0.1511), vec2(0.3934, 0.1443), vec2(0.4012, 0.1363), vec2(0.4083, 0.1283), vec2(0.4148, 0.1203), vec2(0.4206, 0.1123), vec2(0.4257, 0.1044), vec2(0.4298, 0.0970), vec2(0.4329, 0.0901), vec2(0.4350, 0.0837), vec2(0.4362, 0.0779), vec2(0.4357, 0.0721), vec2(0.4337, 0.0664), vec2(0.4301, 0.0607), vec2(0.4249, 0.0551), vec2(0.4194, 0.0505), vec2(0.4136, 0.0469), vec2(0.4075, 0.0442), vec2(0.4011, 0.0425), vec2(0.3946, 0.0407), vec2(0.3880, 0.0387), vec2(0.3813, 0.0365), vec2(0.3744, 0.0342), vec2(0.3675, 0.0314), vec2(0.3606, 0.0281), vec2(0.3537, 0.0244), vec2(0.3468, 0.0201), vec2(0.3417, 0.0147), vec2(0.3385, 0.0081), vec2(0.3372, 0.0002), vec2(0.3377, -0.0088), vec2(0.3389, -0.0189), vec2(0.3408, -0.0299), vec2(0.3432, -0.0419), vec2(0.3463, -0.0549), vec2(0.3493, -0.0676), vec2(0.3522, -0.0799), vec2(0.3551, -0.0920), vec2(0.3578, -0.1037), vec2(0.3602, -0.1157), vec2(0.3625, -0.1280), vec2(0.3645, -0.1407), vec2(0.3662, -0.1536), vec2(0.3680, -0.1650), vec2(0.3699, -0.1747), vec2(0.3718, -0.1828), vec2(0.3739, -0.1894), vec2(0.3778, -0.1979), vec2(0.3837, -0.2084), vec2(0.3916, -0.2210), vec2(0.4014, -0.2355), vec2(0.4107, -0.2498), vec2(0.4194, -0.2636), vec2(0.4276, -0.2772), vec2(0.4352, -0.2903), vec2(0.4424, -0.3035), vec2(0.4491, -0.3167), vec2(0.4553, -0.3298), vec2(0.4612, -0.3429), vec2(0.4669, -0.3512), vec2(0.4727, -0.3546), vec2(0.4784, -0.3532), vec2(0.4840, -0.3470), vec2(0.4902, -0.3389), vec2(0.4969, -0.3288), vec2(0.5042, -0.3169), vec2(0.5119, -0.3030), vec2(0.5190, -0.2888), vec2(0.5255, -0.2742), vec2(0.5312, -0.2593), vec2(0.5364, -0.2440), vec2(0.5418, -0.2310), vec2(0.5477, -0.2203), vec2(0.5539, -0.2118), vec2(0.5604, -0.2056), vec2(0.5666, -0.1988), vec2(0.5723, -0.1913), vec2(0.5776, -0.1831), vec2(0.5824, -0.1743), vec2(0.5876, -0.1642), vec2(0.5930, -0.1528), vec2(0.5987, -0.1401), vec2(0.6046, -0.1262), vec2(0.6098, -0.1138), vec2(0.6143, -0.1030), vec2(0.6181, -0.0938), vec2(0.6211, -0.0862), vec2(0.6262, -0.0809), vec2(0.6336, -0.0780), vec2(0.6431, -0.0774), vec2(0.6548, -0.0791), vec2(0.6659, -0.0825), vec2(0.6766, -0.0874), vec2(0.6867, -0.0939), vec2(0.6963, -0.1020), vec2(0.7068, -0.1114), vec2(0.7181, -0.1222), vec2(0.7303, -0.1343), vec2(0.7433, -0.1477), vec2(0.7574, -0.1633), vec2(0.7725, -0.1813), vec2(0.7887, -0.2016), vec2(0.8059, -0.2242), vec2(0.8229, -0.2509), vec2(0.8397, -0.2819), vec2(0.8565, -0.3170), vec2(0.8730, -0.3563), vec2(0.8881, -0.4036), vec2(0.9018, -0.4589), vec2(0.9140, -0.5222), vec2(0.9248, -0.5935), vec2(0.8663, -0.6444), vec2(0.7387, -0.6749), vec2(0.5418, -0.6850), vec2(0.2757, -0.6746), vec2(0.0761, -0.6572), vec2(-0.0571, -0.6327));
const vec2 LAGOON[40] = vec2[40](vec2(-0.1172, -0.0997), vec2(-0.1237, -0.0924), vec2(-0.1282, -0.0840), vec2(-0.1308, -0.0746), vec2(-0.1314, -0.0641), vec2(-0.1301, -0.0525), vec2(-0.1283, -0.0410), vec2(-0.1260, -0.0295), vec2(-0.1233, -0.0180), vec2(-0.1202, -0.0065), vec2(-0.1159, 0.0036), vec2(-0.1106, 0.0125), vec2(-0.1042, 0.0199), vec2(-0.0968, 0.0261), vec2(-0.0886, 0.0316), vec2(-0.0799, 0.0364), vec2(-0.0705, 0.0405), vec2(-0.0604, 0.0440), vec2(-0.0513, 0.0456), vec2(-0.0432, 0.0453), vec2(-0.0360, 0.0431), vec2(-0.0299, 0.0390), vec2(-0.0269, 0.0345), vec2(-0.0271, 0.0297), vec2(-0.0304, 0.0245), vec2(-0.0370, 0.0189), vec2(-0.0438, 0.0128), vec2(-0.0508, 0.0059), vec2(-0.0581, -0.0015), vec2(-0.0656, -0.0096), vec2(-0.0726, -0.0185), vec2(-0.0791, -0.0282), vec2(-0.0850, -0.0388), vec2(-0.0905, -0.0502), vec2(-0.0951, -0.0615), vec2(-0.0989, -0.0726), vec2(-0.1019, -0.0836), vec2(-0.1041, -0.0944), vec2(-0.1074, -0.1008), vec2(-0.1118, -0.1025));
const vec2 CRES[36] = vec2[36](vec2(0.6396, -0.1797), vec2(0.6461, -0.1980), vec2(0.6512, -0.2166), vec2(0.6550, -0.2354), vec2(0.6574, -0.2545), vec2(0.6585, -0.2739), vec2(0.6598, -0.2933), vec2(0.6613, -0.3126), vec2(0.6630, -0.3320), vec2(0.6650, -0.3515), vec2(0.6670, -0.3702), vec2(0.6690, -0.3883), vec2(0.6710, -0.4058), vec2(0.6730, -0.4226), vec2(0.6730, -0.4349), vec2(0.6709, -0.4425), vec2(0.6667, -0.4456), vec2(0.6605, -0.4441), vec2(0.6546, -0.4374), vec2(0.6492, -0.4256), vec2(0.6442, -0.4086), vec2(0.6397, -0.3866), vec2(0.6358, -0.3651), vec2(0.6325, -0.3444), vec2(0.6299, -0.3243), vec2(0.6279, -0.3049), vec2(0.6255, -0.2855), vec2(0.6227, -0.2660), vec2(0.6194, -0.2466), vec2(0.6156, -0.2271), vec2(0.6140, -0.2096), vec2(0.6146, -0.1942), vec2(0.6174, -0.1808), vec2(0.6224, -0.1694), vec2(0.6277, -0.1654), vec2(0.6334, -0.1688));
const vec2 KRK[24] = vec2[24](vec2(0.7028, -0.1570), vec2(0.7158, -0.1485), vec2(0.7285, -0.1464), vec2(0.7410, -0.1508), vec2(0.7532, -0.1616), vec2(0.7652, -0.1788), vec2(0.7726, -0.1955), vec2(0.7756, -0.2117), vec2(0.7741, -0.2275), vec2(0.7681, -0.2427), vec2(0.7605, -0.2527), vec2(0.7513, -0.2575), vec2(0.7404, -0.2571), vec2(0.7280, -0.2514), vec2(0.7167, -0.2452), vec2(0.7066, -0.2384), vec2(0.6977, -0.2309), vec2(0.6898, -0.2229), vec2(0.6843, -0.2143), vec2(0.6810, -0.2052), vec2(0.6801, -0.1955), vec2(0.6814, -0.1852), vec2(0.6856, -0.1754), vec2(0.6927, -0.1660));
const vec2 ROUTE[61] = vec2[61](vec2(-0.5702, 0.0232), vec2(-0.5534, 0.0294), vec2(-0.5294, 0.0384), vec2(-0.5020, 0.0479), vec2(-0.4750, 0.0556), vec2(-0.4476, 0.0621), vec2(-0.4183, 0.0682), vec2(-0.3901, 0.0721), vec2(-0.3660, 0.0720), vec2(-0.3474, 0.0662), vec2(-0.3327, 0.0562), vec2(-0.3196, 0.0444), vec2(-0.3060, 0.0336), vec2(-0.2918, 0.0228), vec2(-0.2780, 0.0112), vec2(-0.2641, 0.0013), vec2(-0.2497, -0.0047), vec2(-0.2347, -0.0052), vec2(-0.2193, -0.0017), vec2(-0.2037, 0.0035), vec2(-0.1878, 0.0084), vec2(-0.1709, 0.0135), vec2(-0.1532, 0.0196), vec2(-0.1364, 0.0246), vec2(-0.1220, 0.0264), vec2(-0.1114, 0.0223), vec2(-0.1033, 0.0141), vec2(-0.0958, 0.0066), vec2(-0.0868, 0.0044), vec2(-0.0753, 0.0096), vec2(-0.0627, 0.0193), vec2(-0.0500, 0.0314), vec2(-0.0383, 0.0438), vec2(-0.0295, 0.0562), vec2(-0.0226, 0.0696), vec2(-0.0139, 0.0839), vec2(0.0000, 0.0990), vec2(0.0224, 0.1165), vec2(0.0507, 0.1360), vec2(0.0796, 0.1540), vec2(0.1038, 0.1672), vec2(0.1201, 0.1733), vec2(0.1319, 0.1748), vec2(0.1442, 0.1744), vec2(0.1620, 0.1752), vec2(0.1887, 0.1782), vec2(0.2209, 0.1816), vec2(0.2536, 0.1846), vec2(0.2816, 0.1860), vec2(0.3035, 0.1861), vec2(0.3220, 0.1851), vec2(0.3383, 0.1826), vec2(0.3536, 0.1781), vec2(0.3678, 0.1709), vec2(0.3805, 0.1616), vec2(0.3920, 0.1510), vec2(0.4027, 0.1401), vec2(0.4131, 0.1277), vec2(0.4229, 0.1138), vec2(0.4311, 0.1012), vec2(0.4370, 0.0924));
const vec2 TOWNS[29] = vec2[29](vec2(-0.3660, 0.0720), vec2(-0.2497, -0.0047), vec2(-0.1146, 0.1241), vec2(0.2503, 0.3110), vec2(0.3886, 0.2437), vec2(0.4502, -0.3103), vec2(0.6723, -0.0817), vec2(-0.3549, -0.2945), vec2(-0.2890, -0.1784), vec2(-0.6479, -0.1181), vec2(0.0000, 0.0990), vec2(0.1038, 0.1672), vec2(-0.5614, 0.1569), vec2(-0.4427, 0.1420), vec2(-0.3079, 0.1728), vec2(-0.2026, 0.0914), vec2(0.0389, 0.2625), vec2(0.1471, 0.2583), vec2(0.2960, 0.1855), vec2(0.1834, 0.1692), vec2(-0.0400, -0.0953), vec2(-0.4070, -0.0553), vec2(-0.5173, -0.1026), vec2(0.4205, 0.0414), vec2(0.3636, -0.1213), vec2(0.3787, -0.1992), vec2(0.5627, -0.2064), vec2(-0.1259, 0.2070), vec2(-0.2569, -0.1900));
const vec2 RIVERS[37] = vec2[37](vec2(-0.5702, 0.0232), vec2(-0.5323, -0.0247), vec2(-0.4597, -0.1100), vec2(-0.3565, -0.1500), vec2(-0.2481, -0.1491), vec2(-0.1751, -0.1313), vec2(-0.1031, -0.1367), vec2(9.0000, 9.0000), vec2(-0.3409, 0.2514), vec2(-0.2924, 0.1052), vec2(-0.2243, -0.0005), vec2(-0.1725, -0.0644), vec2(-0.1132, -0.1183), vec2(9.0000, 9.0000), vec2(-0.1205, 0.3460), vec2(-0.0892, 0.2210), vec2(-0.0379, 0.1469), vec2(0.0134, 0.0727), vec2(0.0335, 0.0307), vec2(9.0000, 9.0000), vec2(0.1531, 0.4127), vec2(0.1509, 0.2633), vec2(0.1654, 0.1699), vec2(0.1954, 0.1069), vec2(9.0000, 9.0000), vec2(0.3938, 0.3776), vec2(0.3924, 0.2487), vec2(0.3554, 0.1316), vec2(9.0000, 9.0000), vec2(-0.7193, -0.1875), vec2(-0.5758, -0.2137), vec2(-0.4321, -0.2348), vec2(-0.2878, -0.2404), vec2(-0.1793, -0.2394), vec2(-0.0893, -0.2481), vec2(-0.0206, -0.2456), vec2(9.0000, 9.0000));
const vec2 VERONA = vec2(-0.5702, 0.0232);
const vec2 VENICE = vec2(-0.0868, 0.0044);
const vec2 TRIESTE = vec2(0.4370, 0.0924);
const float CITY_AT[3] = float[3](0.0000, 0.4560, 1.0000);   // fraction of the route at each city
// map transform: screen = K * (u, v) + T, u = (lon - 12.33) cos(45.5), v = lat - 45.44 (K complex)
const vec2 MAP_K = vec2(0.514726, -0.019987);
const vec2 MAP_T = vec2(-0.086758, 0.004436);
#define POLY_SDF(NAME, ARR, N) float NAME(vec2 p) { \
    float d = dot(p - ARR[0], p - ARR[0]); float s = 1.0; \
    for (int i = 0, j = N - 1; i < N; j = i, i++) { \
        vec2 e = ARR[j] - ARR[i], w = p - ARR[i]; \
        vec2 b = w - e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0); \
        d = min(d, dot(b, b)); \
        bvec3 c = bvec3(p.y >= ARR[i].y, p.y < ARR[j].y, e.x * w.y > e.y * w.x); \
        if (all(c) || all(not(c))) s = -s; \
    } \
    return s * sqrt(d); }
POLY_SDF(sdSea, COAST, 200)
POLY_SDF(sdLagoon, LAGOON, 40)
POLY_SDF(sdCres, CRES, 36)
POLY_SDF(sdKrk, KRK, 24)

vec2 mapToLL(vec2 s) {           // screen (zoom 1) -> (lon, lat)
    vec2 X = s - MAP_T;
    float k2 = dot(MAP_K, MAP_K);
    vec2 uv = vec2(MAP_K.x * X.x + MAP_K.y * X.y, -MAP_K.y * X.x + MAP_K.x * X.y) / k2;
    return vec2(uv.x / 0.700909 + 12.33, uv.y + 45.44);
}

float riverD(vec2 p) {
    float d = 1e3;
    for (int i = 0; i < 36; i++) {
        vec2 a = RIVERS[i], b = RIVERS[i + 1];
        if (a.x > 5.0 || b.x > 5.0) continue;
        d = min(d, sdSeg(p, a, b));
    }
    return d;
}

// distance to the drawn part of the route, the head of the line and the distance drawn so far
float routeD(vec2 p, float prog, out vec2 head, out float drawn, out float total) {
    total = 0.0;
    for (int i = 0; i < 60; i++) total += length(ROUTE[i + 1] - ROUTE[i]);
    float target = prog * total;
    float acc = 0.0, d = 1e3;
    head = ROUTE[0];
    for (int i = 0; i < 60; i++) {
        vec2 a = ROUTE[i], b = ROUTE[i + 1];
        float L = length(b - a);
        if (acc >= target) break;
        float f = sat((target - acc) / L);
        vec2 e = mix(a, b, f);
        d = min(d, sdSeg(p, a, e));
        head = e;
        acc += L;
    }
    drawn = target;
    return d;
}

vec3 mapView(vec2 sp) {
    float prog = sat(uP[2].x);
    float Z = uP[2].y > 0.01 ? uP[2].y : 1.0;
    vec2 head0; float drawn0, total;
    routeD(vec2(0.0), prog, head0, drawn0, total);
    vec2 centre = mix(vec2(0.0, 0.02), head0, sat((Z - 1.0) / 1.5));
    vec2 p = centre + sp / Z + vec2(0.005 * sin(gT * 0.11), 0.003 * sin(gT * 0.07));
    float px = gPx / Z;
    vec2 ll = mapToLL(p);
    // water and land
    float dSea = sdSea(p);
    float dLag = sdLagoon(p);
    float dIsl = min(sdCres(p), sdKrk(p));
    float wob = (fbm(p * 70.0) - 0.5) * 0.006 + (vnoise(p * 300.0) - 0.5) * 0.0012;
    float dW = max(min(dSea, dLag), -dIsl) + wob;     // negative in water
    float inW = smoothstep(px, -px, dW);
    // deep-blue paper: the sea a shade deeper, the land drier and lighter towards the coast
    vec3 sea = vec3(0.034, 0.068, 0.155);
    vec3 land = vec3(0.085, 0.12, 0.2) * (1.0 + 0.22 * exp(-max(dW, 0.0) / 0.02));
    // shaded relief: the Alps and Prealps to the north, the Karst, the hills of Istria
    float alps = smoothstep(45.78, 46.35, ll.y);
    float karst = smoothstep(13.55, 13.85, ll.x) * smoothstep(45.35, 45.6, ll.y) * (1.0 - alps);
    float istria = smoothstep(13.65, 13.95, ll.x) * smoothstep(45.45, 45.2, ll.y) * step(ll.x, 14.3);
    float relief = alps + 0.55 * karst + 0.35 * istria;
    if (relief > 0.01 && inW < 0.99) {
        vec2 hp = p * 11.0;
        float h0 = fbm(hp), hx = fbm(hp + vec2(0.06, 0.0)), hy = fbm(hp + vec2(0.0, 0.06));
        float shade = (hx - h0) * -0.7 + (hy - h0) * 0.7;          // lit from the north-west
        land += vec3(0.16, 0.2, 0.26) * sat(shade * 6.0) * relief * 0.5;
        land -= vec3(0.03, 0.038, 0.05) * sat(-shade * 6.0) * relief;
        // hachures: short strokes running downhill on the steeper slopes
        vec2 g = normalize(vec2(hx - h0, hy - h0) + 1e-5);
        float strokes = smoothstep(0.75, 1.0, sin(dot(p, vec2(-g.y, g.x)) * 1400.0 / Z));
        land -= vec3(0.025, 0.032, 0.045) * strokes * relief * smoothstep(0.004, 0.012, length(vec2(hx - h0, hy - h0)));
    }
    vec3 col = mix(land, sea, inW);
    // water-lining: engraved lines following the coast out to sea, fading with distance
    float off = max(-dW, 0.0);
    float lines = 0.0;
    for (int i = 1; i <= 6; i++) {
        float fi = float(i);
        lines += smoothstep(px * 1.1, 0.0, abs(off - fi * 0.006 * (1.0 + 0.15 * fi))) * (1.0 - fi / 7.0);
    }
    col += vec3(0.3, 0.42, 0.6) * lines * 0.32 * smoothstep(0.0, -0.001, dSea) * step(-dIsl, 0.0);
    // the coastline: a crisp pale ink line
    float coast = smoothstep(px * 1.25, 0.0, abs(dW));
    col = mix(col, vec3(0.62, 0.7, 0.84) * 0.9, coast);
    // rivers, meandering
    vec2 mq = p + (vec2(fbm(p * 45.0), fbm(p * 45.0 + 7.0)) - 0.5) * 0.012;
    float rv = riverD(mq);
    col = mix(col, vec3(0.3, 0.42, 0.62) * 0.5, smoothstep(px * 0.9, 0.0, rv) * (1.0 - inW) * 0.7);
    // graticule every half degree, faint and dashed
    vec2 gl = abs(fract(ll * 2.0 + 0.5) - 0.5) / 2.0;
    float gx = gl.x * 0.700909 * 0.5151, gy = gl.y * 0.5151;
    float grat = max(smoothstep(px, 0.0, gx) * step(0.5, fract(ll.y * 20.0)), smoothstep(px, 0.0, gy) * step(0.5, fract(ll.x * 14.0)));
    col = mix(col, vec3(0.32, 0.42, 0.58) * 0.5, grat * 0.22);
    // a compass rose out at sea
    vec2 cq = (p - vec2(0.13, -0.37)) / 0.065;
    float cr = length(cq);
    if (cr < 1.3) {
        float ca = atan(cq.y, cq.x);
        float star8 = cr - (0.18 + 0.82 * pow(abs(cos(2.0 * ca)), 14.0) + 0.42 * pow(abs(sin(2.0 * ca)), 14.0));
        float rose = min(abs(star8), min(abs(cr - 1.05), abs(cr - 0.93))) * 0.065;
        col = mix(col, vec3(0.5, 0.6, 0.74) * 0.6, smoothstep(px * 1.1, 0.0, rose));
        col = mix(col, vec3(0.42, 0.52, 0.68) * 0.4, smoothstep(0.0, -0.06, star8) * step(0.5, fract(ca / (PI * 0.25) + 0.5)) * 0.6);
    }
    // towns
    for (int i = 0; i < 29; i++) {
        float dt = length(p - TOWNS[i]);
        col = mix(col, vec3(0.62, 0.68, 0.8) * 0.62, smoothstep(0.0028 / sqrt(Z), 0.0016 / sqrt(Z), dt));
    }
    // paper: fibres and mottling, two fold creases, lamplight from the upper left, worn edges
    float fib = fbm(vec2(sp.x * 150.0, sp.y * 34.0)) * 0.55 + fbm(sp * 55.0 + 3.0) * 0.45;
    float mott = fbm(sp * 6.0 + 11.0);
    col *= (0.82 + 0.34 * fib) * (0.85 + 0.3 * mott);
    float creaseV = sp.x - 0.24 - 0.01 * sin(sp.y * 3.0), creaseH = sp.y + 0.13;
    col *= 1.0 - 0.28 * exp(-abs(creaseV) / 0.003) + 0.1 * exp(-abs(creaseV - 0.007) / 0.006);
    col *= 1.0 - 0.22 * exp(-abs(creaseH) / 0.003) + 0.08 * exp(-abs(creaseH + 0.007) / 0.006);
    float worn = smoothstep(0.003, 0.0, abs(creaseV)) * smoothstep(0.003, 0.0, abs(creaseH));
    col *= 1.0 - 0.3 * worn;
    vec2 lp = sp - vec2(-0.32, 0.28);
    float lamp = 0.5 + 0.85 * exp(-dot(lp, lp) * 1.1);
    col *= lamp * vec3(1.08, 1.0, 0.9);
    // the route, drawn in crimson ink that glows
    vec2 head; float drawn;
    float rd = routeD(p, prog, head, drawn, total);
    vec3 crimson = vec3(0.85, 0.06, 0.08);
    float core = smoothstep(0.0024 / Z + px, 0.0012 / Z, rd);
    col = mix(col, crimson * 1.1, core);
    col += crimson * exp(-rd / 0.012) * 0.28 * step(0.0005, prog);
    // the cities of the journey: rings that kindle as the line arrives
    vec2 cities[3] = vec2[3](VERONA, VENICE, TRIESTE);
    for (int i = 0; i < 3; i++) {
        vec2 c = cities[i];
        float dc = length(p - c);
        float reached = smoothstep(CITY_AT[i] - 0.03, CITY_AT[i] + 0.01, prog + (i == 0 ? 0.05 : 0.0));
        float ring = smoothstep(px * 1.2, 0.0, abs(dc - 0.011));
        float dotc = smoothstep(0.0045, 0.003, dc);
        col = mix(col, vec3(0.78, 0.82, 0.9) * 0.8, max(ring, dotc) * 0.9);
        col += vec3(1.0, 0.45, 0.35) * (exp(-dc / 0.02) * 0.5 + ring * 0.6) * reached;
    }
    // the travelling point of light
    if (prog > 0.0 && prog < 1.0 + 1e-4) {
        float dh = length(p - head);
        float tw = 0.85 + 0.15 * sin(gT * 9.0);
        col += vec3(1.0, 0.55, 0.45) * (exp(-dh / 0.0035) * 4.0 + exp(-dh / 0.03) * 0.6) * tw;
        vec2 hq = p - head;
        col += vec3(1.0, 0.6, 0.5) * 0.5 * (exp(-abs(hq.y) / 0.0012) * exp(-abs(hq.x) / 0.035) + exp(-abs(hq.x) / 0.0012) * exp(-abs(hq.y) / 0.035)) * tw;
    }
    return col;
}

void main() {
    gSp = screen();
    gT = uTime;
    gPx = 1.5 * PIXEL;
    int mode = int(uP[0].x + 0.5);
    gDep = sat(uP[0].y);
    gSteam = sat(uP[0].z);
    gCamX = 0.02 * sin(uTime * 0.05);
    gShift = 7.0 * pow(gDep, 2.2);
    gBlur = 0.38 * pow(gDep, 1.2) * step(0.0001, gDep);
    vec3 col = (mode == 1) ? mapView(gSp) : station(gSp);
    fragColor = vec4(max(col, 0.0), 1.0);
}
