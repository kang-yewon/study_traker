import os
import platform
from datetime import date

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.core.text import LabelBase  # 폰트 등록을 위해 필수 임포트
from kivy.clock import Clock

# 기존 모듈 연결
from database import (
    init_db, SUBJECTS, SUBJECT_LABELS, SUBJECT_COLORS,
    get_record, save_record, get_total_all_time, today_str, format_minutes,
    get_records_in_range, get_monthly_summary, date_range
)
from graph_kivy import draw_donut_kivy, draw_stacked_bar_kivy

# 한글 폰트 등록
LabelBase.register(name="Malgun Gothic", fn_regular="NanumGothic.ttf")

# =========================================================================
# 윈도우 기본 크기 및 최소 크기 제한 설정
# =========================================================================
Window.size = (850, 680)
Window.minimum_width = 800
Window.minimum_height = 600

# [수정] 창 전체의 기본 배경색을 흰색으로 고정
# 기존에는 각 화면(canvas.before)에 크기가 2000x2000으로 고정된 흰색 사각형을
# 따로 그려서 배경을 덮었는데, 창 크기/레이아웃에 따라 일부 영역(특히 상단 탭 바
# 근처)이 Kivy 기본 배경색인 검정으로 비쳐 보이는 문제가 있었습니다.
# Window.clearcolor를 흰색으로 설정하면 창 전체가 항상 흰색 배경을 갖게 되어
# 이 문제가 근본적으로 해결됩니다.
Window.clearcolor = (1, 1, 1, 1)


class NavigationBar(BoxLayout):
    """상단 탭 네비게이션 바 역할"""

    def __init__(self, sm, current_tab, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = '50dp'

        # Home 버튼
        home_btn = Button(
            text="Home", font_name="Malgun Gothic", bold=True,
            background_color=get_color_from_hex("#4A90E2") if current_tab == "home" else get_color_from_hex("#BDC3C7")
        )
        home_btn.bind(on_release=lambda x: setattr(sm, 'current', 'home'))

        # 통계 버튼
        stats_btn = Button(
            text="통계", font_name="Malgun Gothic", bold=True,
            background_color=get_color_from_hex("#4A90E2") if current_tab == "stats" else get_color_from_hex("#BDC3C7")
        )
        stats_btn.bind(on_release=lambda x: setattr(sm, 'current', 'stats'))

        self.add_widget(home_btn)
        self.add_widget(stats_btn)


class HomeScreen(Screen):
    """1) Home 화면"""

    def on_enter(self):
        self.refresh_ui()

    def refresh_ui(self):
        self.clear_widgets()

        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(NavigationBar(self.manager, "home"))

        body = BoxLayout(orientation='horizontal', padding=20, spacing=20)

        # --- 좌측 영역 ---
        left_area = BoxLayout(orientation='vertical', size_hint_x=0.5, spacing=15)
        left_area.add_widget(Label(text="오늘 공부시간", font_name="Malgun Gothic", font_size='18sp', bold=True, size_hint_y=None, height='30dp', color=(0, 0, 0, 1)))

        today_data = get_record(today_str())
        donut_widget = draw_donut_kivy(today_data)
        left_area.add_widget(donut_widget)

        record_btn = Button(text="오늘 공부 기록", font_name="Malgun Gothic", font_size='16sp', bold=True, size_hint_y=None, height='55dp', background_color=get_color_from_hex("#4A90E2"))
        record_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'record'))
        left_area.add_widget(record_btn)

        # --- 우측 영역 ---
        right_area = BoxLayout(orientation='vertical', size_hint_x=0.5, padding=[10, 0, 10, 0], spacing=10)

        today_total = sum(today_data.values())
        right_area.add_widget(Label(text="오늘 총 공부시간", font_name="Malgun Gothic", font_size='14sp', color=(0.4, 0.4, 0.4, 1), halign='left', size_hint_y=None, height='20dp'))
        right_area.add_widget(Label(text=format_minutes(today_total), font_name="Malgun Gothic", font_size='24sp', bold=True, color=(0.1, 0.1, 0.1, 1), halign='left', size_hint_y=None, height='40dp'))

        total_all, _ = get_total_all_time()
        right_area.add_widget(Label(text="전체 누적 공부시간", font_name="Malgun Gothic", font_size='14sp', color=(0.4, 0.4, 0.4, 1), halign='left', size_hint_y=None, height='20dp'))
        right_area.add_widget(Label(text=format_minutes(total_all), font_name="Malgun Gothic", font_size='22sp', bold=True, color=(0.1, 0.1, 0.1, 1), halign='left', size_hint_y=None, height='40dp'))

        right_area.add_widget(Label(text="과목별 공부시간", font_name="Malgun Gothic", font_size='14sp', bold=True, color=(0.2, 0.2, 0.2, 1), halign='left', size_hint_y=None, height='30dp'))

        for s in SUBJECTS:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height='35dp')
            color_box = Label(text="■", font_name="Malgun Gothic", font_size='18sp', color=get_color_from_hex(SUBJECT_COLORS[s]), size_hint_x=0.1)
            lbl_name = Label(text=SUBJECT_LABELS[s], font_name="Malgun Gothic", font_size='14sp', color=(0, 0, 0, 1), size_hint_x=0.4, halign='left')
            lbl_val = Label(text=format_minutes(today_data[s]), font_name="Malgun Gothic", font_size='14sp', bold=True, color=(0, 0, 0, 1), size_hint_x=0.5, halign='right')
            row.add_widget(color_box)
            row.add_widget(lbl_name)
            row.add_widget(lbl_val)
            right_area.add_widget(row)

        right_area.add_widget(Label())  # 여백용 버퍼

        body.add_widget(left_area)
        body.add_widget(right_area)
        main_layout.add_widget(body)
        self.add_widget(main_layout)


