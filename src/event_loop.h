#ifndef EVENT_LOOP
#define EVENT_LOOP

#include "heap.h"
#include <stdbool.h>

typedef struct {
  PriorityHeap *q;
  bool done;
} EventLoop;

bool schedule(PyObject *callback, PyObject *args, uint16_t priority)

#endif
