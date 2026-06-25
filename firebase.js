// ========================================
// FIREBASE CONFIGURATION
// ========================================
// Import Firebase modules
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import { getDatabase, ref, onValue, query, limitToLast, orderByKey } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js';

// Firebase configuration
// GANTI DENGAN KONFIGURASI FIREBASE ANDA!
const firebaseConfig = {
  apiKey: "AIzaSyDpSQbX9mj3iJzhkOqjb_B7oHaIl81Nzak",
  authDomain: "filtora-data.firebaseapp.com",
  databaseURL: "https://filtora-data-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "filtora-data",
  storageBucket: "filtora-data.firebasestorage.app",
  messagingSenderId: "881327176817",
  appId: "1:881327176817:web:553eda9e9da0569aa52fd0",
  measurementId: "G-JMHFS671V1"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

// ========================================
// GLOBAL VARIABLES
// ========================================
let latestSensorData = null;
let latestPrediction = null;
let sensorDataHistory = [];
let maxHistoryPoints = 20; // Jumlah data point untuk grafik

// ========================================
// UTILITY FUNCTIONS
// ========================================

/**
 * Format timestamp untuk ditampilkan
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Tidak tersedia';
    
    // Convert Firebase key format back to readable format
    // 2025-10-15T18-31-30_597593 -> 2025-10-15 18:31:30
    const cleaned = timestamp.replace('T', ' ').replace(/_.*/, '').replace(/-/g, ':');
    const parts = cleaned.split(' ');
    
    if (parts.length === 2) {
        const [date, time] = parts;
        const [year, month, day] = date.split(':');
        const [hour, minute, second] = time.split(':');
        
        return `${day}/${month}/${year} ${hour}:${minute}:${second}`;
    }
    
    return timestamp;
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(connected) {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    
    if (connected) {
        statusDot.className = 'status-dot status-connected';
        statusText.textContent = 'Terhubung';
    } else {
        statusDot.className = 'status-dot status-connecting';
        statusText.textContent = 'Menghubungkan...';
    }
}

/**
 * Update quality indicator
 */
function updateQualityIndicator(label, cluster, code) {
    const indicator = document.getElementById('qualityIndicator');
    const labelElement = document.getElementById('qualityLabel');
    const subtextElement = document.getElementById('qualitySubtext');
    const statCluster = document.getElementById('statCluster');
    const statCode = document.getElementById('statCode');
    
    // Update label
    labelElement.textContent = label || 'Tidak Diketahui';
    
    // Update subtext
    const subtexts = {
        'Baik': 'Kualitas udara sangat baik',
        'Sedang': 'Kualitas udara cukup baik',
        'Buruk': 'Kualitas udara buruk'
    };
    subtextElement.textContent = subtexts[label] || 'Menunggu data...';
    
    // Update class for color
    indicator.className = 'quality-indicator';
    if (label === 'Baik') {
        indicator.classList.add('quality-baik');
    } else if (label === 'Sedang') {
        indicator.classList.add('quality-sedang');
    } else if (label === 'Buruk') {
        indicator.classList.add('quality-buruk');
    } else {
        indicator.classList.add('quality-sedang');
    }
    
    // Update stats
    statCluster.textContent = cluster !== undefined ? cluster : '-';
    statCode.textContent = code !== undefined ? code : '-';
}

/**
 * Update sensor display
 */
function updateSensorDisplay(data) {
    if (!data) return;
    
    // Update each sensor value
    const sensors = {
        'sensorMQ135': data.mq135,
        'sensorMQ2': data.mq2,
        'sensorMQ5': data.mq5,
        'sensorPM25': data.pm25,
        'sensorPM10': data.pm10,
        'sensorTemp': data.temperature,
        'sensorHumid': data.humidity
    };
    
    for (const [id, value] of Object.entries(sensors)) {
        const element = document.getElementById(id);
        if (element && value !== undefined) {
            element.innerHTML = `${parseFloat(value).toFixed(1)}<span class="sensor-unit">${element.querySelector('.sensor-unit').textContent}</span>`;
        }
    }
}

