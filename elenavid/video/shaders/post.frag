#version 430
// Post-processing passes, selected by uPass:
//  0 composite A/B (mix modes)   1 bright-pass + downsample   2 blur   3 upsample-add   4 final grade
in vec2 v_uv;
out vec4 fragColor;
uniform int uPass;
uniform sampler2D uTexA;
uniform sampler2D uTexB;
uniform vec2 uTexel;          // 1 / size of the source texture
uniform vec2 uDir;            // blur direction
uniform float uMix;           // composite amount
uniform int uMode;            // composite mode: 0 cross-fade, 1 dip to black, 2 white flash, 3 curtain
uniform float uTime;
uniform float uRes_y;
// grade
uniform float uExposure;
uniform float uTemp;
uniform float uSat;
uniform float uContrast;
uniform vec3 uLift;
uniform float uVignette;
uniform float uGrain;
uniform float uFade;          // 0 = picture, 1 = black
uniform float uBloomAmt;
uniform float uAberr;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

vec3 aces(vec3 x) {
    const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main() {
    if (uPass == 0) {
        vec3 a = texture(uTexA, v_uv).rgb;
        vec3 b = texture(uTexB, v_uv).rgb;
        vec3 c;
        if (uMode == 0) c = mix(a, b, uMix);
        else if (uMode == 1) c = (uMix < 0.5) ? a * (1.0 - 2.0 * uMix) : b * (2.0 * uMix - 1.0);
        else if (uMode == 2) { float f = 1.0 - abs(2.0 * uMix - 1.0); c = mix(a, b, smoothstep(0.45, 0.55, uMix)) + vec3(f * f * 3.0); }
        else {  // curtain: crimson velvet closes on A, opens on B
            float close = 1.0 - abs(2.0 * uMix - 1.0);
            float x = abs(v_uv.x - 0.5) * 2.0;
            float edge = 1.0 - close;
            float folds = 0.6 + 0.4 * sin(v_uv.x * 90.0 + sin(v_uv.y * 3.0)) * sin(v_uv.x * 37.0);
            vec3 vel = vec3(0.42, 0.03, 0.05) * folds * (0.7 + 0.3 * v_uv.y);
            float m = smoothstep(edge - 0.01, edge + 0.01, x);
            vec3 pic = (uMix < 0.5) ? a : b;
            c = mix(pic, vel, m);
        }
        fragColor = vec4(c, 1.0);
    } else if (uPass == 1) {
        vec3 s = vec3(0.0);
        for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++)
            s += texture(uTexA, v_uv + vec2(i, j) * uTexel).rgb;
        s /= 9.0;
        float l = max(s.r, max(s.g, s.b));
        float k = smoothstep(1.1, 2.8, l);
        fragColor = vec4(s * k, 1.0);
    } else if (uPass == 2) {
        vec3 s = texture(uTexA, v_uv).rgb * 0.227027;
        s += texture(uTexA, v_uv + uDir * uTexel * 1.3846).rgb * 0.3162162;
        s += texture(uTexA, v_uv - uDir * uTexel * 1.3846).rgb * 0.3162162;
        s += texture(uTexA, v_uv + uDir * uTexel * 3.2308).rgb * 0.0702703;
        s += texture(uTexA, v_uv - uDir * uTexel * 3.2308).rgb * 0.0702703;
        fragColor = vec4(s, 1.0);
    } else if (uPass == 3) {
        fragColor = vec4(texture(uTexA, v_uv).rgb + texture(uTexB, v_uv).rgb * 0.8, 1.0);
    } else {
        vec2 d = v_uv - 0.5;
        vec3 c;
        c.r = texture(uTexA, v_uv - d * uAberr).r;
        c.g = texture(uTexA, v_uv).g;
        c.b = texture(uTexA, v_uv + d * uAberr).b;
        c += texture(uTexB, v_uv).rgb * uBloomAmt;
        c *= uExposure;
        c *= vec3(1.0 + 0.10 * uTemp, 1.0 + 0.015 * uTemp, 1.0 - 0.12 * uTemp);
        c = c + uLift * (1.0 - c);
        c = aces(c);
        float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
        c = mix(vec3(l), c, uSat);
        c = clamp((c - 0.5) * uContrast + 0.5, 0.0, 1.0);
        float v = 1.0 - uVignette * pow(length(d * vec2(1.0, 0.8)) * 1.35, 2.2);
        c *= clamp(v, 0.0, 1.0);
        float g = hash(v_uv * 1000.0 + fract(uTime * 37.0)) - 0.5;
        c += g * uGrain * (0.6 + 0.4 * (1.0 - l));
        c *= 1.0 - uFade;
        fragColor = vec4(pow(clamp(c, 0.0, 1.0), vec3(1.0 / 1.0)), 1.0);
    }
}
