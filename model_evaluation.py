"""
Model Evaluation untuk K-Means Clustering
Menghitung metrik kualitas clustering
"""

import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import matplotlib.pyplot as plt

# ========================================
# KONFIGURASI
# ========================================
FIREBASE_CONFIG = {
    'credential_path': 'firebase-key.json',
    'database_url': 'https://filtora-data-default-rtdb.asia-southeast1.firebasedatabase.app/'
}

FEATURES = ['mq135', 'mq2', 'mq5', 'pm25', 'pm10', 'temperature', 'humidity']

# ========================================
# INISIALISASI
# ========================================
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CONFIG['credential_path'])
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_CONFIG['database_url']
        })

# ========================================
# FETCH DATA
# ========================================
def fetch_and_prepare_data():
    """Ambil dan prepare data dari Firebase"""
    ref = db.reference('sensor_data')
    data = ref.get()
    
    if not data:
        return None, None
    
    data_list = []
    for timestamp, values in data.items():
        if all(f in values for f in FEATURES):
            data_list.append([values[f] for f in FEATURES])
    
    X = np.array(data_list)
    
    # Normalization
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X, X_scaled

# ========================================
# ELBOW METHOD
# ========================================
def plot_elbow_method(X_scaled, max_k=10):
    """
    Plot Elbow Method untuk menentukan jumlah cluster optimal
    
    Elbow Method: Mencari "siku" pada grafik inertia vs K
    - Inertia: Sum of squared distances ke centroid terdekat
    - Semakin rendah inertia, semakin baik clustering
    - "Siku" = titik dimana penambahan K tidak signifikan menurunkan inertia
    """
    print("\n📊 Calculating Elbow Method...")
    
    inertias = []
    K_range = range(2, max_k + 1)
    
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)
        print(f"   K={k}: Inertia = {kmeans.inertia_:.2f}")
    
    # Plot
    plt.figure(figsize=(10, 6))
    plt.plot(K_range, inertias, 'bo-', linewidth=2, markersize=8)
    plt.xlabel('Number of Clusters (K)', fontsize=12, fontweight='bold')
    plt.ylabel('Inertia (Within-Cluster Sum of Squares)', fontsize=12, fontweight='bold')
    plt.title('Elbow Method untuk Optimal K', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.xticks(K_range)
    
    # Highlight K=3
    plt.axvline(x=3, color='r', linestyle='--', alpha=0.5, label='K=3 (Current)')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('elbow_method.png', dpi=300, bbox_inches='tight')
    print("✅ Elbow plot saved: elbow_method.png")
    plt.show()

# ========================================
# SILHOUETTE ANALYSIS
# ========================================
def plot_silhouette_analysis(X_scaled, max_k=10):
    """
    Plot Silhouette Score untuk berbagai nilai K
    
    Silhouette Score:
    - Range: -1 to 1
    - Nilai tinggi (mendekati 1) = cluster well-separated
    - Nilai rendah (mendekati 0) = cluster overlapping
    - Nilai negatif = data mungkin di cluster yang salah
    """
    print("\n📊 Calculating Silhouette Scores...")
    
    silhouette_scores = []
    K_range = range(2, max_k + 1)
    
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        silhouette_scores.append(score)
        print(f"   K={k}: Silhouette Score = {score:.4f}")
    
    # Plot
    plt.figure(figsize=(10, 6))
    plt.plot(K_range, silhouette_scores, 'go-', linewidth=2, markersize=8)
    plt.xlabel('Number of Clusters (K)', fontsize=12, fontweight='bold')
    plt.ylabel('Silhouette Score', fontsize=12, fontweight='bold')
    plt.title('Silhouette Score Analysis', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.xticks(K_range)
    
    # Highlight K=3
    plt.axvline(x=3, color='r', linestyle='--', alpha=0.5, label='K=3 (Current)')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('silhouette_analysis.png', dpi=300, bbox_inches='tight')
    print("✅ Silhouette plot saved: silhouette_analysis.png")
    plt.show()
    
    return silhouette_scores

# ========================================
# CLUSTERING METRICS
# ========================================
def evaluate_clustering_metrics(X_scaled, n_clusters=3):
    """
    Evaluasi berbagai metrik clustering untuk K=3
    
    Metrics:
    1. Silhouette Score: Mengukur seberapa mirip objek dengan cluster-nya sendiri
    2. Davies-Bouldin Index: Mengukur rata-rata similarity antar cluster (lower is better)
    3. Calinski-Harabasz Score: Ratio of between-cluster to within-cluster variance (higher is better)
    """
    print(f"\n🔬 Evaluating Clustering Metrics for K={n_clusters}...")
    
    # Fit K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    
    # Calculate metrics
    silhouette = silhouette_score(X_scaled, labels)
    davies_bouldin = davies_bouldin_score(X_scaled, labels)
    calinski_harabasz = calinski_harabasz_score(X_scaled, labels)
    inertia = kmeans.inertia_
    
    print("\n" + "=" * 70)
    print("📊 CLUSTERING QUALITY METRICS")
    print("=" * 70)
    
    print(f"\n1️⃣  Silhouette Score: {silhouette:.4f}")
    print("    Range: -1 to 1 (higher is better)")
    if silhouette > 0.5:
        print("    ✅ EXCELLENT - Clusters are well-separated")
    elif silhouette > 0.3:
        print("    ✅ GOOD - Reasonable cluster structure")
    elif silhouette > 0.1:
        print("    ⚠️  FAIR - Weak cluster structure")
    else:
        print("    ❌ POOR - Clusters are overlapping")
    
    print(f"\n2️⃣  Davies-Bouldin Index: {davies_bouldin:.4f}")
    print("    Range: 0 to ∞ (lower is better)")
    if davies_bouldin < 0.5:
        print("    ✅ EXCELLENT - Clusters are compact and well-separated")
    elif davies_bouldin < 1.0:
        print("    ✅ GOOD - Acceptable cluster separation")
    elif davies_bouldin < 2.0:
        print("    ⚠️  FAIR - Moderate cluster overlap")
    else:
        print("    ❌ POOR - High cluster overlap")
    
    print(f"\n3️⃣  Calinski-Harabasz Score: {calinski_harabasz:.2f}")
    print("    Range: 0 to ∞ (higher is better)")
    if calinski_harabasz > 300:
        print("    ✅ EXCELLENT - Strong cluster definition")
    elif calinski_harabasz > 100:
        print("    ✅ GOOD - Clear cluster structure")
    elif calinski_harabasz > 50:
        print("    ⚠️  FAIR - Weak cluster definition")
    else:
        print("    ❌ POOR - Very weak clusters")
    
    print(f"\n4️⃣  Inertia (WCSS): {inertia:.2f}")
    print("    Within-Cluster Sum of Squares")
    print("    Lower values indicate tighter clusters")
    
    print("\n" + "=" * 70)
    
    # Overall assessment
    print("\n🎯 OVERALL ASSESSMENT:")
    
    good_metrics = 0
    if silhouette > 0.3:
        good_metrics += 1
    if davies_bouldin < 1.0:
        good_metrics += 1
    if calinski_harabasz > 100:
        good_metrics += 1
    
    if good_metrics >= 3:
        print("   ✅ Model berkualitas BAIK untuk klasifikasi kualitas udara")
    elif good_metrics >= 2:
        print("   ✅ Model berkualitas CUKUP, masih dapat digunakan")
    else:
        print("   ⚠️  Model perlu improvement, pertimbangkan:")
        print("      - Menambah jumlah data training")
        print("      - Feature engineering (normalisasi berbeda)")
        print("      - Mencoba algoritma clustering lain")
    
    print("=" * 70)
    
    return {
        'silhouette': silhouette,
        'davies_bouldin': davies_bouldin,
        'calinski_harabasz': calinski_harabasz,
        'inertia': inertia
    }

# ========================================
# CLUSTER DISTRIBUTION
# ========================================
def analyze_cluster_distribution(X, X_scaled, n_clusters=3):
    """
    Analisis distribusi data di setiap cluster
    """
    print("\n📊 Analyzing Cluster Distribution...")
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    
    # Create DataFrame
    df = pd.DataFrame(X, columns=FEATURES)
    df['cluster'] = labels
    
    print("\n" + "=" * 70)
    print("CLUSTER STATISTICS")
    print("=" * 70)
    
    for i in range(n_clusters):
        cluster_data = df[df['cluster'] == i]
        count = len(cluster_data)
        percentage = (count / len(df)) * 100
        
        print(f"\n🔹 Cluster {i} ({count} data, {percentage:.1f}%):")
        print("-" * 70)
        
        stats = cluster_data[FEATURES].describe().loc[['mean', 'std']]
        print(stats.round(2).to_string())
    
    print("\n" + "=" * 70)
    
    return df

# ========================================
# COMPARE DIFFERENT K VALUES
# ========================================
def compare_k_values(X_scaled, k_values=[2, 3, 4, 5]):
    """
    Bandingkan performa untuk berbagai nilai K
    """
    print("\n📊 Comparing Different K Values...")
    print("=" * 70)
    
    results = []
    
    for k in k_values:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        silhouette = silhouette_score(X_scaled, labels)
        davies_bouldin = davies_bouldin_score(X_scaled, labels)
        calinski_harabasz = calinski_harabasz_score(X_scaled, labels)
        inertia = kmeans.inertia_
        
        results.append({
            'K': k,
            'Silhouette': silhouette,
            'Davies-Bouldin': davies_bouldin,
            'Calinski-Harabasz': calinski_harabasz,
            'Inertia': inertia
        })
        
        print(f"\nK = {k}:")
        print(f"  Silhouette: {silhouette:.4f}")
        print(f"  Davies-Bouldin: {davies_bouldin:.4f}")
        print(f"  Calinski-Harabasz: {calinski_harabasz:.2f}")
        print(f"  Inertia: {inertia:.2f}")
    
    print("\n" + "=" * 70)
    
    # Convert to DataFrame for easy viewing
    df_results = pd.DataFrame(results)
    print("\n📋 COMPARISON TABLE:")
    print(df_results.to_string(index=False))
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    best_silhouette = df_results.loc[df_results['Silhouette'].idxmax(), 'K']
    best_davies = df_results.loc[df_results['Davies-Bouldin'].idxmin(), 'K']
    best_calinski = df_results.loc[df_results['Calinski-Harabasz'].idxmax(), 'K']
    
    print(f"  Best Silhouette Score: K = {best_silhouette}")
    print(f"  Best Davies-Bouldin: K = {best_davies}")
    print(f"  Best Calinski-Harabasz: K = {best_calinski}")
    
    # Most common recommendation
    recommendations = [best_silhouette, best_davies, best_calinski]
    most_common_k = max(set(recommendations), key=recommendations.count)
    
    if most_common_k == 3:
        print(f"\n  ✅ K=3 is OPTIMAL for this dataset")
    else:
        print(f"\n  ⚠️  Consider using K={most_common_k} for better results")
    
    return df_results

# ========================================
# MAIN EVALUATION FUNCTION
# ========================================
def run_full_evaluation():
    """
    Menjalankan evaluasi lengkap model clustering
    """
    print("=" * 70)
    print("🔬 K-MEANS CLUSTERING MODEL EVALUATION")
    print("=" * 70)
    
    # Initialize Firebase
    init_firebase()
    
    # Fetch and prepare data
    print("\n📥 Fetching data from Firebase...")
    X, X_scaled = fetch_and_prepare_data()
    
    if X is None:
        print("❌ No data available for evaluation")
        return
    
    print(f"✅ Loaded {len(X)} data points")
    print(f"📊 Features: {', '.join(FEATURES)}")
    
    # 1. Elbow Method
    plot_elbow_method(X_scaled, max_k=8)
    
    # 2. Silhouette Analysis
    plot_silhouette_analysis(X_scaled, max_k=8)
    
    # 3. Evaluate K=3
    metrics = evaluate_clustering_metrics(X_scaled, n_clusters=3)
    
    # 4. Cluster Distribution
    df = analyze_cluster_distribution(X, X_scaled, n_clusters=3)
    
    # 5. Compare different K values
    comparison = compare_k_values(X_scaled, k_values=[2, 3, 4, 5, 6])
    
    print("\n" + "=" * 70)
    print("✅ EVALUATION COMPLETED")
    print("=" * 70)
    print("\n📁 Generated files:")
    print("   - elbow_method.png")
    print("   - silhouette_analysis.png")
    print("\n💡 Use these metrics to validate your K=3 choice or adjust if needed")
    print("=" * 70)

# ========================================
# MAIN
# ========================================
if __name__ == "__main__":
    run_full_evaluation()