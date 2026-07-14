import os
import platform
from datetime import date

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.core.text import LabelBase  # 폰트 등록을 위해 필수 임포트
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Rectangle

# 기존 모듈 연결
from database import (
    init_db, load_subject_metadata,
    get_record, save_record, get_total_all_time, today_str, format_minutes,
    get_records_in_range, get_monthly_summary, date_range, clear_all_records
)

# 한글 폰트 등록
LabelBase.register(name="NanumGothic", fn_regular="NanumGothic.ttf")

# =========================================================================
# 윈도우 기본 크기 및 최소 크기 제한 설정 (데스크톱에서만 적용)
# =========================================================================
from kivy.utils import platform
if platform not in ('android', 'ios'):
    Window.size = (780, 540)
    Window.minimum_width = 640
    Window.minimum_height = 480

# =========================================================================
# 디자인 토큰
# =========================================================================
COLOR_BG = "#F5F6FA"
COLOR_CARD = "#FFFFFF"
COLOR_ACCENT = "#4A90E2"
COLOR_ACCENT_LIGHT = "#E8F0FE"
COLOR_TEXT_PRIMARY = "#1A1A2E"
COLOR_TEXT_SECONDARY = "#6B7280"
COLOR_TEXT_MUTED = "#9CA3AF"
COLOR_DANGER = "#EF4444"
COLOR_SUCCESS = "#10B981"
COLOR_NAV_BG = "#FFFFFF"
COLOR_NAV_INACTIVE = "#9CA3AF"
COLOR_NAV_ACTIVE = "#4A90E2"
COLOR_DIVIDER = "#E5E7EB"
CARD_RADIUS = dp(16)

# 배경색: 연한 그레이
Window.clearcolor = get_color_from_hex(COLOR_BG)


# =========================================================================
# 재사용 컴포넌트: 카드 위젯
# =========================================================================
class CardWidget(BoxLayout):
    """RoundedRectangle 배경을 가진 카드 컨테이너"""

    def __init__(self, bg_color=COLOR_CARD, radius=None, **kwargs):
        if 'padding' not in kwargs:
            kwargs['padding'] = dp(16)
        super().__init__(**kwargs)
        r = radius if radius is not None else CARD_RADIUS
        with self.canvas.before:
            Color(*get_color_from_hex(bg_color))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[r])
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size


# =========================================================================
# 재사용 컴포넌트: 둥근 모서리 버튼
# =========================================================================
class StyledButton(Button):
    """둥근 모서리 + 커스텀 색상 버튼"""

    def __init__(self, bg_hex=COLOR_ACCENT, text_color=(1, 1, 1, 1), radius=None, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = text_color
        self._bg_hex = bg_hex
        self._radius = radius if radius is not None else dp(12)
        with self.canvas.before:
            Color(*get_color_from_hex(bg_hex))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_bg_color(self, hex_color):
        """배경 색상을 동적으로 변경"""
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex(hex_color))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])


# =========================================================================
# 하단 네비게이션 바
# =========================================================================
class BottomNavBar(BoxLayout):
    """하단 탭 네비게이션 (아이콘 인디케이터 + 라벨)"""

    def __init__(self, screen_manager, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(62)
        self.sm = screen_manager

        # 상단 구분선
        self._divider = Widget(size_hint_y=None, height=dp(1))
        self.add_widget(self._divider)
        self._divider.bind(pos=self._draw_divider, size=self._draw_divider)

        # 탭 버튼 컨테이너
        self._nav_box = BoxLayout(orientation='horizontal', size_hint_y=1)
        self.add_widget(self._nav_box)

        # 배경 그리기
        with self._nav_box.canvas.before:
            Color(*get_color_from_hex(COLOR_NAV_BG))
            self._nav_bg_rect = Rectangle(pos=self._nav_box.pos, size=self._nav_box.size)
        self._nav_box.bind(pos=self._update_nav_bg, size=self._update_nav_bg)

        # 탭 데이터
        tab_data = [
            ("홈", "home"),
            ("통계", "stats"),
            ("설정", "settings"),
        ]
        self.tabs = []
        for label_text, screen_name in tab_data:
            tab_widget = self._create_tab(label_text, screen_name)
            self._nav_box.add_widget(tab_widget)
            self.tabs.append((tab_widget, screen_name))

        self.set_active("home")

    def _draw_divider(self, *args):
        self._divider.canvas.clear()
        with self._divider.canvas:
            Color(*get_color_from_hex(COLOR_DIVIDER))
            Rectangle(pos=self._divider.pos, size=self._divider.size)

    def _update_nav_bg(self, *args):
        self._nav_bg_rect.pos = self._nav_box.pos
        self._nav_bg_rect.size = self._nav_box.size

    def _create_tab(self, label_text, screen_name):
        tab = BoxLayout(orientation='vertical', padding=[0, dp(6), 0, dp(4)], spacing=dp(2))

        # 인디케이터 바 (활성 탭 표시용 가로 바)
        indicator = Widget(size_hint_y=None, height=dp(3))
        indicator._active_color = get_color_from_hex(COLOR_NAV_ACTIVE)
        indicator._inactive_color = get_color_from_hex(COLOR_NAV_INACTIVE)
        indicator._is_active = False

        def draw_indicator(widget, *args):
            widget.canvas.clear()
            if widget._is_active:
                with widget.canvas:
                    Color(*widget._active_color)
                    bar_w = min(widget.width * 0.6, dp(28))
                    bar_x = widget.x + (widget.width - bar_w) / 2
                    RoundedRectangle(pos=(bar_x, widget.y), size=(bar_w, widget.height), radius=[dp(1.5)])

        indicator.bind(pos=draw_indicator, size=draw_indicator)
        indicator._draw = draw_indicator

        # 텍스트 라벨
        lbl = Label(
            text=label_text, font_name="NanumGothic",
            font_size='13sp', bold=True,
            color=get_color_from_hex(COLOR_NAV_INACTIVE),
            size_hint_y=None, height=dp(20),
            halign='center', valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))

        tab.add_widget(indicator)
        tab.add_widget(lbl)

        tab._indicator = indicator
        tab._label = lbl
        tab._screen_name = screen_name

        tab.bind(on_touch_down=lambda w, t: self._on_tab_touch(w, t))
        return tab

    def _on_tab_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self.sm.current = widget._screen_name
            self.set_active(widget._screen_name)
            return True
        return False

    def set_active(self, screen_name):
        for tab, name in self.tabs:
            if name == screen_name:
                tab._indicator._is_active = True
                tab._indicator._draw(tab._indicator)
                tab._label.color = get_color_from_hex(COLOR_NAV_ACTIVE)
            else:
                tab._indicator._is_active = False
                tab._indicator._draw(tab._indicator)
                tab._label.color = get_color_from_hex(COLOR_NAV_INACTIVE)


