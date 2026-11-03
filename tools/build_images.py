"""自动生成 TrackForm 用户手册全套高清配图（面向终端用户）。

包含：
1. 封面图 cover.jpg / cover_small.jpg
2. 全部 32 张参数定义与红色高亮示意图（直接调用 trackform.tipfig）
3. 8 组关键参数调整前后对比图（Before vs After）
4. 右侧 6 大图形页签高清标准图与局部放大/工具栏操作图
5. 真实导出 DXF 文件（tool_profile.dxf, arc_tool.dxf, part_section.dxf）的 CAD 预览渲染图
6. 界面布局导览图、悬停提示卡片实景图、截面模式切换图、状态栏与结果面板正常/报警对比图、菜单与案例汇总图
"""
from __future__ import annotations

import os
import sys
import tempfile

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Rectangle
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 引入 TrackForm 项目源码路径
TRACKFORM_ROOT = r"C:\Users\Marco Nie\Development\WorkProgram\TrackForm"
GUIDE_ROOT = r"C:\Users\Marco Nie\Development\WorkProgram\TrackForm-UserGuide"
sys.path.insert(0, TRACKFORM_ROOT)

from trackform import __version__, tipfig
from trackform.arc_tool import evaluate_arc, fit_arc, table1_check, table1_constants, table2_from_equation
from trackform.dxf_export import export_arc_dxf, export_dxf, export_part_dxf
from trackform.envelope import arc_r, compute_profile, overcut_check, phi_range, simulate_section, tool_frame
from trackform.fields import EXPORT_TIPS, FIELDS, UNITS
from trackform.geometry import BASIC_END, GothicSection, Params, SECTION_TYPES, SOLVE_MODES, TABLE_BASIS, solve_section
from trackform.part import part_section
from trackform.plots import PlotsMixin
from tools.make_icon import draw as draw_app_icon

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

DPI = 160
HL = "#d62728"
BLUE = "#1f6fd1"
NAVY = "#2f5d8c"
GREEN = "#2e7d32"
ORANGE = "#d97706"
GRAY = "#64748b"


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def save_fig(fig: Figure, path: str, dpi: int = DPI, pad: float = 0.08):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    FigureCanvasAgg(fig)
    fig.savefig(path, dpi=dpi, facecolor="white", bbox_inches="tight", pad_inches=pad)
    plt.close(fig)
    print(f"  [OK] {os.path.relpath(path, GUIDE_ROOT)}")


class DummyHost(PlotsMixin):
    """复用 TrackForm 的 PlotsMixin 渲染 6 大图形页签。"""

    def __init__(self, params: Params):
        self.params = params
        self.prof = compute_profile(params)
        _, self._gap = overcut_check(self.prof, n_t=301, n_phi=401)
        sim = simulate_section(self.prof, n_y=121, n_phi=801)
        self._sim_y, self._ug, self._ud, self._dev = sim
        dec = params.arc_decimals if params.arc_decimals >= 0 else None
        self.arc_eval = evaluate_arc(self.prof, fit_arc(self.prof, dec), params.profile_tol,
                                     params.n_basic, n_y=161, n_phi=1001)
        ev_t = (evaluate_arc(self.prof, fit_arc(self.prof, None), params.profile_tol,
                             params.n_basic, n_y=161, n_phi=1001)
                if params.table_basis == "fit" and dec is not None else self.arc_eval)
        C = table1_constants(params, ev_t.tool, ev_t.ball_height)
        basic = table2_from_equation(C, params.n_basic) if params.basic_end == "c9" else ev_t.basic
        self.table = dict(C=C, check=table1_check(C, ev_t.basic), basis=TABLE_BASIS[params.table_basis],
                          ev=ev_t, basic=basic, end=BASIC_END[params.basic_end])
        self.figs = {}
        for k in ("tool", "section", "part", "pose", "sim", "arc"):
            f = Figure(figsize=(11.2, 6.4) if k == "arc" else (8.6, 6.4), dpi=DPI)
            c = FigureCanvasAgg(f)
            self.figs[k] = (f, c)

    def render_all(self):
        self._plot_tool()
        self._plot_section()
        self._plot_part()
        self._plot_pose()
        self._plot_sim(self._sim_y, self._ug, self._ud, self._dev)
        self._plot_arc()