/**
 * Update last update time
 */
function updateLastUpdateTime(timestamp) {
    const element = document.getElementById('lastUpdate');
    if (element) {
        element.innerHTML = `<i class="bi bi-clock"></i> Diperbarui: ${formatTimestamp(timestamp)}`;
    }
}

/**
 * Add data to history for charts
 */
function addToHistory(timestamp, data) {
    // Create data point
    const dataPoint = {
        timestamp: timestamp,
        time: formatTimestamp(timestamp).split(' ')[1] || '', // Get time part only
        mq135: data.mq135,
        mq2: data.mq2,
        mq5: data.mq5,
        pm25: data.pm25,
        pm10: data.pm10,
        temperature: data.temperature,
        humidity: data.humidity
    };
    
    // Add to history
    sensorDataHistory.push(dataPoint);
    
    // Limit history size
    if (sensorDataHistory.length > maxHistoryPoints) {
        sensorDataHistory.shift(); // Remove oldest
    }
    
    // Trigger chart update event
    window.dispatchEvent(new CustomEvent('dataUpdated', { detail: sensorDataHistory }));
}

// ========================================
// FIREBASE LISTENERS
// ========================================

/**
 * Listen to sensor data changes
 */
function listenToSensorData() {
    // Get reference to sensor_data, ordered by key, last 20 items
    const sensorRef = query(
        ref(database, 'sensor_data'),
        orderByKey(),
        limitToLast(20)
    );
    
    onValue(sensorRef, (snapshot) => {
        updateConnectionStatus(true);
        
        if (snapshot.exists()) {
            const data = snapshot.val();
            
            // Clear history untuk rebuild dengan data terbaru
            sensorDataHistory = [];
            
            // Get all entries and sort by timestamp
            const entries = Object.entries(data).sort((a, b) => {
                return a[0].localeCompare(b[0]); // Sort by key (timestamp)
            });
            
            // Process all entries
            entries.forEach(([timestamp, sensorData]) => {
                addToHistory(timestamp, sensorData);
            });
            
            // Get latest data
            const latestEntry = entries[entries.length - 1];
            if (latestEntry) {
                const [timestamp, sensorData] = latestEntry;
                latestSensorData = sensorData;
                
                // Update display
                updateSensorDisplay(sensorData);
                updateLastUpdateTime(timestamp);
                
                console.log('✅ Sensor data updated:', timestamp);
            }
        } else {
            console.log('⚠️ No sensor data available');
        }
    }, (error) => {
        console.error('❌ Error reading sensor data:', error);
        updateConnectionStatus(false);
    });
}

/**
 * Listen to prediction changes
 */
function listenToPredictions() {
    // Get reference to predictions, last item
    const predictionRef = query(
        ref(database, 'predictions'),
        orderByKey(),
        limitToLast(1)
    );
    
    onValue(predictionRef, (snapshot) => {
        if (snapshot.exists()) {
            const data = snapshot.val();
            
            // Get latest prediction
            const entries = Object.entries(data);
            if (entries.length > 0) {
                const [timestamp, prediction] = entries[0];
                latestPrediction = prediction;
                
                // Update quality indicator
                updateQualityIndicator(
                    prediction.quality_label,
                    prediction.cluster,
                    prediction.quality_code
                );
                
                console.log('✅ Prediction updated:', prediction.quality_label);
            }
        } else {
            console.log('⚠️ No prediction data available');
        }
    }, (error) => {
        console.error('❌ Error reading predictions:', error);
    });
}

// ========================================
// INITIALIZATION
// ========================================

/**
 * Initialize dashboard
 */
function initDashboard() {
    console.log('🚀 Initializing FILTORA Dashboard...');
    
    // Start listening to Firebase
    listenToSensorData();
    listenToPredictions();
    
    // Initial connection status
    updateConnectionStatus(false);
    
    console.log('✅ Dashboard initialized');
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

// Export for use in other modules
export { sensorDataHistory, latestSensorData, latestPrediction };