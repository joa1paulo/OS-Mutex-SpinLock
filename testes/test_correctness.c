#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L   /* necessario p/ pthread_spinlock_t com -std=c11 */
#endif
#include <stdio.h>
#include <stdlib.h>
#include "../code/platform_thread.h"

#define N_ITER 100000

static long counter;
static pt_mutex_t m;
static pt_spinlock_t s;
static int use_spin;

static void *worker(void *arg) {
    (void)arg;
    for (int i = 0; i < N_ITER; i++) {
        if (use_spin) { pt_spinlock_lock(&s); counter++; pt_spinlock_unlock(&s); }
        else          { pt_mutex_lock(&m);    counter++; pt_mutex_unlock(&m); }
    }
    return NULL;
}

int main(void) {
    int threads[] = {1, 2, 4, 8, 16};
    int fail = 0;
    pt_mutex_init(&m);
    pt_spinlock_init(&s);

    for (use_spin = 0; use_spin <= 1; use_spin++) {
        for (int k = 0; k < 5; k++) {
            int n = threads[k];
            pt_thread_t *t = malloc((size_t)n * sizeof *t);
            counter = 0;
            for (int i = 0; i < n; i++) pt_thread_create(&t[i], worker, NULL);
            for (int i = 0; i < n; i++) pt_thread_join(t[i]);
            free(t);
            long esperado = (long)n * N_ITER;
            int ok = (counter == esperado);
            printf("%-8s threads=%2d contador=%ld esperado=%ld %s\n",
                   use_spin ? "spinlock" : "mutex", n, counter, esperado,
                   ok ? "OK" : "FALHOU");
            if (!ok) fail = 1;
        }
    }
    pt_mutex_destroy(&m);
    pt_spinlock_destroy(&s);
 
    return fail;
}