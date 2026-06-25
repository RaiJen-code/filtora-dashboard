import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import time
import warnings

warnings.filterwarnings('ignore')

# ========================================
# KONFIGURASI FIREBASE
# ========================================
FIREBASE_CONFIG = {
    'credential_path': 'firebase-key.json',
    'database_url': 'https://filtora-data-default-rtdb.asia-southeast1.firebasedatabase.app/'
}

# ========================================
# KONFIGURASI MACHINE LEARNING
# ========================================
ML_CONFIG = {
    'n_clusters': 3,  # Jumlah klaster (Baik, Sedang, Buruk)
    'features': ['mq135', 'mq2', 'mq5', 'pm25', 'pm10', 'temperature', 'humidity'],
    'random_state': 42,
    'min_data_points': 5,  # Minimal data untuk clustering
    'update_interval': 30  # Interval update dalam detik (0 = sekali jalan)
}

# ========================================
# LABEL KUALITAS UDARA
# ========================================
CLUSTER_LABELS = {
    0: "Baik",
    1: "Sedang", 
    2: "Buruk"
}

# ========================================
# INISIALISASI FIREBASE
# ========================================
def init_firebase():
    """
    Menginisialisasi koneksi ke Firebase Realtime Database
    """
    try:
        # Cek apakah Firebase sudah diinisialisasi
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CONFIG['credential_path'])
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_CONFIG['database_url']
            })
        
        print("=" * 80)
        print(" FILTORA - Machine Learning Clustering System")
        print("=" * 80)
        print(" Firebase berhasil diinisialisasi")
        print(f" Database URL: {FIREBASE_CONFIG['database_url']}")
        print(f" Jumlah Klaster: {ML_CONFIG['n_clusters']} (Baik, Sedang, Buruk)")
        print(f" Fitur yang digunakan: {', '.join(ML_CONFIG['features'])}")
        print("=" * 80)
        return True
    except Exception as e:
        print(f" Error inisialisasi Firebase: {e}")
        return False

# ========================================
# FUNGSI AMBIL DATA DARI FIREBASE
# ========================================
def fetch_data_from_firebase(limit=150):
    """
    Mengambil data sensor terbaru dari Firebase node /sensor_data.
    Hanya mengambil 'limit' data terakhir agar tidak memproses data lama 2025.

    Returns:
        pandas.DataFrame: Data sensor dalam bentuk DataFrame
    """
    try:
        print(f"\n Mengambil {limit} data terbaru dari Firebase...")
        # Ambil hanya data terbaru berdasarkan key (timestamp)
        data = db.reference('sensor_data').order_by_key().limit_to_last(limit).get()
        
        if not data:
            print("  Tidak ada data di Firebase")
            return None
        
        # Konversi data Firebase ke DataFrame
        data_list = []
        for timestamp, values in data.items():
            if all(feature in values for feature in ML_CONFIG['features']):
                row = {'timestamp': timestamp}
                row.update(values)
                data_list.append(row)
        
        if not data_list:
            print("  Data tidak memiliki fitur yang lengkap")
            return None
        
        df = pd.DataFrame(data_list)
        print(f" Berhasil mengambil {len(df)} data dari Firebase")
        print(f" Range waktu: {df['timestamp'].min()} s/d {df['timestamp'].max()}")
        
        return df
    
    except Exception as e:
        print(f" Error mengambil data dari Firebase: {e}")
        return None

# ========================================
# FUNGSI PREPROCESSING DATA
# ========================================
def preprocess_data(df):
    """
    Melakukan preprocessing data sebelum clustering
    
    Steps:
    1. Membuang data dengan nilai kosong (NaN)
    2. Memastikan semua fitur ada
    3. Konversi ke tipe numerik
    4. Normalisasi menggunakan StandardScaler
    
    Args:
        df (DataFrame): Data mentah dari Firebase
        
    Returns:
        tuple: (data_normalized, scaler, df_clean)
    """
    try:
        print("\n Preprocessing data...")
        
        # 1. Cek kelengkapan fitur
        missing_features = [f for f in ML_CONFIG['features'] if f not in df.columns]
        if missing_features:
            print(f" Fitur tidak lengkap: {missing_features}")
            return None, None, None
        
        # 2. Pilih hanya kolom fitur yang diperlukan
        df_features = df[ML_CONFIG['features']].copy()
        
        # 3. Konversi ke numeric dan buang NaN
        df_features = df_features.apply(pd.to_numeric, errors='coerce')
        data_before = len(df_features)
        df_features = df_features.dropna()
        data_after = len(df_features)
        
        if data_before > data_after:
            print(f"  Membuang {data_before - data_after} baris dengan nilai kosong")
        
        if len(df_features) < ML_CONFIG['min_data_points']:
            print(f" Data terlalu sedikit untuk clustering (minimum {ML_CONFIG['min_data_points']})")
            return None, None, None
        
        # 4. Normalisasi data menggunakan StandardScaler
        # StandardScaler: (x - mean) / std_dev
        # Mengubah data agar memiliki mean=0 dan std=1
        scaler = StandardScaler()
        data_normalized = scaler.fit_transform(df_features)
        
        print(f" Preprocessing selesai: {len(df_features)} data siap untuk clustering")
        print(f" Statistik data:")
        print(df_features.describe().round(2).to_string())
        
        # Buat DataFrame clean dengan timestamp
        df_clean = df.loc[df_features.index].copy()
        
        return data_normalized, scaler, df_clean
    
    except Exception as e:
        print(f" Error preprocessing: {e}")
        return None, None, None

