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
