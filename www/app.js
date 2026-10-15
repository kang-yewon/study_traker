// Study Tracker Web / Capacitor App Logic

(function() {
  'use strict';

  // --- Constants & Default Data ---
  const DEFAULT_SUBJECTS = [
    { code: 'korean', name: '국어', color: '#4A90E2' },
    { code: 'english', name: '영어', color: '#2ECC71' },
    { code: 'math', name: '수학', color: '#F39C12' },
    { code: 'science', name: '과학', color: '#9B59B6' },
    { code: 'social', name: '사회', color: '#F1C40F' }
  ];

  const STORAGE_KEYS = {
    SUBJECTS: 'study_tracker_subjects_v1',
    RECORDS: 'study_tracker_records_v1'
  };

  // --- State ---
  let currentScreen = 'home';
  let currentStatsPeriod = 'week';
  let donutChart = null;
  let statsChart = null;

  // --- Helpers ---
  function getSubjects() {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.SUBJECTS);
      if (stored) return JSON.parse(stored);
    } catch (e) {
      console.error(e);
    }
    return DEFAULT_SUBJECTS;
  }

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

  function getRecordForDate(dateStr) {
    const records = getRecords();
    const entry = records[dateStr] || {};
    const subjects = getSubjects();
    const result = {};
    subjects.forEach(s => {
      result[s.code] = Number(entry[s.code]) || 0;
    });
    return result;
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
    const subjects = getSubjects();
    let total = 0;
    const perSubject = {};
    subjects.forEach(s => { perSubject[s.code] = 0; });

    Object.values(records).forEach(dayRecord => {
      subjects.forEach(s => {
        const val = Number(dayRecord[s.code]) || 0;
        perSubject[s.code] += val;
        total += val;
      });
    });
    return { total, perSubject };
  }

  function clearAllRecords() {
    localStorage.removeItem(STORAGE_KEYS.RECORDS);
  }

  // --- Screen Navigation ---
  function showScreen(name) {
    currentScreen = name;
    document.querySelectorAll('.screen').forEach(scr => scr.classList.remove('active'));
    const target = document.getElementById(`screen-${name}`);
    if (target) target.classList.add('active');

    // Update navbar active state
    const homeBtn = document.getElementById('nav-btn-home');
    const statsBtn = document.getElementById('nav-btn-stats');
    if (name === 'home' || name === 'record' || name === 'settings') {
      homeBtn.classList.add('active');
      statsBtn.classList.remove('active');
    } else if (name === 'stats') {
      homeBtn.classList.remove('active');
      statsBtn.classList.add('active');
    }

    if (name === 'home') renderHomeScreen();
    if (name === 'stats') renderStatsScreen();
    if (name === 'record') renderRecordScreen();
  }

  // --- Home Screen Logic ---
  function renderHomeScreen() {
    const today = todayStr();
    const todayData = getRecordForDate(today);
    const subjects = getSubjects();

    const todayTotal = Object.values(todayData).reduce((a, b) => a + b, 0);
    const { total: allTotal } = getAllTimeTotal();

    document.getElementById('home-today-total').textContent = formatMinutes(todayTotal);
    document.getElementById('home-all-total').textContent = formatMinutes(allTotal);
    document.getElementById('donut-center-text').textContent = formatMinutes(todayTotal);

    // Subject list rendering
    const listEl = document.getElementById('home-subject-list');
    listEl.innerHTML = '';
    subjects.forEach(s => {
      const row = document.createElement('div');
      row.className = 'subject-item';
      row.innerHTML = `
        <span class="subject-badge" style="color: ${s.color};">■</span>
        <span class="subject-name">${s.name}</span>
        <span class="subject-time">${formatMinutes(todayData[s.code] || 0)}</span>
      `;
      listEl.appendChild(row);
    });

    // Donut Chart
    renderDonutChart(todayData, subjects, todayTotal);
  }

  function renderDonutChart(todayData, subjects, total) {
    const ctx = document.getElementById('donut-canvas').getContext('2d');
    if (donutChart) donutChart.destroy();

    let chartData = [];
    let bgColors = [];

    if (total <= 0) {
      chartData = [1];
      bgColors = ['#E0E0E0'];
    } else {
      subjects.forEach(s => {
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

  // --- Record Screen Logic ---
  function renderRecordScreen() {
    const today = new Date();
    const yInput = document.getElementById('input-year');
    const mInput = document.getElementById('input-month');
    const dInput = document.getElementById('input-day');

    yInput.value = today.getFullYear();
    mInput.value = today.getMonth() + 1;
    dInput.value = today.getDate();
    document.getElementById('record-date-error').textContent = '';

    loadRecordFormData();
  }

  function getSelectedDateString() {
    const y = parseInt(document.getElementById('input-year').value, 10);
    const m = parseInt(document.getElementById('input-month').value, 10);
    const d = parseInt(document.getElementById('input-day').value, 10);

    if (isNaN(y) || isNaN(m) || isNaN(d) || m < 1 || m > 12 || d < 1 || d > 31) {
      return null;
    }
    const dateObj = new Date(y, m - 1, d);
    if (dateObj.getFullYear() !== y || dateObj.getMonth() + 1 !== m || dateObj.getDate() !== d) {
      return null;
    }
    const mStr = String(m).padStart(2, '0');
    const dStr = String(d).padStart(2, '0');
    return `${y}-${mStr}-${dStr}`;
  }

  function loadRecordFormData() {
    const dateStr = getSelectedDateString() || todayStr();
    const todayData = getRecordForDate(dateStr);
    const subjects = getSubjects();

    const formList = document.getElementById('record-form-list');
    formList.innerHTML = '';

    subjects.forEach(s => {
      const totalMin = todayData[s.code] || 0;
      const h = Math.floor(totalMin / 60);
      const m = totalMin % 60;

      const row = document.createElement('div');
      row.className = 'form-row';
      row.innerHTML = `
        <div class="form-subject-info">
          <span class="subject-badge" style="color: ${s.color};">■</span>
          <span>${s.name}</span>
        </div>
        <div class="form-input-box">
          <input type="number" class="time-input input-hours" data-code="${s.code}" value="${h}" min="0" max="23">
          <span class="unit-label">시간</span>
          <input type="number" class="time-input input-minutes" data-code="${s.code}" value="${m}" min="0" max="59">
          <span class="unit-label">분</span>
        </div>
      `;
      formList.appendChild(row);
    });
  }

  function saveRecordFormData() {
    const dateStr = getSelectedDateString();
    const errEl = document.getElementById('record-date-error');
    if (!dateStr) {
      errEl.textContent = '날짜를 올바르게 입력해주세요. (예: 2026 / 2 / 3)';
      return;
    }
    errEl.textContent = '';

    const minutesDict = {};
    const hourInputs = document.querySelectorAll('.input-hours');
    const minInputs = document.querySelectorAll('.input-minutes');

    hourInputs.forEach(hInput => {
      const code = hInput.getAttribute('data-code');
      const mInput = document.querySelector(`.input-minutes[data-code="${code}"]`);
      const h = Math.max(0, Math.min(23, parseInt(hInput.value, 10) || 0));
      const m = Math.max(0, Math.min(59, parseInt(mInput.value, 10) || 0));
      minutesDict[code] = (h * 60) + m;
    });

    saveRecordForDate(dateStr, minutesDict);
    showScreen('home');
  }

  // --- Stats Screen Logic ---
  function getStatsData(period) {
    const subjects = getSubjects();
    const records = getRecords();

    if (period === 'year') {
      // Last 12 months average daily minutes
      const monthlyGroups = {};
      const now = new Date();
      for (let i = 11; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const key = `${y}-${m}`;
        monthlyGroups[key] = { count: 0, sums: {} };
        subjects.forEach(s => { monthlyGroups[key].sums[s.code] = 0; });
      }

      Object.entries(records).forEach(([dateStr, record]) => {
        const monthKey = dateStr.slice(0, 7);
        if (monthlyGroups[monthKey]) {
          monthlyGroups[monthKey].count += 1;
          subjects.forEach(s => {
            monthlyGroups[monthKey].sums[s.code] += (Number(record[s.code]) || 0);
          });
        }
      });

      const labels = Object.keys(monthlyGroups);
      const datasets = subjects.map(s => {
        const data = labels.map(mKey => {
          const group = monthlyGroups[mKey];
          // Average daily minutes in that month
          const avg = group.count > 0 ? Math.round(group.sums[s.code] / group.count) : 0;
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
        subjects.forEach(s => { total += group.sums[s.code]; });
        return Math.round(total / group.count);
      });

      return { labels, datasets, totalsInMinutes };

    } else {
      // Daily breakdown: week (7 days) or month (30 days)
      const daysCount = period === 'week' ? 7 : 30;
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

      const datasets = subjects.map(s => {
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
        subjects.forEach(s => {
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

    // Custom plugin to draw top total labels
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

  // --- Event Bindings ---
  function initEvents() {
    // Nav bar
    document.getElementById('nav-btn-home').addEventListener('click', () => showScreen('home'));
    document.getElementById('nav-btn-stats').addEventListener('click', () => showScreen('stats'));

    // Home buttons
    document.getElementById('btn-go-record').addEventListener('click', () => showScreen('record'));
    document.getElementById('btn-go-settings').addEventListener('click', () => showScreen('settings'));

    // Record buttons & date change
    ['input-year', 'input-month', 'input-day'].forEach(id => {
      document.getElementById(id).addEventListener('change', loadRecordFormData);
    });
    document.getElementById('btn-save-record').addEventListener('click', saveRecordFormData);
    document.getElementById('btn-cancel-record').addEventListener('click', () => showScreen('home'));

    // Stats period filter
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentStatsPeriod = e.target.getAttribute('data-period');
        renderStatsScreen();
      });
    });

    // Settings
    const modal = document.getElementById('confirm-modal');
    document.getElementById('btn-open-reset-modal').addEventListener('click', () => {
      modal.classList.add('active');
    });
    document.getElementById('btn-modal-cancel').addEventListener('click', () => {
      modal.classList.remove('active');
    });
    document.getElementById('btn-modal-confirm').addEventListener('click', () => {
      clearAllRecords();
      modal.classList.remove('active');
      showScreen('home');
    });
    document.getElementById('btn-settings-back').addEventListener('click', () => showScreen('home'));
  }

  // --- Initial Boot ---
  document.addEventListener('DOMContentLoaded', () => {
    initEvents();
    showScreen('home');
  });

})();
