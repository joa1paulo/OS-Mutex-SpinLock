#!/usr/bin/env python3
"""Le os CSVs brutos em dados/ e gera resumo (media/desvio) e graficos.

Uso (a partir da raiz do repositorio):
    python experimentos/gerar_graficos.py

Dependencias: pip install pandas matplotlib
Saidas em experimentos/: resumo.csv, cruzamentos.csv, grafico1_vazao.png,
grafico2_cruzamento.png, grafico3_tempo.png
Os CSVs brutos so sao lidos, nunca alterados.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "dados"
SAIDA = BASE / "experimentos"
SECOES = ["curta", "media", "longa"]
PRIMS = ["mutex", "spinlock"]
THREADS = [1, 2, 4, 8, 16]
CORES = {"mutex": "tab:blue", "spinlock": "tab:red"}
CHAVES = ["plataforma", "primitiva", "secao", "threads"]
MIN_REP = 30


def carregar():
    arqs = sorted(DADOS.glob("*_raw.csv"))
    if not arqs:
        sys.exit("Nenhum *_raw.csv encontrado em dados/")
    print("Lendo:", ", ".join(a.name for a in arqs))
    return pd.concat([pd.read_csv(a) for a in arqs], ignore_index=True)


def validar(df):
    cont = df.groupby(CHAVES).size()
    print(f"{len(df)} linhas | plataformas: {sorted(df.plataforma.unique())} "
          f"| configuracoes: {len(cont)} (esperado 30 por plataforma)")
    if (cont < MIN_REP).any():
        print("AVISO: configuracoes com menos de 30 repeticoes:")
        print(cont[cont < MIN_REP].to_string())
    if (cont > MIN_REP).any():
        print("AVISO: configuracoes com MAIS de 30 repeticoes (dados de teste misturados?):")
        print(cont[cont > MIN_REP].to_string())
    if (df["contador_ok"] != 1).any():
        print("AVISO: ha repeticoes com contador_ok = 0 (condicao de corrida!)")


def resumir(df):
    r = (df.groupby(CHAVES)
           .agg(n=("repeticao", "count"),
                tempo_medio=("tempo_s", "mean"), tempo_dp=("tempo_s", "std"),
                vazao_media=("vazao_aps", "mean"), vazao_dp=("vazao_aps", "std"))
           .reset_index())
    r["secao"] = pd.Categorical(r["secao"], SECOES, ordered=True)
    r["primitiva"] = pd.Categorical(r["primitiva"], PRIMS, ordered=True)
    return r.sort_values(CHAVES).reset_index(drop=True)


def eixo_threads(ax):
    ax.set_xscale("log", base=2)
    ax.set_xticks(THREADS)
    ax.set_xticklabels([str(t) for t in THREADS])
    ax.minorticks_off()
    ax.set_xlabel("numero de threads")
    ax.grid(alpha=0.3)


def grade(resumo, col, dp, ylabel, titulo, arq):
    plats = sorted(resumo.plataforma.unique())
    fig, axs = plt.subplots(len(plats), 3, figsize=(14, 4 * len(plats)), squeeze=False)
    for i, pl in enumerate(plats):
        for j, sec in enumerate(SECOES):
            ax = axs[i][j]
            for p in PRIMS:
                d = resumo[(resumo.plataforma == pl) & (resumo.secao == sec)
                           & (resumo.primitiva == p)].sort_values("threads")
                ax.errorbar(d.threads, d[col], yerr=d[dp], marker="o", capsize=3,
                            label=p, color=CORES[p])
            ax.set_title(f"{pl} - secao {sec}")
            ax.set_ylabel(ylabel)
            eixo_threads(ax)
            ax.legend()
    fig.suptitle(titulo + " (media +/- desvio padrao, 30 repeticoes)")
    fig.tight_layout()
    fig.savefig(SAIDA / arq, dpi=150)
    plt.close(fig)


def cruzamentos(resumo):
    """Razao vazao(spinlock)/vazao(mutex) por nº de threads; cruzamento = razao passa por 1."""
    linhas, razoes = [], {}
    for pl in sorted(resumo.plataforma.unique()):
        for sec in SECOES:
            sel = resumo[(resumo.plataforma == pl) & (resumo.secao == sec)]
            m = sel[sel.primitiva == "mutex"].set_index("threads")["vazao_media"]
            s = sel[sel.primitiva == "spinlock"].set_index("threads")["vazao_media"]
            razao = (s / m).dropna().sort_index()
            razoes[(pl, sec)] = razao
            x = np.log2(razao.index.values.astype(float))
            y = razao.values - 1.0
            cruz = []
            for k in range(len(x) - 1):
                if y[k] * y[k + 1] < 0:
                    t = y[k] / (y[k] - y[k + 1])
                    cruz.append(2 ** (x[k] + t * (x[k + 1] - x[k])))
            linhas.append({"plataforma": pl, "secao": sec,
                           "cruzamento_threads": ";".join(f"{c:.2f}" for c in cruz) or "nenhum",
                           "razao_1thread": round(float(razao.get(1, np.nan)), 3),
                           "razao_16threads": round(float(razao.get(16, np.nan)), 3)})
    return pd.DataFrame(linhas), razoes


def grafico_cruzamento(razoes):
    plats = sorted({pl for pl, _ in razoes})
    fig, axs = plt.subplots(1, len(plats), figsize=(7 * len(plats), 4.5), squeeze=False)
    cores = {"curta": "tab:green", "media": "tab:orange", "longa": "tab:purple"}
    for i, pl in enumerate(plats):
        ax = axs[0][i]
        for sec in SECOES:
            r = razoes[(pl, sec)]
            ax.plot(r.index, r.values, marker="o", label=f"secao {sec}", color=cores[sec])
            x = np.log2(r.index.values.astype(float)); y = r.values - 1.0
            for k in range(len(x) - 1):
                if y[k] * y[k + 1] < 0:
                    t = y[k] / (y[k] - y[k + 1])
                    ax.plot(2 ** (x[k] + t * (x[k + 1] - x[k])), 1.0, "k*", markersize=14)
        ax.axhline(1.0, color="gray", linestyle="--")
        ax.set_yscale("log")
        ax.set_title(f"{pl}: vazao spinlock / vazao mutex")
        ax.set_ylabel("razao (>1: spinlock melhor)")
        eixo_threads(ax)
        ax.legend()
    fig.tight_layout()
    fig.savefig(SAIDA / "grafico2_cruzamento.png", dpi=150)
    plt.close(fig)


def main():
    df = carregar()
    validar(df)
    resumo = resumir(df)
    resumo.to_csv(SAIDA / "resumo.csv", index=False)
    grade(resumo, "vazao_media", "vazao_dp", "vazao (aquisicoes/s)",
          "Vazao x numero de threads", "grafico1_vazao.png")
    grade(resumo, "tempo_medio", "tempo_dp", "tempo total (s)",
          "Tempo total x numero de threads", "grafico3_tempo.png")
    tab, razoes = cruzamentos(resumo)
    tab.to_csv(SAIDA / "cruzamentos.csv", index=False)
    grafico_cruzamento(razoes)
    print("\nCruzamentos (estrela = razao passa por 1):")
    print(tab.to_string(index=False))
    print("\nArquivos gerados em", SAIDA)


if __name__ == "__main__":
    main()