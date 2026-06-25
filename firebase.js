// ================================================
// FILTORA — Firebase Integration
// ================================================
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import { getDatabase, ref, onValue, query, limitToLast, orderByKey, get } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js';

const firebaseConfig = {
  apiKey:            "AIzaSyDpSQbX9mj3iJzhkOqjb_B7oHaIl81Nzak",
  authDomain:        "filtora-data.firebaseapp.com",
  databaseURL:       "https://filtora-data-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId:         "filtora-data",
  storageBucket:     "filtora-data.firebasestorage.app",
  messagingSenderId: "881327176817",
  appId:             "1:881327176817:web:553eda9e9da0569aa52fd0",
  measurementId:     "G-JMHFS671V1"
};

const app      = initializeApp(firebaseConfig);
const database = getDatabase(app);

// ---- State ----
let latestSensorData  = null;
let latestPrediction  = null;
let sensorDataHistory = [];
const MAX_HISTORY     = 20;

// ================================================
// HELPERS
// ================================================

function formatTimestamp(ts) {
  if (!ts) return 'Tidak tersedia';
  // Key format: 2025-10-15T18-31-30_597593
  const cleaned = ts.replace('T', ' ').replace(/_.*/, '');
  const parts   = cleaned.split(' ');
  if (parts.length === 2) {
    const [date, time] = parts;
    const [y, m, d]    = date.split('-');
    const [H, M, S]    = time.split('-');
    return `${d}/${m}/${y} ${H}:${M}:${S}`;
  }
  return ts;
}

function el(id) { return document.getElementById(id); }

// ================================================
// UI UPDATERS
// ================================================

function setConnectionStatus(connected) {
  const dot  = el('statusDot');
  const text = el('statusText');
  if (!dot || !text) return;

  if (connected) {
    dot.className  = 'dot on';
    text.textContent = 'TERHUBUNG';
  } else {
    dot.className  = 'dot off';
    text.textContent = 'MENGHUBUNGKAN...';
  }
}

function setLastUpdate(ts) {
  const e = el('lastUpdate');
  if (e) e.innerHTML = `<i class="bi bi-clock"></i>&nbsp;Diperbarui: ${formatTimestamp(ts)}`;
}

function setQualityBanner(label, cluster, code) {
  const indicator = el('qualityIndicator');
  const labelEl   = el('qualityLabel');
  const subtextEl = el('qualitySubtext');
  const clusterEl = el('statCluster');
  const codeEl    = el('statCode');

  if (labelEl)   labelEl.textContent   = (label || 'TIDAK DIKETAHUI').toUpperCase();
  if (clusterEl) clusterEl.textContent = cluster !== undefined ? cluster : '—';
  if (codeEl)    codeEl.textContent    = code    !== undefined ? code    : '—';

  const subtexts = {
    'Baik':   'Kualitas udara sangat baik — aman untuk beraktivitas di luar ruangan',
    'Sedang': 'Kualitas udara cukup baik — pantau kondisi secara berkala',
    'Buruk':  'Kualitas udara buruk — aktifkan purifier, batasi aktivitas luar ruangan'
  };
  if (subtextEl) subtextEl.textContent = subtexts[label] || 'Menunggu data dari sensor...';

  if (indicator) {
    indicator.className = 'quality-left';
    if      (label === 'Baik')   indicator.classList.add('q-baik');
    else if (label === 'Buruk')  indicator.classList.add('q-buruk');
    else                          indicator.classList.add('q-sedang');
  }
}

function setSensorValues(data) {
  if (!data) return;
  const map = {
    sensorMQ135: data.mq135,
    sensorMQ2:   data.mq2,
    sensorMQ5:   data.mq5,
    sensorPM25:  data.pm25,
    sensorPM10:  data.pm10,
    sensorTemp:  data.temperature,
    sensorHumid: data.humidity
  };
  for (const [id, val] of Object.entries(map)) {
    const e = el(id);
    if (e && val !== undefined && val !== null) {
      e.textContent = parseFloat(val).toFixed(1);
    }
  }
}

function setMLResult(label, cluster, code, timestamp) {
  const labelEl   = el('mlLabel');
  const clusterEl = el('mlCluster');
  const codeEl    = el('mlCode');
  const tsEl      = el('mlTs');

  if (labelEl)   labelEl.textContent   = label   || '—';
  if (clusterEl) clusterEl.textContent = cluster !== undefined ? cluster : '—';
  if (codeEl)    codeEl.textContent    = code    !== undefined ? code    : '—';
  if (tsEl && timestamp) {
    tsEl.textContent = `Prediksi terakhir: ${formatTimestamp(timestamp)}`;
  }
}

// ================================================
// HISTORY
// ================================================

function pushHistory(timestamp, data) {
  sensorDataHistory.push({
    timestamp,
    time:        (formatTimestamp(timestamp).split(' ')[1] || ''),
    mq135:       data.mq135,
    mq2:         data.mq2,
    mq5:         data.mq5,
    pm25:        data.pm25,
    pm10:        data.pm10,
    temperature: data.temperature,
    humidity:    data.humidity
  });
  if (sensorDataHistory.length > MAX_HISTORY) sensorDataHistory.shift();
  window.dispatchEvent(new CustomEvent('dataUpdated', { detail: sensorDataHistory }));
}