# =============================================================================
# 1. 生成封面图 cover.jpg & cover_small.jpg
# =============================================================================
def build_covers():
    print("=== 1. 生成封面图 ===")
    W, H = 1200, 1600
    img = Image.new("RGB", (W, H), (14, 34, 64))
    draw = ImageDraw.Draw(img)
    # 渐变深蓝科技底色
    for y in range(H):
        t = y / (H - 1)
        r = int(18 + (8 - 18) * t)
        g = int(46 + (22 - 46) * t)
        b = int(88 + (48 - 88) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 工程图纸网格暗纹
    grid_col = (28, 64, 112)
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=grid_col, width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=grid_col, width=1)

    # 顶部装饰条
    draw.rectangle([0, 0, W, 18], fill=(46, 134, 222))

    # 绘制软件高清图标居中偏上
    icon = draw_app_icon().resize((460, 460), Image.LANCZOS)
    img.paste(icon, ((W - 460) // 2, 200), icon)

    # 加载中文字体
    font_path = r"C:\Windows\Fonts\msyhbd.ttc"
    font_reg = r"C:\Windows\Fonts\msyh.ttc"
    f_title = ImageFont.truetype(font_path, 88)
    f_sub = ImageFont.truetype(font_path, 46)
    f_desc = ImageFont.truetype(font_reg, 30)
    f_foot = ImageFont.truetype(font_reg, 26)

    draw.text((W // 2, 740), "TrackForm", font=f_title, fill=(255, 255, 255), anchor="mm")
    draw.text((W // 2, 835), "星形套球道成型刀具设计软件", font=f_sub, fill=(130, 204, 255), anchor="mm")
    draw.line([(W // 2 - 260, 900), (W // 2 + 260, 900)], fill=(68, 138, 208), width=3)
    draw.text((W // 2, 955), "用户操作指南  User Guide", font=f_desc, fill=(220, 235, 250), anchor="mm")

    # 中下部：放一张半透明工程廓形示意卡片
    p = Params()
    prof = compute_profile(p)
    fig = Figure(figsize=(8.0, 3.2), dpi=150)
    FigureCanvasAgg(fig)
    fig.patch.set_alpha(0.0)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    for ax in (ax1, ax2):
        ax.set_facecolor((0.08, 0.18, 0.34, 0.75))
        for sp in ax.spines.values():
            sp.set_color("#4a7ab5")
        ax.tick_params(colors="#a5c4e8", labelsize=8)
        ax.grid(color="#2c5282", alpha=0.5, ls="--")
    r, z = prof.full()
    ax1.plot(r, z, color="#4ade80", lw=1.6, label="刀尖允许边界")
    ax1.plot(-r, z, color="#4ade80", lw=1.6)
    ax1.plot(prof.r, prof.z, color="#f87171", lw=2.5, label="精确接触刃口")
    ax1.plot(-prof.r, prof.z, color="#f87171", lw=2.5)
    th = np.linspace(0, 2 * np.pi, 200)
    ax1.plot(p.rb * np.cos(th), p.rb * np.sin(th), "--", color="#94a3b8", lw=0.9)
    ax1.set_aspect("equal")
    ax1.set_title("成型刀具轴截面廓形", color="white", fontsize=11)

    tt = np.linspace(-prof.t_edge, prof.t_edge, 300)
    y, u = prof.section.point(tt)
    ax2.plot(y, u, color="#38bdf8", lw=2.2)
    ax2.plot(p.rb * np.cos(th), p.rb * np.sin(th), "--", color="#fbbf24", lw=1.0)
    ax2.set_aspect("equal")
    ax2.set_ylim(-p.rb - 1.2, 3.0)
    ax2.set_title("球道法向截面与钢球接触", color="white", fontsize=11)
    fig.tight_layout()

    buf_path = os.path.join(tempfile.gettempdir(), "cover_sub.png")
    fig.savefig(buf_path, dpi=150, transparent=True)
    plt.close(fig)
    sub_im = Image.open(buf_path).resize((960, 384), Image.LANCZOS)
    img.paste(sub_im, ((W - 960) // 2, 1030), sub_im)

    draw.text((W // 2, 1490), f"版本 v{__version__}  |  https://trackform-manual.niekun.net",
              font=f_foot, fill=(160, 190, 225), anchor="mm")
    draw.text((W // 2, 1535), "XinCore Studio", font=f_foot, fill=(120, 155, 195), anchor="mm")

    cover_path = os.path.join(GUIDE_ROOT, "cover.jpg")
    cover_sm_path = os.path.join(GUIDE_ROOT, "cover_small.jpg")
    img.save(cover_path, "JPEG", quality=92)
    img.resize((240, 320), Image.LANCZOS).save(cover_sm_path, "JPEG", quality=90)
    print("  [OK] cover.jpg & cover_small.jpg")


# =============================================================================
# 2. 生成全部 32 张参数定义示意图（调用 tipfig.render_png）
# =============================================================================
def build_tipfig_images():
    print("=== 2. 生成 32 张参数定义示意图 (tipfig) ===")
    ch2_dir = ensure_dir(os.path.join(GUIDE_ROOT, "2_basic_params", "resources"))
    ch3_dir = ensure_dir(os.path.join(GUIDE_ROOT, "3_advanced_params", "resources"))

    basic_keys = [
        "ball_d", "pcd", "track_offset",
        "section_type", "solve_mode", "pressure_angle", "conformity", "clearance",
        "ellipse_a", "ellipse_b", "ellipse_uc", "points_file", "points_tol", "allowance",
        "setting_angle",
        "sphere_d", "width", "sphere_center_h",
    ]
    adv_keys = [
        "tip_z", "tip_relief", "tip_relief_len", "extra_extend", "profile_step",
        "gauge_length", "tilt_side",
        "bore_d",
        "clearance_min", "profile_tol",
        "arc_decimals",
        "n_basic", "basic_end", "table_basis",
    ]

    for k in basic_keys:
        png = tipfig.render_png(k, dpi=180)
        out = os.path.join(ch2_dir, f"tip_{k}.png")
        with open(out, "wb") as f:
            f.write(png)
        print(f"  [OK] 2_basic_params/resources/tip_{k}.png")

    for k in adv_keys:
        png = tipfig.render_png(k, dpi=180)
        name = "tip_clearance_limits.png" if k == "clearance_min" else f"tip_{k}.png"
        out = os.path.join(ch3_dir, name)
        with open(out, "wb") as f:
            f.write(png)
        print(f"  [OK] 3_advanced_params/resources/{name}")


# =============================================================================
# 3. 生成第 1 章：界面布局解剖图、悬停提示实景图、截面模式切换图、状态栏与快速上手图
# =============================================================================
def build_ch1_images():
    print("=== 3. 生成第 1 章界面导览与交互配图 ===")
    res = ensure_dir(os.path.join(GUIDE_ROOT, "1_getting_started", "resources"))

    # 3.1 主界面六大分区解剖图 (ui_main_annotated.png)
    p = Params()
    host = DummyHost(p)
    host.render_all()
    tab1_fig = host.figs["tool"][0]
    tmp_tab = os.path.join(tempfile.gettempdir(), "tab1_tmp.png")
    tab1_fig.savefig(tmp_tab, dpi=130, facecolor="white")
    tab_im = Image.open(tmp_tab)

    fig = Figure(figsize=(14.5, 9.2), dpi=150)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1450)
    ax.set_ylim(920, 0)
    ax.axis("off")

    # 窗口背景与标题栏
    ax.add_patch(Rectangle((10, 10), 1430, 900, fc="#f0f2f5", ec="#2f5d8c", lw=2))
    ax.add_patch(Rectangle((10, 10), 1430, 34, fc="#1e293b", ec="none"))
    ax.text(24, 28, f"TrackForm  星形套球道成型刀具设计  v{__version__}", color="white", fontsize=11, fontweight="bold", va="center")
    ax.text(1420, 28, "—   □   ×", color="white", fontsize=11, ha="right", va="center")

    # ① 菜单栏
    ax.add_patch(Rectangle((12, 44), 1426, 28, fc="white", ec="#cbd5e1", lw=1))
    ax.text(26, 59, "文件(F)      计算(C)      导出(E)      视图(V)      帮助(H)", color="#1e293b", fontsize=10, va="center")

    # 左侧面板容器 (x=18..365)
    # ② 输入参数卡片
    ax.add_patch(Rectangle((18, 78), 345, 445, fc="white", ec="#9fb0c4", lw=1.2))
    ax.add_patch(Rectangle((18, 78), 345, 26, fc="#2f5d8c", ec="none"))
    ax.text(28, 92, "输入参数", color="white", fontsize=10, fontweight="bold", va="center")
    ax.text(28, 118, "基本参数（决定齿形）", color="#1e293b", fontsize=9, fontweight="bold", va="center")

    groups_preview = [
        ("① 钢球与球道轨迹", [("钢球直径 Dw", "19.844", "mm"), ("节圆直径 PCD", "62.464", "mm"), ("球道偏移 e", "4.27", "mm")]),
        ("② 球道法向截面", [("截面类型", "椭圆  [v]", ""), ("定义方式", "给定相似度  [v]", ""), ("接触角 α", "42.0", "°"), ("相似度 k", "1.04", ""), ("法向余量", "0.0", "mm")]),
        ("③ 刀具安装", [("切入角 β", "36.0", "°")]),
        ("④ 工件外形", [("外球面直径", "61.113", "mm"), ("工件宽度 W", "23.1", "mm"), ("球心至端面 H", "13.31", "mm")]),
    ]
    yy = 132
    for gtitle, rows in groups_preview:
        h_box = 20 + len(rows) * 21
        ax.add_patch(Rectangle((24, yy), 332, h_box, fc="#f8fafc", ec="#cbd5e1", lw=0.8))
        ax.text(32, yy + 11, gtitle, color="#2f5d8c", fontsize=8.5, fontweight="bold", va="center")
        for idx, (lbl, val, unit) in enumerate(rows):
            ry = yy + 25 + idx * 20
            ax.text(32, ry, lbl, color="#334155", fontsize=8.5, va="center")
            ax.add_patch(Rectangle((150, ry - 8), 165, 16, fc="white", ec="#94a3b8", lw=0.7))
            ax.text(156, ry, val, color="#0f172a", fontsize=8.5, va="center")
            ax.text(322, ry, unit, color="#64748b", fontsize=8, va="center")
        yy += h_box + 5

    ax.add_patch(Rectangle((24, yy + 2), 332, 24, fc="#e2e8f0", ec="#94a3b8", lw=0.8))
    ax.text(190, yy + 14, "[+] 高级参数（点击展开刀尖、刀柄、公差与导出设置）", color="#1e293b", fontsize=8.5, ha="center", va="center")

    # ③ 计算与导出卡片
    ax.add_patch(Rectangle((18, 531), 345, 165, fc="white", ec="#9fb0c4", lw=1.2))
    ax.add_patch(Rectangle((18, 531), 345, 26, fc="#2f5d8c", ec="none"))
    ax.text(28, 545, "计算与导出", color="white", fontsize=10, fontweight="bold", va="center")
    ax.add_patch(Rectangle((26, 563), 329, 32, fc="#2e7d32", ec="none"))
    ax.text(190, 579, ">>  计 算   (F5)", color="white", fontsize=11, fontweight="bold", ha="center", va="center")
    ax.text(28, 608, "计算完成（0.8 s）", color="#2e7d32", fontsize=8.5, va="center")
    exp_btns = ["刀具 DXF", "刀具点表 CSV", "圆弧刀具 DXF", "星形套截面 DXF", "方程常数（Table 1）", "基本轮廓（Table 2）"]
    for i, btxt in enumerate(exp_btns):
        bx = 26 + (i % 2) * 166
        by = 620 + (i // 2) * 24
        ax.add_patch(Rectangle((bx, by), 161, 21, fc="#f1f5f9", ec="#94a3b8", lw=0.8))
        ax.text(bx + 80, by + 10.5, btxt, color="#1e293b", fontsize=8, ha="center", va="center")

    # ④ 计算结果卡片
    ax.add_patch(Rectangle((18, 704), 345, 198, fc="white", ec="#9fb0c4", lw=1.2))
    ax.add_patch(Rectangle((18, 704), 345, 26, fc="#2f5d8c", ec="none"))
    ax.text(28, 718, "计算结果", color="white", fontsize=10, fontweight="bold", va="center")
    ax.add_patch(Rectangle((305, 707), 54, 20, fc="#3f74ab", ec="none"))
    ax.text(332, 717, "[展开]", color="white", fontsize=8.5, ha="center", va="center")
    res_lines = [
        ("截面：椭圆（给定相似度）", "#0f172a"),
        ("轨迹半径 Rp = 31.5225", "#0f172a"),
        ("椭圆半轴 a=10.1762  b=10.6436  uc=0.6929", "#0f172a"),
        ("相似度 = 1.0400   顶隙 = 0.0287  [OK]", "#15803d"),
        ("接触段 r: 7.9269 ~ 10.1384   最大直径 = 20.2768", "#0f172a"),
        ("廓形单调 OK  |  过切校验 OK  |  仿真过切 OK", "#15803d"),
        ("—— 单圆弧近似 ——", "#1e293b"),
        ("R=12.3600  圆心 -2.1920 / +1.0710  Ø20.3360", "#0f172a"),
        ("生成球道偏差 = 3.78 μm（±10）  [合格]", "#15803d"),
    ]
    for i, (ltxt, col) in enumerate(res_lines):
        ax.text(26, 742 + i * 17, ltxt, color=col, fontsize=8, va="center")

    # ⑤ 右侧图形页签区
    ax.add_patch(Rectangle((372, 78), 1060, 824, fc="white", ec="#9fb0c4", lw=1.2))
    tab_names = ["刀具廓形", "球道截面", "星形套截面", "加工姿态(子午面)", "反向仿真偏差", "单圆弧近似"]
    tx = 374
    for idx, tname in enumerate(tab_names):
        tw = 135 if idx != 3 else 155
        fc = "#1f6fd1" if idx == 0 else "#e4e7eb"
        tc = "white" if idx == 0 else "#334155"
        ax.add_patch(Rectangle((tx, 80), tw, 30, fc=fc, ec="#cbd5e1", lw=0.8))
        ax.text(tx + tw / 2, 95, tname, color=tc, fontsize=9.5, fontweight="bold" if idx == 0 else "normal",
                ha="center", va="center")
        tx += tw + 2

    # 嵌入右侧图形图像
    ax_img = fig.add_axes([0.265, 0.06, 0.71, 0.78])
    ax_img.imshow(tab_im)
    ax_img.axis("off")

    # ⑥ 底部工具栏
    ax.add_patch(Rectangle((374, 868), 1056, 32, fc="#f8fafc", ec="#cbd5e1", lw=0.8))
    ax.text(390, 884, "[主页复位]   [← 后退]   [→ 前进]   [拖拽平移]   [框选放大]   [边距调整]   [保存图片]",
            color="#334155", fontsize=9, va="center")
    ax.text(1415, 884, "x=7.52, y=3.14", color="#64748b", fontsize=8.5, ha="right", va="center")

    # 绘制红色编号标注徽标 ①~⑥
    badges = [
        ("① 顶部菜单栏", 430, 58),
        ("② 输入参数区（含悬停示意图提示）", 235, 92),
        ("③ 计算与导出按钮区", 265, 545),
        ("④ 计算结果区（可展开/复制）", 215, 718),
        ("⑤ 六大图形页签（Ctrl+1~6）", 1265, 95),
        ("⑥ 图表缩放/平移/保存工具栏", 1060, 884),
    ]
    for btxt, bx, by in badges:
        ax.text(bx, by, btxt, color="white", fontsize=9, fontweight="bold", va="center",
                bbox=dict(boxstyle="round,pad=0.35", fc=HL, ec="white", lw=1.5))

    save_fig(fig, os.path.join(res, "ui_main_annotated.png"), dpi=150, pad=0.02)

    # 3.2 鼠标悬停图文提示卡片实景图 (ui_hover_tip_demo.png)
    fig = Figure(figsize=(10.5, 5.2), dpi=160)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1050)
    ax.set_ylim(520, 0)
    ax.axis("off")
    # 左侧参数局部
    ax.add_patch(Rectangle((15, 20), 340, 260, fc="#f8fafc", ec="#2f5d8c", lw=1.5))
    ax.add_patch(Rectangle((15, 20), 340, 28, fc="#2f5d8c", ec="none"))
    ax.text(26, 34, "② 球道法向截面（鼠标悬停参数演示）", color="white", fontsize=10, fontweight="bold", va="center")
    demo_rows = [
        ("截面类型", "椭圆  [v]", "", False),
        ("定义方式", "给定相似度  [v]", "", False),
        ("接触角 α", "42.0", "°", True),
        ("相似度 k", "1.04", "", False),
        ("法向余量", "0.0", "mm", False),
    ]
    for i, (lbl, val, u, active) in enumerate(demo_rows):
        ry = 72 + i * 38
        if active:
            ax.add_patch(Rectangle((20, ry - 15), 330, 30, fc="#fee2e2", ec=HL, lw=1.5))
        ax.text(30, ry, lbl, color=HL if active else "#1e293b", fontsize=10,
                fontweight="bold" if active else "normal", va="center")
        ax.add_patch(Rectangle((145, ry - 11), 165, 22, fc="white", ec=HL if active else "#94a3b8", lw=1.2 if active else 0.8))
        ax.text(154, ry, val, color="#0f172a", fontsize=9.5, va="center")
        ax.text(320, ry, u, color="#64748b", fontsize=9, va="center")
    ax.annotate("鼠标悬停在参数名或输入框上 0.4 秒\n右侧自动弹出图文提示（不遮挡输入）",
                xy=(180, 148), xytext=(35, 340),
                color=HL, fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=HL, lw=2))

    # 右侧黄色提示弹窗
    ax.add_patch(Rectangle((370, 15), 660, 490, fc="#ffffe0", ec="#334155", lw=1.2))
    tip_png = os.path.join(GUIDE_ROOT, "2_basic_params", "resources", "tip_pressure_angle.png")
    tip_im = Image.open(tip_png)
    ax_tip = fig.add_axes([0.365, 0.30, 0.60, 0.64])
    ax_tip.imshow(tip_im)
    ax_tip.axis("off")
    tip_text = (
        "【含义】钢球与球道接触点处的法线，与截面对称轴（球道深度方向）的夹角，也叫压力角，单位度。\n"
        "        截面在这一点与钢球相切。\n"
        "【设置】按零件图填写，常见 30°~45°（例如 AC3300-G 为 42°，Nexteer 为 33°）。\n"
        "【影响】接触角越大，接触点越靠近球道边缘，刀具齿形变化越明显。"
    )
    ax.text(385, 380, tip_text, color="#0f172a", fontsize=9.5, va="top", linespacing=1.55)
    save_fig(fig, os.path.join(res, "ui_hover_tip_demo.png"), dpi=160, pad=0.02)

    # 3.3 截面类型与定义方式动态显隐四联对比图 (ui_section_modes_compare.png)
    fig = Figure(figsize=(12.5, 4.0), dpi=160)
    FigureCanvasAgg(fig)
    modes_cfg = [
        ("模式 A：椭圆 + 给定相似度", "#1f6fd1", [
            ("截面类型", "椭圆  [v]", ""),
            ("定义方式", "给定相似度  [v]", ""),
            ("接触角 α", "42.0", "°"),
            ("相似度 k", "1.04", ""),
            ("法向余量", "0.0", "mm"),
        ], "适用：图纸给出接触角 α 与相似度 k\n（或接触点曲率半径 Rc），顶隙自动算出"),
        ("模式 B：椭圆 / 双圆弧 + 给定顶隙", "#2e7d32", [
            ("截面类型", "椭圆 / 双圆弧  [v]", ""),
            ("定义方式", "给定顶隙  [v]", ""),
            ("接触角 α", "42.0", "°"),
            ("顶隙 c", "0.0295", "mm"),
            ("法向余量", "0.0", "mm"),
        ], "适用：图纸给出接触角 α 与顶隙 c，\n相似度 k 作为结果自动算出"),
        ("模式 C：椭圆 + 给定半轴(椭圆)", "#9333ea", [
            ("截面类型", "椭圆  [v]", ""),
            ("定义方式", "给定半轴(椭圆)  [v]", ""),
            ("半轴 a（横向）", "10.18", "mm"),
            ("半轴 b（径向）", "10.64", "mm"),
            ("中心高 uc", "0.69", "mm"),
            ("法向余量", "0.0", "mm"),
        ], "适用：图纸直接标出椭圆长短半轴 a、b\n与椭圆中心位置，接触角/顶隙自动算出"),
        ("模式 D：点表(CSV) 截面", "#d97706", [
            ("截面类型", "点表(CSV)  [v]", ""),
            ("顶隙 c", "0.0101", "mm"),
            ("点表文件", "Nexteer_...csv", "…"),
            ("点表精度", "1e-05", "mm"),
            ("法向余量", "0.0", "mm"),
        ], "适用：图纸给出截面坐标点表（Table 2），\n导入 CSV 并按图纸填顶隙与小数精度"),
    ]
    for idx, (mtitle, col, rows, note) in enumerate(modes_cfg):
        ax = fig.add_axes([0.01 + idx * 0.248, 0.03, 0.238, 0.92])
        ax.set_xlim(0, 240)
        ax.set_ylim(320, 0)
        ax.axis("off")
        ax.add_patch(Rectangle((2, 2), 236, 314, fc="#f8fafc", ec=col, lw=1.5))
        ax.add_patch(Rectangle((2, 2), 236, 30, fc=col, ec="none"))
        ax.text(120, 17, mtitle, color="white", fontsize=8.8, fontweight="bold", ha="center", va="center")
        for r_i, (lbl, val, u) in enumerate(rows):
            ry = 52 + r_i * 34
            ax.text(12, ry, lbl, color="#1e293b", fontsize=8.5, va="center")
            ax.add_patch(Rectangle((98, ry - 11), 108, 22, fc="white", ec="#94a3b8", lw=0.8))
            ax.text(104, ry, val, color="#0f172a", fontsize=8.2, va="center")
            if u == "…":
                ax.add_patch(Rectangle((210, ry - 11), 22, 22, fc="#e2e8f0", ec="#64748b", lw=0.8))
                ax.text(221, ry, "…", color="#0f172a", fontsize=9, ha="center", va="center")
            else:
                ax.text(212, ry, u, color="#64748b", fontsize=8, va="center")
        ax.text(120, 275, note, color=col, fontsize=8, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=col, lw=0.8))
    save_fig(fig, os.path.join(res, "ui_section_modes_compare.png"), dpi=160, pad=0.02)

    # 3.4 状态栏四种典型状态对比图 (ui_status_states.png)
    fig = Figure(figsize=(10.0, 2.8), dpi=160)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1000)
    ax.set_ylim(280, 0)
    ax.axis("off")
    states = [
        ("① 启动就绪 / 已恢复上次设置", "已恢复上次的设置。请点“计算”开始", "#555555", False, "启动软件时自动载入上次关闭前的全部参数，点击【计算 (F5)】即可生成结果"),
        ("② 后台计算进行中（带进度条与秒表）", "正在计算单圆弧近似…  0.6 s", "#b36b00", True, "计算在后台执行，界面不卡顿；实时显示当前所处计算阶段与耗时"),
        ("③ 计算成功完成（绿色提示）", "计算完成（0.9 s）", "#2e7d32", False, "全部计算、仿真校核与 6 个图形页签绘制完成，此时可安全导出文件"),
        ("④ 参数已修改提醒（橙色提示）", "参数已修改，请点“计算”更新结果", "#b36b00", False, "改动任意输入框后自动变为橙色提醒；若未重算直接点导出，软件会弹窗确认"),
    ]
    for i, (stitle, stxt, scol, pbar, desc) in enumerate(states):
        y0 = 12 + i * 66
        ax.add_patch(Rectangle((15, y0), 970, 56, fc="#f8fafc", ec="#cbd5e1", lw=1))
        ax.text(28, y0 + 18, stitle, color="#1e293b", fontsize=9.5, fontweight="bold", va="center")
        ax.text(28, y0 + 40, desc, color="#64748b", fontsize=8.5, va="center")
        # 模拟状态栏小框
        ax.add_patch(Rectangle((630, y0 + 12), 340, 32, fc="white", ec="#94a3b8", lw=1))
        ax.text(642, y0 + 28, stxt, color=scol, fontsize=9, fontweight="bold", va="center")
        if pbar:
            ax.add_patch(Rectangle((870, y0 + 18), 88, 20, fc="#e2e8f0", ec="#64748b", lw=0.8))
            ax.add_patch(Rectangle((890, y0 + 20), 36, 16, fc="#2e7d32", ec="none"))
    save_fig(fig, os.path.join(res, "ui_status_states.png"), dpi=160, pad=0.02)

    # 3.5 三分钟快速上手四步流程图 (quickstart_flow.png)
    fig = Figure(figsize=(11.0, 2.3), dpi=160)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1100)
    ax.set_ylim(230, 0)
    ax.axis("off")
    steps = [
        ("第一步：输入或载入参数", "在左侧按图纸填写基本参数\n或【文件 → 载入示例参数】", "#1f6fd1"),
        ("第二步：点击计算 (F5)", "点击绿色【>> 计算 (F5)】按钮\n等待约 1 秒完成计算与仿真", "#2e7d32"),
        ("第三步：核对结果与图形", "查看左下结果栏绿色 OK / 合格\n切换右侧 6 个页签审阅图形", "#9333ea"),
        ("第四步：导出 DXF / CSV", "点击导出按钮输出刀具 DXF、\n圆弧刀具 DXF 或点表 CSV", "#d97706"),
    ]
    for i, (st, sd, col) in enumerate(steps):
        x0 = 20 + i * 272
        ax.add_patch(FancyBboxPatch((x0, 25), 235, 175, boxstyle="round,pad=8", fc="white", ec=col, lw=2))
        ax.add_patch(Rectangle((x0, 25), 235, 42, fc=col, ec="none"))
        ax.text(x0 + 117.5, 46, st, color="white", fontsize=10, fontweight="bold", ha="center", va="center")
        ax.text(x0 + 117.5, 128, sd, color="#1e293b", fontsize=9.2, ha="center", va="center", linespacing=1.6)
        if i < 3:
            ax.annotate("", xy=(x0 + 268, 112), xytext=(x0 + 240, 112),
                        arrowprops=dict(arrowstyle="-|>", color="#64748b", lw=2.2, mutation_scale=16))
    save_fig(fig, os.path.join(res, "quickstart_flow.png"), dpi=160, pad=0.02)


# =============================================================================
# 4. 生成第 2、3 章：8 组关键参数调整前后对比图 (Before vs After)
# =============================================================================
def build_comparison_images():
    print("=== 4. 生成 8 组关键参数调整前后对比图 ===")
    ch2_dir = ensure_dir(os.path.join(GUIDE_ROOT, "2_basic_params", "resources"))
    ch3_dir = ensure_dir(os.path.join(GUIDE_ROOT, "3_advanced_params", "resources"))

    # 4.1 切入角 β 对比 (30° vs 36° vs 42°) -> ch2_dir/cmp_setting_angle.png
    fig = Figure(figsize=(10.5, 4.5), dpi=160)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    colors = ["#2563eb", "#d62728", "#16a34a"]
    for ang, col in zip((30.0, 36.0, 42.0), colors):
        pr = compute_profile(Params(setting_angle=ang, profile_step=0.03))
        ev = evaluate_arc(pr, fit_arc(pr, 3), n_y=81, n_phi=401)
        lbl = f"β = {ang:g}°（单圆弧 R={ev.tool.R:.3f}, Ø{2*ev.tool.cyl_r:.3f}）"
        ax1.plot(pr.r, pr.z, color=col, lw=2.0, label=lbl)
        ax1.plot(-pr.r, pr.z, color=col, lw=2.0)
        # 刀轴方向示意
        tf = tool_frame(pr.params, 0.0)
        P = tf.P
        shank = P - 38 * tf.d_tip
        ax2.annotate("", (shank[2], shank[0]), (P[2], P[0]),
                     arrowprops=dict(arrowstyle="-|>", color=col, lw=2.0))
        ax2.text(shank[2], shank[0] + 2.5, f"β={ang:g}°", color=col, fontsize=9, fontweight="bold", ha="center")
    p0 = Params()
    th = np.linspace(0, 2 * np.pi, 200)
    ax1.plot(p0.rb * np.cos(th), p0.rb * np.sin(th), "--", color="gray", lw=0.8, label="虚拟钢球")
    ax1.axvline(0, color="gray", ls="-.", lw=0.6)
    ax1.set_aspect("equal")
    ax1.set_title("不同切入角 β 下的精确刀具接触段廓形", fontsize=10.5, fontweight="bold")
    ax1.set_xlabel("r 半径 (mm)")
    ax1.set_ylabel("z 沿刀轴 (mm)")
    ax1.legend(fontsize=8, loc="lower center")
    ax1.grid(alpha=0.3)

    ph = np.linspace(-0.4, 0.4, 80)
    ax2.plot(p0.rp * np.sin(ph), p0.rp * np.cos(ph), "k-.", lw=1.0, label="钢球中心轨迹")
    ax2.add_patch(Circle((0, p0.rp), p0.rb, fill=False, ls="--", color="gray"))
    ax2.set_aspect("equal")
    ax2.set_xlim(-18, 42)
    ax2.set_ylim(15, 72)
    ax2.set_title("子午面内刀轴倾角对比（必须与机床实际安装角一致）", fontsize=10.5, fontweight="bold")
    ax2.set_xlabel("Z 工件轴线 (mm)")
    ax2.set_ylabel("X 径向 (mm)")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch2_dir, "cmp_setting_angle.png"))

    # 4.2 相似度 k 对比 (1.02 vs 1.04 vs 1.08) -> ch2_dir/cmp_conformity.png
    fig = Figure(figsize=(10.5, 4.3), dpi=160)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    for k_val, col in zip((1.02, 1.04, 1.08), colors):
        pr = compute_profile(Params(conformity=k_val, profile_step=0.03))
        sec = pr.section
        tt = np.linspace(-0.35, 0.35, 200)
        y, u = sec.point(tt)
        ax1.plot(y, u, color=col, lw=1.8, label=f"k = {k_val:g}（算出顶隙 c = {sec.clearance:.4f} mm）")
        ax2.plot(pr.r, pr.z - p0.rb, color=col, lw=1.8, label=f"k = {k_val:g} 刀具接触段")
    yb = np.linspace(-2.5, 2.5, 200)
    ax1.plot(yb, -np.sqrt(p0.rb**2 - yb**2), "k--", lw=1.0, label="钢球底部")
    ax1.set_xlim(-2.5, 2.5)
    ax1.set_ylim(-p0.rb - 0.08, -p0.rb + 0.15)
    ax1.set_title("球道底局部放大：相似度 k 越大，顶隙 c 越大", fontsize=10.5, fontweight="bold")
    ax1.set_xlabel("y 横向 (mm)")
    ax1.set_ylabel("u 深度 (mm)")
    ax1.legend(fontsize=8, loc="upper center")
    ax1.grid(alpha=0.3)

    ax2.set_title("对刀具接触段廓形的影响（k 越大越偏离钢球）", fontsize=10.5, fontweight="bold")
    ax2.set_xlabel("r 刀具半径 (mm)")
    ax2.set_ylabel("z - rb (mm)")
    ax2.legend(fontsize=8.5)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch2_dir, "cmp_conformity.png"))

    # 4.3 法向余量 allowance 对比 (0.0 精加工 vs 0.15 留料) -> ch2_dir/cmp_allowance.png
    fig = Figure(figsize=(10.5, 4.3), dpi=160)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    for alw, col, ls, title_tag in [(0.0, "#1f6fd1", "-", "法向余量 = 0 mm（精加工到位）"),
                                    (0.15, "#d62728", "--", "法向余量 = 0.15 mm（半精加工单边留料）")]:
        pr = compute_profile(Params(allowance=alw, profile_step=0.03))
        tt = np.linspace(-pr.t_edge, pr.t_edge, 300)
        y, u = pr.section.point(tt)
        ax1.plot(y, u, color=col, ls=ls, lw=1.8, label=title_tag)
        ax2.plot(pr.r, pr.z, color=col, ls=ls, lw=1.8, label=f"{title_tag}\n最大直径 Ø{2*pr.r.max():.3f} mm")
    ax1.set_aspect("equal")
    ax1.set_ylim(-p0.rb - 1.0, 2.5)
    ax1.set_title("球道截面对比（余量 > 0 时球道切小、留出磨削量）", fontsize=10, fontweight="bold")
    ax1.set_xlabel("y 横向 (mm)")
    ax1.set_ylabel("u (mm)")
    ax1.legend(fontsize=8, loc="upper center")
    ax1.grid(alpha=0.3)

    ax2.set_aspect("equal")
    ax2.set_title("刀具接触段对比（余量 > 0 时刀具整体内缩变小）", fontsize=10, fontweight="bold")
    ax2.set_xlabel("r 刀具半径 (mm)")
    ax2.set_ylabel("z 沿刀轴 (mm)")
    ax2.legend(fontsize=8, loc="lower left")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch2_dir, "cmp_allowance.png"))

    # 4.4 点表精度 points_tol 对比 (1e-5 正常光顺 vs 0 硬插值) -> ch2_dir/cmp_points_tol.png
    fig = Figure(figsize=(10.5, 4.2), dpi=160)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    pts_path = os.path.join(TRACKFORM_ROOT, "examples", "Nexteer_34205673_截面点表.csv")
    pr_smooth = compute_profile(Params(ball_d=17.4625, pcd=55.9414, track_offset=0.0, section_type="points",
                                       points_file=pts_path, points_tol=1e-5, clearance=0.0101,
                                       setting_angle=36.0, sphere_d=200.0, width=24.0, sphere_center_h=12.0,
                                       tip_z=5.23775, extra_extend=0.0, profile_step=0.02))
    pr_raw = compute_profile(Params(ball_d=17.4625, pcd=55.9414, track_offset=0.0, section_type="points",
                                    points_file=pts_path, points_tol=0.0, clearance=0.0101,
                                    setting_angle=36.0, sphere_d=200.0, width=24.0, sphere_center_h=12.0,
                                    tip_z=5.23775, extra_extend=0.0, profile_step=0.02))
    ts = np.linspace(0.2, pr_smooth.t_edge * 0.9, 300)
    ax1.plot(ts, pr_raw.section.curvature_radius(ts), color="#94a3b8", lw=1.0, label="点表精度 = 0（不光顺，曲率高频抖动）")
    ax1.plot(ts, pr_smooth.section.curvature_radius(ts), color="#1f6fd1", lw=2.0, label="点表精度 = 1e-5（按 5 位小数光顺，曲率平滑）")
    ax1.set_title("点表截面的曲率半径分布对比", fontsize=10.5, fontweight="bold")
    ax1.set_xlabel("截面弧长参数 t (mm)")
    ax1.set_ylabel("截面曲率半径 (mm)")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # 对比两者算出的刀具半径相对于理想圆弧的残差
    tl = fit_arc(pr_smooth, None)
    ax2.plot(pr_raw.z, (pr_raw.r - tl.radius(pr_raw.z)) * 1000, color="#94a3b8", lw=1.0, label="点表精度 = 0（舍入误差放大为刀形波动）")
    ax2.plot(pr_smooth.z, (pr_smooth.r - tl.radius(pr_smooth.z)) * 1000, color="#d62728", lw=1.8, label="点表精度 = 1e-5（刀形光滑，偏差 < 0.05 μm）")
    ax2.set_title("对计算出的刀具半径精度的影响", fontsize=10.5, fontweight="bold")
    ax2.set_xlabel("z 沿刀轴 (mm)")
    ax2.set_ylabel("刀具半径残差 (μm)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch2_dir, "cmp_points_tol.png"))

    # 4.5 刀尖高度三态对比 (9.922 默认 vs 6.200 优化短刀尖 vs 5.500 过低截断报警) -> ch3_dir/cmp_tip_z_three_states.png
    fig = Figure(figsize=(12.0, 4.2), dpi=160)
    cases_tip = [
        (9.922, "① 默认值：刀尖高度 = 9.922 mm（钢球半径）", "#1f6fd1", "绿色刀尖段较长，切削刃完整 [OK]"),
        (6.200, "② 推荐优化：刀尖高度 = 6.200 mm（高于 6.0205）", "#16a34a", "绿色刀尖段大幅缩短，刀头刚性更好、更易磨制 [OK]"),
        (5.500, "③ 错误设置：刀尖高度 = 5.500 mm（低于 6.0205）", "#d62728", "低于接触段最高点 6.0205，截掉切削刃，球道底欠切！[报警]"),
    ]
    for i, (tz, ctitle, col, note) in enumerate(cases_tip):
        ax = fig.add_subplot(1, 3, i + 1)
        pr = compute_profile(Params(tip_z=tz, profile_step=0.03))
        r, z = pr.full()
        ax.plot(r, z, "g-", lw=1.5, label="刀尖段最大外形")
        ax.plot(-r, z, "g-", lw=1.5)
        ax.plot(pr.r, pr.z, "r-", lw=2.5, alpha=0.7, label="接触段（切削刃）")
        ax.plot(-pr.r, pr.z, "r-", lw=2.5, alpha=0.7)
        ax.axhline(pr.contact_z_top, color="#d62728", ls=":", lw=1.1, label=f"接触段最高点 z={pr.contact_z_top:.4f}")
        ax.axhline(tz, color=col, ls="--", lw=1.2, label=f"设定刀尖高度 z={tz:g}")
        ax.set_aspect("equal")
        ax.set_xlim(-11, 11)
        ax.set_ylim(-3.2, 11)
        ax.set_title(ctitle, fontsize=9.2, fontweight="bold", color=col)
        ax.text(0, -2.2, note, color=col, fontsize=8, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=col, lw=0.8))
        ax.legend(fontsize=7.2, loc="center")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch3_dir, "cmp_tip_z_three_states.png"))

    # 4.6 让刀过渡长度对比 (1.0 mm 平滑过渡 vs 0.0 mm 无过渡台阶) -> ch3_dir/cmp_tip_relief_len.png
    fig = Figure(figsize=(10.0, 4.0), dpi=160)
    for i, (rlen, ctitle, col, desc) in enumerate([
        (1.0, "让刀过渡 = 1.0 mm（默认推荐：平滑过渡）", "#16a34a", "让刀量在 1 mm 长度内从 0 平滑增加到 0.05 mm，无台阶、好磨制"),
        (0.0, "让刀过渡 = 0.0 mm（不推荐：突变台阶）", "#d62728", "在接触段最高点处直接向内缩进 0.05 mm，形成尖角台阶，易崩刃"),
    ]):
        ax = fig.add_subplot(1, 2, i + 1)
        pr = compute_profile(Params(tip_relief=0.15, tip_relief_len=rlen, profile_step=0.02))  # 放大让刀量以便看清局部
        zz = np.linspace(pr.z[0] - 0.5, pr.tip_z[-1], 100)
        ax.plot(arc_r(pr.section, pr.params, zz), zz, ":", color="#1f6fd1", lw=1.4, label="球道底圆弧约束")
        ax.plot(pr.r, pr.z, "r-", lw=2.6, label="红色接触段（切削）")
        ax.plot(pr.tip_r, pr.tip_z, "g-", lw=2.0, label="绿色刀尖段（让刀）")
        ax.plot(pr.r[0], pr.z[0], "o", color=col, ms=6)
        r0, z0 = float(pr.r[0]), float(pr.z[0])
        ax.set_xlim(r0 - 1.5, r0 + 0.9)
        ax.set_ylim(z0 - 0.8, z0 + 2.0)
        ax.set_title(ctitle, fontsize=10, fontweight="bold", color=col)
        ax.text(r0 - 0.3, z0 - 0.55, desc, color=col, fontsize=8, ha="center",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=col, lw=0.8))
        ax.set_xlabel("r 半径 (mm) —— 交界处局部放大")
        ax.set_ylabel("z 沿刀轴 (mm)")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch3_dir, "cmp_tip_relief_len.png"))

    # 4.7 刀柄方向对比 (朝 +Z vs 朝 -Z) -> ch3_dir/cmp_tilt_side_pose.png
    fig = Figure(figsize=(11.0, 4.6), dpi=160)
    for i, (side, stitle) in enumerate([(1, "刀柄方向：朝 +Z（伸向外球面中心偏移侧）"),
                                        (-1, "刀柄方向：朝 -Z（伸向另一端面侧，齿形完全相同）")]):
        ax = fig.add_subplot(1, 2, i + 1)
        h = DummyHost(Params(tilt_side=side, profile_step=0.04))
        p = h.params
        prof = h.prof
        h._draw_workpiece(ax, half=True)
        ph0, ph1 = phi_range(p)
        r, z = prof.full()
        for j, phi in enumerate(np.linspace(ph0, ph1, 3)):
            tf = tool_frame(p, phi)
            d = tf.d_tip
            n = np.array([d[2], 0, -d[0]])
            pts_r = tf.P[None, :] + z[:, None] * d[None, :] + r[:, None] * n[None, :]
            pts_l = tf.P[None, :] + z[:, None] * d[None, :] - r[:, None] * n[None, :]
            col = ["tab:green", "tab:orange", "tab:purple"][j]
            head = np.vstack([pts_r, pts_l[::-1]])
            ax.fill(head[:, 2], head[:, 0], color=col, alpha=0.35, lw=1, ec=col,
                    label=f"摆角 φ={np.degrees(phi):.1f}°")
            g = tf.P - p.gauge_length * d
            ax.plot([g[2] - 15 * n[2], g[2] + 15 * n[2]], [g[0] - 15 * n[0], g[0] + 15 * n[0]], color=col, lw=2.2)
            ax.plot([tf.P[2], g[2]], [tf.P[0], g[0]], color=col, ls="-.", lw=0.7)
        ax.set_aspect("equal")
        ax.set_title(stitle, fontsize=10, fontweight="bold", color="#1f6fd1" if side == 1 else "#d62728")
        ax.set_xlabel("Z 工件轴线 (mm)")
        ax.set_ylabel("X 径向 (mm)")
        ax.legend(fontsize=8, loc="lower left")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch3_dir, "cmp_tilt_side_pose.png"))

    # 4.8 单圆弧取整位数对比 (3 位小数 vs 1 位小数) -> ch3_dir/cmp_arc_decimals.png
    fig = Figure(figsize=(10.5, 4.2), dpi=160)
    pr = compute_profile(Params())
    for i, (dec, dtitle) in enumerate([(3, "取整位数 = 3（保留到 0.001 mm，默认推荐）"),
                                       (1, "取整位数 = 1（只保留到 0.1 mm，取整误差过大超差）")]):
        ax = fig.add_subplot(1, 2, i + 1)
        ev = evaluate_arc(pr, fit_arc(pr, dec), 0.02, 117, n_y=161, n_phi=1001)
        tl = ev.tool
        ax.plot(ev.ys, ev.dev * 1000, "b-", lw=1.8, label="单圆弧刀具切出球道 − 设计截面")
        lim = ev.profile_tol / 2 * 1000
        ax.axhline(lim, color="r", ls="--", lw=1.0, label=f"轮廓度公差带 ±{lim:g} μm")
        ax.axhline(-lim, color="r", ls="--", lw=1.0)
        ax.fill_between(ev.ys, -lim, lim, color="g" if ev.ok else "r", alpha=0.07)
        status = f"最大偏差 {ev.max_dev*1000:.2f} μm  [{'合格' if ev.ok else '超差!'}]"
        ax.set_title(f"{dtitle}\nR={tl.R:g}, 圆心 {tl.rc:+g}/{-tl.zc:+g} → {status}",
                     fontsize=9.5, fontweight="bold", color="#16a34a" if ev.ok else "#d62728")
        ax.set_ylim(-55 if dec == 1 else -15, 55 if dec == 1 else 15)
        ax.set_xlabel("截面横向 y (mm)")
        ax.set_ylabel("法向偏差 (μm)")
        ax.legend(fontsize=8, loc="lower left")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(ch3_dir, "cmp_arc_decimals.png"))


