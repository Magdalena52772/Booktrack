import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, HDBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def run_user_clustering(
    conn,
    output_path="clustering_subplots.png",
    comparison_path="clustering_comparison.png",
):
    """
    Uruchamia K-Means, aktualizuje bazę danych i generuje główny wykres 2x2
    wyświetlany w widoku aplikacji. Dodatkowo zapisuje 2-rzędowy raport wizualny PNG
    (góra: rozrzut z centroidami, dół: słupki metryk i pokrycia bazy) do pracy dyplomowej.
    """
    try:
        query = """
            SELECT id, username, books_read, pages_per_day, current_streak
            FROM users
            WHERE status = 'active'
        """
        df = pd.read_sql(query, con=conn)

        if df.empty or len(df) < 4:
            return {
                "success": False,
                "message": "Too few active users in the database for clustering (min. 4 required).",
            }

        features = df[["books_read", "pages_per_day", "current_streak"]].fillna(0)
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)

        # Główny algorytm K-Means (4 klastry) do widoku i bazy danych
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        df["cluster"] = kmeans.fit_predict(scaled_features)
        kmeans_silhouette = silhouette_score(scaled_features, df["cluster"])

        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute(
                "UPDATE users SET cluster_group = ? WHERE id = ?",
                (int(row["cluster"]), int(row["id"])),
            )
        conn.commit()

        # =====================================================================
        # Wykres K-Means 2x2 wyświetlany w aplikacji
        # =====================================================================
        fig, axes = plt.subplots(2, 2, figsize=(14, 7), sharex=True, sharey=True)
        axes = axes.flatten()

        cluster_labels = {
            0: "Cluster 0: Casual Readers",
            1: "Cluster 1: Regular Readers",
            2: "Cluster 2: Engaged Readers",
            3: "Cluster 3: Power Users",
        }
        colors = ["#3d312f", "#6B2F2F", "#2c3e50", "#d4a34d"]

        for i in range(4):
            ax = axes[i]
            ax.scatter(
                df["books_read"],
                df["pages_per_day"],
                c="lightgray",
                alpha=0.35,
                s=25,
                label="Others",
            )
            subset = df[df["cluster"] == i]
            ax.scatter(
                subset["books_read"],
                subset["pages_per_day"],
                c=colors[i],
                alpha=0.95,
                s=45,
                edgecolors="white",
                linewidths=0.5,
                label=f"Group {i} ({len(subset)} users)",
            )
            ax.set_title(
                cluster_labels.get(i, f"Cluster {i}"),
                fontsize=10,
                fontweight="bold",
                pad=8,
            )
            ax.set_xlabel("Books Read", fontsize=9)
            ax.set_ylabel("Pages / Day", fontsize=9)
            ax.grid(True, linestyle="--", alpha=0.5)
            ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

        plt.suptitle(
            "Booktrack User Behavioral Segmentation (K-Means)",
            fontsize=13,
            fontweight="bold",
            y=0.96,
        )
        plt.subplots_adjust(
            left=0.06, right=0.97, top=0.88, bottom=0.09, hspace=0.25, wspace=0.15
        )
        plt.savefig(output_path, dpi=250)
        plt.close()

        # =====================================================================
        # Raport porównawczy 2-rzędowy (Góra: rozrzut, Dół: słupki),
        # porównanie K-Means vs HDBSCAN vs Random Sampling
        # =====================================================================
        rng = np.random.default_rng(seed=42)
        df["random_cluster"] = rng.integers(0, 4, size=len(df))
        random_silhouette = silhouette_score(scaled_features, df["random_cluster"])

        min_size = max(15, int(len(df) * 0.03))
        hdbscan = HDBSCAN(min_cluster_size=min_size, copy=True)
        df["hdbscan_cluster"] = hdbscan.fit_predict(scaled_features)

        non_noise_mask = df["hdbscan_cluster"] != -1
        unique_hdbscan = sorted(df.loc[non_noise_mask, "hdbscan_cluster"].unique())

        if len(unique_hdbscan) > 1:
            hdbscan_silhouette = silhouette_score(
                scaled_features[non_noise_mask],
                df.loc[non_noise_mask, "hdbscan_cluster"],
            )
        else:
            hdbscan_silhouette = 0.0

        noise_count = int((df["hdbscan_cluster"] == -1).sum())
        noise_ratio = round((noise_count / len(df)) * 100, 1)

        fig_comp = plt.figure(figsize=(16, 9.5))
        gs = fig_comp.add_gridspec(
            2, 3, height_ratios=[1.25, 1.0], hspace=0.38, wspace=0.16
        )

        palette = ["#2b2d42", "#9b2226", "#1d3557", "#d4a34d", "#2d6a4f", "#7f5539"]
        df["kmeans_alias"] = df["cluster"]

        top_panels = [
            ("1. Random Sampling (Punkt odniesienia)", "random_cluster"),
            ("2. K-Means (k = 4)", "kmeans_alias"),
            ("3. HDBSCAN (Klastrowanie gęstościowe)", "hdbscan_cluster"),
        ]

        top_axes = [fig_comp.add_subplot(gs[0, i]) for i in range(3)]
        for i in range(1, 3):
            top_axes[i].sharex(top_axes[0])
            top_axes[i].sharey(top_axes[0])

        for ax, (title, col_name) in zip(top_axes, top_panels):
            labels_in_col = sorted(df[col_name].unique())
            valid_clusters = [label for label in labels_in_col if label != -1]
            color_map = {
                lbl: palette[idx % len(palette)]
                for idx, lbl in enumerate(valid_clusters)
            }

            if -1 in labels_in_col:
                noise_sub = df[df[col_name] == -1]
                ax.scatter(
                    noise_sub["books_read"],
                    noise_sub["pages_per_day"],
                    c="#adb5bd",
                    marker="x",
                    s=24,
                    linewidths=1.0,
                    alpha=0.6,
                )

            for lbl in valid_clusters:
                subset = df[df[col_name] == lbl]
                ax.scatter(
                    subset["books_read"],
                    subset["pages_per_day"],
                    c=color_map[lbl],
                    marker="o",
                    s=20,
                    alpha=0.55,
                    edgecolors="none",
                )
                # Rysowanie wyraźnego centroidu (środka klastra)
                ax.scatter(
                    subset["books_read"].mean(),
                    subset["pages_per_day"].mean(),
                    c=color_map[lbl],
                    marker="D",
                    s=95,
                    edgecolors="white",
                    linewidths=1.5,
                    zorder=10,
                )

            legend_handles = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor=color_map[lbl],
                    markersize=6,
                    label=f"Klaster {lbl} ({(df[col_name] == lbl).sum()} os.)",
                )
                for lbl in valid_clusters[:5]
            ]
            if -1 in labels_in_col:
                legend_handles.append(
                    Line2D(
                        [0],
                        [0],
                        marker="x",
                        color="#8d99ae",
                        linestyle="None",
                        markersize=6,
                        markeredgewidth=1.3,
                        label=f"Szum ({noise_count} os.)",
                    )
                )
            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="D",
                    color="w",
                    markerfacecolor="#333333",
                    markersize=6,
                    label="Środek klastra (centroid)",
                )
            )

            ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
            ax.set_xlabel("Przeczytane książki", fontsize=9.5)
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.legend(
                handles=legend_handles, loc="upper right", fontsize=8, framealpha=0.94
            )

        top_axes[0].set_ylabel("Strony / dzień", fontsize=9.5)

        # Dolny panel: Porównanie metryk i pokrycia bazy użytkowników
        # Lewy dół: Porównanie Silhouette Score
        ax_sil = fig_comp.add_subplot(gs[1, 0])
        methods_names = [
            "Random\nSampling",
            "K-Means\n(k = 4)",
            "HDBSCAN\n(Gęstościowy)",
        ]
        sil_values = [random_silhouette, kmeans_silhouette, hdbscan_silhouette]
        bar_colors = ["#adb5bd", "#6B2F2F", "#2c3e50"]

        bars = ax_sil.bar(
            methods_names, sil_values, color=bar_colors, width=0.5, edgecolor="white"
        )
        ax_sil.axhline(0, color="black", linewidth=0.8)
        ax_sil.set_ylim(min(-0.1, min(sil_values) - 0.08), max(sil_values) + 0.12)
        ax_sil.set_title(
            "Jakość separacji (Silhouette Score)\n(wyżej = lepiej)",
            fontsize=10.5,
            fontweight="bold",
        )
        ax_sil.set_ylabel("Wartość współczynnika", fontsize=9.5)
        ax_sil.grid(axis="y", linestyle="--", alpha=0.4)

        for bar, val in zip(bars, sil_values):
            y_pos = val + 0.015 if val >= 0 else val - 0.035
            ax_sil.text(
                bar.get_x() + bar.get_width() / 2,
                y_pos,
                f"{val:.3f}",
                ha="center",
                va="bottom" if val >= 0 else "top",
                fontsize=9.5,
                fontweight="bold",
            )

        # Prawy dół (łączący 2 kolumny): Pokrycie bazy użytkowników vs Szum (%)
        ax_cov = fig_comp.add_subplot(gs[1, 1:])
        clustered_pct = [100.0, 100.0, round(100.0 - noise_ratio, 1)]
        noise_pct = [0.0, 0.0, noise_ratio]

        x = np.arange(len(methods_names))
        b1 = ax_cov.bar(
            x,
            clustered_pct,
            width=0.42,
            label="Przypisani do segmentów (%)",
            color="#3d312f",
        )
        b2 = ax_cov.bar(
            x,
            noise_pct,
            width=0.42,
            bottom=clustered_pct,
            label="Odrzuceni jako szum / anomalie (%)",
            color="#d4a34d",
        )

        ax_cov.set_xticks(x)
        ax_cov.set_xticklabels(
            ["Random Sampling", "K-Means (k = 4)", "HDBSCAN (Gęstościowy)"]
        )
        ax_cov.set_ylim(0, 115)
        ax_cov.set_title(
            "Pokrycie bazy aktywnych użytkowników vs Odsetek szumu (%)",
            fontsize=10.5,
            fontweight="bold",
        )
        ax_cov.set_ylabel("Udział bazy (%)", fontsize=9.5)
        ax_cov.grid(axis="y", linestyle="--", alpha=0.4)
        ax_cov.legend(loc="upper right", fontsize=8.5, framealpha=0.94)

        for i in range(len(x)):
            ax_cov.text(
                x[i],
                clustered_pct[i] / 2,
                f"{clustered_pct[i]:.1f}%",
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
                fontsize=9.5,
            )
            if noise_pct[i] > 0:
                ax_cov.text(
                    x[i],
                    clustered_pct[i] + noise_pct[i] / 2,
                    f"{noise_pct[i]:.1f}% szumu",
                    ha="center",
                    va="center",
                    color="#222222",
                    fontweight="bold",
                    fontsize=9,
                )

        plt.suptitle(
            "Ewaluacja metod segmentacji behawioralnej użytkowników (Booktrack)",
            fontsize=13.5,
            fontweight="bold",
            y=0.97,
        )
        plt.subplots_adjust(left=0.06, right=0.97, top=0.90, bottom=0.07)
        plt.savefig(comparison_path, dpi=300)
        plt.close()

        cluster_counts = df["cluster"].value_counts().to_dict()
        return {
            "success": True,
            "total_users": len(df),
            "counts": cluster_counts,
            "output_path": output_path,
        }

    except Exception as e:
        return {"success": False, "message": str(e)}
