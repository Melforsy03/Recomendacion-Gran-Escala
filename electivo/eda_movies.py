#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDA de electivo/movies.json

Salidas:
- Consola: resumen general (nº de registros, nulos, duplicados, estadísticas)
- Carpeta outputs/eda/: gráficos PNG y CSV con métricas básicas y hallazgos
"""
import os
import json
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Configuración estética
sns.set(style="whitegrid", context="talk")
plt.rcParams.update({"figure.dpi": 120, "savefig.bbox": "tight"})

DATA_PATH = os.path.join(os.path.dirname(__file__), "movies.json")
# Guardar resultados en la carpeta outputs/eda del proyecto (raíz)
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "eda")
os.makedirs(OUT_DIR, exist_ok=True)


def load_data(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    return df


def basic_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = {
        "n_registros": len(df),
        "columnas": list(df.columns),
        "n_duplicados_ID": int(df.duplicated(subset=["ID"]).sum()) if "ID" in df.columns else None,
        "n_duplicados_name": int(df.duplicated(subset=["name"]).sum()) if "name" in df.columns else None,
    }
    # Nulos por columna
    na_counts = df.isna().sum().to_dict()
    summary["nulos_por_columna"] = na_counts

    # Guardar a CSV legible
    summary_rows = []
    for k, v in summary.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                summary_rows.append({"metric": f"{k}.{kk}", "value": vv})
        elif isinstance(v, list):
            summary_rows.append({"metric": k, "value": ", ".join(map(str, v))})
        else:
            summary_rows.append({"metric": k, "value": v})

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(os.path.join(OUT_DIR, "resumen_basico.csv"), index=False)
    return summary_df


def save_duplicates(df: pd.DataFrame) -> None:
    """Guardar duplicados por ID y por name si existen."""
    if "ID" in df.columns:
        dups_id = df[df.duplicated(subset=["ID"], keep=False)].sort_values("ID")
        if not dups_id.empty:
            dups_id.to_csv(os.path.join(OUT_DIR, "duplicados_por_ID.csv"), index=False)
    if "name" in df.columns:
        dups_name = df[df.duplicated(subset=["name"], keep=False)].sort_values("name")
        if not dups_name.empty:
            dups_name.to_csv(os.path.join(OUT_DIR, "duplicados_por_name.csv"), index=False)


def numeric_stats(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["puan", "pop"] if c in df.columns]
    if not cols:
        return pd.DataFrame()
    stats = df[cols].describe().T
    stats["missing"] = df[cols].isna().sum()
    stats.to_csv(os.path.join(OUT_DIR, "estadisticas_numericas.csv"))
    return stats


def description_features(df: pd.DataFrame) -> pd.DataFrame:
    if "description" not in df.columns:
        return pd.DataFrame()
    desc_len = df["description"].fillna("").astype(str).str.len()
    word_count = df["description"].fillna("").astype(str).str.split().apply(len)

    feat = pd.DataFrame({
        "desc_len": desc_len,
        "word_count": word_count,
    })
    feat.to_csv(os.path.join(OUT_DIR, "descripcion_features.csv"), index=False)
    return feat


def genre_counts(df: pd.DataFrame) -> pd.DataFrame:
    gcols = [c for c in ["genre_1", "genre_2"] if c in df.columns]
    if not gcols:
        return pd.DataFrame()
    all_genres = []
    for c in gcols:
        all_genres.extend(df[c].dropna().astype(str).tolist())
    cnt = Counter(all_genres)
    gc = pd.DataFrame(cnt.items(), columns=["genre", "count"]).sort_values("count", ascending=False)
    gc.to_csv(os.path.join(OUT_DIR, "generos_conteo.csv"), index=False)
    return gc


def plot_hist(df: pd.DataFrame, col: str, title: str, bins: int = 30):
    if col not in df.columns:
        return
    plt.figure(figsize=(8, 5))
    sns.histplot(df[col].dropna(), bins=bins, kde=True, color="#2B7A78")
    plt.title(title)
    plt.xlabel(col)
    plt.ylabel("Frecuencia")
    plt.savefig(os.path.join(OUT_DIR, f"hist_{col}.png"))
    plt.close()


def plot_bar(df: pd.DataFrame, x: str, y: str, title: str, top: int = 15):
    if x not in df.columns or y not in df.columns:
        return
    data = df.nlargest(top, y)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=data, x=y, y=x, palette="viridis")
    plt.title(title)
    plt.xlabel(y)
    plt.ylabel(x)
    plt.savefig(os.path.join(OUT_DIR, f"bar_{x}_{y}.png"))
    plt.close()


def plot_scatter(df: pd.DataFrame, x: str, y: str, title: str):
    if x not in df.columns or y not in df.columns:
        return
    plt.figure(figsize=(7, 5))
    sns.scatterplot(data=df, x=x, y=y, alpha=0.6)
    plt.title(title)
    plt.savefig(os.path.join(OUT_DIR, f"scatter_{x}_{y}.png"))
    plt.close()


def detect_outliers_iqr(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Detectar outliers por IQR y guardar boxplots por columna."""
    found = []
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col].dropna().astype(float)
        if s.empty:
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (df[col] < low) | (df[col] > high)
        out = df.loc[mask, [c for c in ["ID", "name", col] if c in df.columns]].copy()
        out["columna"] = col
        if not out.empty:
            found.append(out)

        # Boxplot
        plt.figure(figsize=(6, 4))
        sns.boxplot(x=df[col], color="#4E79A7")
        plt.title(f"Boxplot {col}")
        plt.xlabel(col)
        plt.savefig(os.path.join(OUT_DIR, f"box_{col}.png"))
        plt.close()

    if found:
        outliers_df = pd.concat(found, ignore_index=True)
        outliers_df.to_csv(os.path.join(OUT_DIR, "outliers_iqr.csv"), index=False)
        return outliers_df
    return pd.DataFrame()


