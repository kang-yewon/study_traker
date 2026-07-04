import os
import platform
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

# 기존 모듈 연결[cite: 4]
from database import (
    init_db, SUBJECTS, SUBJECT_LABELS, SUBJECT_COLORS,
    get_record, save_record, get_total_all_time, today_str, format_minutes,
    get_records_in_range, get_monthly_summary, date_range
)
from graph_kivy import draw_donut_kivy, draw_stacked_bar_kivy

# 기존 register_korean_font 함수 지우고 이 2줄만 남기세요!
from kivy.core.text import LabelBase
LabelBase.register(name="Malgun Gothic", fn_regular="NanumGothic.ttf")
# =========================================================================
# [중요] Kivy 시스템에 한글 폰트(맑은 고딕) 명시적 등록 (OSError 해결)
# =========================================================================
# def register_korean_font():
#     sys_os = platform.system()
#     if sys_os == "Windows":
#         # Windows 표준 폰트 디렉토리 내부의 실제 파일 경로 매핑
#         font_dir = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts')
#         reg_font = os.path.join(font_dir, 'malgun.ttf')      # 일반
#         bold_font = os.path.join(font_dir, 'malgunbd.ttf')   # 굵게
        
#         if os.path.exists(reg_font):
#             LabelBase.register(
#                 name="Malgun Gothic", 
#                 fn_regular=reg_font, 
#                 fn_bold=bold_font if os.path.exists(bold_font) else reg_font
#             )
#     elif sys_os == "Darwin":  # macOS 대비용 예외 처리
#         mac_font = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
#         if os.path.exists(mac_font):
#             LabelBase.register(name="Malgun Gothic", fn_regular=mac_font)

# register_korean_font()
# =========================================================================