# =========================================================================
# MainTabScreen: 모든 탭을 통합하는 컨테이너 (하단 내비 포함)
# =========================================================================
class MainTabScreen(Screen):
    """4개 탭(홈/통계/기록/설정)을 담고 하단 탭바를 고정하는 메인 컨테이너"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.main_layout = BoxLayout(orientation='vertical')

        # 하위 ScreenManager 생성 (탭 전환 시 깜빡임 없이 전환되도록 NoTransition 적용)
        self.sub_sm = ScreenManager(transition=NoTransition())

        self.home_scr = HomeScreen(name='home')
        self.stats_scr = StatsScreen(name='stats')
        self.record_scr = RecordScreen(name='record')
        self.settings_scr = SettingsScreen(name='settings')

        self.sub_sm.add_widget(self.home_scr)
        self.sub_sm.add_widget(self.stats_scr)
        self.sub_sm.add_widget(self.record_scr)
        self.sub_sm.add_widget(self.settings_scr)

        # 하단 네비게이션 바 생성
        self.nav_bar = BottomNavBar(self.sub_sm)

        self.main_layout.add_widget(self.sub_sm)
        self.main_layout.add_widget(self.nav_bar)

        self.add_widget(self.main_layout)

    def on_enter(self):
        # 복귀 시 현재 활성화된 하위 스크린의 on_enter 강제 유도
        if self.sub_sm.current_screen:
            self.sub_sm.current_screen.on_enter()


# =========================================================================
# HomeScreen: 카드 기반 세로 스크롤 레이아웃
# =========================================================================
class HomeScreen(Screen):
    """홈 화면 (인사말 + 도넛 차트 + 요약 카드 + 과목별 카드 + 빠른 기록 버튼)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.main_layout = BoxLayout(orientation='vertical')
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        # 세로 스크롤 콘텐츠 컨테이너
        self.content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(16), dp(16), dp(16), dp(16)],
            spacing=dp(14)
        )
        
        def update_height(*args):
            self.content.height = max(self.content.minimum_height, self.scroll_view.height)
            
        self.content.bind(minimum_height=update_height)
        self.scroll_view.bind(height=update_height)

        # --- 1. 인사말 카드 ---
        self.greeting_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(80),
            padding=[dp(20), dp(14), dp(20), dp(14)],
            spacing=dp(4)
        )
        greeting_lbl = Label(
            text="\uc624\ub298\uc758 \uacf5\ubd80 \ud604\ud669",
            font_name="NanumGothic",
            font_size='20sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(28),
            halign='left', valign='middle'
        )
        greeting_lbl.bind(size=greeting_lbl.setter('text_size'))

        self._date_lbl = Label(
            text="", font_name="NanumGothic",
            font_size='14sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(22),
            halign='left', valign='middle'
        )
        self._date_lbl.bind(size=self._date_lbl.setter('text_size'))

        self.greeting_card.add_widget(greeting_lbl)
        self.greeting_card.add_widget(self._date_lbl)
        self.content.add_widget(self.greeting_card)

        # --- 2. 도넛 차트 카드 ---
        self.chart_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(280),
            padding=[dp(16), dp(12), dp(16), dp(8)],
            spacing=dp(4)
        )
        chart_title = Label(
            text="\uc624\ub298 \uacf5\ubd80\uc2dc\uac04",
            font_name="NanumGothic",
            font_size='16sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(26),
            halign='left', valign='middle'
        )
        chart_title.bind(size=chart_title.setter('text_size'))
        self.chart_card.add_widget(chart_title)

        self.donut_container = BoxLayout(size_hint_y=1)
        self.chart_card.add_widget(self.donut_container)
        self.content.add_widget(self.chart_card)

        # --- 3. 요약 카드 (가로 2열) ---
        summary_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(90),
            spacing=dp(12)
        )

        # 오늘 총 공부시간 카드
        self.today_card = CardWidget(
            orientation='vertical',
            size_hint_x=0.5,
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(4)
        )
        today_title = Label(
            text="\uc624\ub298 \ucd1d \uacf5\ubd80",
            font_name="NanumGothic",
            font_size='13sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(18),
            halign='left', valign='middle'
        )
        today_title.bind(size=today_title.setter('text_size'))
        self.lbl_today_total = Label(
            text="0m", font_name="NanumGothic",
            font_size='24sp', bold=True,
            color=get_color_from_hex(COLOR_ACCENT),
            size_hint_y=None, height=dp(32),
            halign='left', valign='middle'
        )
        self.lbl_today_total.bind(size=self.lbl_today_total.setter('text_size'))
        self.today_card.add_widget(today_title)
        self.today_card.add_widget(self.lbl_today_total)

        # 전체 누적 공부시간 카드
        self.alltime_card = CardWidget(
            orientation='vertical',
            size_hint_x=0.5,
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(4)
        )
        alltime_title = Label(
            text="\uc804\uccb4 \ub204\uc801",
            font_name="NanumGothic",
            font_size='13sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(18),
            halign='left', valign='middle'
        )
        alltime_title.bind(size=alltime_title.setter('text_size'))
        self.lbl_total_all = Label(
            text="0m", font_name="NanumGothic",
            font_size='24sp', bold=True,
            color=get_color_from_hex(COLOR_SUCCESS),
            size_hint_y=None, height=dp(32),
            halign='left', valign='middle'
        )
        self.lbl_total_all.bind(size=self.lbl_total_all.setter('text_size'))
        self.alltime_card.add_widget(alltime_title)
        self.alltime_card.add_widget(self.lbl_total_all)

        summary_row.add_widget(self.today_card)
        summary_row.add_widget(self.alltime_card)
        self.content.add_widget(summary_row)

        # --- 4. 과목별 공부시간 카드 ---
        self.subjects_card = CardWidget(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(8)
        )
        subj_title = Label(
            text="\uacfc\ubaa9\ubcc4 \uacf5\ubd80\uc2dc\uac04",
            font_name="NanumGothic",
            font_size='16sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(26),
            halign='left', valign='middle'
        )
        subj_title.bind(size=subj_title.setter('text_size'))
        self.subjects_card.add_widget(subj_title)

        self.subjects_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(6)
        )
        self.subjects_card.add_widget(self.subjects_layout)
        self.content.add_widget(self.subjects_card)

        # --- 5. 빠른 기록 버튼 ---
        self.record_btn = StyledButton(
            text="\uacf5\ubd80 \uae30\ub85d\ud558\uae30",
            font_name="NanumGothic",
            font_size='17sp', bold=True,
            bg_hex=COLOR_ACCENT,
            size_hint_y=None, height=dp(52)
        )
        self.record_btn.bind(on_release=self.go_record_screen)
        self.content.add_widget(self.record_btn)

        # 상단 정렬을 위한 스페이서
        self.content.add_widget(Widget(size_hint_y=1))

        self.scroll_view.add_widget(self.content)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)

    def go_record_screen(self, instance):
        app = App.get_running_app()
        if app.root:
            main_tab = app.root.get_screen('main_tab')
            main_tab.sub_sm.current = 'record'

    def on_enter(self):
        self.refresh_ui()

    def refresh_ui(self):
        today_data = get_record(today_str())
        subjects, labels, colors = load_subject_metadata()

        # graph_kivy 지연 로딩
        from graph_kivy import draw_donut_kivy

        # 날짜 업데이트
        today = date.today()
        weekdays = ["\uc6d4", "\ud654", "\uc218", "\ubaa9", "\uae08", "\ud1a0", "\uc77c"]
        wd = weekdays[today.weekday()]
        self._date_lbl.text = f"{today.month}\uc6d4 {today.day}\uc77c ({wd})"

        # 1. 도넛 그래프 업데이트
        self.donut_container.clear_widgets()
        donut_widget = draw_donut_kivy(today_data, is_portrait=True)
        self.donut_container.add_widget(donut_widget)

        # 2. 오늘 총 공부시간 업데이트
        today_total = sum(today_data.values())
        self.lbl_today_total.text = format_minutes(today_total)

        # 3. 전체 누적 공부시간 업데이트
        total_all, _ = get_total_all_time()
        self.lbl_total_all.text = format_minutes(total_all)

        # 4. 과목별 공부시간 업데이트
        self.subjects_layout.clear_widgets()
        subject_count = len(subjects)
        self.subjects_layout.height = dp(subject_count * 40)
        # 부모 카드 높이도 업데이트 (타이틀 + 패딩 + 목록)
        self.subjects_card.height = dp(26 + 24 + 8 + subject_count * 40)

        for s in subjects:
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None, height=dp(36),
                spacing=dp(10)
            )

            # 색상 인디케이터 (원형 도트)
            color_dot = Label(
                text="-", font_name="NanumGothic",
                font_size='16sp', bold=True,
                color=get_color_from_hex(colors[s]),
                size_hint_x=None, width=dp(20),
                halign='center', valign='middle'
            )
            color_dot.bind(size=color_dot.setter('text_size'))

            # 과목명
            lbl_name = Label(
                text=labels[s], font_name="NanumGothic",
                font_size='15sp',
                color=get_color_from_hex(COLOR_TEXT_PRIMARY),
                size_hint_x=1,
                halign='left', valign='middle'
            )
            lbl_name.bind(size=lbl_name.setter('text_size'))

            # 공부 시간
            lbl_val = Label(
                text=format_minutes(today_data.get(s, 0)),
                font_name="NanumGothic",
                font_size='15sp', bold=True,
                color=get_color_from_hex(COLOR_TEXT_PRIMARY),
                size_hint_x=None, width=dp(80),
                halign='right', valign='middle'
            )
            lbl_val.bind(size=lbl_val.setter('text_size'))

            row.add_widget(color_dot)
            row.add_widget(lbl_name)
            row.add_widget(lbl_val)
            self.subjects_layout.add_widget(row)


