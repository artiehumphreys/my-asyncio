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

// __new__: allocate the Python object (no C-level init yet)
static PyObject *PyEventLoop_new(PyTypeObject *type, PyObject *args,
                                 PyObject *kwds) {
  (void)args;
  (void)kwds;
  PyEventLoopObject *self = (PyEventLoopObject *)type->tp_alloc(type, 0);
  return (PyObject *)self;
}

// __init__: initialize the embedded C EventLoop
static int PyEventLoop_init(PyEventLoopObject *self, PyObject *args,
                            PyObject *kwds) {
  (void)args;
  (void)kwds;
  if (!event_loop_init(&self->loop)) {
    PyErr_SetString(PyExc_RuntimeError, "failed to initialize event loop");
    return -1;
  }
  return 0;
}

// destructor: clean up C event loop, then free the Python object
static void PyEventLoop_dealloc(PyEventLoopObject *self) {
  event_loop_destroy(&self->loop);
  Py_TYPE(self)->tp_free((PyObject *)self);
}
