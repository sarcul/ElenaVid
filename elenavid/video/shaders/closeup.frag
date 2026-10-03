#version 430
// THE CLOSE-UP: a low-key, split-lit profile. Textures from portrait.py:
//   uFace: R mask, G height, B lips, A dark details      uHairTex: R mask, G strands, B height, A ear
// The neck's sternocleidomastoid and external jugular are analytic so they tighten and pulse.
#include common
uniform sampler2D uFace;
uniform sampler2D uHairTex;
// uP[0] head origin xy (screen), scale, tilt    uP[1] canvas X0,Y0,X1,Y1
// uP[2] tension, cold, pulse phase, exposure    uP[3] earring xy, bokeh drift
// uP[4] SCM start, end                          uP[5] vein start, end

vec3 bokeh(vec2 sp, float t) {
    vec3 acc = vec3(0.0);
    for (int i = 0; i < 22; i++) {
        float fi = float(i);
        vec2 c = vec2(hash11(fi * 3.1) * 1.5 - 0.35, hash11(fi * 7.7) * 1.1 - 0.55);
        c += 0.02 * vec2(sin(t * 0.1 + fi), cos(t * 0.13 + fi * 2.0)) + vec2(uP[3].z * 0.06, 0.0);
        float r = 0.03 + 0.07 * hash11(fi * 1.3);
        float d = length(sp - c);
        float disc = smoothstep(r, r * 0.9, d) * (0.65 + 0.35 * smoothstep(r * 0.5, r, d));
        vec3 col = mix(vec3(1.0, 0.68, 0.34), vec3(1.0, 0.84, 0.58), hash11(fi * 5.0));
        col = mix(col, vec3(0.55, 0.7, 1.0), uP[2].y * hash11(fi * 9.0));
        acc += col * disc * (0.05 + 0.09 * hash11(fi * 2.2)) * (0.7 + 0.3 * sin(t * 0.6 + fi));
    }
    return acc;
}

float ridge(vec2 p, vec2 a, vec2 b, float w, float bend) {
    vec2 ab = b - a;
    float t = clamp(dot(p - a, ab) / dot(ab, ab), 0.0, 1.0);
    vec2 perp = normalize(vec2(-ab.y, ab.x));
    vec2 c = a + ab * t + perp * bend * sin(PI * t);
    float d = length(p - c);
    return exp(-d * d / (w * w)) * smoothstep(0.0, 0.15, t) * smoothstep(1.0, 0.82, t);
}

float neckRelief(vec2 q) {
    float ten = uP[2].x;
    // the muscle carries the tautness; the vein is a finer vessel crossing it, and it pulses
    float scm = (0.025 + 0.15 * ten) * ridge(q, uP[4].xy, uP[4].zw, 0.011 + 0.004 * ten, 0.012);
    float beat = pow(max(sin(uP[2].z), 0.0), 4.0);
    float vw = 0.0032 + 0.0012 * ten * (0.85 + 0.15 * beat);
    float vein = (0.004 + 0.045 * ten * ten) * (1.0 + 0.2 * ten * beat) * ridge(q, uP[5].xy, uP[5].zw, vw, 0.006);
    float larynx = 0.02 * ten * exp(-dot(q - vec2(-0.016, -0.125), q - vec2(-0.016, -0.125)) / 0.00012);
    return scm + vein + larynx;
}

vec2 faceUV(vec2 q) {
    return vec2((q.x - uP[1].x) / (uP[1].z - uP[1].x), (q.y - uP[1].y) / (uP[1].w - uP[1].y));
}