# =========================================================================
# RecordScreen: 날짜 입력 축소 + 카드 기반 레이아웃
# =========================================================================
class RecordScreen(Screen):
    """공부 기록 입력 화면 (날짜 입력 가로폭 축소, 카드형 입력 폼)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.main_layout = BoxLayout(orientation='vertical')
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        self.content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(16), dp(16), dp(16), dp(16)],
            spacing=dp(14)
        )
        def update_height(*args):
            self.content.height = max(self.content.minimum_height, self.scroll_view.height)
            
        self.content.bind(minimum_height=update_height)
        self.scroll_view.bind(height=update_height)

        # --- 타이틀 카드 ---
        title_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(70),
            padding=[dp(20), dp(12), dp(20), dp(12)],
            spacing=dp(4)
        )
        title_lbl = Label(
            text="\uacf5\ubd80 \uae30\ub85d",
            font_name="NanumGothic",
            font_size='20sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(26),
            halign='left', valign='middle'
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))
        desc_lbl = Label(
            text="\uc2dc\uac04\uacfc \ubd84\uc744 \uc785\ub825\ud558\uace0 \uc800\uc7a5\ud558\uc138\uc694",
            font_name="NanumGothic", font_size='13sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(18),
            halign='left', valign='middle'
        )
        desc_lbl.bind(size=desc_lbl.setter('text_size'))
        title_card.add_widget(title_lbl)
        title_card.add_widget(desc_lbl)
        self.content.add_widget(title_card)

        # --- 날짜 선택 카드 (가로폭 축소) ---
        date_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(100),
            padding=[dp(20), dp(12), dp(20), dp(12)],
            spacing=dp(8)
        )
        date_title = Label(
            text="\ub0a0\uc9dc \uc120\ud0dd",
            font_name="NanumGothic",
            font_size='15sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(22),
            halign='left', valign='middle'
        )
        date_title.bind(size=date_title.setter('text_size'))
        date_card.add_widget(date_title)

        # 날짜 입력 행 (가로폭 제한)
        date_row_wrapper = BoxLayout(size_hint_y=None, height=dp(40))
        date_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(40),
            spacing=dp(6),
            size_hint_x=None, width=dp(260)
        )

        self.year_input = TextInput(
            input_filter='int', multiline=False,
            halign='center', font_size='15sp',
            hint_text="\ub144", size_hint_x=0.38,
            padding=[dp(4), dp(8), dp(4), dp(8)]
        )
        self.month_input = TextInput(
            input_filter='int', multiline=False,
            halign='center', font_size='15sp',
            hint_text="\uc6d4", size_hint_x=0.24,
            padding=[dp(4), dp(8), dp(4), dp(8)]
        )
        self.day_input = TextInput(
            input_filter='int', multiline=False,
            halign='center', font_size='15sp',
            hint_text="\uc77c", size_hint_x=0.24,
            padding=[dp(4), dp(8), dp(4), dp(8)]
        )

        sep_style = {
            'font_size': '16sp',
            'color': get_color_from_hex(COLOR_TEXT_MUTED),
            'size_hint_x': 0.07,
            'halign': 'center',
            'valign': 'middle'
        }

        date_row.add_widget(self.year_input)
        sep1 = Label(text="/", **sep_style)
        date_row.add_widget(sep1)
        date_row.add_widget(self.month_input)
        sep2 = Label(text="/", **sep_style)
        date_row.add_widget(sep2)
        date_row.add_widget(self.day_input)

        date_row_wrapper.add_widget(date_row)
        date_row_wrapper.add_widget(Widget(size_hint_x=1))  # 나머지 공간 밀어내기
        date_card.add_widget(date_row_wrapper)

        self.content.add_widget(date_card)

        # 오류 메시지용 라벨
        self.date_error_label = Label(
            text="", font_name="NanumGothic",
            font_size='13sp', color=get_color_from_hex(COLOR_DANGER),
            size_hint_y=None, height=dp(16),
            halign='left', valign='middle'
        )
        self.date_error_label.bind(size=self.date_error_label.setter('text_size'))
        self.content.add_widget(self.date_error_label)

        # --- 과목별 시간 입력 카드 ---
        self.form_card = CardWidget(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(16), dp(12), dp(16), dp(12)],
            spacing=dp(8)
        )
        form_title = Label(
            text="\uacfc\ubaa9\ubcc4 \uc2dc\uac04 \uc785\ub825",
            font_name="NanumGothic",
            font_size='15sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(24),
            halign='left', valign='middle'
        )
        form_title.bind(size=form_title.setter('text_size'))
        self.form_card.add_widget(form_title)

        self.form_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(6)
        )
        self.form_card.add_widget(self.form_container)
        self.content.add_widget(self.form_card)

        # --- 하단 액션 버튼 ---
        btn_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(50),
            spacing=dp(12)
        )
        save_btn = StyledButton(
            text="\uc800\uc7a5",
            font_name="NanumGothic",
            font_size='16sp', bold=True,
            bg_hex=COLOR_SUCCESS,
            size_hint_x=0.6
        )
        save_btn.bind(on_release=self.save_data)

        cancel_btn = StyledButton(
            text="\ucde8\uc18c",
            font_name="NanumGothic",
            font_size='16sp', bold=True,
            bg_hex=COLOR_TEXT_MUTED,
            size_hint_x=0.4
        )
        cancel_btn.bind(on_release=self.go_home)

        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        self.content.add_widget(btn_row)

        # 상단 정렬을 위한 스페이서
        self.content.add_widget(Widget(size_hint_y=1))

        self.scroll_view.add_widget(self.content)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)

    def go_home(self, instance):
        app = App.get_running_app()
        if app.root:
            main_tab = app.root.get_screen('main_tab')
            main_tab.sub_sm.current = 'home'
            main_tab.nav_bar.set_active('home')

    def on_enter(self):
        today = date.today()
        self.year_input.text = str(today.year)
        self.month_input.text = str(today.month)
        self.day_input.text = str(today.day)

        self.date_error_label.text = ""

        # 과목 동적 로딩 및 폼 입력 재구성
        subjects, labels, colors = load_subject_metadata()
        self.form_container.clear_widgets()

        # 헤더 행
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28), spacing=dp(8))
        h_subj = Label(
            text="\uacfc\ubaa9", font_name="NanumGothic", font_size='13sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_x=0.4, halign='left', valign='middle'
        )
        h_subj.bind(size=h_subj.setter('text_size'))
        h_hour = Label(
            text="\uc2dc\uac04", font_name="NanumGothic", font_size='13sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_x=0.3, halign='center', valign='middle'
        )
        h_hour.bind(size=h_hour.setter('text_size'))
        h_min = Label(
            text="\ubd84", font_name="NanumGothic", font_size='13sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_x=0.3, halign='center', valign='middle'
        )
        h_min.bind(size=h_min.setter('text_size'))
        header.add_widget(h_subj)
        header.add_widget(h_hour)
        header.add_widget(h_min)
        self.form_container.add_widget(header)

        self.inputs = {}
        today_data = get_record(today_str())

        form_height = dp(28)  # 헤더 높이

        for s in subjects:
            total_min = int(today_data.get(s, 0))
            h, m = divmod(total_min, 60)

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44), spacing=dp(8))

            # 과목 라벨 (색상 도트 + 이름)
            subj_label = BoxLayout(orientation='horizontal', size_hint_x=0.4, spacing=dp(6))
            dot = Label(
                text="-", font_name="NanumGothic",
                font_size='14sp', bold=True,
                color=get_color_from_hex(colors[s]),
                size_hint_x=None, width=dp(16),
                halign='center', valign='middle'
            )
            dot.bind(size=dot.setter('text_size'))
            name_lbl = Label(
                text=labels[s], font_name="NanumGothic",
                font_size='15sp', bold=True,
                color=get_color_from_hex(COLOR_TEXT_PRIMARY),
                halign='left', valign='middle'
            )
            name_lbl.bind(size=name_lbl.setter('text_size'))
            subj_label.add_widget(dot)
            subj_label.add_widget(name_lbl)

            txt_h = TextInput(
                text=str(h), input_filter='int',
                multiline=False, halign='center',
                font_size='16sp', size_hint_x=0.3,
                padding=[dp(4), dp(8), dp(4), dp(8)]
            )
            txt_m = TextInput(
                text=str(m), input_filter='int',
                multiline=False, halign='center',
                font_size='16sp', size_hint_x=0.3,
                padding=[dp(4), dp(8), dp(4), dp(8)]
            )

            row.add_widget(subj_label)
            row.add_widget(txt_h)
            row.add_widget(txt_m)
            self.form_container.add_widget(row)
            self.inputs[s] = (txt_h, txt_m)
            form_height += dp(50)  # 행 높이 + 스페이싱

        self.form_container.height = form_height
        self.form_card.height = form_height + dp(24 + 12 + 12 + 8)

    def save_data(self, instance):
        try:
            y = int(self.year_input.text)
            mo = int(self.month_input.text)
            d = int(self.day_input.text)
            selected_date = date(y, mo, d)
        except (ValueError, TypeError):
            self.date_error_label.text = "\ub0a0\uc9dc\ub97c \uc62c\ubc14\ub974\uac8c \uc785\ub825\ud574\uc8fc\uc138\uc694. (\uc608: 2025 / 2 / 3)"
            return

        date_str = selected_date.strftime("%Y-%m-%d")
        self.date_error_label.text = ""

        minutes_dict = {}
        for s, (txt_h, txt_m) in self.inputs.items():
            h = int(txt_h.text) if txt_h.text else 0
            m = int(txt_m.text) if txt_m.text else 0
            h = max(0, min(23, h))
            m = max(0, min(59, m))
            minutes_dict[s] = (h * 60) + m

        save_record(date_str, minutes_dict)
        self.go_home(None)


# =========================================================================
# StatsScreen: 카드 기반 통계 화면
# =========================================================================
class StatsScreen(Screen):
    """통계 화면 (기간 필터 카드 + 차트 카드)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_period = "week"

        self.main_layout = BoxLayout(orientation='vertical')
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        self.content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(16), dp(16), dp(16), dp(16)],
            spacing=dp(14)
        )
        
        def update_height(*args):
            self.content.height = max(self.content.minimum_height, self.scroll_view.height)
            
        self.content.bind(minimum_height=update_height)
        self.scroll_view.bind(height=update_height)

        # --- 타이틀 카드 ---
        title_card = CardWidget(
            orientation='horizontal',
            size_hint_y=None, height=dp(50),
            padding=[dp(20), dp(12), dp(20), dp(12)]
        )
        stats_title = Label(
            text="\ud559\uc2b5 \ud1b5\uacc4",
            font_name="NanumGothic",
            font_size='20sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            halign='left', valign='middle'
        )
        stats_title.bind(size=stats_title.setter('text_size'))
        title_card.add_widget(stats_title)
        self.content.add_widget(title_card)

        # --- 기간 필터 카드 ---
        filter_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(70),
            padding=[dp(12), dp(10), dp(12), dp(10)],
            spacing=dp(6)
        )
        filter_label = Label(
            text="\uae30\uac04 \uc120\ud0dd",
            font_name="NanumGothic",
            font_size='13sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(16),
            halign='left', valign='middle'
        )
        filter_label.bind(size=filter_label.setter('text_size'))
        filter_card.add_widget(filter_label)

        filter_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=dp(36),
            spacing=dp(8)
        )

        periods = [("\uc77c\uc8fc\uc77c", "week"), ("\ud55c\ub2ec", "month"), ("\uc77c\ub144", "year")]
        self.period_buttons = {}
        for label, key in periods:
            btn = StyledButton(
                text=label, font_name="NanumGothic",
                font_size='14sp', bold=True,
                bg_hex=COLOR_DIVIDER,
                text_color=get_color_from_hex(COLOR_TEXT_SECONDARY)
            )
            btn.bind(on_release=lambda x, k=key: self.set_period(k))
            filter_row.add_widget(btn)
            self.period_buttons[key] = btn

        filter_card.add_widget(filter_row)
        self.content.add_widget(filter_card)

        # --- 차트 카드 ---
        self.chart_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(380),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        self.chart_container = BoxLayout(size_hint_y=1)
        self.chart_card.add_widget(self.chart_container)
        self.content.add_widget(self.chart_card)

        # 상단 정렬을 위한 스페이서
        self.content.add_widget(Widget(size_hint_y=1))

        self.scroll_view.add_widget(self.content)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)

        # 화면 크기 변경 시 차트 새로고침 바인딩
        self.bind(size=self.on_size_change)

    def on_size_change(self, instance, value):
        # 탭이 활성화된 상태에서만 차트 재생성하여 중복 렌더링 방지
        if self.manager and self.manager.current == 'stats':
            self.refresh_ui()

    def on_enter(self):
        self.refresh_ui()

    def set_period(self, period_key):
        self.current_period = period_key
        self.refresh_ui()

    def refresh_ui(self):
        for key, btn in self.period_buttons.items():
            if key == self.current_period:
                btn.set_bg_color(COLOR_ACCENT)
                btn.color = (1, 1, 1, 1)
            else:
                btn.set_bg_color(COLOR_DIVIDER)
                btn.color = get_color_from_hex(COLOR_TEXT_SECONDARY)

        if self.current_period == "year":
            records = get_monthly_summary()
        else:
            start, end = date_range(self.current_period)
            records = get_records_in_range(start, end)

        # graph_kivy 지연 로딩
        from graph_kivy import draw_stacked_bar_kivy

        self.chart_container.clear_widgets()
        is_portrait = self.width < self.height
        chart_widget = draw_stacked_bar_kivy(records, is_portrait=is_portrait)
        self.chart_container.add_widget(chart_widget)


