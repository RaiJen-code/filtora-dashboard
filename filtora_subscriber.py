import paho.mqtt.client as mqtt
import firebase_admin
from firebase_admin import credentials, db
import json
import ssl
import time
from datetime import datetime

# ========================================
# KONFIGURASI EMQX BROKER
# ========================================
MQTT_CONFIG = {
    'broker': 'y818991f.ala.asia-southeast1.emqxsl.com',
    'port': 8883,
    'username': 'apaaja',
    'password': '123456789',
    'topic_subscribe': 'udara/sensor/#'  # Subscribe ke semua topik sensor
}

# ========================================
# KONFIGURASI FIREBASE
# ========================================
FIREBASE_CONFIG = {
    'credential_path': 'firebase-key.json',
    'database_url': 'https://filtora-data-default-rtdb.asia-southeast1.firebasedatabase.app/'
}

# ========================================
# VARIABEL GLOBAL UNTUK BUFFER DATA
# ========================================
# Buffer untuk menyimpan data dari berbagai topik sebelum dikirim ke Firebase
sensor_buffer = {
    'mq135': None,
    'mq2': None,
    'mq5': None,
    'pm25': None,
    'pm10': None,
    'temperature': None,
    'humidity': None,
    'timestamp': None,
    'device_id': None,
    'location': None
}

# ========================================
# INISIALISASI FIREBASE
# ========================================
def init_firebase():
    """
    Menginisialisasi koneksi ke Firebase Realtime Database
    menggunakan service account credentials
    """
    try:
        cred = credentials.Certificate(FIREBASE_CONFIG['credential_path'])
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_CONFIG['database_url']
        })
        print("✅ Firebase berhasil diinisialisasi")
        print(f"📍 Database URL: {FIREBASE_CONFIG['database_url']}\n")
        return True
    except Exception as e:
        print(f"❌ Error inisialisasi Firebase: {e}")
        return False

# ========================================
# FUNGSI KIRIM DATA KE FIREBASE
# ========================================
def send_to_firebase(data):
    """
    Mengirim data sensor ke Firebase Realtime Database
    
    Args:
        data (dict): Data sensor yang akan disimpan
    
    Struktur data di Firebase:
    /sensor_data/{timestamp_key}/
        - mq135
        - mq2
        - mq5
        - pm25
        - pm10
        - temperature
        - humidity
        - device_id
        - location
        - timestamp
    """
    try:
        # Referensi ke node sensor_data di Firebase
        ref = db.reference('sensor_data')
        
        # Gunakan timestamp sebagai key unik
        # Ganti karakter yang tidak valid untuk Firebase key
        timestamp_key = data['timestamp'].replace(':', '-').replace('.', '-')
        
        # Push data ke Firebase
        ref.child(timestamp_key).set(data)
        
        print(f"🔥 Data berhasil dikirim ke Firebase")
        print(f"   Node: /sensor_data/{timestamp_key}")
        print(f"   MQ135: {data['mq135']}, MQ2: {data['mq2']}, PM2.5: {data['pm25']}")
        print("-" * 70)
        
        return True
    except Exception as e:
        print(f"❌ Error mengirim data ke Firebase: {e}")
        return False

# ========================================
# FUNGSI CEK KELENGKAPAN DATA
# ========================================
def is_data_complete():
    """
    Mengecek apakah semua data sensor sudah lengkap dalam buffer
    
    Returns:
        bool: True jika semua sensor sudah ada datanya
    """
    required_fields = ['mq135', 'mq2', 'mq5', 'pm25', 'pm10', 'temperature', 'humidity']
    return all(sensor_buffer[field] is not None for field in required_fields)

# ========================================
# FUNGSI RESET BUFFER
# ========================================
def reset_buffer():
    """
    Mereset buffer data sensor setelah data dikirim ke Firebase
    """
    for key in sensor_buffer:
        sensor_buffer[key] = None

# ========================================
# CALLBACK: KONEKSI MQTT BERHASIL
# ========================================
def on_connect(client, userdata, flags, rc):
    """
    Callback yang dipanggil saat koneksi ke broker MQTT berhasil/gagal
    
    Args:
        rc (int): Return code dari koneksi
            0: Koneksi berhasil
            1-5: Berbagai jenis error koneksi
    """
    if rc == 0:
        print("✅ Berhasil terhubung ke broker EMQX")
        # Subscribe ke semua topik sensor setelah koneksi berhasil
        client.subscribe(MQTT_CONFIG['topic_subscribe'])
        print(f"📡 Subscribe ke topik: {MQTT_CONFIG['topic_subscribe']}")
        print("⏳ Menunggu data dari sensor...\n")
    else:
        error_messages = {
            1: "Protokol MQTT salah",
            2: "Client ID ditolak",
            3: "Server tidak tersedia",
            4: "Username/password salah",
            5: "Tidak terotorisasi"
        }
        print(f"❌ Gagal terhubung ke broker")
        print(f"   Kode error: {rc} - {error_messages.get(rc, 'Error tidak diketahui')}")

