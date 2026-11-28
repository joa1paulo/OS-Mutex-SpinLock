# Mutex e Spinlock: avaliação comparativa entre Linux e Windows

Projeto de **GBC045 – Sistemas Operacionais** (UFU / FACOM, 2026/2): *Threads, Sincronização e Avaliação Multiplataforma*, **Tema 1 – Mutex e Spinlock**.

## Integrantes

| Nome | Matrícula |
|---|---|
| João Paulo Duarte Ramos | 12511BCC009 |
| Yasmin Alves | 12411BSI355 |
| Leticia Souza Lopes | 12511BCC015 |

Repositório: https://github.com/joa1paulo/OS-Mutex-SpinLock

## O que foi feito

- **Camada de abstração de threads** (`code/platform_thread.h/.c`): API única (`pt_thread_*`, `pt_mutex_*`, `pt_spinlock_*`) traduzida para pthreads no Linux e para a API Win32 nativa no Windows (`CreateThread`, `CRITICAL_SECTION`, sem winpthreads). No Windows o spinlock é próprio (test-and-test-and-set com `InterlockedExchange` e `YieldProcessor`), pois a Win32 não oferece spinlock em modo usuário.
- **Programa de teste** (`testes/test_correctness.c`): N threads incrementam um contador compartilhado protegido por cada primitiva; confere o valor final.
- **Benchmark** (`experimentos/benchmark.c`): N threads executam, juntas, um total fixo de aquisições do lock; mede tempo total e vazão.
- **Análise** (`experimentos/gerar_graficos.py`): média, desvio padrão, gráficos e pontos de inversão spinlock × mutex.

### Experimento

| Variável | Valores |
|---|---|
| Número de threads | 1, 2, 4, 8, 16 |
| Duração da seção crítica | curta (só incrementar o contador), média (≈ 1 µs), longa (≈ 100 µs) |
| Primitiva | mutex, spinlock |
| Repetições | 30 por configuração, em cada plataforma |
| Total de aquisições | 1.000.000 (curta), 200.000 (média), 2.000 (longa), dividido entre as N threads |

## Estrutura do repositório

```
README.md
video/            vídeo de apresentação (ou link, ver abaixo)
code/             platform_thread.h, platform_thread.c
build/            executáveis gerados na compilação (vazia no repositório, ver build/README.md)
testes/           test_correctness.c
dados/            CSVs brutos (linux_raw.csv, windows_raw.csv) e hash do código usado
experimentos/     benchmark.c, gerar_graficos.py, resumo.csv, cruzamentos.csv, gráficos (PNG)
```

## Ambiente das coletas

- Intel Core i5-7400 (4 núcleos, 4 threads lógicas, 3,00 GHz base), uma única máquina.
- Ubuntu (Linux) e Windows em **dual boot**, ambos nativos (sem VM, WSL2 ou Cygwin).
- Linux: `gcc -std=c11 -O3 -pthread`. Windows: MinGW-w64 (GCC 16.1.0, MSYS2 UCRT64), `gcc -std=c11 -O3`, somente Win32 API.
- **Commit usado nas duas coletas: `4389bf1`** (registrado em `dados/hash_linux.txt` e `dados/hash_windows.txt`).

## Como reproduzir

### Requisitos

- **Compilador C11 com suporte à API Win32 moderna**
  - Linux: GCC (pacote `build-essential`).
  - Windows: **MinGW-w64** recente (recomendado: MSYS2 UCRT64, `pacman -S mingw-w64-ucrt-x86_64-gcc`). O MinGW "clássico" (mingw.org, GCC 6.x) **não é suportado**.
- Python 3 com `pandas` e `matplotlib` (só para os gráficos).

Todos os comandos são executados na **raiz do repositório**.

```
git clone https://github.com/joa1paulo/OS-Mutex-SpinLock.git
cd OS-Mutex-SpinLock
```

> A pasta `build/` já vem no repositório (o `gcc` não a cria sozinho; veja `build/README.md`).

### 1. Linux

```bash
# teste de correção
gcc -std=c11 -O3 -pthread testes/test_correctness.c code/platform_thread.c -o build/test_correctness
./build/test_correctness

# benchmark completo (30 repetições por configuração)
rm -f dados/linux_raw.csv
gcc -std=c11 -O3 -pthread experimentos/benchmark.c code/platform_thread.c -o build/benchmark
./build/benchmark --out dados/linux_raw.csv
```

### 2. Windows (PowerShell, GCC do MSYS2 UCRT64 no PATH)

```powershell
# teste de correção
gcc -std=c11 -O3 testes/test_correctness.c code/platform_thread.c -o build/test_correctness.exe
build\test_correctness.exe

# benchmark completo (30 repetições por configuração)
Remove-Item dados\windows_raw.csv -ErrorAction SilentlyContinue
gcc -std=c11 -O3 experimentos/benchmark.c code/platform_thread.c -o build/benchmark.exe
build\benchmark.exe --out dados\windows_raw.csv
```

> O benchmark **acrescenta** linhas ao CSV de saída: apague o arquivo antigo antes de uma nova coleta.

Opções do benchmark (todas opcionais): `--rep R` (padrão 30), `--primitiva mutex|spinlock`, `--secao curta|media|longa`, `--threads N`, `--total T`, `--plataforma nome`, `--out arquivo.csv`.
Teste rápido: `--rep 2 --threads 4 --out teste.csv` (apague o `teste.csv` depois).

Para uma coleta fiel: nenhum outro programa aberto e plano de energia de alto desempenho.
Os resultados absolutos variam conforme a máquina; o que se espera reproduzir são as tendências descritas em "Principais resultados".

### 3. Gráficos e resumo

```
pip install pandas matplotlib
python experimentos/gerar_graficos.py
```
(No Windows, se `python` não existir, use `py`.)

## Dados e resultados

- `dados/linux_raw.csv` e `dados/windows_raw.csv`: dados **brutos**, uma linha por repetição (900 por plataforma), gerados diretamente pelo benchmark e nunca editados à mão. Colunas: `plataforma, primitiva, secao, threads, total_aquisicoes, repeticao, tempo_s, vazao_aps, contador_ok`.
- `experimentos/`: tabelas de resumo e gráficos gerados a partir dos CSVs brutos.
- O relatório técnico (PDF de 4 páginas) é entregue no Moodle.

### Principais resultados (detalhes no relatório)

- Com seção crítica serial, o tempo total **não diminui** com mais threads (mutex, seção longa: ≈ 0,20 s de 1 a 16 threads nas duas plataformas).
- O spinlock só compensa, em geral, com seção curta ou média e N ≤ número de CPUs (4); com 8 e 16 threads ele perde e fica muito mais instável.
- A diferença entre Linux e Windows concentra-se na seção curta: o spinlock perde a vantagem com 2 threads no Windows e só entre 4 e 8 threads no Linux.

## Limitações

Uma máquina de 4 CPUs sem SMT; spinlock do Windows próprio (o do Linux é o do glibc); sem afinidade de CPU; uso de CPU não medido; total de aquisições diferente por duração de seção. Lista completa no relatório (seção 6).