# ========================================
# FUNGSI K-MEANS CLUSTERING
# ========================================
def perform_clustering(data_normalized, df_clean):
    """
    Melakukan K-Means Clustering untuk klasifikasi kualitas udara
    
    Algoritma K-Means:
    - Membagi data menjadi K kelompok (clusters)
    - Setiap data point akan masuk ke cluster terdekat
    - Iterasi hingga centroid stabil
    
    Args:
        data_normalized (array): Data yang sudah dinormalisasi
        df_clean (DataFrame): Data asli (untuk analisis centroid)
        
    Returns:
        tuple: (kmeans_model, cluster_labels, centroids_analysis)
    """
    try:
        print("\n Menjalankan K-Means Clustering...")
        
        # Inisialisasi K-Means
        kmeans = KMeans(
            n_clusters=ML_CONFIG['n_clusters'],
            random_state=ML_CONFIG['random_state'],
            n_init=10,  # Jumlah inisialisasi berbeda untuk stabilitas
            max_iter=300  # Maksimal iterasi
        )
        
        # Fit model dan prediksi cluster
        cluster_labels = kmeans.fit_predict(data_normalized)
        
        # Tambahkan label cluster ke DataFrame
        df_clean['cluster'] = cluster_labels
        
        print(f" Clustering selesai")
        print(f" Distribusi cluster:")
        for i in range(ML_CONFIG['n_clusters']):
            count = np.sum(cluster_labels == i)
            percentage = (count / len(cluster_labels)) * 100
            print(f"   Cluster {i}: {count} data ({percentage:.1f}%)")
        
        # Analisis centroid untuk setiap cluster
        centroids_analysis = analyze_centroids(df_clean)
        
        return kmeans, cluster_labels, centroids_analysis
    
    except Exception as e:
        print(f" Error clustering: {e}")
        return None, None, None

# ========================================
# FUNGSI ANALISIS CENTROID
# ========================================
def analyze_centroids(df_clean):
    """
    Menganalisis centroid (rata-rata) setiap cluster untuk menentukan label
    
    Logic:
    - Cluster dengan nilai polutan tertinggi = "Buruk"
    - Cluster dengan nilai polutan terendah = "Baik"
    - Cluster di tengah = "Sedang"
    
    Polutan utama: MQ135, MQ2, MQ5, PM2.5, PM10
    
    Args:
        df_clean (DataFrame): Data dengan kolom cluster
        
    Returns:
        dict: Mapping cluster number ke label kualitas
    """
    try:
        print("\n Menganalisis centroid setiap cluster...")
        
        # Kolom polutan yang akan dianalisis
        pollutant_features = ['mq135', 'mq2', 'mq5', 'pm25', 'pm10']
        
        centroids = {}
        pollution_scores = {}
        
        for cluster_id in range(ML_CONFIG['n_clusters']):
            cluster_data = df_clean[df_clean['cluster'] == cluster_id]
            
            # Hitung rata-rata untuk setiap fitur
            centroid = cluster_data[ML_CONFIG['features']].mean()
            centroids[cluster_id] = centroid
            
            # Hitung skor polusi (rata-rata dari polutan utama)
            pollution_score = cluster_data[pollutant_features].mean().mean()
            pollution_scores[cluster_id] = pollution_score
            
            print(f"\n   Cluster {cluster_id}:")
            print(f"   - Rata-rata MQ135: {centroid['mq135']:.2f}")
            print(f"   - Rata-rata PM2.5: {centroid['pm25']:.2f}")
            print(f"   - Rata-rata PM10: {centroid['pm10']:.2f}")
            print(f"   - Skor Polusi: {pollution_score:.2f}")
        
        # Urutkan cluster berdasarkan skor polusi
        # Cluster dengan skor tertinggi = Buruk (2)
        # Cluster dengan skor terendah = Baik (0)
        # Cluster di tengah = Sedang (1)
        sorted_clusters = sorted(pollution_scores.items(), key=lambda x: x[1])
        
        cluster_to_label = {
            sorted_clusters[0][0]: 0,  # Skor terendah → Baik (0)
            sorted_clusters[1][0]: 1,  # Skor tengah → Sedang (1)
            sorted_clusters[2][0]: 2   # Skor tertinggi → Buruk (2)
        }
        
        print("\n📋 Mapping Cluster ke Label Kualitas:")
        for cluster_id, quality_label in cluster_to_label.items():
            label_name = CLUSTER_LABELS[quality_label]
            score = pollution_scores[cluster_id]
            print(f"   Cluster {cluster_id} (Skor: {score:.2f}) → {label_name}")
        
        return cluster_to_label
    
    except Exception as e:
        print(f" Error analisis centroid: {e}")
        return None

