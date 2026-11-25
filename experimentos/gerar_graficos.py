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


Z_LIMITE = 2.0       # diferenca maior que 2 erros-padrao => estatisticamente real (~95%)
EFEITO_MIN = 0.05    # e maior que 5% => relevante na pratica (evita marcar diferencas minimas)


def cruzamentos(resumo):
    """Compara spinlock x mutex em cada N.

    Regime por N: S = spinlock melhor, M = mutex melhor, = empate (diferenca das
    medias menor que 2 erros-padrao ou menor que 5%: indistinguivel do ruido).
    Inversao = troca de regime entre dois pontos com diferenca significativa;
    o ponto de cruzamento e interpolado (escala log2 de N) entre esses dois pontos.
    """
    linhas, info = [], {}
    for pl in sorted(resumo.plataforma.unique()):
        for sec in SECOES:
            sel = resumo[(resumo.plataforma == pl) & (resumo.secao == sec)]
            m = sel[sel.primitiva == "mutex"].set_index("threads")
            s = sel[sel.primitiva == "spinlock"].set_index("threads")
            ns = sorted(set(m.index) & set(s.index))
            razao, regime = [], []
            for n in ns:
                dif = s.loc[n, "vazao_media"] - m.loc[n, "vazao_media"]
                ep = np.sqrt(s.loc[n, "vazao_dp"] ** 2 / s.loc[n, "n"]
                             + m.loc[n, "vazao_dp"] ** 2 / m.loc[n, "n"])
                z = dif / ep if ep > 0 else 0.0
                razao.append(float(s.loc[n, "vazao_media"] / m.loc[n, "vazao_media"]))
                rel = razao[-1] - 1.0
                regime.append("S" if z > Z_LIMITE and rel > EFEITO_MIN
                              else "M" if z < -Z_LIMITE and rel < -EFEITO_MIN else "=")
            sig = [k for k, g in enumerate(regime) if g != "="]
            cruz, trechos = [], []
            for a, b in zip(sig, sig[1:]):
                if regime[a] != regime[b]:
                    xa, xb = np.log2(ns[a]), np.log2(ns[b])
                    ya, yb = razao[a] - 1.0, razao[b] - 1.0
                    t = ya / (ya - yb)
                    cruz.append(2 ** (xa + t * (xb - xa)))
                    trechos.append(f"{ns[a]}-{ns[b]}")
            perde = next((ns[k] for k in range(len(ns))
                          if regime[k] == "M" and "S" not in regime[k:]), None)
            info[(pl, sec)] = (ns, razao, regime, cruz)
            linhas.append({"plataforma": pl, "secao": sec,
                           "regime_por_N": " ".join(f"{n}:{g}" for n, g in zip(ns, regime)),
                           "inversao_entre_N": ";".join(trechos) or "nenhuma",
                           "cruzamento_threads": ";".join(f"{c:.2f}" for c in cruz) or "nenhum",
                           "spinlock_perde_a_partir_de_N": perde if perde else "nunca",
                           "razao_1thread": round(razao[0], 3),
                           "razao_16threads": round(razao[-1], 3)})
    return pd.DataFrame(linhas), info


def grafico_cruzamento(info):
    plats = sorted({pl for pl, _ in info})
    fig, axs = plt.subplots(1, len(plats), figsize=(7 * len(plats), 5), squeeze=False)
    cores = {"curta": "tab:green", "media": "tab:orange", "longa": "tab:purple"}
    for i, pl in enumerate(plats):
        ax = axs[0][i]
        for sec in SECOES:
            ns, razao, regime, cruz = info[(pl, sec)]
            ax.plot(ns, razao, marker="o", label=f"secao {sec}", color=cores[sec])
            for n, r, g in zip(ns, razao, regime):
                if g == "=":
                    ax.plot(n, r, "o", markersize=9, markerfacecolor="white",
                            markeredgecolor=cores[sec])
            for c in cruz:
                ax.plot(c, 1.0, "k*", markersize=15)
        ax.axhline(1.0, color="gray", linestyle="--")
        ax.set_yscale("log")
        ax.set_title(f"{pl}: vazao spinlock / vazao mutex")
        ax.set_ylabel("razao (>1: spinlock melhor)")
        eixo_threads(ax)
        ax.legend()
    fig.suptitle("estrela = inversao real | circulo vazado = sem diferenca significativa "
                 "(< 2 erros-padrao ou < 5%)")
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
    tab, info = cruzamentos(resumo)
    tab.to_csv(SAIDA / "cruzamentos.csv", index=False)
    grafico_cruzamento(info)
    print("\nInversoes spinlock x mutex (S=spinlock melhor, M=mutex melhor, ==empate):")
    print(tab.to_string(index=False))
    print("\nArquivos gerados em", SAIDA)


if __name__ == "__main__":
    main()