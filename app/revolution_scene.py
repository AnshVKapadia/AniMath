"""Standalone, bounded-cost Manim template for the first 3D scene family."""
from manim import *

INNER_IS_ZERO = False
OUTER_EXPRESSION = "np.sqrt(x)"
INNER_EXPRESSION = "x"
OUTER_TEX = r"\sqrt{x}"
INNER_TEX = r"x"
X_START = 0.0
X_END = 1.0
VOLUME_APPROX = 0.1666666667

FRAME_WIDTH = 14.22
FRAME_HEIGHT = 8.0
HEADER_HEIGHT = 0.9
FOOTER_HEIGHT = 1.15


def fit_to_box(mobject, max_width, max_height):
    """Shrink an overlay without changing its aspect ratio."""
    if mobject.width > max_width:
        mobject.scale_to_fit_width(max_width)
    if mobject.height > max_height:
        mobject.scale_to_fit_height(max_height)
    return mobject


def overlay_panel(*mobjects, edge=UP, max_height=HEADER_HEIGHT):
    """Create an opaque, camera-fixed rail for explanatory material."""
    content = VGroup(*mobjects).arrange(DOWN, buff=0.08)
    fit_to_box(content, FRAME_WIDTH - 0.7, max_height - 0.14)
    background = BackgroundRectangle(
        content,
        buff=0.12,
        fill_color="#101820",
        fill_opacity=0.94,
        stroke_width=0,
    )
    panel = VGroup(background, content)
    panel.to_edge(edge, buff=0.08)
    return panel


def validate_fixed_layout(**named_mobjects):
    """Fail loudly if fixed overlays escape the frame or collide."""
    frame_left, frame_right = -FRAME_WIDTH / 2, FRAME_WIDTH / 2
    frame_bottom, frame_top = -FRAME_HEIGHT / 2, FRAME_HEIGHT / 2
    for name, mob in named_mobjects.items():
        if (
            mob.get_left()[0] < frame_left
            or mob.get_right()[0] > frame_right
            or mob.get_bottom()[1] < frame_bottom
            or mob.get_top()[1] > frame_top
        ):
            raise ValueError(f"{name} leaves the safe frame")
    items = list(named_mobjects.items())
    for index, (first_name, first) in enumerate(items):
        for second_name, second in items[index + 1 :]:
            separated = (
                first.get_right()[0] <= second.get_left()[0]
                or second.get_right()[0] <= first.get_left()[0]
                or first.get_top()[1] <= second.get_bottom()[1]
                or second.get_top()[1] <= first.get_bottom()[1]
            )
            if not separated:
                raise ValueError(f"{first_name} overlaps {second_name}")