# ========================================
# FUNGSI MAPPING CLUSTER KE LABEL
# ========================================
def map_clusters_to_labels(df_clean, cluster_to_label):
    """
    Mengonversi cluster number menjadi label kualitas udara
    
    Args:
        df_clean (DataFrame): Data dengan kolom cluster
        cluster_to_label (dict): Mapping cluster ke label
        
    Returns:
        DataFrame: Data dengan kolom quality_label
    """
    try:
        # Map cluster ke label kualitas (0=Baik, 1=Sedang, 2=Buruk)
        df_clean['quality_code'] = df_clean['cluster'].map(cluster_to_label)
        
        # Map quality code ke label text
        df_clean['quality_label'] = df_clean['quality_code'].map(CLUSTER_LABELS)
        
        return df_clean
    
    except Exception as e:
        print(f" Error mapping labels: {e}")
        return None

# ========================================
# FUNGSI SIMPAN HASIL KE FIREBASE
# ========================================
def save_predictions_to_firebase(df_clean):
    """
    Menyimpan hasil prediksi clustering ke Firebase
    
    Struktur data di Firebase:
    /predictions/{timestamp}/
        - cluster: int (0, 1, 2)
        - quality_code: int (0=Baik, 1=Sedang, 2=Buruk)
        - quality_label: string ("Baik", "Sedang", "Buruk")
        - predicted_at: timestamp prediksi dibuat
    
    Args:
        df_clean (DataFrame): Data dengan hasil clustering
    """
    try:
        print("\n Menyimpan hasil prediksi ke Firebase...")
        
        ref = db.reference('predictions')
        predicted_at = datetime.now().isoformat()
        
        success_count = 0
        
        for _, row in df_clean.iterrows():
            timestamp = row['timestamp']
            
            prediction_data = {
                'cluster': int(row['cluster']),
                'quality_code': int(row['quality_code']),
                'quality_label': row['quality_label'],
                'predicted_at': predicted_at,
                # Simpan juga nilai sensor untuk referensi
                'sensor_values': {
                    'mq135': float(row['mq135']),
                    'mq2': float(row['mq2']),
                    'mq5': float(row['mq5']),
                    'pm25': float(row['pm25']),
                    'pm10': float(row['pm10']),
                    'temperature': float(row['temperature']),
                    'humidity': float(row['humidity'])
                }
            }
            
            # Simpan ke Firebase
            safe_timestamp = timestamp.replace(":", "-").replace(".", "_")
            ref.child(safe_timestamp).set(prediction_data)
            success_count += 1
        
        print(f" Berhasil menyimpan {success_count} prediksi ke Firebase")
        print(f" Node: /predictions")

        # ── Simpan prediksi TERBARU ke /latest_prediction ──────────────
        # Dashboard membaca node ini agar selalu dapat data real-time
        # tanpa bergantung pada urutan key timestamp lama.
        latest_row  = df_clean.iloc[-1]
        latest_pred = {
            'cluster':       int(latest_row['cluster']),
            'quality_code':  int(latest_row['quality_code']),
            'quality_label': latest_row['quality_label'],
            'predicted_at':  predicted_at,
            'sensor_values': {
                'mq135':       float(latest_row['mq135']),
                'mq2':         float(latest_row['mq2']),
                'mq5':         float(latest_row['mq5']),
                'pm25':        float(latest_row['pm25']),
                'pm10':        float(latest_row['pm10']),
                'temperature': float(latest_row['temperature']),
                'humidity':    float(latest_row['humidity'])
            }
        }
        db.reference('latest_prediction').set(latest_pred)
        print(f" Latest prediksi tersimpan di /latest_prediction → {latest_pred['quality_label']}")

        # Tampilkan ringkasan hasil
        print("\n Ringkasan Hasil Klasifikasi:")
        for quality_code, label in CLUSTER_LABELS.items():
            count = len(df_clean[df_clean['quality_code'] == quality_code])
            percentage = (count / len(df_clean)) * 100
            print(f"   {label}: {count} data ({percentage:.1f}%)")

        return True
    
    except Exception as e:
        print(f" Error menyimpan ke Firebase: {e}")
        return False

