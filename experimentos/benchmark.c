/* Benchmark Tema 1: mutex x spinlock.
 *
 * Roda a matriz completa: 3 duracoes de secao critica x 2 primitivas x
 * 5 numeros de threads, repetida --rep vezes (padrao 30). Cada repeticao
 * gera uma linha no CSV bruto (nunca editar o CSV a mao).
 * As repeticoes sao o laco mais externo: as configuracoes se intercalam,
 * espalhando ruido do sistema por todas elas.
 *
 * Uso: benchmark [--plataforma nome] [--out arq.csv] [--rep R]
 *                [--primitiva mutex|spinlock] [--secao curta|media|longa]
 *                [--threads N] [--total T]
 */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdatomic.h>
#include "../code/platform_thread.h"
#ifndef _WIN32
#include <time.h>
#include <unistd.h>
#endif

#define MAX_THREADS 16

static const int      THREADS[]      = {1, 2, 4, 8, 16};
static const char    *SEC_NOME[]     = {"curta", "media", "longa"};
static const uint64_t SEC_NS[]       = {0, 1000, 100000};          /* trabalho na secao critica */
static const long long TOTAL_PADRAO[] = {1000000, 200000, 2000};   /* aquisicoes totais por secao */
static const char    *PRIM_NOME[]    = {"mutex", "spinlock"};

typedef struct { int use_spin; uint64_t work_ns; long long n_iter; } job_t;

static pt_mutex_t    g_mutex;
static pt_spinlock_t g_spin;
static long long     g_counter;
static atomic_int    g_ready;
static atomic_int    g_go;

/* ---------- tempo ---------- */
static uint64_t now_ns(void) {
#ifdef _WIN32
    static LARGE_INTEGER freq;   /* inicializada em main antes de criar threads */
    LARGE_INTEGER c;
    if (freq.QuadPart == 0) QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&c);
    uint64_t ticks = (uint64_t)c.QuadPart, f = (uint64_t)freq.QuadPart;
    return (ticks / f) * 1000000000ULL + (ticks % f) * 1000000000ULL / f;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

static void sleep_1ms(void) {
#ifdef _WIN32
    Sleep(1);
#else
    struct timespec ts = {0, 1000000L};
    nanosleep(&ts, NULL);
#endif
}

static int num_cpus(void) {
#ifdef _WIN32
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    return (int)si.dwNumberOfProcessors;
#else
    return (int)sysconf(_SC_NPROCESSORS_ONLN);
#endif
}

static void busy_wait(uint64_t ns) {
    uint64_t end = now_ns() + ns;
    while (now_ns() < end) { }
}

/* ---------- worker ---------- */
static void *worker(void *arg) {
    const job_t *j = (const job_t *)arg;
    atomic_fetch_add(&g_ready, 1);
    while (!atomic_load(&g_go)) { }            /* largada simultanea */
    for (long long i = 0; i < j->n_iter; i++) {
        if (j->use_spin) pt_spinlock_lock(&g_spin); else pt_mutex_lock(&g_mutex);
        g_counter++;
        if (j->work_ns) busy_wait(j->work_ns);
        if (j->use_spin) pt_spinlock_unlock(&g_spin); else pt_mutex_unlock(&g_mutex);
    }
    return NULL;
}

/* Executa uma repeticao. Retorna 1 se o contador final confere. */
static int run_one(int use_spin, int sec, int n, long long total, double *tempo_s) {
    job_t jobs[MAX_THREADS];
    pt_thread_t th[MAX_THREADS];
    long long base = total / n, resto = total % n;

    g_counter = 0;
    atomic_store(&g_ready, 0);
    atomic_store(&g_go, 0);

    for (int i = 0; i < n; i++) {
        jobs[i].use_spin = use_spin;
        jobs[i].work_ns  = SEC_NS[sec];
        jobs[i].n_iter   = base + (i < resto ? 1 : 0);
        if (pt_thread_create(&th[i], worker, &jobs[i]) != 0) {
            fprintf(stderr, "erro ao criar thread\n");
            exit(1);
        }
    }
    while (atomic_load(&g_ready) < n) sleep_1ms();

    uint64_t t0 = now_ns();
    atomic_store(&g_go, 1);
    for (int i = 0; i < n; i++) pt_thread_join(th[i]);
    uint64_t t1 = now_ns();

    *tempo_s = (double)(t1 - t0) / 1e9;
    return g_counter == total;
}