# 윈도우 기본 크기 및 최소 크기 제한 설정
Window.size = (850, 680)
Window.minimum_width = 800
Window.minimum_height = 600

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
        
        # 메인 레이아웃 (상단 탭바 + 하디 바디)
        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(NavigationBar(self.manager, "home"))
        
        # 콘텐츠 바디 (좌측 그래프, 우측 통계 텍스트)
        body = BoxLayout(orientation='horizontal', padding=20, spacing=20)
        
        # --- 좌측 영역 ---
        left_area = BoxLayout(orientation='vertical', size_hint_x=0.5, spacing=15)
        left_area.add_widget(Label(text="오늘 공부시간", font_name="Malgun Gothic", font_size='18sp', bold=True, size_hint_y=None, height='30dp', color=(0,0,0,1)))
        
        # 도넛 그래프 불러오기
        today_data = get_record(today_str())
        donut_widget = draw_donut_kivy(today_data)
        left_area.add_widget(donut_widget)
        
        # 오늘 공부 기록 버튼
        record_btn = Button(text="오늘 공부 기록", font_name="Malgun Gothic", font_size='16sp', bold=True, size_hint_y=None, height='55dp', background_color=get_color_from_hex("#4A90E2"))
        record_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'record'))
        left_area.add_widget(record_btn)
        
        # --- 우측 영역 ---
        right_area = BoxLayout(orientation='vertical', size_hint_x=0.5, padding=[10, 0, 10, 0], spacing=10)
        
        today_total = sum(today_data.values())
        right_area.add_widget(Label(text="오늘 총 공부시간", font_name="Malgun Gothic", font_size='14sp', color=(0.4,0.4,0.4,1), halign='left', size_hint_y=None, height='20dp'))
        right_area.add_widget(Label(text=format_minutes(today_total), font_name="Malgun Gothic", font_size='24sp', bold=True, color=(0.1,0.1,0.1,1), halign='left', size_hint_y=None, height='40dp'))
        
        total_all, _ = get_total_all_time()
        right_area.add_widget(Label(text="전체 누적 공부시간", font_name="Malgun Gothic", font_size='14sp', color=(0.4,0.4,0.4,1), halign='left', size_hint_y=None, height='20dp'))
        right_area.add_widget(Label(text=format_minutes(total_all), font_name="Malgun Gothic", font_size='22sp', bold=True, color=(0.1,0.1,0.1,1), halign='left', size_hint_y=None, height='40dp'))
        
        right_area.add_widget(Label(text="과목별 공부시간", font_name="Malgun Gothic", font_size='14sp', bold=True, color=(0.2,0.2,0.2,1), halign='left', size_hint_y=None, height='30dp'))
        
        # 과목별 리스트 생성
        for s in SUBJECTS:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height='35dp')
            color_box = Label(text="■", font_name="Malgun Gothic", font_size='18sp', color=get_color_from_hex(SUBJECT_COLORS[s]), size_hint_x=0.1)
            lbl_name = Label(text=SUBJECT_LABELS[s], font_name="Malgun Gothic", font_size='14sp', color=(0,0,0,1), size_hint_x=0.4, halign='left')
            lbl_val = Label(text=format_minutes(today_data[s]), font_name="Malgun Gothic", font_size='14sp', bold=True, color=(0,0,0,1), size_hint_x=0.5, halign='right')
            
            row.add_widget(color_box)
            row.add_widget(lbl_name)
            row.add_widget(lbl_val)
            right_area.add_widget(row)
            
        right_area.add_widget(Label()) # 여백용 버퍼
        
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
        
        main_layout.add_widget(Label(text=f"오늘 공부 기록 ({today_str()})", font_name="Malgun Gothic", font_size='22sp', bold=True, color=(0,0,0,1), size_hint_y=None, height='40dp'))
        main_layout.add_widget(Label(text="시간과 분을 입력하고 저장해주세요. (당일 기록은 언제든 덮어써집니다)", font_name="Malgun Gothic", font_size='12sp', color=(0.4,0.4,0.4,1), size_hint_y=None, height='20dp'))
        
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
        main_layout.add_widget(Label()) # 여백 버퍼
        
        self.add_widget(main_layout)

    def save_data(self, instance):
        minutes_dict = {}
        for s in SUBJECTS:
            txt_h, txt_m = self.inputs[s]
            h = int(txt_h.text) if txt_h.text else 0
            m = int(txt_m.text) if txt_m.text else 0
            
            h = max(0, min(23, h))
            m = max(0, min(59, m))
            minutes_dict[s] = (h * 60) + m
            
        save_record(today_str(), minutes_dict)
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
        
        # 기간 선택 세그먼트 버튼 바
        filter_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', padding=5, spacing=10)
        filter_bar.add_widget(Label(text="기간 선택:", font_name="Malgun Gothic", font_size='14sp', bold=True, color=(0,0,0,1), size_hint_x=0.2))
        
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
        
        # 데이터 쿼리 조건 분기
        if self.current_period == "year":
            records = get_monthly_summary()
        else:
            start, end = date_range(self.current_period)
            records = get_records_in_range(start, end)
            
        # 스택 바 차트 위젯화 후 배치
        chart_widget = draw_stacked_bar_kivy(records)
        main_layout.add_widget(chart_widget)
        
        self.add_widget(main_layout)


class StudyTrackerKivyApp(App):
    def build(self):
        from kivy.graphics import Color, Rectangle
        init_db()#[cite: 4]
        
        sm = ScreenManager()
        
        home_scr = HomeScreen(name='home')
        record_scr = RecordScreen(name='record')
        stats_scr = StatsScreen(name='stats')
        
        for scr in [home_scr, record_scr, stats_scr]:
            with scr.canvas.before:
                Color(1, 1, 1, 1) # 하얀색 배경 지정
                self.rect = Rectangle(size=(2000, 2000), pos=(0,0))
                
        sm.add_widget(home_scr)
        sm.add_widget(record_scr)
        sm.add_widget(stats_scr)
        
        return sm

if __name__ == "__main__":
    StudyTrackerKivyApp().run()#[cite: 4]