# ========================================
# FUNGSI VISUALISASI CLUSTERING
# ========================================
def visualize_clustering(df_clean, save_plot=True):
    """
    Membuat visualisasi hasil clustering
    
    Membuat 2 scatter plot:
    1. PM2.5 vs MQ135 (polutan utama)
    2. PM10 vs MQ2 (polutan tambahan)
    
    Args:
        df_clean (DataFrame): Data dengan hasil clustering
        save_plot (bool): Simpan plot ke file
    """
    try:
        print("\n Membuat visualisasi clustering...")
        
        # Set style
        sns.set_style("whitegrid")
        
        # Buat figure dengan 2 subplot
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # Color palette untuk cluster
        colors = {0: '#2ecc71', 1: '#f39c12', 2: '#e74c3c'}  # Hijau, Kuning, Merah
        
        # Plot 1: PM2.5 vs MQ135
        for quality_code, label in CLUSTER_LABELS.items():
            cluster_data = df_clean[df_clean['quality_code'] == quality_code]
            axes[0].scatter(
                cluster_data['mq135'], 
                cluster_data['pm25'],
                c=colors[quality_code],
                label=label,
                alpha=0.6,
                s=100,
                edgecolors='black',
                linewidth=0.5
            )
        
        axes[0].set_xlabel('MQ135 (Gas Quality Sensor)', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('PM2.5 (µg/m³)', fontsize=12, fontweight='bold')
        axes[0].set_title('Clustering: PM2.5 vs MQ135', fontsize=14, fontweight='bold')
        axes[0].legend(title='Kualitas Udara', fontsize=10)
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: PM10 vs MQ2
        for quality_code, label in CLUSTER_LABELS.items():
            cluster_data = df_clean[df_clean['quality_code'] == quality_code]
            axes[1].scatter(
                cluster_data['mq2'], 
                cluster_data['pm10'],
                c=colors[quality_code],
                label=label,
                alpha=0.6,
                s=100,
                edgecolors='black',
                linewidth=0.5
            )
        
        axes[1].set_xlabel('MQ2 (Smoke Sensor)', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('PM10 (µg/m³)', fontsize=12, fontweight='bold')
        axes[1].set_title('Clustering: PM10 vs MQ2', fontsize=14, fontweight='bold')
        axes[1].legend(title='Kualitas Udara', fontsize=10)
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_plot:
            filename = f"clustering_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✅ Visualisasi disimpan: {filename}")
        
        plt.show()
        
        return True
    
    except Exception as e:
        print(f" Error visualisasi: {e}")
        return False

# ========================================
# FUNGSI VISUALISASI DISTRIBUSI
# ========================================
def visualize_distribution(df_clean):
    """
    Membuat visualisasi distribusi sensor per kualitas udara
    """
    try:
        print("\n Membuat visualisasi distribusi...")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('Distribusi Sensor Berdasarkan Kualitas Udara', 
                     fontsize=16, fontweight='bold')
        
        features_to_plot = ['mq135', 'mq2', 'pm25', 'pm10', 'temperature', 'humidity']
        colors = ['#2ecc71', '#f39c12', '#e74c3c']  # Hijau, Kuning, Merah
        
        for idx, feature in enumerate(features_to_plot):
            row = idx // 3
            col = idx % 3
            ax = axes[row, col]
            
            # Box plot untuk setiap kualitas udara
            data_to_plot = [
                df_clean[df_clean['quality_label'] == 'Baik'][feature],
                df_clean[df_clean['quality_label'] == 'Sedang'][feature],
                df_clean[df_clean['quality_label'] == 'Buruk'][feature]
            ]
            
            bp = ax.boxplot(data_to_plot, labels=['Baik', 'Sedang', 'Buruk'],
                           patch_artist=True)
            
            # Warna box plot
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
            
            ax.set_title(feature.upper(), fontweight='bold')
            ax.set_ylabel('Nilai Sensor')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        filename = f"distribution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f" Visualisasi distribusi disimpan: {filename}")
        
        plt.show()
        
        return True
    
    except Exception as e:
        print(f" Error visualisasi distribusi: {e}")
        return False

# ========================================
# FUNGSI UTAMA PIPELINE ML
# ========================================
def run_ml_pipeline(visualize=True):
    """
    Menjalankan seluruh pipeline machine learning
    
    Pipeline:
    1. Ambil data dari Firebase
    2. Preprocessing
    3. K-Means Clustering
    4. Analisis centroid dan mapping label
    5. Simpan hasil ke Firebase
    6. (Opsional) Visualisasi
    
    Args:
        visualize (bool): Apakah membuat visualisasi
        
    Returns:
        bool: Status keberhasilan
    """
    try:
        print("\n" + "=" * 80)
        print(" MEMULAI PIPELINE MACHINE LEARNING")
        print("=" * 80)
        
        start_time = time.time()
        
        # 1. Ambil data dari Firebase
        df = fetch_data_from_firebase()
        if df is None or len(df) == 0:
            print("\n⚠️  Tidak dapat melanjutkan: Data tidak tersedia")
            return False
        
        # 2. Preprocessing
        data_normalized, scaler, df_clean = preprocess_data(df)
        if data_normalized is None:
            print("\n⚠️  Tidak dapat melanjutkan: Preprocessing gagal")
            return False
        
        # 3. K-Means Clustering
        kmeans, cluster_labels, cluster_to_label = perform_clustering(data_normalized, df_clean)
        if kmeans is None:
            print("\n⚠️  Tidak dapat melanjutkan: Clustering gagal")
            return False
        
        # 4. Mapping cluster ke label
        df_clean = map_clusters_to_labels(df_clean, cluster_to_label)
        if df_clean is None:
            print("\n⚠️  Tidak dapat melanjutkan: Mapping label gagal")
            return False
        
        # 5. Simpan ke Firebase
        if not save_predictions_to_firebase(df_clean):
            print("\n⚠️  Gagal menyimpan hasil ke Firebase")
            return False
        
        # 6. Visualisasi (opsional)
        if visualize:
            visualize_clustering(df_clean, save_plot=True)
            visualize_distribution(df_clean)
        
        # Selesai
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 80)
        print(" PIPELINE MACHINE LEARNING SELESAI")
        print("=" * 80)
        print(f"  Waktu eksekusi: {elapsed_time:.2f} detik")
        print(f" Total data diproses: {len(df_clean)}")
        print(f" Hasil tersimpan di: /predictions")
        print("=" * 80)
        
        return True
    
    except Exception as e:
        print(f"\n Error dalam pipeline ML: {e}")
        return False