# =========================================================================
# SettingsScreen: 카드 기반 설정 화면
# =========================================================================
class SettingsScreen(Screen):
    """설정 화면 (카드형 설정 항목 + 앱 정보)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.main_layout = BoxLayout(orientation='vertical')
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        self.content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(16), dp(16), dp(16), dp(16)],
            spacing=dp(14)
        )
        def update_height(*args):
            self.content.height = max(self.content.minimum_height, self.scroll_view.height)
            
        self.content.bind(minimum_height=update_height)
        self.scroll_view.bind(height=update_height)

        # --- 타이틀 카드 ---
        title_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(70),
            padding=[dp(20), dp(12), dp(20), dp(12)],
            spacing=dp(4)
        )
        title_lbl = Label(
            text="\uc124\uc815",
            font_name="NanumGothic",
            font_size='20sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(26),
            halign='left', valign='middle'
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))
        desc_lbl = Label(
            text="\uc571 \uc124\uc815 \ubc0f \ub370\uc774\ud130\ub97c \uad00\ub9ac\ud569\ub2c8\ub2e4",
            font_name="NanumGothic", font_size='13sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(18),
            halign='left', valign='middle'
        )
        desc_lbl.bind(size=desc_lbl.setter('text_size'))
        title_card.add_widget(title_lbl)
        title_card.add_widget(desc_lbl)
        self.content.add_widget(title_card)

        # --- 데이터 관리 카드 ---
        data_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(140),
            padding=[dp(20), dp(16), dp(20), dp(16)],
            spacing=dp(10)
        )
        data_title = Label(
            text="\ub370\uc774\ud130 \uad00\ub9ac",
            font_name="NanumGothic",
            font_size='16sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(24),
            halign='left', valign='middle'
        )
        data_title.bind(size=data_title.setter('text_size'))
        data_desc = Label(
            text="\ubaa8\ub4e0 \uacf5\ubd80 \uae30\ub85d\uc744 \uc0ad\uc81c\ud569\ub2c8\ub2e4. \uc774 \uc791\uc5c5\uc740 \ub418\ub3cc\ub9b4 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
            font_name="NanumGothic", font_size='13sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(18),
            halign='left', valign='middle'
        )
        data_desc.bind(size=data_desc.setter('text_size'))

        reset_btn = StyledButton(
            text="\uae30\ub85d \uc804\uccb4 \ucd08\uae30\ud654",
            font_name="NanumGothic",
            font_size='15sp', bold=True,
            bg_hex=COLOR_DANGER,
            size_hint_y=None, height=dp(44)
        )
        reset_btn.bind(on_release=self.show_confirm_popup)

        data_card.add_widget(data_title)
        data_card.add_widget(data_desc)
        data_card.add_widget(reset_btn)
        self.content.add_widget(data_card)

        # --- 앱 정보 카드 ---
        info_card = CardWidget(
            orientation='vertical',
            size_hint_y=None, height=dp(100),
            padding=[dp(20), dp(16), dp(20), dp(16)],
            spacing=dp(6)
        )
        info_title = Label(
            text="\uc571 \uc815\ubcf4",
            font_name="NanumGothic",
            font_size='16sp', bold=True,
            color=get_color_from_hex(COLOR_TEXT_PRIMARY),
            size_hint_y=None, height=dp(24),
            halign='left', valign='middle'
        )
        info_title.bind(size=info_title.setter('text_size'))
        info_version = Label(
            text="Study Tracker v2.0",
            font_name="NanumGothic",
            font_size='14sp',
            color=get_color_from_hex(COLOR_TEXT_SECONDARY),
            size_hint_y=None, height=dp(20),
            halign='left', valign='middle'
        )
        info_version.bind(size=info_version.setter('text_size'))
        info_desc = Label(
            text="\ud6a8\uc728\uc801\uc778 \ud559\uc2b5 \uc2dc\uac04 \uad00\ub9ac\ub97c \ub3c4\uc640\ub4dc\ub9bd\ub2c8\ub2e4",
            font_name="NanumGothic", font_size='13sp',
            color=get_color_from_hex(COLOR_TEXT_MUTED),
            size_hint_y=None, height=dp(18),
            halign='left', valign='middle'
        )
        info_desc.bind(size=info_desc.setter('text_size'))

        info_card.add_widget(info_title)
        info_card.add_widget(info_version)
        info_card.add_widget(info_desc)
        self.content.add_widget(info_card)

        # 상단 정렬을 위한 스페이서
        self.content.add_widget(Widget(size_hint_y=1))

        self.scroll_view.add_widget(self.content)
        self.main_layout.add_widget(self.scroll_view)
        self.add_widget(self.main_layout)

    def show_confirm_popup(self, instance):
        # 팝업용 레이아웃 생성
        content_layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        # 경고 메시지
        content_layout.add_widget(
            Label(
                text="\uc815\ub9d0\ub85c \ubaa8\ub4e0 \uacf5\ubd80 \uae30\ub85d\uc744\n\ucd08\uae30\ud654\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?\n\n\uc774 \uc791\uc5c5\uc740 \ub418\ub3cc\ub9b4 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
                font_name="NanumGothic", font_size='15sp', halign='center', color=(1, 1, 1, 1)
            )
        )

        # 버튼 영역
        btn_box = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(45))

        confirm_btn = Button(
            text="\uc608, \ucd08\uae30\ud654",
            font_name="NanumGothic", bold=True,
            background_color=get_color_from_hex(COLOR_DANGER)
        )
        cancel_btn = Button(
            text="\uc544\ub2c8\uc624",
            font_name="NanumGothic", bold=True,
            background_color=get_color_from_hex(COLOR_TEXT_MUTED)
        )

        btn_box.add_widget(confirm_btn)
        btn_box.add_widget(cancel_btn)
        content_layout.add_widget(btn_box)

        # 기기 가로너비에 맞춰 팝업 크기 동적 결정 (최대 380dp)
        popup_width = min(Window.width * 0.85, dp(380))

        # 팝업 인스턴스 생성
        popup = Popup(
            title="\uae30\ub85d \ucd08\uae30\ud654 \ud655\uc778", title_font="NanumGothic",
            content=content_layout, size_hint=(None, None), size=(popup_width, dp(220)),
            auto_dismiss=False
        )

        # 바인딩
        cancel_btn.bind(on_release=popup.dismiss)
        confirm_btn.bind(on_release=lambda x: self.reset_history(popup))

        popup.open()

    def reset_history(self, popup):
        # DB 초기화 함수 호출
        clear_all_records()

        # 팝업 닫기
        popup.dismiss()

        # 홈 화면으로 복귀
        app = App.get_running_app()
        if app.root:
            main_tab = app.root.get_screen('main_tab')
            main_tab.sub_sm.current = 'home'
            main_tab.nav_bar.set_active('home')


# =========================================================================
# 로딩 화면
# =========================================================================
class LoadingScreen(Screen):
    """최초 실행 시 검은 화면 대신 나타나는 로딩 화면"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(50), spacing=dp(16))

        # 상단 여백
        layout.add_widget(Widget(size_hint_y=1))

        layout.add_widget(Label(
            text="Study Tracker",
            font_name="NanumGothic",
            font_size='30sp',
            bold=True,
            color=get_color_from_hex(COLOR_ACCENT),
            size_hint_y=None, height=dp(40),
            halign='center'
        ))
        layout.add_widget(Label(
            text="\ub370\uc774\ud130\ub97c \ubd88\ub7ec\uc624\ub294 \uc911...",
            font_name="NanumGothic",
            font_size='15sp',
            color=get_color_from_hex(COLOR_TEXT_MUTED),
            size_hint_y=None, height=dp(24),
            halign='center'
        ))

        # 하단 여백
        layout.add_widget(Widget(size_hint_y=1))

        self.add_widget(layout)