class GeneratedScene(ThreeDScene):
    def construct(self):
        self.camera.background_color = "#101820"
        outer = lambda x: eval(OUTER_EXPRESSION, {"__builtins__": {}, "np": np}, {"x": x})
        inner = lambda x: eval(INNER_EXPRESSION, {"__builtins__": {}, "np": np}, {"x": x})
        sample_x = np.linspace(X_START, X_END, 257)
        max_radius = max(float(np.max(outer(sample_x))), 0.5)
        x_padding = max(0.08 * (X_END - X_START), 0.1)
        radius_limit = 1.2 * max_radius
        axes = ThreeDAxes(x_range=[X_START, X_END + x_padding, (X_END-X_START)/4],
                          y_range=[-radius_limit, radius_limit, radius_limit/2],
                          z_range=[-radius_limit, radius_limit, radius_limit/2], x_length=4.2,
                          y_length=5.4, z_length=5.4, tips=False)
        axes.move_to(ORIGIN)
        p = axes.c2p
        self.set_camera_orientation(phi=0, theta=-90*DEGREES, zoom=.85)
        title = MathTex(r"\text{Disks and washers in 3D}", font_size=32)
        subtitle = MathTex(r"\text{Rotate the shaded region about the }x\text{-axis}", font_size=24)
        header = overlay_panel(title, subtitle)
        self.add_fixed_in_frame_mobjects(header)
        self.add(axes)
        axis_label = MathTex("x", font_size=24).move_to(p(X_END + 1.1*x_padding, 0, 0))
        self.add_fixed_orientation_mobjects(axis_label)
        curves = MathTex(
            r"R(x)=" + OUTER_TEX + r",\qquad r(x)=" + INNER_TEX
            + rf",\qquad {X_START:g}\le x\le {X_END:g}",
            font_size=26,
        )
        curves_panel = overlay_panel(curves, edge=DOWN, max_height=0.65)
        validate_fixed_layout(header=header, footer=curves_panel)
        self.add_fixed_in_frame_mobjects(curves_panel)
        upper = ParametricFunction(lambda x: p(x, outer(x), 0), t_range=[X_START,X_END], color=BLUE_C)
        lower = ParametricFunction(lambda x: p(x, inner(x), 0), t_range=[X_START,X_END], color=YELLOW)
        region = Surface(lambda x,t: p(x, inner(x)+t*(outer(x)-inner(x)), 0),
                         u_range=[X_START,X_END], v_range=[0,1], resolution=(16,2),
                         checkerboard_colors=[TEAL,TEAL], fill_opacity=.55, stroke_width=0)
        self.play(Create(upper), Create(lower), FadeIn(region), run_time=2)
        self.wait(1)
        self.remove(curves_panel)
        self.move_camera(phi=65*DEGREES, theta=-55*DEGREES, run_time=2)
        # Reveal fixed mesh sectors while the generating region rotates. This avoids
        # rebuilding a dense surface every frame and shows a genuine sweep in 3D.
        outer_sectors = VGroup()
        inner_sectors = VGroup()
        for k in range(12):
            angles = [k*TAU/12, (k+1)*TAU/12]
            outer_sectors.add(Surface(lambda x,t: p(x,outer(x)*np.cos(t),outer(x)*np.sin(t)),
                u_range=[X_START,X_END],v_range=angles,resolution=(12,3),checkerboard_colors=[BLUE_D,BLUE_D],
                fill_opacity=.25,stroke_width=.25))
            if not INNER_IS_ZERO:
                inner_sectors.add(Surface(lambda x,t: p(x,inner(x)*np.cos(t),inner(x)*np.sin(t)),
                    u_range=[X_START,X_END],v_range=angles,resolution=(12,3),checkerboard_colors=[YELLOW_D,YELLOW_D],
                    fill_opacity=.2,stroke_width=.25))
        rotating = VGroup(region,upper,lower)
        self.play(Rotate(rotating,angle=TAU,axis=RIGHT,about_point=p(X_START,0,0)),
                  LaggedStart(*[FadeIn(s) for s in outer_sectors],lag_ratio=.1),
                  LaggedStart(*[FadeIn(s) for s in inner_sectors],lag_ratio=.1) if len(inner_sectors) else Wait(4),
                  run_time=4,rate_func=linear)
        self.play(FadeOut(rotating),run_time=.5)
        self.move_camera(theta=-30*DEGREES,run_time=2)
        self.play(FadeOut(outer_sectors),FadeOut(inner_sectors),run_time=.5)
        # Annular faces are perpendicular to x; radius varies over the true annulus.
        def washer(x, color=TEAL):
            return Surface(lambda r,t: p(x,r*np.cos(t),r*np.sin(t)),
                u_range=[inner(x),outer(x)],v_range=[0,TAU],resolution=(2,32),
                checkerboard_colors=[color,color],fill_opacity=.65,stroke_width=.2)
        edge_buffer = 0.08 * (X_END-X_START)
        slices=VGroup(*[washer(x) for x in np.linspace(X_START+edge_buffer,X_END-edge_buffer,10)])
        self.play(LaggedStart(*[FadeIn(s) for s in slices],lag_ratio=.1),run_time=2)
        self.wait(1)
        self.play(FadeOut(slices),run_time=.5)
        x=X_START + .6*(X_END-X_START)
        dx=.06*(X_END-X_START)
        face=washer(x,ORANGE)
        back=face.copy().shift(p(x+dx,0,0)-p(x,0,0))
        walls=VGroup(*[Surface(lambda s,t,r=r: p(s,r*np.cos(t),r*np.sin(t)),
            u_range=[x,x+dx],v_range=[0,TAU],resolution=(1,32),
            checkerboard_colors=[ORANGE,ORANGE],fill_opacity=.65,stroke_width=.2)
            for r in ([outer(x)] if INNER_IS_ZERO else [outer(x),inner(x)])])
        radii=VGroup(Line(p(x,0,0),p(x,0,outer(x)),color=BLUE_C),
                     Line(p(x,0,0),p(x,inner(x),0),color=YELLOW))
        thickness=Line(p(x,-outer(x),0),p(x+dx,-outer(x),0),color=WHITE)
        self.play(FadeIn(face),FadeIn(back),FadeIn(walls),Create(radii),Create(thickness),run_time=1.5)
        self.remove(header)
        radii_text = MathTex(
            r"\text{Outer radius: }R(x)=" + OUTER_TEX + r"\qquad"
            + r"\text{Inner radius: }r(x)=" + INNER_TEX
            + r"\qquad\text{Thickness: }dx",
            font_size=24,
        )
        detail_header = overlay_panel(title.copy(), radii_text)
        area = MathTex(
            r"A(x)=\pi R(x)^2" if INNER_IS_ZERO else r"A(x)=\pi\!\left(R(x)^2-r(x)^2\right)",
            font_size=28,
        )
        result = MathTex(
            rf"V=\int_{{{X_START:g}}}^{{{X_END:g}}}A(x)\,dx\approx {VOLUME_APPROX:.4g}",
            font_size=28,
        )
        formula_footer = overlay_panel(area, result, edge=DOWN, max_height=FOOTER_HEIGHT)
        validate_fixed_layout(header=detail_header, footer=formula_footer)
        self.add_fixed_in_frame_mobjects(detail_header, formula_footer)
        self.wait(3)
        self.remove(detail_header)
        note = MathTex(r"\text{A disk is a washer with inner radius }0", font_size=25)
        note_header = overlay_panel(title.copy(), note)
        validate_fixed_layout(header=note_header, footer=formula_footer)
        self.add_fixed_in_frame_mobjects(note_header)
        if not INNER_IS_ZERO:
            self.remove(area,result)
            disk=Surface(lambda r,t:p(x,r*np.cos(t),r*np.sin(t)),u_range=[0,outer(x)],
                v_range=[0,TAU],resolution=(2,32),checkerboard_colors=[ORANGE,ORANGE],fill_opacity=.65,stroke_width=.2)
            self.play(FadeOut(back),FadeOut(walls),FadeOut(radii),FadeOut(thickness),Transform(face,disk),run_time=1.5)
        self.wait(2)