class RecordScreen(Screen):
    """2) Record 화면"""

    def on_enter(self):
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        main_layout = BoxLayout(orientation='vertical', padding=30, spacing=15)

        main_layout.add_widget(Label(text="공부 기록", font_name="Malgun Gothic", font_size='22sp', bold=True, color=(0, 0, 0, 1), size_hint_y=None, height='40dp'))
        main_layout.add_widget(Label(text="시간과 분을 입력하고 저장해주세요. 같은 날짜로 다시 저장하면 기존 기록을 덮어씁니다.", font_name="Malgun Gothic", font_size='12sp', color=(0.4, 0.4, 0.4, 1), size_hint_y=None, height='20dp'))

        # [추가] 날짜 조정 영역 — 과목 입력 칸보다 위에 배치
        today = date.today()
        date_box = BoxLayout(orientation='horizontal', spacing=8, size_hint_y=None, height='45dp')
        date_box.add_widget(Label(text="날짜 조정", font_name="Malgun Gothic", font_size='15sp', bold=True, color=(0, 0, 0, 1), size_hint_x=0.3))

        self.year_input = TextInput(text=str(today.year), input_filter='int', multiline=False, halign='center', font_size='15sp', hint_text="년")
        self.month_input = TextInput(text=str(today.month), input_filter='int', multiline=False, halign='center', font_size='15sp', hint_text="월")
        self.day_input = TextInput(text=str(today.day), input_filter='int', multiline=False, halign='center', font_size='15sp', hint_text="일")

        date_box.add_widget(self.year_input)
        date_box.add_widget(Label(text="년", font_name="Malgun Gothic", font_size='15sp', color=(0, 0, 0, 1), size_hint_x=0.08))
        date_box.add_widget(self.month_input)
        date_box.add_widget(Label(text="월", font_name="Malgun Gothic", font_size='15sp', color=(0, 0, 0, 1), size_hint_x=0.08))
        date_box.add_widget(self.day_input)
        date_box.add_widget(Label(text="일", font_name="Malgun Gothic", font_size='15sp', color=(0, 0, 0, 1), size_hint_x=0.08))

        main_layout.add_widget(date_box)

        # 오류 메시지용 라벨 (잘못된 날짜 입력 시 표시)
        self.date_error_label = Label(text="", font_name="Malgun Gothic", font_size='12sp', color=(0.9, 0.2, 0.2, 1), size_hint_y=None, height='18dp')
        main_layout.add_widget(self.date_error_label)

        # 입력 폼 그리드 (과목명 | 시간 입력 | 분 입력)
        form_grid = GridLayout(cols=3, spacing=15, size_hint_y=None, height='280dp')
        self.inputs = {}
        today_data = get_record(today_str())
        for s in SUBJECTS:
            total_min = int(today_data.get(s, 0))
            h, m = divmod(total_min, 60)
            lbl = Label(text=f"■ {SUBJECT_LABELS[s]}", font_name="Malgun Gothic", font_size='16sp', bold=True, color=get_color_from_hex(SUBJECT_COLORS[s]))
            txt_h = TextInput(text=str(h), input_filter='int', multiline=False, halign='center', font_size='16sp')
            txt_m = TextInput(text=str(m), input_filter='int', multiline=False, halign='center', font_size='16sp')
            form_grid.add_widget(lbl)
            form_grid.add_widget(txt_h)
            form_grid.add_widget(txt_m)
            self.inputs[s] = (txt_h, txt_m)

        main_layout.add_widget(form_grid)

        # 하단 제어 버튼
        btn_group = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=None, height='55dp')
        save_btn = Button(text="기록 저장", font_name="Malgun Gothic", font_size='16sp', bold=True, background_color=get_color_from_hex("#2ECC71"))
        save_btn.bind(on_release=self.save_data)
        cancel_btn = Button(text="취소 및 돌아가기", font_name="Malgun Gothic", font_size='16sp', bold=True, background_color=get_color_from_hex("#95A5A6"))
        cancel_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'home'))
        btn_group.add_widget(save_btn)
        btn_group.add_widget(cancel_btn)
        main_layout.add_widget(btn_group)

        main_layout.add_widget(Label())  # 여백 버퍼
        self.add_widget(main_layout)

    def save_data(self, instance):
        # [추가] 날짜 조정 입력값 검증
        try:
            y = int(self.year_input.text)
            mo = int(self.month_input.text)
            d = int(self.day_input.text)
            selected_date = date(y, mo, d)
        except (ValueError, TypeError):
            self.date_error_label.text = "날짜를 올바르게 입력해주세요. (예: 2025 / 2 / 3)"
            return

        date_str = selected_date.strftime("%Y-%m-%d")
        self.date_error_label.text = ""

        minutes_dict = {}
        for s in SUBJECTS:
            txt_h, txt_m = self.inputs[s]
            h = int(txt_h.text) if txt_h.text else 0
            m = int(txt_m.text) if txt_m.text else 0
            h = max(0, min(23, h))
            m = max(0, min(59, m))
            minutes_dict[s] = (h * 60) + m

        # 같은 날짜가 이미 존재하면 database.py의 UPSERT 로직에 의해 자동으로 덮어쓰기 됨
        save_record(date_str, minutes_dict)
        self.manager.current = 'home'