# ========================================
# FUNGSI MAIN
# ========================================
def main():
    """
    Fungsi utama untuk menjalankan program
    
    Mode operasi:
    1. Sekali jalan (update_interval = 0)
    2. Continuous monitoring (update_interval > 0)
    """
    
    # Inisialisasi Firebase
    if not init_firebase():
        return
    
    # Cek mode operasi
    if ML_CONFIG['update_interval'] == 0:
        # Mode: Sekali jalan
        print("\n Mode: Eksekusi Sekali")
        run_ml_pipeline(visualize=True)
    else:
        # Mode: Continuous monitoring
        print(f"\n Mode: Monitoring Kontinu (update setiap {ML_CONFIG['update_interval']} detik)")
        print("⚠️  Tekan Ctrl+C untuk menghentikan\n")
        
        try:
            iteration = 1
            while True:
                print(f"\n{'='*80}")
                print(f" ITERASI {iteration}")
                print(f"{'='*80}")
                
                run_ml_pipeline(visualize=False)
                
                print(f"\n Menunggu {ML_CONFIG['update_interval']} detik untuk update berikutnya...")
                time.sleep(ML_CONFIG['update_interval'])
                
                iteration += 1
                
        except KeyboardInterrupt:
            print("\n\n Program dihentikan oleh pengguna (Ctrl+C)")
        finally:
            print(" Program selesai\n")

# ========================================
# ENTRY POINT
# ========================================
if __name__ == "__main__":
    main()