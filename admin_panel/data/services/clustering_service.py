import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

def run_user_clustering(conn, output_path='clustering_subplots.png'):
    """
    Pobiera aktywnych użytkowników, uruchamia algorytm klastrowania K-Means,
    aktualizuje bazę danych oraz generuje czytelną siatkę wykresów 2x2 z legendą.
    """
    try:
        # Pobranie danych aktywnych użytkowników z bazy
        query = """
            SELECT id, username, books_read, pages_per_day, current_streak
            FROM users
            WHERE status = 'active'
        """
        df = pd.read_sql(query, con=conn)

        if df.empty or len(df) < 4:
            return {
                "success": False,
                "message": "Too few active users in the database for clustering (min. 4 required)."
            }

        # Wybór cech (features) oraz ich standaryzacja
        features = df[['books_read', 'pages_per_day', 'current_streak']].fillna(0)
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)

        # Uruchomienie algorytmu K-Means (podział na 4 klastry)
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(scaled_features)

        # Zapisanie przypisanych grup (klastrów) z powrotem do bazy danych
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute(
                "UPDATE users SET cluster_group = ? WHERE id = ?",
                (int(row['cluster']), int(row['id']))
            )
        conn.commit()

        # Generowanie profesjonalnej siatki wykresów 2x2
        fig, axes = plt.subplots(2, 2, figsize=(14, 7), sharex=True, sharey=True)
        axes = axes.flatten()

        cluster_labels = {
            0: 'Cluster 0: Casual Readers',
            1: 'Cluster 1: Regular Readers',
            2: 'Cluster 2: Engaged Readers',
            3: 'Cluster 3: Power Users'
        }

        # Paleta kolorów spójna z motywem aplikacji
        colors = ['#3d312f', '#6B2F2F', '#2c3e50', '#d4a34d']

        for i in range(4):
            ax = axes[i]
            # Tło: wszyscy użytkownicy na szaro w celach kontekstowych
            ax.scatter(df['books_read'], df['pages_per_day'], c='lightgray', alpha=0.35, s=25, label='Others')

            # Pierwszy plan: wyodrębniony docelowy klaster
            subset = df[df['cluster'] == i]
            ax.scatter(
                subset['books_read'],
                subset['pages_per_day'],
                c=colors[i],
                alpha=0.95,
                s=45,
                edgecolors='white',
                linewidths=0.5,
                label=f'Group {i} ({len(subset)} users)'
            )

            ax.set_title(cluster_labels.get(i, f'Cluster {i}'), fontsize=10, fontweight='bold', pad=8)
            ax.set_xlabel('Books Read', fontsize=9)
            ax.set_ylabel('Pages / Day', fontsize=9)
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.legend(loc='upper right', fontsize=8, framealpha=0.9)

        plt.suptitle('Booktrack User Behavioral Segmentation (K-Means)', fontsize=13, fontweight='bold', y=0.96)
        plt.subplots_adjust(left=0.06, right=0.97, top=0.88, bottom=0.09, hspace=0.25, wspace=0.15)

        plt.savefig(output_path, dpi=250)
        plt.close()

        # Zwrócenie podsumowania statystyk do widoku
        cluster_counts = df['cluster'].value_counts().to_dict()
        return {
            "success": True,
            "total_users": len(df),
            "counts": cluster_counts,
            "output_path": output_path
        }

    except Exception as e:
        return {"success": False, "message": str(e)}