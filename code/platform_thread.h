#ifndef PLATFORM_THREAD_H
#define PLATFORM_THREAD_H

/* Camada de abstracao de threads: API unica, API nativa por baixo.
   Linux/FreeBSD -> pthreads | Windows -> Win32 (sem winpthreads). */

#ifdef _WIN32
  #include <windows.h>
  typedef HANDLE             pt_thread_t;
  typedef CRITICAL_SECTION   pt_mutex_t;
  typedef volatile LONG      pt_spinlock_t;   /* 0 = livre, 1 = ocupado */
#else
  #include <pthread.h>
  typedef pthread_t          pt_thread_t;
  typedef pthread_mutex_t    pt_mutex_t;
  typedef pthread_spinlock_t pt_spinlock_t;
#endif

/* Todas retornam 0 em caso de sucesso. */

/* Threads */
int pt_thread_create(pt_thread_t *t, void *(*fn)(void *), void *arg);
int pt_thread_join(pt_thread_t t);

/* Mutex */
int pt_mutex_init(pt_mutex_t *m);
int pt_mutex_lock(pt_mutex_t *m);
int pt_mutex_unlock(pt_mutex_t *m);
int pt_mutex_destroy(pt_mutex_t *m);

/* Spinlock */
int pt_spinlock_init(pt_spinlock_t *s);
int pt_spinlock_lock(pt_spinlock_t *s);
int pt_spinlock_unlock(pt_spinlock_t *s);
int pt_spinlock_destroy(pt_spinlock_t *s);

#endif