# =============================================================================
# 5. 生成第 4 章：计算结果面板正常/报警解读图 & Table 1 几何对应图
# =============================================================================
def build_ch4_images():
    print("=== 5. 生成第 4 章计算结果面板与 Table 1 图解 ===")
    res = ensure_dir(os.path.join(GUIDE_ROOT, "4_result_panel", "resources"))

    # 5.1 正常计算结果展开窗口带分区批注图 (result_panel_normal.png)
    fig = Figure(figsize=(11.5, 7.6), dpi=160)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1150)
    ax.set_ylim(760, 0)
    ax.axis("off")

    ax.add_patch(Rectangle((15, 15), 620, 730, fc="white", ec="#2f5d8c", lw=1.8))
    ax.add_patch(Rectangle((15, 15), 620, 32, fc="#1e293b", ec="none"))
    ax.text(28, 31, "计算结果 - TrackForm（独立展开窗口，支持一键复制）", color="white", fontsize=10, fontweight="bold", va="center")
    ax.add_patch(Rectangle((17, 47), 616, 30, fc="#f1f5f9", ec="#cbd5e1", lw=0.8))
    ax.text(28, 62, "每次计算后自动刷新；可选中文字复制", color="#475569", fontsize=9, va="center")
    ax.add_patch(Rectangle((540, 51), 82, 22, fc="white", ec="#64748b", lw=0.8))
    ax.text(581, 62, "复制全部", color="#0f172a", fontsize=8.5, ha="center", va="center")

    lines_normal = [
        ("截面：椭圆（给定相似度）", "#0f172a", None),
        ("轨迹半径 Rp = 31.5225", "#0f172a", None),
        ("椭圆半轴 a(横向) = 10.1762", "#0f172a", None),
        ("椭圆半轴 b(径向) = 10.6436", "#0f172a", None),
        ("椭圆中心高 uc = 0.6929（距球道底 10.6436）", "#0f172a", None),
        ("相似度 = 1.0400", "#0f172a", None),
        ("顶隙 = 0.0287  ", "#0f172a", ("OK", "#16a34a")),
        ("球道边缘接触角  = 57.53°", "#0f172a", None),
        ("接触段 r: 7.9269 ~ 10.1384", "#0f172a", None),
        ("接触段 z: -0.1747 ~ 6.0205", "#0f172a", None),
        ("刀头最大直径    = 20.2768", "#0f172a", None),
        ("廓形单调(无自交)  ", "#0f172a", ("OK", "#16a34a")),
        ("过切校验 最小间隙 = -2.23e-07  ", "#0f172a", ("OK", "#16a34a")),
        ("仿真最大过切 = 2.15e-07  ", "#0f172a", ("OK", "#16a34a")),
        ("仿真接触区欠切 = 8.42e-06  ", "#0f172a", ("OK", "#16a34a")),
        ("球道底欠切 = 0.0500（顶隙区，仅提示）", "#0f172a", None),
        ("—— 单圆弧近似 ——", "#1f4e79", None),
        ("R=12.3600  圆心 -2.1920 / +1.0710  Ø20.3360", "#0f172a", None),
        ("生成球道偏差 = 3.78 μm（±10）  ", "#0f172a", ("合格", "#16a34a")),
        ("生成球道顶隙 = 0.0325  ", "#0f172a", ("OK", "#16a34a")),
        ("—— 轮廓方程常数 Table 1（拟合值）——", "#1f4e79", None),
        ("C1 = 2.19160    C2 = -25.50227    C3 = -18.52849", "#0f172a", None),
        ("C4 = -19.59946  C5 = 1.07098      C6 = -21.56794", "#0f172a", None),
        ("C7 = 650.36593  C8 = -6.06824     C9 = 1.07098", "#0f172a", None),
        ("C10 = 152.76417", "#0f172a", None),
        ("常数自检：由常数还原的轮廓与基本轮廓最大偏差 0.02 μm  ", "#0f172a", ("OK", "#16a34a")),
    ]
    for idx, (txt, col, tag) in enumerate(lines_normal):
        yy = 96 + idx * 24.5
        ax.text(32, yy, txt, color=col, fontsize=9, fontweight="bold" if "——" in txt else "normal", va="center")
        if tag:
            w_px = sum(13.5 if ord(ch) > 127 else 7.2 for ch in txt)
            ax.text(36 + w_px, yy, tag[0], color=tag[1], fontsize=9.5, fontweight="bold", va="center")

    # 右侧分块说明批注
    brackets = [
        (88, 275, "① 球道截面几何参数", "显示轨迹半径 Rp、求出的椭圆半轴/圆弧半径、\n实际相似度与顶隙（在上下限内标绿色 OK）", "#1f6fd1"),
        (285, 360, "② 精确成型刀尺寸范围", "接触段半径 r、轴向位置 z 范围及刀头最大直径；\n接触段最高点 z（6.0205）是刀尖高度的下限", "#9333ea"),
        (368, 480, "③ 四项加工安全性校核", "自动检验刀具无自交、整段球道无过切、反向仿真\n接触区吻合；球道底欠切≈让刀量属正常顶隙保护", "#16a34a"),
        (488, 585, "④ 单圆弧近似刀具与合格判定", "给出可直接磨刀的圆弧半径 R、圆心径向/轴向偏置、\n圆柱直径 Ø，并校验切出的球道是否在轮廓度公差内", "#d97706"),
        (593, 730, "⑤ 图纸轮廓方程常数 C1~C10", "对应客户产品图纸 Table 1 的 10 个常数及方程复现\n自检偏差（< 1 μm 标绿色 OK）", "#2f5d8c"),
    ]
    for y1, y2, btitle, bdesc, col in brackets:
        ym = (y1 + y2) / 2
        ax.plot([642, 656, 656, 642], [y1, y1, y2, y2], color=col, lw=1.8)
        ax.add_patch(FancyBboxPatch((668, ym - 34), 460, 68, boxstyle="round,pad=6", fc="#f8fafc", ec=col, lw=1.4))
        ax.text(682, ym - 12, btitle, color=col, fontsize=9.8, fontweight="bold", va="center")
        ax.text(682, ym + 14, bdesc, color="#334155", fontsize=8.5, va="center", linespacing=1.4)

    save_fig(fig, os.path.join(res, "result_panel_normal.png"), dpi=160, pad=0.02)

    # 5.2 异常与红色报警结果面板示例图 (result_panel_warnings.png)
    fig = Figure(figsize=(10.8, 5.2), dpi=160)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1080)
    ax.set_ylim(520, 0)
    ax.axis("off")
    ax.add_patch(Rectangle((15, 15), 1050, 490, fc="white", ec=HL, lw=1.8))
    ax.add_patch(Rectangle((15, 15), 1050, 32, fc=HL, ec="none"))
    ax.text(28, 31, "计算结果面板 —— 常见红色报警提示与含义对照（出现任一红字时导出前均会弹窗拦截提醒）",
            color="white", fontsize=10, fontweight="bold", va="center")

    warns_demo = [
        ("报警情形 A：刀尖高度设得过低（截断切削刃）",
         "刀尖高度 5.5 低于接触段最高点 6.0205：切削刃被截掉，球道底将欠切！请把刀尖高度设为 ≥ 6.0205\n"
         "球道底欠切 = 0.3125（刀尖高度截断切削刃）",
         "解决办法：展开【高级参数 → 刀尖与廓形】，将“刀尖高度”改为大于或等于提示的接触段最高点数值。"),
        ("报警情形 B：顶隙超出图纸允许范围",
         "顶隙 = 0.0462  超出范围!\n"
         "生成球道顶隙 = 0.0498  超出范围!",
         "解决办法：核对基本参数中的“相似度 k”或“顶隙 c”是否填错，或核对【高级参数 → 校验范围】中的顶隙上下限是否与图纸一致。"),
        ("报警情形 C：点表模式下顶隙或椭圆半轴中心高不匹配",
         "钢球未与截面贴合，请核对顶隙/椭圆中心！   （或：钢球与截面干涉（截面过窄）！）",
         "解决办法：选“点表(CSV)”时必须把“顶隙 c”改为该点表图纸规定的顶隙；选“给定半轴”时核对椭圆中心高 uc。"),
        ("报警情形 D：单圆弧近似刀具超差（如用于双圆弧尖底截面或公差过严）",
         "生成球道偏差 = 292.80 μm（±10）  超差!\n"
         "圆弧刀具刀尖被“刀尖高度”截短（圆弧切出球道底处 z = 6.0682）…刀尖高度应 ≥ 6.0682",
         "解决办法：双圆弧(尖底)球道不能用单圆弧刀加工，请导出【刀具 DXF / 刀具点表 CSV】磨制精确成型刀。"),
    ]
    for i, (wtitle, wred, wfix) in enumerate(warns_demo):
        y0 = 60 + i * 110
        ax.add_patch(Rectangle((28, y0), 1024, 98, fc="#fff5f5", ec="#fca5a5", lw=1))
        ax.text(40, y0 + 18, wtitle, color="#1e293b", fontsize=9.5, fontweight="bold", va="center")
        ax.text(40, y0 + 48, wred, color=HL, fontsize=8.8, fontweight="bold", va="center", linespacing=1.4)
        ax.text(40, y0 + 82, wfix, color="#15803d", fontsize=8.8, va="center")
    save_fig(fig, os.path.join(res, "result_panel_warnings.png"), dpi=160, pad=0.02)

    # 5.3 单圆弧近似刀具尺寸标注与 Table 1/2 工程用途对应图 (table1_geometry_map.png)
    fig = Figure(figsize=(11.0, 4.8), dpi=160)
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    p = Params()
    prof = compute_profile(p)
    tool = fit_arc(prof, 3)
    r, z = tool.profile()
    for sg in (1, -1):
        ax1.plot(sg * r, z, "g-", lw=2.0, label="单圆弧刀具（圆弧 + 圆柱）" if sg == 1 else None)
    ax1.plot([-tool.tip_r, tool.tip_r], [tool.z_tip] * 2, "g-", lw=2.0)
    ax1.axvline(0, color="gray", ls="-.", lw=0.8)
    ax1.axhline(0, color="gray", ls="-.", lw=0.8)
    ax1.plot(0, 0, "k+", ms=9, label="原点（虚拟钢球中心）")
    ax1.plot(tool.rc, tool.zc, "ro", ms=6)
    ax1.annotate(f"圆弧圆心\n径向：{tool.rc:+.4f} mm（负号=交叉到刀轴另一侧）\n轴向：{-tool.zc:+.4f} mm（朝刀柄方向为正）",
                 (tool.rc, tool.zc), (-12.2, tool.zc - 4.2), color=HL, fontsize=8.3, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#fff5f5", ec=HL, lw=0.8),
                 arrowprops=dict(arrowstyle="->", color=HL, lw=1.2))
    ax1.annotate(f"圆弧半径 R = {tool.R:.4f} mm",
                 (tool.rc + tool.R * 0.85, tool.zc + tool.R * 0.52), (1.8, 8.2), color="#1f6fd1", fontsize=8.8, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#eff6ff", ec="#1f6fd1", lw=0.8),
                 arrowprops=dict(arrowstyle="->", color="#1f6fd1", lw=1.2))
    ax1.annotate(f"圆柱段直径 Ø = {2*tool.cyl_r:.4f} mm",
                 (tool.cyl_r, tool.zc - 2.0), (1.5, -5.2), color="#16a34a", fontsize=8.8, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#f0fdf4", ec="#16a34a", lw=0.8),
                 arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.2))
    ax1.set_aspect("equal")
    ax1.set_xlim(-13, 13)
    ax1.set_ylim(-6.5, 10.5)
    ax1.set_title("结果栏“单圆弧近似”各项尺寸在刀具上的位置", fontsize=10.5, fontweight="bold")
    ax1.set_xlabel("r 刀具半径 (mm)")
    ax1.set_ylabel("z 沿刀轴 (mm)，刀尖方向为正")
    ax1.grid(alpha=0.3)

    # 右图：单圆弧结果与 Table 1 / Table 2 的下游工程应用流向（不含内部推导公式）
    ax2.axis("off")
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 100)
    ax2.add_patch(FancyBboxPatch((3, 4), 94, 90, boxstyle="round,pad=3", fc="#f8fafc", ec="#2f5d8c", lw=1.5))
    ax2.text(50, 90, "下半部分结果数据的工程应用指南", color="#1f4e79", fontsize=10.8, fontweight="bold", ha="center", va="center")
    cards_info = [
        (63, "#1f6fd1", "① 单圆弧近似刀具尺寸（R / 圆心 / Ø）",
         "· 直接用于数控工具磨床磨制“圆弧 + 圆柱”成型刀\n"
         "· 点击【圆弧刀具 DXF】可一键导出带真实 ARC 圆弧的加工图"),
        (36, "#16a34a", "② 生成球道偏差与生成球道顶隙",
         "· 自动检验用取整后的圆弧刀加工出的球道是否满足图纸公差\n"
         "· 显示绿色“合格”与“OK”即可放心用单圆弧刀替代自由曲线刀"),
        (9, "#9333ea", "③ 轮廓方程常数 Table 1（C1 ~ C10）",
         "· 对应客户产品开发图纸上的 Table 1 常数表\n"
         "· 点击【方程常数（Table 1）】与【基本轮廓（Table 2）】直接导出填图"),
    ]
    for y0, col, ctitle, cbody in cards_info:
        ax2.add_patch(FancyBboxPatch((8, y0), 84, 20, boxstyle="round,pad=2", fc="white", ec=col, lw=1.3))
        ax2.text(12, y0 + 15.0, ctitle, color=col, fontsize=9.2, fontweight="bold", va="center")
        ax2.text(12, y0 + 6.2, cbody, color="#334155", fontsize=8.3, va="center", linespacing=1.45)
    fig.tight_layout()
    save_fig(fig, os.path.join(res, "table1_geometry_map.png"))