void main() {
    vec2 sp = screen();
    float t = uTime;
    vec3 col = vec3(0.010, 0.007, 0.005) + bokeh(sp, t);
    vec2 q = (sp - uP[0].xy) / uP[0].z;
    q = rot(-uP[0].w) * q;
    vec2 uv = faceUV(q);
    float tension = uP[2].x;
    vec3 L = normalize(vec3(-0.86, 0.42, 0.34));     // the follow-spot from the front, above
    vec3 R = normalize(vec3(0.9, 0.3, -0.15));       // warm upstage rim behind her
    vec3 key = vec3(1.0, 0.75, 0.46) * 3.4 * uP[2].w;
    vec3 rimC = vec3(1.0, 0.6, 0.32) * 2.4;
    if (all(greaterThan(uv, vec2(0.0))) && all(lessThan(uv, vec2(1.0)))) {
        vec4 F = texture(uFace, uv);
        vec4 Hh = texture(uHairTex, uv);
        vec2 tx = 1.0 / vec2(textureSize(uFace, 0));
        float e = (uP[1].z - uP[1].x) * tx.x;
        float hx = texture(uFace, uv + vec2(tx.x, 0.0)).g - texture(uFace, uv - vec2(tx.x, 0.0)).g;
        float hy = texture(uFace, uv + vec2(0.0, tx.y)).g - texture(uFace, uv - vec2(0.0, tx.y)).g;
        float nr0 = neckRelief(q);
        hx += (neckRelief(q + vec2(e, 0.0)) - neckRelief(q - vec2(e, 0.0))) * F.r;
        hy += (neckRelief(q + vec2(0.0, e)) - neckRelief(q - vec2(0.0, e))) * F.r;
        vec3 n = normalize(vec3(-hx * 26.0, -hy * 26.0, 1.0));
        float mask = F.r;
        if (mask > 0.001) {
            float ndl = dot(n, L);
            float diff = sat((ndl + 0.18) / 1.18);
            float rim = pow(sat(dot(n, R)), 1.8);
            vec3 skin = vec3(0.76, 0.56, 0.46);
            vec3 c = skin * key * diff * diff * diff;
            c += skin * vec3(0.9, 0.35, 0.22) * key * 0.035 * exp(-pow((ndl - 0.05) / 0.08, 2.0))    // subsurface at the terminator
                 * (1.0 - 0.75 * smoothstep(0.01, 0.06, nr0));                                    // (not a red seam on the ridges)
            c += skin * rimC * rim * 0.8;
            c += skin * vec3(0.022, 0.016, 0.014);                       // faint fill from the hall
            vec3 lipC = vec3(0.46, 0.07, 0.09) * key * (0.15 + diff * diff) + vec3(0.02, 0.0, 0.0);
            c = mix(c, lipC, F.b * 0.88);
            vec3 Hv = normalize(L + vec3(0.0, 0.0, 1.0));
            float sp1 = pow(sat(dot(n, Hv)), 40.0);
            float neckShine = smoothstep(0.004, 0.03, nr0);
            c += key * sp1 * (0.08 + 0.6 * F.b + 0.5 * tension * neckShine);
            // the vein: a faint cool line beneath the skin
            float vein = ridge(q, uP[5].xy, uP[5].zw, 0.004 + 0.0015 * tension, 0.006);
            c = mix(c, c * vec3(0.74, 0.82, 1.06), vein * (0.25 + 0.6 * tension));
            c = mix(c, vec3(0.018, 0.01, 0.008), F.a * 0.92);
            col = mix(col, c, mask);
        }
        if (Hh.r > 0.001) {
            float hx2 = texture(uHairTex, uv + vec2(tx.x, 0.0)).b - texture(uHairTex, uv - vec2(tx.x, 0.0)).b;
            float hy2 = texture(uHairTex, uv + vec2(0.0, tx.y)).b - texture(uHairTex, uv - vec2(0.0, tx.y)).b;
            vec3 nh = normalize(vec3(-hx2 * 18.0, -hy2 * 18.0, 1.0));
            vec3 hc = vec3(0.03, 0.019, 0.014) * (0.5 + 1.3 * Hh.g);
            hc += vec3(0.42, 0.27, 0.16) * key * 0.1 * pow(sat(dot(nh, L)), 2.0) * (0.3 + Hh.g);
            hc += rimC * 0.55 * pow(sat(dot(nh, R)), 2.0) * (0.4 + Hh.g);
            col = mix(col, hc, Hh.r);
        }
    }
    // a small pearl drop at the lobe
    vec2 eq = q - uP[3].xy;
    float drop = length(eq * vec2(1.0, 0.7)) - 0.0035;
    vec3 pearl = vec3(0.9, 0.86, 0.8) * (0.15 + key.r * 0.25 * sat(dot(normalize(vec3(eq, 0.003)), L)));
    col = mix(col, pearl, smoothstep(0.0006, -0.0006, drop));
    col += vec3(1.0, 0.95, 0.88) * 0.0000025 / (dot(eq - vec2(-0.0012, 0.0012), eq - vec2(-0.0012, 0.0012)) + 0.0000012);
    // the gown's neckline at the bottom edge
    float neckY = -0.33 + 0.12 * (q.x + 0.1);
    if (q.y < neckY && q.x > -0.25) {
        float a = smoothstep(0.0, 0.004, neckY - q.y);
        vec3 velvet = vec3(0.32, 0.015, 0.03) * key * 0.3 * (0.6 + 0.4 * fbm(q * 80.0));
        velvet += vec3(1.0, 0.3, 0.18) * 0.1 * smoothstep(0.03, 0.0, neckY - q.y);
        col = mix(col, velvet, a);
    }
    col = mix(col, col * vec3(0.78, 0.88, 1.15), uP[2].y * 0.5);
    fragColor = vec4(col, 1.0);
}
