#version 430
// Typography and the luminous leitmotif lines, drawn over the composited HDR scene.
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D uScene;
uniform sampler2D uText0;
uniform sampler2D uText1;
uniform sampler2D uText2;
uniform sampler2D uText3;
uniform vec4 uTextRect[4];    // x0, y0, x1, y1 in uv (y up)
uniform vec4 uTextParam[4];   // reveal (0..1 of width), alpha, style, glow
uniform vec4 uTextTint[4];    // rgb tint, active-syllable centre x
uniform int uNText;
// motif lines: up to 4 polylines of up to 96 points each
uniform vec4 uLinePts[384];   // x, y (uv), alpha, width(px)
uniform int uLineN[4];
uniform vec4 uLineCol[4];     // rgb, glow
uniform float uTime;
uniform vec2 uRes;

float sdSeg(vec2 p, vec2 a, vec2 b) { vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-9), 0.0, 1.0); return length(pa - ba * h); }

vec4 sampleText(int i, vec2 uv) {
    if (i == 0) return texture(uText0, uv);
    if (i == 1) return texture(uText1, uv);
    if (i == 2) return texture(uText2, uv);
    return texture(uText3, uv);
}

void main() {
    vec3 c = texture(uScene, v_uv).rgb;
    vec2 px = v_uv * uRes;
    // ---- motif lines
    for (int L = 0; L < 4; L++) {
        int n = uLineN[L];
        if (n < 2) continue;
        float best = 1e9;
        float aBest = 0.0;
        float wBest = 1.0;
        for (int k = 0; k < 95; k++) {
            if (k >= n - 1) break;
            vec4 a = uLinePts[L * 96 + k];
            vec4 b = uLinePts[L * 96 + k + 1];
            if (a.z <= 0.001 && b.z <= 0.001) continue;
            vec2 pa = a.xy * uRes, pb = b.xy * uRes;
            float d = sdSeg(px, pa, pb);
            if (d < best) {
                best = d;
                vec2 ba = pb - pa;
                float h = clamp(dot(px - pa, ba) / max(dot(ba, ba), 1e-9), 0.0, 1.0);
                aBest = mix(a.z, b.z, h);
                wBest = mix(a.w, b.w, h);
            }
        }
        float core = smoothstep(wBest + 1.0, wBest - 1.0, best);
        float halo = exp(-best / (wBest * 4.0 + 6.0)) * uLineCol[L].a;
        c += uLineCol[L].rgb * (core * 1.6 + halo) * aBest;
    }
    // ---- typography
    for (int i = 0; i < 4; i++) {
        if (i >= uNText) break;
        vec4 r = uTextRect[i];
        if (v_uv.x < r.x || v_uv.x > r.z || v_uv.y < r.y || v_uv.y > r.w) continue;
        vec2 tuv = (v_uv - r.xy) / (r.zw - r.xy);
        vec4 tx = sampleText(i, vec2(tuv.x, tuv.y));
        // the texture's red channel = Italian glyphs, green = English, blue = shadow
        float reveal = uTextParam[i].x;
        float alpha = uTextParam[i].y;
        float sung = smoothstep(reveal + 0.004, reveal - 0.004, tuv.x);
        float actv = exp(-pow((tuv.x - uTextTint[i].w) * 30.0, 2.0)) * uTextParam[i].w;
        vec3 tint = uTextTint[i].rgb;
        float it = tx.r;
        float en = tx.g;
        float sh = tx.b;
        c *= 1.0 - sh * (0.55 + 0.4 * uTextParam[i].z) * alpha;   // z = 1: a caption's deeper shadow
        vec3 itCol = tint * (0.32 + 0.68 * sung) + tint * actv * 0.9;
        c = mix(c, itCol * 1.15, it * alpha);
        c = mix(c, vec3(0.78, 0.76, 0.72), en * alpha * 0.85);
    }
    fragColor = vec4(c, 1.0);
}