# =============================================================================
# 6. 生成第 5 章：右侧 6 大图形页签高清图与工具栏指南
# =============================================================================
def build_ch5_images():
    print("=== 6. 生成第 5 章 6 大图形页签高清图 ===")
    res = ensure_dir(os.path.join(GUIDE_ROOT, "5_tabs_charts", "resources"))
    host = DummyHost(Params())
    host.render_all()
    save_fig(host.figs["tool"][0], os.path.join(res, "tab1_tool.png"))
    save_fig(host.figs["section"][0], os.path.join(res, "tab2_section_ellipse.png"))
    save_fig(host.figs["part"][0], os.path.join(res, "tab3_part.png"))
    save_fig(host.figs["pose"][0], os.path.join(res, "tab4_pose.png"))
    save_fig(host.figs["sim"][0], os.path.join(res, "tab5_sim.png"))
    save_fig(host.figs["arc"][0], os.path.join(res, "tab6_arc.png"))

    # 双圆弧截面页签图 (tab2_section_gothic.png)
    host_goth = DummyHost(Params(section_type="gothic", conformity=1.04))
    host_goth._plot_section()
    save_fig(host_goth.figs["section"][0], os.path.join(res, "tab2_section_gothic.png"))

    # 底部工具栏操作指南与局部放大示意 (toolbar_annotated.png)
    fig = Figure(figsize=(11.0, 4.2), dpi=160)
    ax1 = fig.add_axes([0.02, 0.56, 0.96, 0.40])
    ax1.set_xlim(0, 1100)
    ax1.set_ylim(160, 0)
    ax1.axis("off")
    ax1.add_patch(Rectangle((10, 15), 1080, 52, fc="#f8fafc", ec="#2f5d8c", lw=1.5))
    tools_info = [
        (35, "[主页复位 Home]", "一键恢复初始全图视野"),
        (195, "[← / → 前后视图]", "回退或重做上一步缩放位置"),
        (385, "[拖拽平移 Pan]", "按下左键拖动平移，右键拖动缩放"),
        (595, "[框选放大 Zoom]", "左键拉框放大刀尖/顶隙微米级细节"),
        (805, "[边距设置]", "调整图形四周留白比例"),
        (960, "[保存图片 Save]", "将当前页签另存为高清 PNG/PDF"),
    ]
    for tx, tname, tdesc in tools_info:
        ax1.add_patch(Rectangle((tx, 23), 135, 36, fc="white", ec="#64748b", lw=1))
        ax1.text(tx + 67.5, 41, tname, color="#1f4e79", fontsize=9, fontweight="bold", ha="center", va="center")
        ax1.annotate(tdesc, xy=(tx + 67.5, 60), xytext=(tx + 67.5, 125),
                     color="#0f172a", fontsize=8.3, ha="center", va="center",
                     bbox=dict(boxstyle="round,pad=0.25", fc="#ffffe0", ec="#cbd5e1"),
                     arrowprops=dict(arrowstyle="->", color=HL, lw=1.2))

    # 下方展示局部框选放大效果（左：全图框选刀尖，右：放大后的刀尖与球道底圆弧约束）
    ax_l = fig.add_axes([0.06, 0.06, 0.40, 0.44])
    ax_r = fig.add_axes([0.55, 0.06, 0.40, 0.44])
    pr = host.prof
    r, z = pr.full()
    for a in (ax_l, ax_r):
        a.plot(r, z, "g-", lw=1.5, label="刀尖段最大外形")
        a.plot(pr.r, pr.z, "r-", lw=2.2, label="接触段（切削）")
        zz = np.linspace(pr.z[0] - 0.5, pr.tip_z[-1] + 0.5, 100)
        a.plot(arc_r(pr.section, pr.params, zz), zz, ":", color="tab:blue", lw=1.2, label="球道底约束")
        a.grid(alpha=0.3)
    r0, z0 = float(pr.r[0]), float(pr.z[0])
    ax_l.add_patch(Rectangle((r0 - 1.3, z0 - 0.8), 2.2, 2.2, fill=False, ec=HL, lw=1.8, ls="--"))
    ax_l.text(r0 - 2.2, z0 - 1.5, "用【框选放大 Zoom】拉框选中交界处", color=HL, fontsize=8.5, ha="center", fontweight="bold")
    ax_l.set_xlim(-2, 11)
    ax_l.set_ylim(-3, 11)
    ax_l.set_title("缩放前：全局视图", fontsize=9.5, fontweight="bold")

    ax_r.set_xlim(r0 - 1.3, r0 + 0.9)
    ax_r.set_ylim(z0 - 0.8, z0 + 1.4)
    ax_r.plot(r0, z0, "ro", ms=5)
    ax_r.annotate("接触段终点与让刀段平滑相接\n（让刀量 0.05 mm 清晰可见）",
                  (r0, z0), (r0 - 1.15, z0 - 0.55), color=HL, fontsize=8.2,
                  arrowprops=dict(arrowstyle="->", color=HL, lw=1))
    ax_r.set_title("框选放大后：清晰检查接触段与刀尖段交界细节", fontsize=9.5, fontweight="bold", color=HL)
    ax_r.legend(fontsize=7.5, loc="upper right")
    save_fig(fig, os.path.join(res, "toolbar_annotated.png"))


