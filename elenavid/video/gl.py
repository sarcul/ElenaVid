"""GPU plumbing: a headless OpenGL 4.3 context, HDR framebuffers, shader programs, bloom."""
from __future__ import annotations

from pathlib import Path

import moderngl
import numpy as np

from ..config import W, H

SHADER_DIR = Path(__file__).parent / "shaders"

VERT = """
#version 430
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""


def load_source(name: str) -> str:
    """Concatenate common.glsl with a scene shader (simple #include replacement)."""
    src = (SHADER_DIR / name).read_text(encoding="utf-8")
    common = (SHADER_DIR / "common.glsl").read_text(encoding="utf-8")
    return src.replace("#include common", common)


class GPU:
    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.ctx = moderngl.create_standalone_context(require=430)
        self.quad = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4"))
        self.progs = {}
        self.vaos = {}
        self.tex = {}
        self.fbo_scene = [self._target(w, h) for _ in range(2)]
        self.fbo_comp = self._target(w, h)
        self.fbo_over = self._target(w, h)
        # bloom pyramid
        self.bloom = []
        bw, bh = w // 2, h // 2
        for _ in range(5):
            self.bloom.append((self._target(bw, bh), self._target(bw, bh)))
            bw, bh = max(1, bw // 2), max(1, bh // 2)
        self.fbo_out = self.ctx.framebuffer(color_attachments=[self.ctx.texture((w, h), 3, dtype="f1")])

    def _target(self, w, h):
        t = self.ctx.texture((w, h), 4, dtype="f2")
        t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        t.repeat_x = False
        t.repeat_y = False
        return self.ctx.framebuffer(color_attachments=[t])

    def program(self, key, frag_name):
        if key not in self.progs:
            src = load_source(frag_name)
            try:
                prog = self.ctx.program(vertex_shader=VERT, fragment_shader=src)
            except moderngl.Error as e:
                raise RuntimeError(f"shader {frag_name} failed:\n{e}") from None
            self.progs[key] = prog
            self.vaos[key] = self.ctx.vertex_array(prog, [(self.quad, "2f", "in_pos")])
        return self.progs[key]

    def set(self, key, **uniforms):
        prog = self.progs[key]
        for k, v in uniforms.items():
            if k in prog:
                try:
                    if isinstance(v, np.ndarray):
                        u = prog[k]
                        n = getattr(u, "array_length", 1) or 1
                        arr = v.astype("f4")
                        if arr.ndim == 2:
                            arr = arr[:n]
                        elif n > 1:
                            arr = arr[: n * u.dimension]
                        prog[k].write(np.ascontiguousarray(arr).tobytes())
                    else:
                        prog[k].value = v
                except Exception as e:
                    raise RuntimeError(f"uniform {k} on {key}: {e}") from None

    def draw(self, key, fbo, textures=()):
        fbo.use()
        for unit, (name, tex) in enumerate(textures):
            tex.use(location=unit)
            if name in self.progs[key]:
                self.progs[key][name].value = unit
        self.vaos[key].render(moderngl.TRIANGLE_STRIP)

    def texture_rgba(self, key, img: np.ndarray):
        """Upload (h, w, 4) uint8 as a texture (flipped to GL orientation)."""
        h, w = img.shape[:2]
        if key in self.tex and self.tex[key].size == (w, h):
            self.tex[key].write(np.ascontiguousarray(img[::-1]).tobytes())
            return self.tex[key]
        t = self.ctx.texture((w, h), 4, data=np.ascontiguousarray(img[::-1]).tobytes())
        t.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        t.build_mipmaps()
        t.repeat_x = False
        t.repeat_y = False
        self.tex[key] = t
        return t

    def read(self):
        return np.frombuffer(self.fbo_out.read(components=3, dtype="f1"), dtype=np.uint8).reshape(
            self.h, self.w, 3)[::-1]
