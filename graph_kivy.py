# graph_kivy.py
import io
import platform
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage

# 기존 database.py에서 필요한 요소 가져오기
from database import (
    load_subject_metadata,
    format_minutes,
)

_font_setup_done = False

def format_short(minutes):
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"

# 한글 폰트 설정
def _setup_korean_font():
    global _font_setup_done
    if _font_setup_done:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")  # 대화형 백엔드 비활성화 (Kivy 출력용)
        import matplotlib.pyplot as plt
        
        os_name = platform.system()
        if os_name == "Windows":
            plt.rcParams["font.family"] = "Malgun Gothic"
        elif os_name == "Darwin":
            plt.rcParams["font.family"] = "AppleGothic"
        else:
            plt.rcParams["font.family"] = "NanumGothic"
        plt.rcParams["axes.unicode_minus"] = False
        _font_setup_done = True
    except Exception:
        pass

def fig_to_kivy_widget(fig):
    """Matplotlib Figure를 Kivy Image 위젯으로 변환"""
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    im = CoreImage(buf, ext='png')
    kivy_img = KivyImage(texture=im.texture, fit_mode='contain')
    plt.close(fig)  # 백그라운드 피겨 닫기 (메모리 관리)
    return kivy_img

def draw_donut_kivy(per_subject, is_portrait=False):
    """오늘 공부시간 도넛 그래프 생성"""
    _setup_korean_font()
    from matplotlib.figure import Figure
    
    subjects, labels, colors = load_subject_metadata()
    total = sum(per_subject.values())
    
    if is_portrait:
        fig = Figure(figsize=(3.5, 3.5), dpi=100)
    else:
        fig = Figure(figsize=(4, 4), dpi=100)
        
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111)
    
    if total <= 0:
        ax.pie([1], colors=["#E0E0E0"], wedgeprops=dict(width=0.35, edgecolor="white"), startangle=90)
        center_text = "0m"
    else:
        values = [per_subject.get(s, 0) for s in subjects]
        color_list = [colors[s] for s in subjects]
        filtered = [(v, c) for v, c in zip(values, color_list) if v > 0]
        vs = [v for v, _ in filtered]
        cs = [c for _, c in filtered]
        ax.pie(vs, colors=cs, wedgeprops=dict(width=0.35, edgecolor="white"), startangle=90)
        center_text = format_minutes(total)
        
    text_size = 11 if is_portrait else 14
    ax.text(0, 0, center_text, ha="center", va="center", fontsize=text_size, fontweight="bold")
    ax.set(aspect="equal")
    return fig_to_kivy_widget(fig)

def draw_stacked_bar_kivy(records, is_portrait=False):
    """통계 화면 스택 바 차트 생성"""
    _setup_korean_font()
    from matplotlib.figure import Figure
    
    subjects, labels, colors = load_subject_metadata()
    
    if is_portrait:
        fig = Figure(figsize=(4.5, 5.0), dpi=100)
    else:
        fig = Figure(figsize=(7, 4.5), dpi=100)
        
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111)
    
    if not records:
        ax.text(0.5, 0.5, "기록이 없습니다", ha="center", va="center", fontsize=12, transform=ax.transAxes, color="#888")
        ax.set_xticks([])
        ax.set_yticks([])
        return fig_to_kivy_widget(fig)
        
    labels_dates = [r["date"][5:] for r in records]
    n = len(records)
    x = list(range(n))
    bottoms = [0.0] * n
    
    for s in subjects:
        vals = [r.get(s, 0) / 60.0 for r in records]
        ax.bar(x, vals, bottom=bottoms, color=colors[s], label=labels[s], width=0.5, edgecolor="white")
        bottoms = [b + v for b, v in zip(bottoms, vals)]
        
    max_total = max(bottoms) if bottoms else 0
    label_fontsize = 7 if is_portrait else 8
    
    for i, total_hours in enumerate(bottoms):
        total_minutes = int(round(total_hours * 60))
        if total_minutes <= 0:
            continue
        ax.text(i, total_hours + max(max_total * 0.02, 0.05), format_short(total_minutes), ha="center", va="bottom", fontsize=label_fontsize)
        
    ax.set_xticks(x)
    if n > 10:
        ax.set_xticklabels(labels_dates, rotation=45, ha="right", fontsize=label_fontsize - 1)
    else:
        ax.set_xticklabels(labels_dates, fontsize=label_fontsize)
        
    ax.set_ylabel("공부시간 (시간)", fontsize=label_fontsize + 1)
    ax.set_ylim(0, max(max_total * 1.2, 1))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    
    legend_cols = min(2 if is_portrait else 5, len(subjects))
    legend_fontsize = 6 if is_portrait else 7
    ax.legend(loc="upper right", fontsize=legend_fontsize, frameon=False, ncol=legend_cols)
    fig.tight_layout()
    
    return fig_to_kivy_widget(fig)