// Study Tracker Web / Capacitor App Logic
// Comprehensive update: Subject management, Stopwatch with background persistence, and Date-specific adjustment

(function() {
  'use strict';

  // --- Constants & Default Data ---
  const DEFAULT_SUBJECTS = [
    { code: 'korean', name: '국어', color: '#4A90E2', isDefault: true, deleted: false },
    { code: 'english', name: '영어', color: '#2ECC71', isDefault: true, deleted: false },
    { code: 'math', name: '수학', color: '#F39C12', isDefault: true, deleted: false },
    { code: 'science', name: '과학', color: '#9B59B6', isDefault: true, deleted: false },
    { code: 'social', name: '사회', color: '#F1C40F', isDefault: true, deleted: false }
  ];

  // Available Color Palette (5 default subject colors + 6 custom colors = 11 colors)
  const COLOR_PALETTE = [
    { name: '파랑', hex: '#4A90E2' },
    { name: '초록', hex: '#2ECC71' },
    { name: '주황', hex: '#F39C12' },
    { name: '보라', hex: '#9B59B6' },
    { name: '노랑', hex: '#F1C40F' },
    { name: '빨강', hex: '#E74C3C' },
    { name: '분홍', hex: '#FF69B4' },
    { name: '갈색', hex: '#8D6E63' },
    { name: '짙은 남색', hex: '#1A237E' },
    { name: '민트색', hex: '#1ABC9C' },
    { name: '아이보리', hex: '#F5F5DC' }
  ];

  const STORAGE_KEYS = {
    SUBJECTS: 'study_tracker_subjects_v2',
    RECORDS: 'study_tracker_records_v1',
    STOPWATCH: 'study_tracker_stopwatch_state_v1'
  };

  // --- State Variables ---
  let currentScreen = 'home';
  let currentStatsPeriod = 'week';
  let donutChart = null;
  let statsChart = null;
  let stopwatchInterval = null;
  let selectedNewSubjectColor = null;
  let subjectToDeleteCode = null;

  // --- Helper: Date Functions ---
  function todayStr() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  function formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dStr = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${dStr}`;
  }

  function formatMinutes(minutes) {
    const min = Math.round(Number(minutes) || 0);
    const h = Math.floor(min / 60);
    const m = min % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  function formatShort(minutes) {
    const min = Math.round(Number(minutes) || 0);
    const h = Math.floor(min / 60);
    const m = min % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
  }

  // Format seconds into HH:MM (e.g. 01:32) as seen in Image 2
  function formatSecondsToHHMM(totalSeconds) {
    const sec = Math.max(0, Math.floor(Number(totalSeconds) || 0));
    const totalMinutes = Math.floor(sec / 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    const hStr = String(h).padStart(2, '0');
    const mStr = String(m).padStart(2, '0');
    return `${hStr}:${mStr}`;
  }

  // --- Data Access: Subjects ---
  function getAllSubjects() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.SUBJECTS);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.error(e);
    }
    // Initial migration/setup
    saveAllSubjects(DEFAULT_SUBJECTS);
    return DEFAULT_SUBJECTS;
  }

  function saveAllSubjects(subjects) {
    try {
      localStorage.setItem(STORAGE_KEYS.SUBJECTS, JSON.stringify(subjects));
    } catch (e) {
      console.error(e);
    }
  }

  function getActiveSubjects() {
    return getAllSubjects().filter(s => !s.deleted);
  }

  function getSubjectByCode(code) {
    return getAllSubjects().find(s => s.code === code) || null;
  }

  // Add a new subject
  function addNewSubject(name, color) {
    const subjects = getAllSubjects();
    const code = 'subj_' + Date.now();
    subjects.push({
      code: code,
      name: name.trim(),
      color: color,
      isDefault: false,
      deleted: false
    });
    saveAllSubjects(subjects);
  }

  // Soft-delete subject (past study records are completely preserved!)
  function softDeleteSubject(code) {
    const subjects = getAllSubjects();
    const target = subjects.find(s => s.code === code);
    if (target) {
      target.deleted = true;
      saveAllSubjects(subjects);
    }
  }

  // --- Data Access: Records ---
  function getRecords() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.RECORDS);
      if (stored) return JSON.parse(stored);
    } catch (e) {
      console.error(e);
    }
    return {};
  }

  function saveRecords(records) {
    try {
      localStorage.setItem(STORAGE_KEYS.RECORDS, JSON.stringify(records));
    } catch (e) {
      console.error(e);
    }
  }

  function getRecordForDate(dateStr) {
    const records = getRecords();
    return records[dateStr] || {};
  }

  function saveRecordForDate(dateStr, minutesDict) {
    const records = getRecords();
    records[dateStr] = { ...(records[dateStr] || {}) };
    for (const [code, min] of Object.entries(minutesDict)) {
      records[dateStr][code] = Math.max(0, Number(min) || 0);
    }
    saveRecords(records);
  }

  function getAllTimeTotal() {
    const records = getRecords();
    const subjects = getAllSubjects();
    let total = 0;
    const perSubject = {};
    subjects.forEach(s => { perSubject[s.code] = 0; });

    Object.values(records).forEach(dayRecord => {
      Object.entries(dayRecord).forEach(([code, val]) => {
        const min = Number(val) || 0;
        perSubject[code] = (perSubject[code] || 0) + min;
        total += min;
      });
    });
    return { total, perSubject };
  }

  function clearAllRecords() {
    localStorage.removeItem(STORAGE_KEYS.RECORDS);
    localStorage.removeItem(STORAGE_KEYS.STOPWATCH);
  }

  // --- Data Access: Stopwatch State ---
  function getStopwatchState() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.STOPWATCH);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error(e);
    }
    return {
      date: todayStr(),
      activeSubject: null,
      startTime: null,
      accumulatedSeconds: {}
    };
  }

  function saveStopwatchState(state) {
    try {
      localStorage.setItem(STORAGE_KEYS.STOPWATCH, JSON.stringify(state));
    } catch (e) {
      console.error(e);
    }
  }

  // Calculate live current seconds for a subject
  function getLiveSecondsForSubject(state, code) {
    let sec = (state.accumulatedSeconds && state.accumulatedSeconds[code]) || 0;
    if (state.activeSubject === code && state.startTime) {
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      sec += Math.max(0, elapsed);
    }
    return sec;
  }

  // Sync today's saved records into stopwatch state if stopwatch is empty
  function initStopwatchFromSavedRecord(dateStr) {
    let state = getStopwatchState();
    if (state.date !== dateStr) {
      // New day or different date selected
      state = {
        date: dateStr,
        activeSubject: null,
        startTime: null,
        accumulatedSeconds: {}
      };
      // Populate from existing record if any
      const saved = getRecordForDate(dateStr);
      Object.entries(saved).forEach(([code, min]) => {
        state.accumulatedSeconds[code] = (min || 0) * 60;
      });
      saveStopwatchState(state);
    } else {
      // If today and accumulatedSeconds empty, pre-fill from saved
      const saved = getRecordForDate(dateStr);
      let hasAccumulated = Object.values(state.accumulatedSeconds).some(s => s > 0);
      if (!hasAccumulated && Object.keys(saved).length > 0) {
        Object.entries(saved).forEach(([code, min]) => {
          state.accumulatedSeconds[code] = (min || 0) * 60;
        });
        saveStopwatchState(state);
      }
    }
    return state;
  }

  // --- Screen Navigation ---
  function showScreen(name) {
    currentScreen = name;
    document.querySelectorAll('.screen').forEach(scr => scr.classList.remove('active'));
    const target = document.getElementById(`screen-${name}`);
    if (target) target.classList.add('active');

    // Update navbar active state and visibility
    const navbar = document.querySelector('.navbar');
    const homeBtn = document.getElementById('nav-btn-home');
    const statsBtn = document.getElementById('nav-btn-stats');

    if (name === 'settings') {
      // User rule: 설정 들어가면 위쪽에 HOME 과 통계 탭이 없어야 해
      if (navbar) navbar.style.display = 'none';
    } else {
      if (navbar) navbar.style.display = 'flex';
      if (name === 'home' || name === 'record') {
        homeBtn.classList.add('active');
        statsBtn.classList.remove('active');
      } else if (name === 'stats') {
        homeBtn.classList.remove('active');
        statsBtn.classList.add('active');
      }
    }

    if (name === 'home') renderHomeScreen();
    if (name === 'stats') renderStatsScreen();
    if (name === 'record') renderStopwatchScreen();
    if (name === 'settings') renderSettingsScreen();
  }

  // =========================================================================
  // 1. Home Screen Logic
  // =========================================================================
  function renderHomeScreen() {
    const today = todayStr();
    const todayData = getRecordForDate(today);
    const allSubjects = getAllSubjects();
    const activeSubjects = getActiveSubjects();

    // Map of code to subject metadata
    const subjectMap = {};
    allSubjects.forEach(s => { subjectMap[s.code] = s; });

    // Include active subjects, plus any deleted subjects that have minutes today
    const displaySubjects = [...activeSubjects];
    Object.keys(todayData).forEach(code => {
      if (todayData[code] > 0 && !displaySubjects.some(s => s.code === code)) {
        const sub = subjectMap[code];
        if (sub) displaySubjects.push(sub);
      }
    });

    const todayTotal = Object.values(todayData).reduce((a, b) => a + b, 0);
    const { total: allTotal } = getAllTimeTotal();

    document.getElementById('home-today-total').textContent = formatMinutes(todayTotal);
    document.getElementById('home-all-total').textContent = formatMinutes(allTotal);
    document.getElementById('donut-center-text').textContent = formatMinutes(todayTotal);

    // Subject list
    const listEl = document.getElementById('home-subject-list');
    listEl.innerHTML = '';
    displaySubjects.forEach(s => {
      const row = document.createElement('div');
      row.className = 'subject-item';
      row.innerHTML = `
        <span class="subject-badge" style="color: ${s.color};">■</span>
        <span class="subject-name">${s.name}${s.deleted ? ' (삭제됨)' : ''}</span>
        <span class="subject-time">${formatMinutes(todayData[s.code] || 0)}</span>
      `;
      listEl.appendChild(row);
    });

    // Donut Chart
    renderDonutChart(todayData, displaySubjects, todayTotal);
  }

  function renderDonutChart(todayData, displaySubjects, total) {
    const ctx = document.getElementById('donut-canvas').getContext('2d');
    if (donutChart) donutChart.destroy();

    let chartData = [];
    let bgColors = [];

    if (total <= 0) {
      chartData = [1];
      bgColors = ['#E0E0E0'];
    } else {
      displaySubjects.forEach(s => {
        const val = todayData[s.code] || 0;
        if (val > 0) {
          chartData.push(val);
          bgColors.push(s.color);
        }
      });
    }

    donutChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: chartData,
          backgroundColor: bgColors,
          borderWidth: 2,
          borderColor: '#FFFFFF',
          hoverOffset: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '68%',
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: total > 0,
            callbacks: {
              label: function(context) {
                const min = context.raw;
                return ` ${formatMinutes(min)}`;
              }
            }
          }
        }
      }
    });
  }

  // =========================================================================
  // 2. Stopwatch Screen Logic (Image 2 UI & Rules)
  // =========================================================================
  function renderStopwatchScreen() {
    const state = initStopwatchFromSavedRecord(todayStr());
    initStopwatchDateSelectors(state.date);
    renderStopwatchCards(state);
    startStopwatchLiveTicker();
  }

  function initStopwatchDateSelectors(selectedDateStr) {
    const [y, m, d] = selectedDateStr.split('-').map(Number);
    const yearInput = document.getElementById('stopwatch-year');
    const monthSelect = document.getElementById('stopwatch-month');
    const daySelect = document.getElementById('stopwatch-day');

    yearInput.value = y;

    monthSelect.innerHTML = '';
    for (let i = 1; i <= 12; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = `${i}월`;
      if (i === m) opt.selected = true;
      monthSelect.appendChild(opt);
    }

    updateStopwatchDayOptions(y, m, d);
  }

  function updateStopwatchDayOptions(year, month, selectedDay) {
    const daySelect = document.getElementById('stopwatch-day');
    daySelect.innerHTML = '';
    const daysInMonth = new Date(year, month, 0).getDate();
    for (let i = 1; i <= daysInMonth; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = `${i}일`;
      if (i === selectedDay) opt.selected = true;
      daySelect.appendChild(opt);
    }
  }

  function getStopwatchSelectedDate() {
    const y = parseInt(document.getElementById('stopwatch-year').value, 10);
    const m = parseInt(document.getElementById('stopwatch-month').value, 10);
    const d = parseInt(document.getElementById('stopwatch-day').value, 10);
    const mStr = String(m).padStart(2, '0');
    const dStr = String(d).padStart(2, '0');
    return `${y}-${mStr}-${dStr}`;
  }

  function renderStopwatchCards(state) {
    const activeSubjects = getActiveSubjects();
    const cardListEl = document.getElementById('stopwatch-card-list');
    cardListEl.innerHTML = '';

    activeSubjects.forEach(s => {
      const isRunning = (state.activeSubject === s.code);
      const totalSec = getLiveSecondsForSubject(state, s.code);
      const timeHHMM = formatSecondsToHHMM(totalSec);

      const card = document.createElement('div');
      card.className = `stopwatch-card ${isRunning ? 'running' : ''}`;
      card.id = `stopwatch-card-${s.code}`;

      card.innerHTML = `
        <div class="stopwatch-left">
          <div class="stopwatch-subject-name">
            <span style="color: ${s.color};">■</span>
            ${s.name}
          </div>
          <button class="stopwatch-status-pill ${isRunning ? 'btn-stop' : 'btn-start'}" data-code="${s.code}">
            ${isRunning ? '멈춤' : '시작'}
          </button>
        </div>
        <div class="stopwatch-time-pill ${isRunning ? 'ticking' : ''}" id="time-display-${s.code}">
          ${timeHHMM}
        </div>
      `;

      // Event listener for Start / Stop toggle
      const toggleBtn = card.querySelector('.stopwatch-status-pill');
      toggleBtn.addEventListener('click', () => handleStopwatchToggle(s.code));

      cardListEl.appendChild(card);
    });
  }

  function handleStopwatchToggle(clickedCode) {
    let state = getStopwatchState();

    if (state.activeSubject === clickedCode) {
      // 1. User clicked "멈춤" on currently running subject
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      state.accumulatedSeconds[clickedCode] = (state.accumulatedSeconds[clickedCode] || 0) + Math.max(0, elapsed);
      state.activeSubject = null;
      state.startTime = null;
      saveStopwatchState(state);
      renderStopwatchCards(state);

    } else if (state.activeSubject !== null) {
      // 2. User clicked "시작" while ANOTHER subject is currently running
      // Rule: "두 스탑워치를 동시에 실행하는 건 안돼... 국어 공부로 전환하고 싶으면 멈춤 버튼을 누르면 돼. 그 다음 국어 시작 버튼을 눌러야 하고."
      const runningSubject = getSubjectByCode(state.activeSubject);
      const runningName = runningSubject ? runningSubject.name : '다른 과목';
      alert(`[${runningName}] 공부가 이미 진행 중입니다!\n동시에 두 과목을 잴 수 없으므로, 먼저 진행 중인 [${runningName}]의 [멈춤] 버튼을 눌러주세요.`);

    } else {
      // 3. No subject is running -> Start this subject
      state.activeSubject = clickedCode;
      state.startTime = Date.now();
      saveStopwatchState(state);
      renderStopwatchCards(state);
    }
  }

  // 1-second interval ticker for smooth display updates
  function startStopwatchLiveTicker() {
    if (stopwatchInterval) clearInterval(stopwatchInterval);

    stopwatchInterval = setInterval(() => {
      const state = getStopwatchState();
      if (!state.activeSubject) return;

      const code = state.activeSubject;
      const totalSec = getLiveSecondsForSubject(state, code);
      const displayEl = document.getElementById(`time-display-${code}`);
      if (displayEl) {
        displayEl.textContent = formatSecondsToHHMM(totalSec);
      }
    }, 1000);
  }

  // "공부 끝" (Finish Study) Button Action
  function finishStudySession() {
    let state = getStopwatchState();

    // 1. Stop any currently active subject
    if (state.activeSubject && state.startTime) {
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      state.accumulatedSeconds[state.activeSubject] = (state.accumulatedSeconds[state.activeSubject] || 0) + Math.max(0, elapsed);
      state.activeSubject = null;
      state.startTime = null;
      saveStopwatchState(state);
    }

    // 2. Commit all accumulated seconds to database record (converted to minutes)
    const targetDate = state.date || todayStr();
    const minutesDict = {};
    let totalSavedMinutes = 0;

    Object.entries(state.accumulatedSeconds).forEach(([code, sec]) => {
      const min = Math.floor((sec || 0) / 60);
      minutesDict[code] = min;
      totalSavedMinutes += min;
    });

    saveRecordForDate(targetDate, minutesDict);

    // 3. Immediately reflect in UI & alert
    alert(`공부가 종료되었습니다!\n총 ${formatMinutes(totalSavedMinutes)}의 기록이 저장되어 통계에 즉시 반영되었습니다.`);

    // 4. Return to Home screen with updated stats
    showScreen('home');
  }

  // =========================================================================
  // 3. Stats Screen Logic
  // =========================================================================
  function getStatsData(period) {
    const allSubjects = getAllSubjects();
    const records = getRecords();

    // Determine all subjects that ever had records, or are active
    const subjectMap = {};
    allSubjects.forEach(s => { subjectMap[s.code] = s; });

    if (period === 'year') {
      const monthlyGroups = {};
      const now = new Date();
      for (let i = 11; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const key = `${y}-${m}`;
        monthlyGroups[key] = { count: 0, sums: {} };
        allSubjects.forEach(s => { monthlyGroups[key].sums[s.code] = 0; });
      }

      Object.entries(records).forEach(([dateStr, record]) => {
        const monthKey = dateStr.slice(0, 7);
        if (monthlyGroups[monthKey]) {
          monthlyGroups[monthKey].count += 1;
          Object.entries(record).forEach(([code, min]) => {
            if (!monthlyGroups[monthKey].sums[code]) monthlyGroups[monthKey].sums[code] = 0;
            monthlyGroups[monthKey].sums[code] += (Number(min) || 0);
          });
        }
      });

      const labels = Object.keys(monthlyGroups);
      // Only include subjects that have > 0 minutes in this period or are active
      const relevantSubjects = allSubjects.filter(s => {
        return !s.deleted || labels.some(mKey => (monthlyGroups[mKey].sums[s.code] || 0) > 0);
      });

      const datasets = relevantSubjects.map(s => {
        const data = labels.map(mKey => {
          const group = monthlyGroups[mKey];
          const avg = group.count > 0 ? Math.round((group.sums[s.code] || 0) / group.count) : 0;
          return Number((avg / 60).toFixed(2));
        });
        return {
          label: s.name,
          data: data,
          backgroundColor: s.color,
          stack: 'study',
          borderWidth: 1,
          borderColor: '#FFFFFF'
        };
      });

      const totalsInMinutes = labels.map(mKey => {
        const group = monthlyGroups[mKey];
        if (group.count <= 0) return 0;
        let total = 0;
        relevantSubjects.forEach(s => { total += (group.sums[s.code] || 0); });
        return Math.round(total / group.count);
      });

      return { labels, datasets, totalsInMinutes };

    } else {
      const daysCount = (period === 'week') ? 7 : 30;
      const dates = [];
      const labels = [];
      const now = new Date();

      for (let i = daysCount - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(now.getDate() - i);
        const dateStr = formatDate(d);
        dates.push(dateStr);
        labels.push(dateStr.slice(5)); // MM-DD
      }

      // Check which subjects have records across these dates
      const relevantSubjects = allSubjects.filter(s => {
        return !s.deleted || dates.some(dStr => ((records[dStr] || {})[s.code] || 0) > 0);
      });

      const datasets = relevantSubjects.map(s => {
        const data = dates.map(dStr => {
          const entry = records[dStr] || {};
          const min = Number(entry[s.code]) || 0;
          return Number((min / 60).toFixed(2));
        });
        return {
          label: s.name,
          data: data,
          backgroundColor: s.color,
          stack: 'study',
          borderWidth: 1,
          borderColor: '#FFFFFF'
        };
      });

      const totalsInMinutes = dates.map(dStr => {
        const entry = records[dStr] || {};
        let dayTotal = 0;
        relevantSubjects.forEach(s => {
          dayTotal += Number(entry[s.code]) || 0;
        });
        return dayTotal;
      });

      return { labels, datasets, totalsInMinutes };
    }
  }

  function renderStatsScreen() {
    const { labels, datasets, totalsInMinutes } = getStatsData(currentStatsPeriod);
    const ctx = document.getElementById('stats-canvas').getContext('2d');
    const noDataEl = document.getElementById('stats-no-data');

    const hasAnyRecord = totalsInMinutes.some(t => t > 0);
    noDataEl.style.display = hasAnyRecord ? 'none' : 'block';

    if (statsChart) statsChart.destroy();

    const topLabelPlugin = {
      id: 'topLabelPlugin',
      afterDatasetsDraw(chart) {
        const { ctx, scales: { x, y } } = chart;
        ctx.save();
        ctx.font = 'bold 11px NanumGothic, sans-serif';
        ctx.fillStyle = '#4A5568';
        ctx.textAlign = 'center';

        totalsInMinutes.forEach((min, idx) => {
          if (min <= 0) return;
          const xPos = x.getPixelForValue(idx);
          const totalHours = min / 60;
          const yPos = Math.max(10, y.getPixelForValue(totalHours) - 6);
          ctx.fillText(formatShort(min), xPos, yPos);
        });
        ctx.restore();
      }
    };

    statsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: datasets
      },
      plugins: [topLabelPlugin],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: { top: 20, right: 10, bottom: 5, left: 5 }
        },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: {
              font: { family: 'NanumGothic', size: labels.length > 15 ? 9 : 11 },
              maxRotation: labels.length > 10 ? 45 : 0
            }
          },
          y: {
            stacked: true,
            title: {
              display: true,
              text: '공부시간 (시간)',
              font: { family: 'NanumGothic', size: 12 }
            },
            beginAtZero: true,
            grid: { color: 'rgba(0, 0, 0, 0.06)' },
            ticks: {
              stepSize: 1,
              font: { family: 'NanumGothic' }
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'end',
            labels: {
              boxWidth: 12,
              font: { family: 'NanumGothic', size: 11 }
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const hours = context.raw;
                const min = Math.round(hours * 60);
                return ` ${context.dataset.label}: ${formatMinutes(min)}`;
              }
            }
          }
        }
      }
    });
  }

  // =========================================================================
  // 4. Settings Screen Logic (Subject Management & Manual Adjustment)
  // =========================================================================
  function renderSettingsScreen() {
    renderSubjectManagementList();
    initManualAdjustmentSection();
  }

  // 4.1 Subject Management List
  function renderSubjectManagementList() {
    const activeSubjects = getActiveSubjects();
    const listEl = document.getElementById('subject-manage-list');
    listEl.innerHTML = '';

    activeSubjects.forEach(s => {
      const item = document.createElement('div');
      item.className = 'subject-manage-item';
      item.innerHTML = `
        <div class="subject-manage-left">
          <span class="color-dot" style="background-color: ${s.color};"></span>
          <span style="font-weight: bold; font-size: 15px;">${s.name}</span>
          ${s.isDefault ? '<span style="font-size: 11px; color: var(--text-muted);">(기본)</span>' : ''}
        </div>
        <button class="btn-delete-subject" data-code="${s.code}">삭제</button>
      `;

      // Delete action with confirmation
      const delBtn = item.querySelector('.btn-delete-subject');
      delBtn.addEventListener('click', () => {
        if (activeSubjects.length <= 1) {
          alert('최소 1개 이상의 과목이 유지되어야 합니다.');
          return;
        }
        subjectToDeleteCode = s.code;
        const deleteModal = document.getElementById('delete-subject-modal');
        const modalText = document.getElementById('delete-subject-modal-text');
        modalText.innerHTML = `
          <strong>[${s.name}]</strong> 과목을 정말로 삭제하시겠습니까?<br><br>
          <span style="color: #2B6CB0; font-size: 13px;">
            ※ 안내: 과목을 삭제하더라도 <strong>과거에 기록된 공부 시간은 절대 삭제되지 않고</strong> 통계에 안전하게 보존됩니다.
          </span>
        `;
        deleteModal.classList.add('active');
      });

      listEl.appendChild(item);
    });
  }

  // 4.2 Add Subject Modal & Color Palette
  function openAddSubjectModal() {
    const modal = document.getElementById('add-subject-modal');
    const nameInput = document.getElementById('input-new-subject-name');
    nameInput.value = '';
    selectedNewSubjectColor = null;

    // Build palette chips with in-use validation
    const activeSubjects = getActiveSubjects();
    const activeColors = new Set(activeSubjects.map(s => s.color.toUpperCase()));

    const chipsContainer = document.getElementById('palette-chips-grid');
    chipsContainer.innerHTML = '';

    COLOR_PALETTE.forEach(c => {
      const hexUpper = c.hex.toUpperCase();
      const isUsed = activeColors.has(hexUpper);

      const isLightColor = c.name === '아이보리' || c.name === '노랑';
      const chip = document.createElement('div');
      chip.className = `palette-chip ${isLightColor ? 'ivory' : ''} ${isUsed ? 'disabled' : ''}`;
      chip.style.backgroundColor = c.hex;
      chip.textContent = isUsed ? `${c.name} (사용중)` : c.name;
      chip.setAttribute('data-hex', c.hex);

      if (!isUsed) {
        chip.addEventListener('click', () => {
          document.querySelectorAll('.palette-chip').forEach(el => el.classList.remove('selected'));
          chip.classList.add('selected');
          selectedNewSubjectColor = c.hex;
        });
      }

      chipsContainer.appendChild(chip);
    });

    modal.classList.add('active');
  }

  function confirmAddSubject() {
    const nameInput = document.getElementById('input-new-subject-name');
    const name = nameInput.value.trim();

    if (!name) {
      alert('과목 이름을 입력해주세요.');
      nameInput.focus();
      return;
    }

    if (!selectedNewSubjectColor) {
      alert('사용할 색상을 팔레트에서 선택해주세요.');
      return;
    }

    addNewSubject(name, selectedNewSubjectColor);
    document.getElementById('add-subject-modal').classList.remove('active');
    renderSubjectManagementList();
  }

  // 4.3 Manual Adjustment Section
  function initManualAdjustmentSection() {
    const today = new Date();
    const y = today.getFullYear();
    const m = today.getMonth() + 1;
    const d = today.getDate();

    const yInput = document.getElementById('manual-year');
    const mSelect = document.getElementById('manual-month');
    const dSelect = document.getElementById('manual-day');

    yInput.value = y;

    mSelect.innerHTML = '';
    for (let i = 1; i <= 12; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = `${i}월`;
      if (i === m) opt.selected = true;
      mSelect.appendChild(opt);
    }

    updateManualDayOptions(y, m, d);
    loadManualAdjustmentData();
  }

  function updateManualDayOptions(year, month, selectedDay) {
    const dSelect = document.getElementById('manual-day');
    dSelect.innerHTML = '';
    const daysInMonth = new Date(year, month, 0).getDate();
    for (let i = 1; i <= daysInMonth; i++) {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = `${i}일`;
      if (i === selectedDay) opt.selected = true;
      dSelect.appendChild(opt);
    }
  }

  function getManualSelectedDate() {
    const y = parseInt(document.getElementById('manual-year').value, 10);
    const m = parseInt(document.getElementById('manual-month').value, 10);
    const d = parseInt(document.getElementById('manual-day').value, 10);
    const mStr = String(m).padStart(2, '0');
    const dStr = String(d).padStart(2, '0');
    return `${y}-${mStr}-${dStr}`;
  }

  function loadManualAdjustmentData() {
    const dateStr = getManualSelectedDate();
    const dayData = getRecordForDate(dateStr);
    const allSubjects = getAllSubjects();
    const activeSubjects = getActiveSubjects();

    // Include active subjects, plus any deleted subject with saved minutes for this date
    const displaySubjects = [...activeSubjects];
    allSubjects.forEach(s => {
      if (s.deleted && (dayData[s.code] || 0) > 0 && !displaySubjects.some(item => item.code === s.code)) {
        displaySubjects.push(s);
      }
    });

    const gridEl = document.getElementById('manual-adjust-grid');
    gridEl.innerHTML = '';

    displaySubjects.forEach(s => {
      const totalMin = dayData[s.code] || 0;
      const h = Math.floor(totalMin / 60);
      const m = totalMin % 60;

      const row = document.createElement('div');
      row.className = 'manual-row';
      row.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="color: ${s.color};">■</span>
          <span style="font-weight: bold; font-size: 14px;">${s.name}${s.deleted ? ' (삭제됨)' : ''}</span>
        </div>
        <div class="manual-inputs">
          <input type="number" class="date-select manual-hour" data-code="${s.code}" value="${h}" min="0" max="23" style="width: 50px; text-align: center;">
          <span style="font-size: 13px;">시간</span>
          <input type="number" class="date-select manual-min" data-code="${s.code}" value="${m}" min="0" max="59" style="width: 50px; text-align: center;">
          <span style="font-size: 13px;">분</span>
        </div>
      `;
      gridEl.appendChild(row);
    });
  }

  function saveManualAdjustmentData() {
    const dateStr = getManualSelectedDate();
    const minutesDict = {};

    document.querySelectorAll('.manual-hour').forEach(hInput => {
      const code = hInput.getAttribute('data-code');
      const mInput = document.querySelector(`.manual-min[data-code="${code}"]`);
      const h = Math.max(0, Math.min(23, parseInt(hInput.value, 10) || 0));
      const m = Math.max(0, Math.min(59, parseInt(mInput.value, 10) || 0));
      minutesDict[code] = (h * 60) + m;
    });

    saveRecordForDate(dateStr, minutesDict);

    // If adjusting today's date, also sync stopwatch accumulated seconds
    const state = getStopwatchState();
    if (state.date === dateStr) {
      Object.entries(minutesDict).forEach(([code, min]) => {
        state.accumulatedSeconds[code] = min * 60;
      });
      saveStopwatchState(state);
    }

    alert(`[${dateStr}] 공부시간이 성공적으로 수정되었습니다!`);
  }

  // =========================================================================
  // 4.4 Data Backup: TXT Export & Import
  // =========================================================================
  async function exportRecordsToTxt() {
    const allSubjects = getAllSubjects();
    const allRecords = getRecords();

    let textOutput = '';
    textOutput += '==================================================\n';
    textOutput += '           StudyTimer 공부 기록 백업 파일          \n';
    textOutput += `  내보낸 일시: ${new Date().toLocaleString('ko-KR')}\n`;
    textOutput += '==================================================\n\n';

    textOutput += '[과목 목록]\n';
    allSubjects.forEach(s => {
      textOutput += `- ${s.name} (코드: ${s.code}, 색상: ${s.color})${s.deleted ? ' [삭제된 과목]' : ''}\n`;
    });
    textOutput += '\n';

    textOutput += '[날짜별 공부 시간 기록]\n';
    const sortedDates = Object.keys(allRecords).sort();
    if (sortedDates.length === 0) {
      textOutput += '(저장된 공부 기록이 없습니다)\n';
    } else {
      sortedDates.forEach(dateStr => {
        const dayData = allRecords[dateStr];
        const parts = [];
        Object.entries(dayData).forEach(([code, min]) => {
          if (min > 0) {
            const sub = allSubjects.find(s => s.code === code);
            const name = sub ? sub.name : code;
            parts.push(`${name}: ${min}분 (${formatMinutes(min)})`);
          }
        });
        textOutput += `${dateStr} => ${parts.length > 0 ? parts.join(', ') : '0분'}\n`;
      });
    }
    textOutput += '\n';

    // Automated JSON Payload block
    textOutput += '==================================================\n';
    textOutput += '# SYSTEM BACKUP DATA (자동 복원용 데이터 블록)\n';
    textOutput += '==================================================\n';
    const payload = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      subjects: allSubjects,
      records: allRecords
    };
    textOutput += '[DATA_JSON_START]\n';
    textOutput += JSON.stringify(payload, null, 2) + '\n';
    textOutput += '[DATA_JSON_END]\n';

    const filename = `StudyTimer_기록_${todayStr()}.txt`;

    // 1. Show modal preview with full text so user can always view and copy directly
    const modal = document.getElementById('export-modal');
    const previewEl = document.getElementById('export-text-preview');
    if (modal && previewEl) {
      previewEl.value = textOutput;
      modal.classList.add('active');
    }

    // 2. Try native Android Filesystem + Share Sheet via Capacitor plugins
    try {
      const Filesystem = window.Capacitor?.Plugins?.Filesystem;
      const Share = window.Capacitor?.Plugins?.Share;
      if (Filesystem && Share) {
        const writeResult = await Filesystem.writeFile({
          path: filename,
          data: textOutput,
          directory: 'CACHE',
          encoding: 'utf8'
        });

        if (writeResult && writeResult.uri) {
          await Share.share({
            title: 'StudyTimer 기록 내보내기',
            text: 'StudyTimer 공부 기록 백업 텍스트 파일입니다.',
            url: writeResult.uri,
            dialogTitle: '기록 백업 파일 저장 및 공유'
          });
        }
      }
    } catch (err) {
      console.warn('Native export error:', err);
    }

    // 3. Web download fallback for desktop browser
    try {
      const blob = new Blob([textOutput], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 300);
    } catch (e) {
      console.warn('Web blob download fallback error:', e);
    }
  }

  function parseFallbackTxt(content) {
    const records = {};
    const lines = content.split('\n');
    let currentDate = null;
    const allSubjects = getAllSubjects();

    lines.forEach(rawLine => {
      const line = rawLine.trim();
      if (!line || line.startsWith('#') || line.startsWith('=')) return;

      const dateMatch = line.match(/^(\d{4}-\d{2}-\d{2})/);
      if (dateMatch) {
        currentDate = dateMatch[1];
        if (!records[currentDate]) records[currentDate] = {};
        if (line.includes('=>')) {
          const after = line.split('=>')[1];
          after.split(',').forEach(item => {
            if (item.includes(':')) {
              const [namePart, minPart] = item.split(':');
              const cleanName = namePart.trim();
              const minMatch = minPart.match(/\d+/);
              if (minMatch) {
                const min = parseInt(minMatch[0], 10);
                const sub = allSubjects.find(s => s.name === cleanName || s.code === cleanName);
                const code = sub ? sub.code : cleanName;
                records[currentDate][code] = min;
              }
            }
          });
        }
      }
    });
    return { records };
  }

  function importRecordsFromTxt(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(evt) {
      try {
        const content = evt.target.result;
        let importedData = null;

        if (content.includes('[DATA_JSON_START]') && content.includes('[DATA_JSON_END]')) {
          const jsonPart = content.split('[DATA_JSON_START]')[1].split('[DATA_JSON_END]')[0].trim();
          importedData = JSON.parse(jsonPart);
        } else {
          try {
            importedData = JSON.parse(content);
          } catch (e) {
            importedData = parseFallbackTxt(content);
          }
        }

        if (!importedData || !importedData.records) {
          throw new Error('유효한 StudyTimer 기록 데이터가 없습니다.');
        }

        // 1. Merge subjects
        if (Array.isArray(importedData.subjects)) {
          const currentSubjects = getAllSubjects();
          importedData.subjects.forEach(newSub => {
            const exists = currentSubjects.find(s => s.code === newSub.code);
            if (!exists) {
              currentSubjects.push(newSub);
            }
          });
          saveAllSubjects(currentSubjects);
        }

        // 2. Overwrite records:
        // Rule: 동일한 날짜의 기록이 다르면 텍스트 파일의 기록으로 덮어씀
        const currentRecords = getRecords();
        let overwrittenCount = 0;
        let newCount = 0;

        Object.entries(importedData.records).forEach(([dateStr, record]) => {
          if (currentRecords[dateStr]) {
            overwrittenCount++;
          } else {
            newCount++;
          }
          currentRecords[dateStr] = { ...record };
        });

        saveRecords(currentRecords);

        // 3. Sync today's stopwatch state if today is updated
        const today = todayStr();
        if (importedData.records[today]) {
          const state = getStopwatchState();
          if (state.date === today) {
            state.accumulatedSeconds = {};
            Object.entries(importedData.records[today]).forEach(([code, min]) => {
              state.accumulatedSeconds[code] = (min || 0) * 60;
            });
            saveStopwatchState(state);
          }
        }

        alert(`기록 텍스트 파일을 성공적으로 불러왔습니다!\n- 신규 추가된 날짜: ${newCount}일\n- 텍스트 파일 기록으로 덮어쓴 날짜: ${overwrittenCount}일`);

        renderSettingsScreen();
        renderHomeScreen();

      } catch (err) {
        console.error(err);
        alert('파일을 불러오는 중 오류가 발생했습니다: ' + err.message);
      }
    };
    reader.readAsText(file, 'utf-8');
  }

  // =========================================================================
  // 5. Global Event Bindings & Initializer
  // =========================================================================
  function initEvents() {
    // 5.1 Nav Bar
    document.getElementById('nav-btn-home').addEventListener('click', () => showScreen('home'));
    document.getElementById('nav-btn-stats').addEventListener('click', () => showScreen('stats'));

    // 5.2 Home Buttons
    document.getElementById('btn-go-record').addEventListener('click', () => showScreen('record'));
    document.getElementById('btn-go-settings').addEventListener('click', () => showScreen('settings'));

    // 5.3 Stopwatch Screen Events
    const yInput = document.getElementById('stopwatch-year');
    const mSelect = document.getElementById('stopwatch-month');
    const dSelect = document.getElementById('stopwatch-day');

    const onStopwatchDateChange = () => {
      const y = parseInt(yInput.value, 10);
      const m = parseInt(mSelect.value, 10);
      const curD = parseInt(dSelect.value, 10);
      updateStopwatchDayOptions(y, m, curD);

      const newDate = getStopwatchSelectedDate();
      const state = initStopwatchFromSavedRecord(newDate);
      renderStopwatchCards(state);
    };

    yInput.addEventListener('change', onStopwatchDateChange);
    mSelect.addEventListener('change', onStopwatchDateChange);
    dSelect.addEventListener('change', onStopwatchDateChange);

    document.getElementById('btn-finish-study').addEventListener('click', finishStudySession);

    // 5.4 Stats Screen Filter Buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentStatsPeriod = e.target.getAttribute('data-period');
        renderStatsScreen();
      });
    });

    // 5.5 Settings Screen Events
    document.getElementById('btn-open-add-subject').addEventListener('click', openAddSubjectModal);
    document.getElementById('btn-confirm-add-subject').addEventListener('click', confirmAddSubject);
    document.getElementById('btn-cancel-add-subject').addEventListener('click', () => {
      document.getElementById('add-subject-modal').classList.remove('active');
    });

    // Confirm Delete Subject Modal
    document.getElementById('btn-confirm-delete-subject').addEventListener('click', () => {
      if (subjectToDeleteCode) {
        softDeleteSubject(subjectToDeleteCode);
        subjectToDeleteCode = null;
        document.getElementById('delete-subject-modal').classList.remove('active');
        renderSubjectManagementList();
      }
    });
    document.getElementById('btn-cancel-delete-subject').addEventListener('click', () => {
      subjectToDeleteCode = null;
      document.getElementById('delete-subject-modal').classList.remove('active');
    });

    // Manual Adjustment Date Events
    const manY = document.getElementById('manual-year');
    const manM = document.getElementById('manual-month');
    const manD = document.getElementById('manual-day');

    const onManualDateChange = () => {
      const y = parseInt(manY.value, 10);
      const m = parseInt(manM.value, 10);
      const curD = parseInt(manD.value, 10);
      updateManualDayOptions(y, m, curD);
      loadManualAdjustmentData();
    };

    manY.addEventListener('change', onManualDateChange);
    manM.addEventListener('change', onManualDateChange);
    manD.addEventListener('change', onManualDateChange);

    document.getElementById('btn-save-manual').addEventListener('click', saveManualAdjustmentData);

    // Backup & Restore Events
    document.getElementById('btn-export-records').addEventListener('click', exportRecordsToTxt);
    document.getElementById('btn-import-records').addEventListener('click', () => {
      document.getElementById('file-import-input').click();
    });
    document.getElementById('file-import-input').addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        importRecordsFromTxt(e.target.files[0]);
      }
      e.target.value = '';
    });

    // Reset All Records Modal
    const resetModal = document.getElementById('confirm-modal');
    document.getElementById('btn-open-reset-modal').addEventListener('click', () => {
      resetModal.classList.add('active');
    });
    document.getElementById('btn-modal-cancel').addEventListener('click', () => {
      resetModal.classList.remove('active');
    });
    document.getElementById('btn-modal-confirm').addEventListener('click', () => {
      clearAllRecords();
      resetModal.classList.remove('active');
      showScreen('home');
      alert('모든 공부 기록이 초기화되었습니다.');
    });

    // Export Modal Events
    const exportModal = document.getElementById('export-modal');
    const btnCopyExport = document.getElementById('btn-copy-export-text');
    const btnCloseExport = document.getElementById('btn-close-export-modal');

    if (btnCopyExport) {
      btnCopyExport.addEventListener('click', () => {
        const preview = document.getElementById('export-text-preview');
        if (preview && preview.value) {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(preview.value).then(() => {
              alert('백업 데이터가 클립보드에 복사되었습니다!');
            }).catch(() => {
              preview.select();
              document.execCommand('copy');
              alert('백업 데이터가 클립보드에 복사되었습니다!');
            });
          } else {
            preview.select();
            document.execCommand('copy');
            alert('백업 데이터가 클립보드에 복사되었습니다!');
          }
        }
      });
    }

    if (btnCloseExport) {
      btnCloseExport.addEventListener('click', () => {
        if (exportModal) exportModal.classList.remove('active');
      });
    }

    document.getElementById('btn-settings-back').addEventListener('click', () => showScreen('home'));
  }

  // --- Initial Boot ---
  document.addEventListener('DOMContentLoaded', () => {
    initEvents();
    showScreen('home');
  });

})();
