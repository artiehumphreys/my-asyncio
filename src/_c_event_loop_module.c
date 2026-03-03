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

// call_soon(callback, args=None, priority=10)
// parses Python args, validates types, forwards to C event_loop_call_soon
static PyObject *PyEventLoop_call_soon(PyEventLoopObject *self, PyObject *args,
                                       PyObject *kwds) {
  static char *kwlist[] = {"callback", "args", "priority", NULL};
  PyObject *callback;
  PyObject *cb_args = NULL;
  int priority = 10; // NORMAL default

  // "O|Oi": O = required object, | = rest optional, O = object, i = int
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|Oi", kwlist, &callback,
                                   &cb_args, &priority))
    return NULL;

  if (!PyCallable_Check(callback)) {
    PyErr_SetString(PyExc_TypeError, "callback must be callable");
    return NULL;
  }

  // normalize None → NULL for the C layer
  if (cb_args == Py_None)
    cb_args = NULL;
  if (cb_args != NULL && !PyTuple_Check(cb_args)) {
    PyErr_SetString(PyExc_TypeError, "args must be a tuple or None");
    return NULL;
  }

  if (!event_loop_call_soon(&self->loop, callback, cb_args,
                            (int16_t)priority)) {
    PyErr_SetString(PyExc_RuntimeError, "call_soon failed");
    return NULL;
  }

  Py_RETURN_NONE;
}

// call_later(delay, callback, args=None, priority=10)
static PyObject *PyEventLoop_call_later(PyEventLoopObject *self,
                                        PyObject *args, PyObject *kwds) {
  static char *kwlist[] = {"delay", "callback", "args", "priority", NULL};
  double delay;
  PyObject *callback;
  PyObject *cb_args = NULL;
  int priority = 10;

  // "dO|Oi": d = required double, O = required object, rest optional
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "dO|Oi", kwlist, &delay,
                                   &callback, &cb_args, &priority))
    return NULL;

  if (!PyCallable_Check(callback)) {
    PyErr_SetString(PyExc_TypeError, "callback must be callable");
    return NULL;
  }

  if (cb_args == Py_None)
    cb_args = NULL;
  if (cb_args != NULL && !PyTuple_Check(cb_args)) {
    PyErr_SetString(PyExc_TypeError, "args must be a tuple or None");
    return NULL;
  }

  if (!event_loop_call_later(&self->loop, callback, cb_args, delay,
                             (int16_t)priority)) {
    PyErr_SetString(PyExc_RuntimeError, "call_later failed");
    return NULL;
  }

  Py_RETURN_NONE;
}
