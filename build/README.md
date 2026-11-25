# Pasta `build/`

Esta pasta fica **vazia de propósito**: é onde os executáveis são gerados na hora de compilar.

## Por que ela existe no repositório

O `gcc` **não cria pastas** para o arquivo de saída. Se `build/` não existir, o comando `gcc ... -o build/benchmark` falha com *"No such file or directory"* (no Linux) ou deixa de gerar o `.exe` (no Windows). O Git não guarda pastas vazias, por isso este arquivo existe: ele mantém `build/` presente em qualquer clone ou download do repositório, e os comandos do `README.md` funcionam sem passos extras.

## O que NÃO fica no Git

Os executáveis (`benchmark`, `test_correctness`, `*.exe`, `*.o`) são ignorados pelo `.gitignore`. Cada plataforma compila o seu, então um não sobrescreve o do outro, e o repositório guarda só o código-fonte e os dados.

## Como usar

Na raiz do repositório:

```
gcc -std=c11 -O3 -pthread experimentos/benchmark.c code/platform_thread.c -o build/benchmark        # Linux
gcc -std=c11 -O3 experimentos/benchmark.c code/platform_thread.c -o build/benchmark.exe              # Windows
```

Se esta pasta tiver sido apagada, recrie com `mkdir build` (Linux e Windows).
