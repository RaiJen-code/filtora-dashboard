// ========================================
// CHART CONFIGURATION & INITIALIZATION
// ========================================

import { sensorDataHistory } from './firebase.js';

// Chart instances
let pmChart = null;
let gasChart = null;
let envChart = null;

// Chart colors
const chartColors = {
    pm25: {
        border: 'rgb(156, 39, 176)',
        background: 'rgba(156, 39, 176, 0.1)'
    },
    pm10: {
        border: 'rgb(76, 175, 80)',
        background: 'rgba(76, 175, 80, 0.1)'
    },
    mq135: {
        border: 'rgb(33, 150, 243)',
        background: 'rgba(33, 150, 243, 0.1)'
    },
    mq2: {
        border: 'rgb(255, 152, 0)',
        background: 'rgba(255, 152, 0, 0.1)'
    },
    mq5: {
        border: 'rgb(233, 30, 99)',
        background: 'rgba(233, 30, 99, 0.1)'
    },
    temperature: {
        border: 'rgb(244, 67, 54)',
        background: 'rgba(244, 67, 54, 0.1)'
    },
    humidity: {
        border: 'rgb(0, 188, 212)',
        background: 'rgba(0, 188, 212, 0.1)'
    }
};

// ========================================
// CHART INITIALIZATION
// ========================================

/**
 * Initialize PM Chart (PM2.5 & PM10)
 */
function initPMChart() {
    const ctx = document.getElementById('pmChart');
    if (!ctx) return;
    
    pmChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'PM2.5 (µg/m³)',
                    data: [],
                    borderColor: chartColors.pm25.border,
                    backgroundColor: chartColors.pm25.background,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'PM10 (µg/m³)',
                    data: [],
                    borderColor: chartColors.pm10.border,
                    backgroundColor: chartColors.pm10.background,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: 11
                        },
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

/**
 * Initialize Gas Sensors Chart (MQ135, MQ2, MQ5)
 */
function initGasChart() {
    const ctx = document.getElementById('gasChart');
    if (!ctx) return;
    
    gasChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'MQ135 (ppm)',
                    data: [],
                    borderColor: chartColors.mq135.border,
                    backgroundColor: chartColors.mq135.background,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'MQ2 (ppm)',
                    data: [],
                    borderColor: chartColors.mq2.border,
                    backgroundColor: chartColors.mq2.background,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'MQ5 (ppm)',
                    data: [],
                    borderColor: chartColors.mq5.border,
                    backgroundColor: chartColors.mq5.background,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: 11
                        },
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

/**
 * Initialize Environment Chart (Temperature & Humidity)
 */
function initEnvChart() {
    const ctx = document.getElementById('envChart');
    if (!ctx) return;
    
    envChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Suhu (°C)',
                    data: [],
                    borderColor: chartColors.temperature.border,
                    backgroundColor: chartColors.temperature.background,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'Kelembapan (%)',
                    data: [],
                    borderColor: chartColors.humidity.border,
                    backgroundColor: chartColors.humidity.background,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1);
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Suhu (°C)',
                        font: {
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Kelembapan (%)',
                        font: {
                            weight: 'bold'
                        }
                    },
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            size: 11
                        },
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// ========================================
// CHART UPDATE FUNCTIONS
// ========================================

/**
 * Update all charts with new data
 */
function updateCharts(historyData) {
    if (!historyData || historyData.length === 0) return;
    
    // Extract labels and data
    const labels = historyData.map(d => d.time);
    
    // Update PM Chart
    if (pmChart) {
        pmChart.data.labels = labels;
        pmChart.data.datasets[0].data = historyData.map(d => d.pm25);
        pmChart.data.datasets[1].data = historyData.map(d => d.pm10);
        pmChart.update('none'); // Update without animation for smoother experience
    }
    
    // Update Gas Chart
    if (gasChart) {
        gasChart.data.labels = labels;
        gasChart.data.datasets[0].data = historyData.map(d => d.mq135);
        gasChart.data.datasets[1].data = historyData.map(d => d.mq2);
        gasChart.data.datasets[2].data = historyData.map(d => d.mq5);
        gasChart.update('none');
    }
    
    // Update Environment Chart
    if (envChart) {
        envChart.data.labels = labels;
        envChart.data.datasets[0].data = historyData.map(d => d.temperature);
        envChart.data.datasets[1].data = historyData.map(d => d.humidity);
        envChart.update('none');
    }
}

// ========================================
// EVENT LISTENERS
// ========================================

/**
 * Listen for data updates from firebase.js
 */
window.addEventListener('dataUpdated', (event) => {
    const historyData = event.detail;
    updateCharts(historyData);
    console.log('📊 Charts updated with', historyData.length, 'data points');
});

// ========================================
// INITIALIZATION
// ========================================

/**
 * Initialize all charts
 */
function initCharts() {
    console.log('📊 Initializing charts...');
    
    // Initialize all three charts
    initPMChart();
    initGasChart();
    initEnvChart();
    
    console.log('✅ Charts initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCharts);
} else {
    initCharts();
}