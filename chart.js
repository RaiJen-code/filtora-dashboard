// ================================================
// FILTORA — Chart Configuration (Neo Brutalism)
// ================================================
import { sensorDataHistory } from './firebase.js';

let pmChart  = null;
let gasChart = null;
let envChart = null;

// ---- Palette (matches CSS variables) ----
const C = {
  purple: { line: '#8B2BE2', fill: 'rgba(139,43,226,.12)' },
  green:  { line: '#00C060', fill: 'rgba(0,192,96,.12)'   },
  blue:   { line: '#1655F5', fill: 'rgba(22,85,245,.12)'  },
  orange: { line: '#FF7300', fill: 'rgba(255,115,0,.12)'  },
  red:    { line: '#FF3030', fill: 'rgba(255,48,48,.12)'  },
  heat:   { line: '#FF3030', fill: 'rgba(255,48,48,.1)'   },
  cyan:   { line: '#00C9E8', fill: 'rgba(0,201,232,.1)'   }
};

// ---- Shared chart defaults ----
const DEFAULTS = {
  responsive: true,
  maintainAspectRatio: true,
  interaction: { intersect: false, mode: 'index' },
  animation: { duration: 300 },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        usePointStyle: true,
        pointStyle: 'rectRot',
        padding: 16,
        font: { size: 11, weight: '700', family: "'Space Grotesk', sans-serif" },
        color: '#1A1A1A'
      }
    },
    tooltip: {
      backgroundColor: '#1A1A1A',
      titleColor: '#FFE500',
      bodyColor: '#FFFFFF',
      borderColor: '#1A1A1A',
      borderWidth: 2,
      padding: 12,
      titleFont: { size: 11, weight: '800', family: "'Space Grotesk', sans-serif" },
      bodyFont:  { size: 12, weight: '600', family: "'Space Grotesk', sans-serif" },
      callbacks: {
        label: (ctx) => `  ${ctx.dataset.label}: ${ctx.parsed.y !== null ? ctx.parsed.y.toFixed(1) : '—'}`
      }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(26,26,26,.08)', lineWidth: 1 },
      border: { color: '#1A1A1A', width: 2 },
      ticks: {
        font: { size: 10, weight: '700', family: "'Space Grotesk', sans-serif" },
        color: '#666',
        maxRotation: 45, minRotation: 45
      }
    },
    y: {
      beginAtZero: true,
      grid: { color: 'rgba(26,26,26,.08)', lineWidth: 1 },
      border: { color: '#1A1A1A', width: 2 },
      ticks: {
        font: { size: 10, weight: '700', family: "'Space Grotesk', sans-serif" },
        color: '#666'
      }
    }
  }
};

function dataset(label, color, data = []) {
  return {
    label,
    data,
    borderColor:     color.line,
    backgroundColor: color.fill,
    borderWidth: 2.5,
    tension: 0.35,
    fill: true,
    pointRadius: 4,
    pointBorderWidth: 2,
    pointBorderColor: color.line,
    pointBackgroundColor: '#fff',
    pointHoverRadius: 6,
    pointHoverBorderWidth: 2.5
  };
}

// ================================================
// INIT CHARTS
// ================================================

function initPMChart() {
  const ctx = document.getElementById('pmChart');
  if (!ctx) return;
  pmChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        dataset('PM2.5 (µg/m³)', C.purple),
        dataset('PM10 (µg/m³)',  C.green)
      ]
    },
    options: JSON.parse(JSON.stringify(DEFAULTS))
  });
}

function initGasChart() {
  const ctx = document.getElementById('gasChart');
  if (!ctx) return;
  gasChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        dataset('MQ135 (ppm)', C.blue),
        dataset('MQ2 (ppm)',   C.orange),
        dataset('MQ5 (ppm)',   C.red)
      ]
    },
    options: JSON.parse(JSON.stringify(DEFAULTS))
  });
}

function initEnvChart() {
  const ctx = document.getElementById('envChart');
  if (!ctx) return;

  // Deep clone DEFAULTS and add dual Y-axis
  const opts = JSON.parse(JSON.stringify(DEFAULTS));
  opts.scales.y.title = {
    display: true,
    text: 'Suhu (°C)',
    font: { size: 10, weight: '800', family: "'Space Grotesk', sans-serif" },
    color: '#666'
  };
  opts.scales.y1 = {
    type: 'linear',
    display: true,
    position: 'right',
    beginAtZero: false,
    grid: { drawOnChartArea: false },
    border: { color: '#1A1A1A', width: 2 },
    title: {
      display: true,
      text: 'Kelembapan (%)',
      font: { size: 10, weight: '800', family: "'Space Grotesk', sans-serif" },
      color: '#666'
    },
    ticks: {
      font: { size: 10, weight: '700', family: "'Space Grotesk', sans-serif" },
      color: '#666'
    }
  };

  envChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { ...dataset('Suhu (°C)',        C.heat), yAxisID: 'y'  },
        { ...dataset('Kelembapan (%)',   C.cyan), yAxisID: 'y1' }
      ]
    },
    options: opts
  });
}

// ================================================
// UPDATE CHARTS
// ================================================

function updateCharts(history) {
  if (!history || !history.length) return;
  const labels = history.map(d => d.time);

  if (pmChart) {
    pmChart.data.labels          = labels;
    pmChart.data.datasets[0].data = history.map(d => d.pm25);
    pmChart.data.datasets[1].data = history.map(d => d.pm10);
    pmChart.update('none');
  }

  if (gasChart) {
    gasChart.data.labels          = labels;
    gasChart.data.datasets[0].data = history.map(d => d.mq135);
    gasChart.data.datasets[1].data = history.map(d => d.mq2);
    gasChart.data.datasets[2].data = history.map(d => d.mq5);
    gasChart.update('none');
  }

  if (envChart) {
    envChart.data.labels          = labels;
    envChart.data.datasets[0].data = history.map(d => d.temperature);
    envChart.data.datasets[1].data = history.map(d => d.humidity);
    envChart.update('none');
  }

  console.log(`📊 Charts updated — ${history.length} data points`);
}

// ================================================
// EVENT LISTENER
// ================================================

window.addEventListener('dataUpdated', (e) => updateCharts(e.detail));

// ================================================
// INIT
// ================================================

function init() {
  console.log('📊 Initializing FILTORA charts...');
  initPMChart();
  initGasChart();
  initEnvChart();
  console.log('✅ Charts ready');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
