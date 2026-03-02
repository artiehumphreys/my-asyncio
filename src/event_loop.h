#ifndef EVENT_LOOP
#define EVENT_LOOP

#include "heap.h"
#include <stdbool.h>
#include <stdint.h>

typedef struct {
  PriorityHeap q;
  bool running;
  double start_time;
} EventLoop;

bool event_loop_init(EventLoop *e);
void event_loop_destroy(EventLoop *e);

bool event_loop_call_soon(EventLoop *e, PyObject *callback, PyObject *args,
                          int16_t priority);
bool event_loop_call_later(EventLoop *e, PyObject *callback, PyObject *args,
                           double delay, int16_t priority);

double event_loop_time(const EventLoop *e);
bool event_loop_run_once(EventLoop *e);

#endif
