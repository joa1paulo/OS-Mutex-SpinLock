#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include <stdlib.h>
#include "platform_thread.h"

#ifdef _WIN32
/* ===================== Windows (Win32 nativo) ===================== */

typedef struct { void *(*fn)(void *); void *arg; } pt_start_t;

static DWORD WINAPI pt_trampoline(LPVOID p) {
    pt_start_t s = *(pt_start_t *)p;
    free(p);
    s.fn(s.arg);
    return 0;
}

int pt_thread_create(pt_thread_t *t, void *(*fn)(void *), void *arg) {
    pt_start_t *s = malloc(sizeof *s);
    if (!s) return -1;
    s->fn = fn; s->arg = arg;
    *t = CreateThread(NULL, 0, pt_trampoline, s, 0, NULL);
    if (*t == NULL) { free(s); return -1; }
    return 0;
}

int pt_thread_join(pt_thread_t t) {
    DWORD r = WaitForSingleObject(t, INFINITE);
    CloseHandle(t);
    return r == WAIT_OBJECT_0 ? 0 : -1;
}

int pt_mutex_init(pt_mutex_t *m)    { InitializeCriticalSection(m); return 0; }
int pt_mutex_lock(pt_mutex_t *m)    { EnterCriticalSection(m);      return 0; }
int pt_mutex_unlock(pt_mutex_t *m)  { LeaveCriticalSection(m);      return 0; }
int pt_mutex_destroy(pt_mutex_t *m) { DeleteCriticalSection(m);     return 0; }

/* Win32 nao tem spinlock em modo usuario: test-and-test-and-set. */
int pt_spinlock_init(pt_spinlock_t *s) { *s = 0; return 0; }
int pt_spinlock_lock(pt_spinlock_t *s) {
    while (InterlockedExchange(s, 1) != 0) {
        while (*s) YieldProcessor();
    }
    return 0;
}
int pt_spinlock_unlock(pt_spinlock_t *s)  { InterlockedExchange(s, 0); return 0; }
int pt_spinlock_destroy(pt_spinlock_t *s) { (void)s; return 0; }

#else
/* ===================== Linux / FreeBSD (pthreads) ===================== */

int pt_thread_create(pt_thread_t *t, void *(*fn)(void *), void *arg) {
    return pthread_create(t, NULL, fn, arg);
}
int pt_thread_join(pt_thread_t t) { return pthread_join(t, NULL); }

int pt_mutex_init(pt_mutex_t *m)    { return pthread_mutex_init(m, NULL); }
int pt_mutex_lock(pt_mutex_t *m)    { return pthread_mutex_lock(m); }
int pt_mutex_unlock(pt_mutex_t *m)  { return pthread_mutex_unlock(m); }
int pt_mutex_destroy(pt_mutex_t *m) { return pthread_mutex_destroy(m); }

int pt_spinlock_init(pt_spinlock_t *s)    { return pthread_spin_init(s, PTHREAD_PROCESS_PRIVATE); }
int pt_spinlock_lock(pt_spinlock_t *s)    { return pthread_spin_lock(s); }
int pt_spinlock_unlock(pt_spinlock_t *s)  { return pthread_spin_unlock(s); }
int pt_spinlock_destroy(pt_spinlock_t *s) { return pthread_spin_destroy(s); }
#endif