/* ---------- main ---------- */
static int indice(const char **nomes, int qtd, const char *s) {
    for (int i = 0; i < qtd; i++) if (strcmp(nomes[i], s) == 0) return i;
    return -1;
}

int main(int argc, char **argv) {
#ifdef _WIN32
    const char *plataforma = "windows";
#else
    const char *plataforma = "linux";
#endif
    const char *out = NULL;
    int reps = 30, f_prim = -1, f_sec = -1, f_thr = -1;
    long long total_override = 0;

    for (int i = 1; i + 1 < argc; i += 2) {
        const char *k = argv[i], *v = argv[i + 1];
        if      (!strcmp(k, "--plataforma")) plataforma = v;
        else if (!strcmp(k, "--out"))        out = v;
        else if (!strcmp(k, "--rep"))        reps = atoi(v);
        else if (!strcmp(k, "--primitiva"))  f_prim = indice(PRIM_NOME, 2, v);
        else if (!strcmp(k, "--secao"))      f_sec = indice(SEC_NOME, 3, v);
        else if (!strcmp(k, "--threads"))    f_thr = atoi(v);
        else if (!strcmp(k, "--total"))      total_override = strtoll(v, NULL, 10);
        else { fprintf(stderr, "opcao desconhecida: %s\n", k); return 2; }
    }
    if (reps < 1) { fprintf(stderr, "--rep invalido\n"); return 2; }

    char padrao[256];
    if (!out) { snprintf(padrao, sizeof padrao, "%s_raw.csv", plataforma); out = padrao; }

    now_ns();                                   /* inicializa o timer */
    pt_mutex_init(&g_mutex);
    pt_spinlock_init(&g_spin);

    FILE *f = fopen(out, "a");
    if (!f) { perror("fopen"); return 1; }
    fseek(f, 0, SEEK_END);
    if (ftell(f) == 0)
        fprintf(f, "plataforma,primitiva,secao,threads,total_aquisicoes,repeticao,tempo_s,vazao_aps,contador_ok\n");

    fprintf(stderr, "plataforma=%s cpus_logicas=%d reps=%d saida=%s\n",
            plataforma, num_cpus(), reps, out);

    int erro = 0;
    for (int rep = 1; rep <= reps; rep++) {
        for (int sec = 0; sec < 3; sec++) {
            if (f_sec >= 0 && sec != f_sec) continue;
            long long total = total_override ? total_override : TOTAL_PADRAO[sec];
            for (int p = 0; p < 2; p++) {
                if (f_prim >= 0 && p != f_prim) continue;
                for (int k = 0; k < 5; k++) {
                    int n = THREADS[k];
                    if (f_thr > 0 && n != f_thr) continue;
                    double t;
                    int ok = run_one(p, sec, n, total, &t);
                    if (!ok) erro = 1;
                    fprintf(f, "%s,%s,%s,%d,%lld,%d,%.9f,%.3f,%d\n",
                            plataforma, PRIM_NOME[p], SEC_NOME[sec], n, total, rep,
                            t, (double)total / t, ok);
                    fflush(f);
                }
            }
        }
        fprintf(stderr, "repeticao %d/%d concluida\n", rep, reps);
    }
    fclose(f);
    pt_mutex_destroy(&g_mutex);
    pt_spinlock_destroy(&g_spin);
    return erro;
}