"""
FILTORA — Firebase Direct Simulator
====================================
Mengirim data sensor langsung ke Firebase Realtime Database (tanpa MQTT).

Gunakan script ini untuk simulasi dashboard:
    1. Jalankan script ini di terminal pertama  →  python simulator_firebase.py
    2. Jalankan ML di terminal kedua            →  python filtora_ml_clustering.py
    3. Buka dashboard di browser               →  https://raijen-code.github.io/filtora-dashboard/

Field yang ditulis ke Firebase /sensor_data/{timestamp_key}:
    mq135, mq2, mq5, pm25, pm10, temperature, humidity
"""

import firebase_admin
from firebase_admin import credentials, db
import random
import time
from datetime import datetime

# ============================================================
# KONFIGURASI
# ============================================================
FIREBASE_CONFIG = {
    'credential_path': 'firebase-key.json',
    'database_url': 'https://filtora-data-default-rtdb.asia-southeast1.firebasedatabase.app/'
}

PUBLISH_INTERVAL = 5   # detik antar kiriman data
MAX_RECORDS      = 200 # batas maksimal data di /sensor_data (auto-cleanup)

# ============================================================
# RENTANG NILAI PER KONDISI
# ============================================================
CONDITIONS = {
    'good': {
        'mq135': (50,  150), 'mq2': (100, 300),  'mq5': (80,  250),
        'pm25':  (0,   12),  'pm10': (0,   20),
        'temp':  (22,  28),  'humid': (40, 60)
    },
    'moderate': {
        'mq135': (150, 300), 'mq2': (300, 600),  'mq5': (250, 500),
        'pm25':  (12,  35),  'pm10': (20,  50),
        'temp':  (24,  30),  'humid': (50, 70)
    },
    'poor': {
        'mq135': (300, 500), 'mq2': (600, 900),  'mq5': (500, 750),
        'pm25':  (35,  55),  'pm10': (50,  100),
        'temp':  (25,  32),  'humid': (55, 75)
    },
    'very_poor': {
        'mq135': (500, 800), 'mq2': (900, 1200), 'mq5': (750, 1000),
        'pm25':  (55,  100), 'pm10': (100, 200),
        'temp':  (26,  33),  'humid': (60, 80)
    }
}

CONDITION_EMOJI = {
    'good': '🟢', 'moderate': '🟡', 'poor': '🟠', 'very_poor': '🔴'
}

# ============================================================
# INISIALISASI FIREBASE
# ============================================================
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CONFIG['credential_path'])
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_CONFIG['database_url']
        })
    print(f"✅ Firebase terhubung: {FIREBASE_CONFIG['database_url']}")

# ============================================================
# GENERATE DATA SENSOR RANDOM
# ============================================================
def generate_data():
    cond = random.choice(list(CONDITIONS.keys()))
    r    = CONDITIONS[cond]

    return cond, {
        'mq135':       round(random.uniform(*r['mq135']), 2),
        'mq2':         round(random.uniform(*r['mq2']),   2),
        'mq5':         round(random.uniform(*r['mq5']),   2),
        'pm25':        round(random.uniform(*r['pm25']),  2),
        'pm10':        round(random.uniform(*r['pm10']),  2),
        'temperature': round(random.uniform(*r['temp']),  2),
        'humidity':    round(random.uniform(*r['humid']), 2),
    }

# ============================================================
# TULIS KE FIREBASE
# ============================================================
def write_sensor_data(sensor_data):
    now    = datetime.now()
    # Format key: 2026-06-25T10-30-00_123456  (cocok dengan parser di firebase.js)
    ts_key = now.strftime('%Y-%m-%dT%H-%M-%S') + f'_{now.microsecond}'

    payload = dict(sensor_data)
    payload['timestamp'] = now.isoformat()   # untuk dibaca kembali oleh filtora_ml_clustering.py
    payload['device_id'] = 'simulator_001'
    payload['location']  = 'lab'

    db.reference('sensor_data').child(ts_key).set(payload)
    return ts_key

# ============================================================
# CLEANUP: HAPUS DATA LAMA BILA MELEBIHI MAX_RECORDS
# ============================================================
def cleanup_old_data():
    ref  = db.reference('sensor_data')
    data = ref.order_by_key().get()
    if not data:
        return

    keys = sorted(data.keys())
    if len(keys) > MAX_RECORDS:
        to_delete = keys[:len(keys) - MAX_RECORDS]
        for k in to_delete:
            ref.child(k).delete()
        print(f"   🗑  Cleanup: {len(to_delete)} entri lama dihapus")

# ============================================================
# MAIN LOOP
# ============================================================
def main():
    print("=" * 65)
    print("🔥  FILTORA — Firebase Direct Simulator")
    print("=" * 65)
    print(f"   Interval  : {PUBLISH_INTERVAL} detik")
    print(f"   Target    : Firebase /sensor_data")
    print(f"   Max record: {MAX_RECORDS} (auto-cleanup)")
    print("   Ctrl+C    : hentikan simulator")
    print("=" * 65)

    init_firebase()

    count   = 0
    cleanup_every = 20  # cleanup setiap 20 kiriman

    try:
        while True:
            count += 1
            cond, data = generate_data()
            ts_key     = write_sensor_data(data)

            emoji = CONDITION_EMOJI[cond]
            print(f"\n[#{count:04d}] {datetime.now().strftime('%H:%M:%S')}  "
                  f"{emoji} {cond.upper()}")
            print(f"  MQ135={data['mq135']:7.2f}  MQ2={data['mq2']:7.2f}  MQ5={data['mq5']:7.2f}")
            print(f"  PM2.5={data['pm25']:6.2f}  PM10={data['pm10']:7.2f}")
            print(f"  Suhu={data['temperature']}°C  Humid={data['humidity']}%")
            print(f"  ✅ → /sensor_data/{ts_key}")

            # Cleanup berkala
            if count % cleanup_every == 0:
                cleanup_old_data()

            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n🛑 Simulator dihentikan setelah {count} kiriman.")
        print("   Jalankan: python filtora_ml_clustering.py  untuk update prediksi ML.")

if __name__ == "__main__":
    main()
