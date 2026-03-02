#include "event_loop.h"
#include "heap.h"

#include <stdbool.h>
#include <stdlib.h>
#include <time.h>

static double timespec_to_double(const struct timespec *ts) {
  return ts->tv_sec + ts->tv_nsec / 1e9;
}

bool event_loop_init(EventLoop *e) {
  if (!heap_init(&e->q))
    return false;

  e->running = true;

  struct timespec start;
  if (clock_gettime(CLOCK_MONOTONIC, &start) != 0)
    return false;

  e->start_time = timespec_to_double(&start);

  return true;
}

void event_loop_stop(EventLoop *e) { e->running = false; }

void event_loop_destroy(EventLoop *e) {
  heap_destroy(&e->q);
  e->running = false;
}

bool event_loop_call_soon(EventLoop *e, PyObject *callback, PyObject *args,
                          int16_t priority) {
  struct timespec now;
  if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
    return false;

  double current_time = timespec_to_double(&now);
  if (!heap_push(&e->q, priority, current_time, current_time, callback, args))
    return false;

  return true;
}

bool event_loop_call_later(EventLoop *e, PyObject *callback, PyObject *args,
                           double delay, int16_t priority) {
  struct timespec now;
  if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
    return false;

  double current_time = timespec_to_double(&now);
  if (!heap_push(&e->q, priority, current_time + delay, current_time, callback,
                 args))
    return false;

  return true;
}

double event_loop_time(const EventLoop *e) {
  struct timespec now;
  if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
    return -1.0;

  double current_time = timespec_to_double(&now);
  return current_time - e->start_time;
}

bool event_loop_run_once(EventLoop *e) {
  if (!e->running || heap_size(&e->q) == 0)
    return false;

  struct timespec now;
  if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
    return false;

  double current_time = timespec_to_double(&now);

  heap_age(&e->q, current_time);

  double next_time = heap_peek_time(&e->q);
  if (next_time > current_time)
    return true; // work pending, not ready yet.

  HeapItem item;
  if (!heap_pop(&e->q, &item))
    return false;

  PyObject *result = (item.args != NULL)
                         ? PyObject_Call(item.callback, item.args, NULL)
                         : PyObject_CallNoArgs(item.callback);

  Py_XDECREF(result);
  Py_DECREF(item.callback);
  Py_XDECREF(item.args);

  if (result == NULL)
    PyErr_Print();

  return e->running;
}

void event_loop_run_forever(EventLoop *e) {
  while (e->running) {
    if (heap_size(&e->q) == 0) {
      struct timespec sleep_ts = {0, 1e9}; // 1 ms sleep
      nanosleep(&sleep_ts, NULL);
      continue;
    }

    if (!event_loop_run_once(e))
      break;

    double next_time = heap_peek_time(&e->q);
    if (next_time < 0)
      continue;

    // sleep until next task is due
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
      break;

    double current_time = timespec_to_double(&now);
    double wait_time = next_time - current_time;
    if (wait_time > 0) {
      struct timespec sleep_ts;
      sleep_ts.tv_sec = (time_t)wait_time;
      sleep_ts.tv_nsec = (long)((wait_time - sleep_ts.tv_sec) * 1e9);

      nanosleep(&sleep_ts, NULL);
    }
  }
}