def correlation_heatmap(df: pd.DataFrame, extra_numeric: pd.DataFrame | None = None):
    """Matriz de correlación y heatmap para columnas numéricas disponibles."""
    numeric_cols = []
    for c in ["puan", "pop"]:
        if c in df.columns:
            numeric_cols.append(c)
    if extra_numeric is not None and not extra_numeric.empty:
        num_df = pd.concat([df[numeric_cols], extra_numeric], axis=1)
    else:
        num_df = df[numeric_cols].copy()
    if num_df.empty:
        return
    corr = num_df.corr(numeric_only=True)
    plt.figure(figsize=(6, 5))
    sns.heatmap(corr, annot=True, cmap="crest", fmt=".2f", square=True)
    plt.title("Matriz de correlación")
    plt.savefig(os.path.join(OUT_DIR, "correlacion_heatmap.png"))
    plt.close()


def avg_rating_by_genre(df: pd.DataFrame) -> pd.DataFrame:
    if "puan" not in df.columns:
        return pd.DataFrame()
    gcols = [c for c in ["genre_1", "genre_2"] if c in df.columns]
    if not gcols:
        return pd.DataFrame()
    # Unificar géneros en una sola columna (exploded)
    gdf = df[["puan"] + gcols].copy()
    gdf = gdf.melt(value_vars=gcols, id_vars=["puan"], value_name="genre").dropna(subset=["genre"]).drop(columns=["variable"]) 
    res = gdf.groupby("genre", as_index=False)["puan"].agg(["count", "mean"]).reset_index()
    res = res.rename(columns={"mean": "avg_puan"}).sort_values("avg_puan", ascending=False)
    res.to_csv(os.path.join(OUT_DIR, "avg_puan_por_genero.csv"), index=False)

    # Gráfico de barras top N
    top = res.nlargest(12, "avg_puan")
    plt.figure(figsize=(10, 6))
    sns.barplot(data=top, x="avg_puan", y="genre", palette="mako")
    plt.xlabel("Puntuación media (puan)")
    plt.ylabel("Género")
    plt.title("Top géneros por puntuación media")
    plt.savefig(os.path.join(OUT_DIR, "bar_top_generos_avg_puan.png"))
    plt.close()

    return res


def pca_exploration(num_df: pd.DataFrame):
    if num_df is None or num_df.empty:
        return
    X = num_df.fillna(num_df.median(numeric_only=True))
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    pca = PCA(n_components=min(4, Xs.shape[1]))
    comps = pca.fit_transform(Xs)

    # Varianza explicada
    exp_var = pca.explained_variance_ratio_
    pd.DataFrame({"component": [f"PC{i+1}" for i in range(len(exp_var))], "explained_variance": exp_var}) \
        .to_csv(os.path.join(OUT_DIR, "pca_explained_variance.csv"), index=False)
    plt.figure(figsize=(6, 4))
    sns.barplot(x=[f"PC{i+1}" for i in range(len(exp_var))], y=exp_var, color="#59A14F")
    plt.ylabel("Varianza explicada")
    plt.title("PCA - Varianza explicada")
    plt.savefig(os.path.join(OUT_DIR, "pca_varianza_explicada.png"))
    plt.close()

    # Scatter PC1 vs PC2
    if comps.shape[1] >= 2:
        plt.figure(figsize=(6, 5))
        plt.scatter(comps[:, 0], comps[:, 1], alpha=0.5)
        plt.xlabel("PC1")
        plt.ylabel("PC2")
        plt.title("PCA - PC1 vs PC2")
        plt.savefig(os.path.join(OUT_DIR, "pca_scatter_pc1_pc2.png"))
        plt.close()