# =============================================================================
# 7. 生成第 6 章：真实 DXF 图纸 CAD 预览图 & CSV 编程基准对比图
# =============================================================================
def render_dxf_to_png(dxf_path: str, png_path: str, title: str):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    fig = plt.figure(figsize=(11.5, 7.2), dpi=160)
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.91])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)
    ax.set_facecolor("#181c24")
    fig.patch.set_facecolor("#181c24")
    ax.set_title(title, color="white", fontsize=12, fontweight="bold", pad=10)
    fig.savefig(png_path, dpi=160, facecolor="#181c24", bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"  [OK] {os.path.relpath(png_path, GUIDE_ROOT)}")


def build_ch6_images():
    print("=== 7. 生成第 6 章 DXF CAD 预览图与 CSV 编程基准图 ===")
    res = ensure_dir(os.path.join(GUIDE_ROOT, "6_exports_data", "resources"))
    host = DummyHost(Params())
    tmp_dir = tempfile.gettempdir()

    dxf1 = os.path.join(tmp_dir, "tool_profile.dxf")
    dxf2 = os.path.join(tmp_dir, "arc_tool.dxf")
    dxf3 = os.path.join(tmp_dir, "part_section.dxf")
    export_dxf(host.prof, dxf1, detail=False)
    export_arc_dxf(host.arc_eval, host.prof, dxf2, host.table, detail=False)
    export_part_dxf(host.prof, dxf3, detail=False)

    render_dxf_to_png(dxf1, os.path.join(res, "dxf_tool_preview.png"),
                      "tool_profile.dxf（刀具 DXF）—— 左：精确刀具轴截面（绿 PROFILE + 橙 TIP_MAX）  右：球道截面与参数表")
    render_dxf_to_png(dxf2, os.path.join(res, "dxf_arc_preview.png"),
                      "arc_tool.dxf（圆弧刀具 DXF）—— 真实 ARC 圆弧实体 + 尺寸标注 + 精确廓形对照 + Table 1 常数")
    render_dxf_to_png(dxf3, os.path.join(res, "dxf_part_preview.png"),
                      "part_section.dxf（星形套截面 DXF）—— 过球道轴向剖面 + ANSI31 剖面线 + 轨迹圆弧 + 完整尺寸")

    # CSV 编程坐标基准对比图 (csv_coordinate_bases.png)
    fig = Figure(figsize=(10.5, 4.2), dpi=160)
    ax = fig.add_subplot(111)
    p, prof = host.params, host.prof
    r, z = prof.full()
    L = p.gauge_length
    ax.plot(z, r, "g-", lw=1.6, label="刀尖段（不切削，最大允许外形）")
    ax.plot(z, -r, "g-", lw=1.6)
    ax.plot(prof.z, prof.r, "r-", lw=2.8, label="接触段（切削刃，必须精确）")
    ax.plot(prof.z, -prof.r, "r-", lw=2.8)
    ax.plot([-L, -L], [-14, 14], "k-", lw=3.0, label="HSK 刀柄端面")
    ax.plot([-L, 0], [8, 8], color="#64748b", lw=1.0)
    ax.plot([-L, 0], [-8, -8], color="#64748b", lw=1.0)
    ax.add_patch(Circle((0, 0), p.rb, fill=False, ls="--", color="gray", lw=0.9))
    ax.axvline(0, color="#1f6fd1", ls="-.", lw=1.2)
    ax.axhline(0, color="gray", ls="-.", lw=0.7)

    # 标注某一点 P 在两种基准下的坐标
    idx_pt = len(prof.z) // 2
    zp, rp = float(prof.z[idx_pt]), float(prof.r[idx_pt])
    ax.plot(zp, rp, "ro", ms=6)
    ax.annotate("", (zp, 11.5), (0, 11.5), arrowprops=dict(arrowstyle="<|-|>", color="#1f6fd1", lw=1.5))
    ax.text(zp / 2, 12.2, f"z_球心 = {zp:+.3f}", color="#1f6fd1", fontsize=9.5, fontweight="bold", ha="center")

    ax.annotate("", (zp, -11.5), (-L, -11.5), arrowprops=dict(arrowstyle="<|-|>", color=HL, lw=1.5))
    ax.text((zp - L) / 2, -13.5, f"z_端面 = z_球心 + L = {zp + L:.3f} mm（以刀柄端面为编程零点）",
            color=HL, fontsize=9.5, fontweight="bold", ha="center")

    ax.annotate("", (0, -6.0), (-L, -6.0), arrowprops=dict(arrowstyle="<|-|>", color="#334155", lw=1.2))
    ax.text(-L / 2, -5.2, f"球心距 L = {L:g} mm", color="#334155", fontsize=9, ha="center")

    ax.set_aspect("equal")
    ax.set_xlim(-L - 6, 14)
    ax.set_ylim(-16.5, 16.5)
    ax.set_title("刀具点表 CSV 中两个轴向坐标列（z_球心 vs z_端面）的对刀基准关系", fontsize=11, fontweight="bold")
    ax.set_xlabel("沿刀轴方向 z (mm)，刀尖朝右")
    ax.set_ylabel("刀具半径 r (mm)")
    ax.legend(loc="upper left", fontsize=8.5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(res, "csv_coordinate_bases.png"))