# =========================================================================
# 메인 앱
# =========================================================================
class StudyTrackerKivyApp(App):
    def build(self):
        # 검은 화면을 방지하기 위해 로딩 화면만 먼저 ScreenManager에 담아 반환
        self.sm = ScreenManager()
        self.loading_scr = LoadingScreen(name='loading')
        self.sm.add_widget(self.loading_scr)

        # 다음 프레임(0.1초 뒤)에 무거운 DB 초기화 및 실제 스크린 인스턴스 생성 실행
        Clock.schedule_once(self.initialize_app, 0.1)

        return self.sm

    def initialize_app(self, dt):
        # 1. DB 초기화 및 로드
        init_db()

        # 2. 메인 탭 스크린 생성 (내부에 4개 탭 포함)
        self.main_tab_scr = MainTabScreen(name='main_tab')

        # 3. ScreenManager에 추가
        self.sm.add_widget(self.main_tab_scr)

        # 4. 메인 탭 화면으로 전환 후 로딩 화면 제거
        self.sm.current = 'main_tab'
        self.sm.remove_widget(self.loading_scr)

        # 레이아웃 강제 갱신
        Clock.schedule_once(self._force_relayout, 0)

    def _force_relayout(self, dt):
        Window.size = Window.size


if __name__ == "__main__":
    StudyTrackerKivyApp().run()