# ========================================
# CALLBACK: PESAN MQTT DITERIMA
# ========================================
def on_message(client, userdata, msg):
    """
    Callback yang dipanggil setiap kali pesan MQTT diterima
    
    Args:
        msg: Object pesan MQTT yang berisi topic dan payload
    
    Strategi:
    1. Parse JSON payload
    2. Identifikasi jenis sensor dari topik
    3. Simpan ke buffer
    4. Jika data lengkap, kirim ke Firebase
    """
    try:
        # Decode payload JSON
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        
        # Tampilkan info pesan diterima
        print(f"📩 Pesan diterima dari: {topic}")
        
        # Tangani topik combined (semua sensor sekaligus)
        if 'combined' in topic:
            print(f"   📦 Data gabungan diterima")
            
            # Extract data dari payload combined
            sensors = payload.get('sensors', {})
            
            # Siapkan data untuk Firebase
            firebase_data = {
                'device_id': payload.get('device_id', 'unknown'),
                'location': payload.get('location', 'unknown'),
                'timestamp': payload.get('timestamp', datetime.now().isoformat()),
                'mq135': sensors.get('mq135'),
                'mq2': sensors.get('mq2'),
                'mq5': sensors.get('mq5'),
                'pm25': sensors.get('pm25'),
                'pm10': sensors.get('pm10'),
                'temperature': sensors.get('temperature'),
                'humidity': sensors.get('humidity'),
                'air_condition': sensors.get('air_condition', 'unknown')
            }
            
            # Langsung kirim ke Firebase
            send_to_firebase(firebase_data)
            
        else:
            # Tangani topik individual sensor
            sensor_type = payload.get('sensor_type')
            value = payload.get('value')
            
            print(f"   Sensor: {sensor_type} → Nilai: {value}")
            
            # Simpan data ke buffer
            if sensor_type in sensor_buffer:
                sensor_buffer[sensor_type] = value
                sensor_buffer['timestamp'] = payload.get('timestamp')
                sensor_buffer['device_id'] = payload.get('device_id')
                sensor_buffer['location'] = payload.get('location')
            
            # Cek apakah data sudah lengkap
            if is_data_complete():
                print(f"   ✅ Data lengkap, mengirim ke Firebase...")
                
                # Siapkan data untuk Firebase
                firebase_data = {
                    'device_id': sensor_buffer['device_id'],
                    'location': sensor_buffer['location'],
                    'timestamp': sensor_buffer['timestamp'],
                    'mq135': sensor_buffer['mq135'],
                    'mq2': sensor_buffer['mq2'],
                    'mq5': sensor_buffer['mq5'],
                    'pm25': sensor_buffer['pm25'],
                    'pm10': sensor_buffer['pm10'],
                    'temperature': sensor_buffer['temperature'],
                    'humidity': sensor_buffer['humidity']
                }
                
                # Kirim ke Firebase
                send_to_firebase(firebase_data)
                
                # Reset buffer untuk data berikutnya
                reset_buffer()
            else:
                # Tampilkan sensor mana saja yang belum ada datanya
                missing = [k for k, v in sensor_buffer.items() 
                          if k in ['mq135', 'mq2', 'mq5', 'pm25', 'pm10', 'temperature', 'humidity'] 
                          and v is None]
                print(f"   ⏳ Menunggu data dari: {', '.join(missing)}")
        
    except json.JSONDecodeError:
        print(f"❌ Error: Payload bukan JSON yang valid")
    except Exception as e:
        print(f"❌ Error memproses pesan: {e}")

# ========================================
# CALLBACK: KONEKSI TERPUTUS
# ========================================
def on_disconnect(client, userdata, rc):
    """
    Callback yang dipanggil saat koneksi terputus
    
    Args:
        rc (int): Return code disconnect
            0: Disconnect normal (dipanggil oleh program)
            Lainnya: Disconnect tidak diharapkan
    """
    if rc != 0:
        print(f"⚠️  Koneksi terputus tidak terduga (kode: {rc})")
        print("🔄 Mencoba reconnect otomatis...")
    else:
        print("✅ Koneksi ditutup dengan normal")

# ========================================
# FUNGSI UTAMA
# ========================================
def main():
    """
    Fungsi utama untuk menjalankan MQTT subscriber
    
    Flow:
    1. Inisialisasi Firebase
    2. Setup MQTT client dengan TLS
    3. Connect ke broker EMQX
    4. Loop untuk menerima pesan
    5. Graceful shutdown saat Ctrl+C
    """
    
    print("=" * 70)
    print("🌍 FILTORA - MQTT to Firebase Subscriber")
    print("=" * 70)
    
    # Inisialisasi Firebase terlebih dahulu
    if not init_firebase():
        print("❌ Gagal menginisialisasi Firebase. Program dihentikan.")
        return
    
    # Setup MQTT Client
    client = mqtt.Client(client_id="filtora_subscriber_01")
    
    # Set username dan password
    client.username_pw_set(MQTT_CONFIG['username'], MQTT_CONFIG['password'])
    
    # Set callback functions
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Konfigurasi TLS/SSL untuk koneksi aman
    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS
    )
    client.tls_insecure_set(False)
    
    # Enable automatic reconnection
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    try:
        # Koneksi ke broker EMQX
        print(f"🔌 Menghubungkan ke broker: {MQTT_CONFIG['broker']}:{MQTT_CONFIG['port']}")
        client.connect(MQTT_CONFIG['broker'], MQTT_CONFIG['port'], keepalive=60)
        
        # Loop forever untuk menerima pesan
        # loop_forever() akan otomatis reconnect jika koneksi terputus
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n⛔ Program dihentikan oleh pengguna (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        print("🔌 Menutup koneksi MQTT...")
        client.disconnect()
        client.loop_stop()
        print("✅ Program selesai\n")

# ========================================
# ENTRY POINT
# ========================================
if __name__ == "__main__":
    main()