# =============================================================================
# 8. 生成第 7、8、9 章：菜单全景图、四大实战案例汇总图、常见故障排错图
# =============================================================================
def build_ch7_8_9_images():
    print("=== 8. 生成第 7、8、9 章菜单、案例与排错配图 ===")
    res7 = ensure_dir(os.path.join(GUIDE_ROOT, "7_menus_session", "resources"))
    res8 = ensure_dir(os.path.join(GUIDE_ROOT, "8_workflows_cases", "resources"))
    res9 = ensure_dir(os.path.join(GUIDE_ROOT, "9_troubleshooting", "resources"))

    # 8.1 五大下拉菜单全景图 (menus_overview.png)
    fig = Figure(figsize=(12.5, 3.8), dpi=160)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1250)
    ax.set_ylim(380, 0)
    ax.axis("off")
    menus_data = [
        ("文件(F)", [
            ("载入参数…", "Ctrl+O"),
            ("保存参数…", "Ctrl+S"),
            ("载入示例参数", "AC3300-G 等"),
            ("恢复默认设置", ""),
            ("---", ""),
            ("退出", "Alt+F4"),
        ]),
        ("计算(C)", [
            ("计算", "F5"),
        ]),
        ("导出(E)", [
            ("刀具 DXF…", ""),
            ("刀具点表 CSV…", ""),
            ("圆弧刀具 DXF…", ""),
            ("星形套截面 DXF…", ""),
            ("---", ""),
            ("轮廓方程常数 CSV（Table 1）…", ""),
            ("基本轮廓 CSV（Table 2）…", ""),
        ]),
        ("视图(V)", [
            ("展开计算结果窗口", ""),
            ("展开 / 折叠高级参数", ""),
            ("---", ""),
            ("刀具廓形", "Ctrl+1"),
            ("球道截面", "Ctrl+2"),
            ("星形套截面", "Ctrl+3"),
            ("加工姿态(子午面)", "Ctrl+4"),
            ("反向仿真偏差", "Ctrl+5"),
            ("单圆弧近似", "Ctrl+6"),
        ]),
        ("帮助(H)", [
            ("打开示例目录", ""),
            ("打开数据文件夹（上次设置、参数、导出）", ""),
            ("---", ""),
            ("关于 TrackForm", ""),
        ]),
    ]
    xs = [15, 225, 385, 675, 935]
    ws = [195, 145, 275, 245, 300]
    for (mtitle, mitems), x0, w in zip(menus_data, xs, ws):
        ax.add_patch(Rectangle((x0, 15), w, 30, fc="#2f5d8c", ec="#1e293b", lw=1))
        ax.text(x0 + 14, 30, mtitle, color="white", fontsize=10, fontweight="bold", va="center")
        h_menu = 14 + len(mitems) * 32
        ax.add_patch(Rectangle((x0, 45), w, h_menu, fc="white", ec="#94a3b8", lw=1.2))
        for idx, (ilbl, iacc) in enumerate(mitems):
            iy = 65 + idx * 32
            if ilbl == "---":
                ax.plot([x0 + 8, x0 + w - 8], [iy, iy], color="#cbd5e1", lw=1)
            else:
                ax.text(x0 + 14, iy, ilbl, color="#0f172a", fontsize=8.8, va="center")
                if iacc:
                    ax.text(x0 + w - 12, iy, iacc, color="#1f6fd1", fontsize=8.5, fontweight="bold", ha="right", va="center")
    save_fig(fig, os.path.join(res7, "menus_overview.png"), dpi=160, pad=0.02)

    # 8.2 案例二：Nexteer 34205673 点表导入与单圆弧拟合验证图 (case2_nexteer_points.png)
    pts_path = os.path.join(TRACKFORM_ROOT, "examples", "Nexteer_34205673_截面点表.csv")
    h_nex = DummyHost(Params(ball_d=17.4625, pcd=55.9414, track_offset=0.0, section_type="points",
                             points_file=pts_path, points_tol=1e-5, clearance=0.0101,
                             clearance_min=0.0051, clearance_max=0.0201,
                             setting_angle=36.0, sphere_d=200.0, width=24.0, sphere_center_h=12.0,
                             tip_z=5.23775, extra_extend=0.0, profile_step=0.02))
    h_nex.render_all()
    save_fig(h_nex.figs["section"][0], os.path.join(res8, "case2_nexteer_section.png"))
    save_fig(h_nex.figs["arc"][0], os.path.join(res8, "case2_nexteer_arc.png"))

    # 8.3 案例三：双圆弧（尖底）球道精确成型刀 vs 单圆弧近似超差报警图 (case3_gothic_exact_vs_arc.png)
    h_goth = DummyHost(Params(section_type="gothic", conformity=1.04, profile_step=0.02))
    h_goth.render_all()
    save_fig(h_goth.figs["tool"][0], os.path.join(res8, "case3_gothic_tool.png"))
    save_fig(h_goth.figs["sim"][0], os.path.join(res8, "case3_gothic_sim.png"))
    save_fig(h_goth.figs["arc"][0], os.path.join(res8, "case3_gothic_arc_fail.png"))

    # 8.4 第 9 章故障排除：钢球未与截面贴合 vs 干涉 vs 正常贴合三联图 (err_ball_gap_mismatch.png)
    fig = Figure(figsize=(11.5, 3.8), dpi=160)
    p0, sec0, *_ = tipfig._base()
    tt = np.linspace(-1.3, 1.3, 300)
    y0, u0 = sec0.point(tt)
    th = np.linspace(-np.pi, 0, 200)
    configs = [
        (0.0, "① 正常状态：钢球与球道侧面相切贴合", "#16a34a", "最小间隙 ≈ 0，接触角处准确相切 [OK]"),
        (-0.45, "② 报错：钢球未与截面贴合！", "#d62728", "顶隙填得过大或椭圆中心高 uc 偏小，钢球悬空"),
        (0.45, "③ 报错：钢球与截面干涉（截面过窄）！", "#d62728", "顶隙填得过小或椭圆中心高 uc 偏大，钢球卡入壁面"),
    ]
    for i, (du, title_t, col, desc_t) in enumerate(configs):
        ax = fig.add_subplot(1, 3, i + 1)
        ax.plot(y0, u0 + du, "b-", lw=2.0, label="球道截面")
        ax.plot(p0.rb * np.cos(th), p0.rb * np.sin(th), "k--", lw=1.2, label="钢球")
        al = sec0.alpha
        for s in (1, -1):
            ax.plot(s * p0.rb * np.sin(al), -p0.rb * np.cos(al), "o", color=col, ms=6)
        ax.set_aspect("equal")
        ax.set_xlim(-11.5, 11.5)
        ax.set_ylim(-11.8, -1.5)
        ax.set_title(title_t, fontsize=9.5, fontweight="bold", color=col)
        ax.text(0, -2.5, desc_t, color=col, fontsize=8, ha="center",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=col, lw=0.8))
        ax.grid(alpha=0.3)
    fig.tight_layout()
    save_fig(fig, os.path.join(res9, "err_ball_gap_mismatch.png"))


def main():
    build_covers()
    build_tipfig_images()
    build_ch1_images()
    build_comparison_images()
    build_ch4_images()
    build_ch5_images()
    build_ch6_images()
    build_ch7_8_9_images()
    print("\n=== 全部配图生成完成！===")


if __name__ == "__main__":
    main()