// ================================================
// FIREBASE LISTENERS
// ================================================

function listenSensorData() {
  const q = query(ref(database, 'sensor_data'), orderByKey(), limitToLast(MAX_HISTORY));

  onValue(q, (snap) => {
    setConnectionStatus(true);
    if (!snap.exists()) return;

    const entries = Object.entries(snap.val()).sort((a, b) => a[0].localeCompare(b[0]));

    // Rebuild history
    sensorDataHistory = [];
    entries.forEach(([ts, data]) => pushHistory(ts, data));

    // Latest entry → update UI
    const [lastTs, lastData] = entries[entries.length - 1];
    latestSensorData = lastData;
    setSensorValues(lastData);
    setLastUpdate(lastTs);

    console.log('✅ Sensor data updated:', lastTs);
  }, (err) => {
    console.error('❌ Sensor data error:', err);
    setConnectionStatus(false);
  });
}

function listenPredictions() {
  // Prioritas 1: /latest_prediction (ditulis oleh filtora_ml_clustering.py)
  // Ini selalu berisi prediksi terbaru, langsung tanpa sort masalah.
  onValue(ref(database, 'latest_prediction'), (snap) => {
    if (!snap.exists()) {
      // Fallback ke /predictions jika /latest_prediction belum ada
      listenPredictionsLegacy();
      return;
    }

    const pred       = snap.val();
    latestPrediction = pred;

    setQualityBanner(pred.quality_label, pred.cluster, pred.quality_code);
    setMLResult(pred.quality_label, pred.cluster, pred.quality_code, pred.predicted_at);

    console.log('✅ Latest prediction:', pred.quality_label, '@', pred.predicted_at);
  }, (err) => {
    console.error('❌ latest_prediction error:', err);
  });
}

function listenPredictionsLegacy() {
  // Fallback: baca /predictions (data lama, diurutkan by key)
  const q = query(ref(database, 'predictions'), orderByKey(), limitToLast(1));
  onValue(q, (snap) => {
    if (!snap.exists()) return;
    const entries = Object.entries(snap.val());
    if (!entries.length) return;

    const [ts, pred] = entries[0];
    latestPrediction = pred;

    setQualityBanner(pred.quality_label, pred.cluster, pred.quality_code);
    setMLResult(pred.quality_label, pred.cluster, pred.quality_code, ts);
    console.log('✅ Prediction (legacy):', pred.quality_label);
  }, (err) => {
    console.error('❌ Prediction legacy error:', err);
  });
}

// ================================================
// ML REFRESH (triggered by button via custom event)
// ================================================

window.addEventListener('mlRefreshRequested', async () => {
  const tsEl = document.getElementById('mlTs');
  try {
    // Coba /latest_prediction dulu (hasil dari filtora_ml_clustering.py terbaru)
    const latestSnap = await get(ref(database, 'latest_prediction'));

    if (latestSnap.exists()) {
      const pred       = latestSnap.val();
      latestPrediction = pred;
      setQualityBanner(pred.quality_label, pred.cluster, pred.quality_code);
      setMLResult(pred.quality_label, pred.cluster, pred.quality_code, pred.predicted_at);
      if (tsEl) tsEl.textContent = `Diperbarui: ${new Date(pred.predicted_at).toLocaleString('id-ID')}`;
      console.log('🔄 ML refresh (latest_prediction):', pred.quality_label);
      return;
    }

    // Fallback ke /predictions jika /latest_prediction belum ada
    const q    = query(ref(database, 'predictions'), orderByKey(), limitToLast(1));
    const snap = await get(q);
    if (snap.exists()) {
      const entries = Object.entries(snap.val());
      if (entries.length) {
        const [ts, pred] = entries[0];
        latestPrediction = pred;
        setQualityBanner(pred.quality_label, pred.cluster, pred.quality_code);
        setMLResult(pred.quality_label, pred.cluster, pred.quality_code, ts);
        if (tsEl) tsEl.textContent = `Diperbarui: ${formatTimestamp(ts)}`;
        console.log('🔄 ML refresh (legacy):', pred.quality_label);
      }
    } else {
      if (tsEl) tsEl.textContent = 'Belum ada prediksi. Jalankan filtora_ml_clustering.py terlebih dahulu.';
    }
  } catch (err) {
    console.error('❌ ML refresh error:', err);
    if (tsEl) tsEl.textContent = 'Gagal memuat prediksi. Cek koneksi Firebase.';
  }
});

// ================================================
// INIT
// ================================================

function init() {
  console.log('🚀 FILTORA Dashboard — initializing...');
  setConnectionStatus(false);
  listenSensorData();
  listenPredictions();
  console.log('✅ Firebase listeners active');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

export { sensorDataHistory, latestSensorData, latestPrediction };