def main():
    print("🔎 Cargando datos desde:", DATA_PATH)
    df = load_data(DATA_PATH)

    print(f"✅ Registros: {len(df)} | Columnas: {list(df.columns)}")

    # Resumen básico y nulos
    print("\n📋 Resumen básico y nulos por columna → outputs/eda/resumen_basico.csv")
    summary_df = basic_summary(df)
    print(summary_df)

    # Duplicados
    print("\n📑 Buscando duplicados por ID y por name → outputs/eda/duplicados_*.csv")
    save_duplicates(df)

    # Estadísticas numéricas
    print("\n📈 Estadísticas numéricas (puan, pop) → outputs/eda/estadisticas_numericas.csv")
    stats_df = numeric_stats(df)
    if not stats_df.empty:
        print(stats_df)

    # Features de descripción
    print("\n📝 Métricas de descripción → outputs/eda/descripcion_features.csv")
    desc_df = description_features(df)
    if not desc_df.empty:
        print(desc_df.describe().T)

    # Conteos de géneros
    print("\n🎭 Conteos de géneros → outputs/eda/generos_conteo.csv")
    gcounts = genre_counts(df)
    if not gcounts.empty:
        print(gcounts.head(10))

    # Gráficos
    print("\n🖼️ Generando gráficos en outputs/eda/")
    plot_hist(df, "puan", "Distribución de puntuación (puan)", bins=20)
    plot_hist(df, "pop", "Distribución de popularidad (pop)", bins=20)
    if not desc_df.empty:
        plot_hist(desc_df, "desc_len", "Distribución longitud de descripción", bins=30)
        plot_hist(desc_df, "word_count", "Distribución palabras en descripción", bins=30)
    if not gcounts.empty:
        plot_bar(gcounts, x="genre", y="count", title="Top géneros (apariciones)", top=15)

    # Relación simple puan vs pop
    if all(c in df.columns for c in ["puan", "pop"]):
        corr = df[["puan", "pop"]].corr().iloc[0, 1]
        print(f"\n🔗 Correlación puan-pop: {corr:.3f}")
        plot_scatter(df, "pop", "puan", "Relación popularidad vs. puntuación")

    # Outliers por IQR
    print("\n🚩 Detectando outliers (IQR) en puan y pop → outputs/eda/outliers_iqr.csv")
    detect_outliers_iqr(df, [c for c in ["puan", "pop"] if c in df.columns])

    # Correlación y heatmap con features de descripción
    print("\n🌡️ Matriz de correlación + heatmap → outputs/eda/correlacion_heatmap.png")
    corr_extra = desc_df[["desc_len", "word_count"]] if not desc_df.empty else None
    correlation_heatmap(df, corr_extra)

    # Medias por género y gráfico
    print("\n🎚️ Puntuación media por género → outputs/eda/avg_puan_por_genero.csv")
    avg_rating_by_genre(df)

    # PCA exploratorio con numéricas disponibles
    print("\n🧭 PCA exploratorio → outputs/eda/pca_*.png / .csv")
    num_for_pca = []
    for c in ["puan", "pop"]:
        if c in df.columns:
            num_for_pca.append(c)
    if not desc_df.empty:
        num_for_pca.extend(["desc_len", "word_count"])
        num_df = pd.concat([df[[c for c in ["puan", "pop"] if c in df.columns]].reset_index(drop=True),
                            desc_df[["desc_len", "word_count"]].reset_index(drop=True)], axis=1)
    else:
        num_df = df[[c for c in ["puan", "pop"] if c in df.columns]].copy()
    pca_exploration(num_df)

    # Guardar dataset de features útil para modelos posteriores
    features_out = os.path.join(OUT_DIR, "eda_features.csv")
    export_df = df.copy()
    if not desc_df.empty:
        export_df = pd.concat([export_df.reset_index(drop=True), desc_df.reset_index(drop=True)], axis=1)
    export_cols = [c for c in ["ID", "name", "puan", "pop", "genre_1", "genre_2", "desc_len", "word_count", "description"] if c in export_df.columns]
    export_df[export_cols].to_csv(features_out, index=False)
    print("\n💾 Dataset de features guardado en:", features_out)

    print(f"\n✅ EDA completado. Archivos en: {OUT_DIR}")


if __name__ == "__main__":
    main()