class StatsScreen(Screen):
    """3) Stats 화면"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_period = "week"

    def on_enter(self):
        self.refresh_ui()

    def set_period(self, period_key):
        self.current_period = period_key
        self.refresh_ui()

    def refresh_ui(self):
        self.clear_widgets()
        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(NavigationBar(self.manager, "stats"))

        filter_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', padding=5, spacing=10)
        filter_bar.add_widget(Label(text="기간 선택:", font_name="Malgun Gothic", font_size='14sp', bold=True, color=(0, 0, 0, 1), size_hint_x=0.2))

        periods = [("일주일", "week"), ("한달", "month"), ("일년", "year")]
        for label, key in periods:
            is_active = (self.current_period == key)
            btn = Button(
                text=label, font_name="Malgun Gothic",
                background_color=get_color_from_hex("#4A90E2") if is_active else get_color_from_hex("#E0E0E0")
            )
            btn.bind(on_release=lambda x, k=key: self.set_period(k))
            filter_bar.add_widget(btn)

        main_layout.add_widget(filter_bar)

        if self.current_period == "year":
            records = get_monthly_summary()
        else:
            start, end = date_range(self.current_period)
            records = get_records_in_range(start, end)

        chart_widget = draw_stacked_bar_kivy(records)
        main_layout.add_widget(chart_widget)
        self.add_widget(main_layout)


class StudyTrackerKivyApp(App):
    def build(self):
        init_db()
        sm = ScreenManager()

        home_scr = HomeScreen(name='home')
        record_scr = RecordScreen(name='record')
        stats_scr = StatsScreen(name='stats')

        sm.add_widget(home_scr)
        sm.add_widget(record_scr)
        sm.add_widget(stats_scr)

        # [수정] 첫 로딩 시 UI가 왼쪽 아래로 찌부되어 보이는 문제 해결
        # 네이티브 창이 완전히 생성/초기화되기 전에 위젯들의 첫 레이아웃 계산이
        # 이루어지면서 발생하는 Kivy의 잘 알려진 타이밍 이슈입니다.
        # 다음 프레임에서 창 크기를 스스로에게 다시 대입해 강제로 리사이즈
        # 이벤트를 발생시키면, 모든 레이아웃이 실제 창 크기 기준으로 다시
        # 계산되어 정상적으로 표시됩니다.
        Clock.schedule_once(self._force_relayout, 0)

        return sm

    def _force_relayout(self, dt):
        Window.size = Window.size


if __name__ == "__main__":
    StudyTrackerKivyApp().run()
