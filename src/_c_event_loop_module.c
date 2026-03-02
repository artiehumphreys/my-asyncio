#include <Python.h>
#include <time.h>

#include "event_loop.h"
#include "heap.h"

/* Python object wrapping our C EventLoop.
   EventLoop is embedded directly (not a pointer) since
   event_loop_init takes a pointer to existing storage. */
typedef struct {
  PyObject_HEAD EventLoop loop;
} PyEventLoopObject;
