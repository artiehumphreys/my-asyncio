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

// time() -> float: elapsed seconds since loop creation
static PyObject *PyEventLoop_time(PyEventLoopObject *self,
                                  PyObject *Py_UNUSED(ignored)) {
  double t = event_loop_time(&self->loop);
  if (t < 0.0) {
    PyErr_SetString(PyExc_RuntimeError, "clock_gettime failed");
    return NULL;
  }
  return PyFloat_FromDouble(t);
}

// run_once() -> bool: execute one ready callback
static PyObject *PyEventLoop_run_once(PyEventLoopObject *self,
                                      PyObject *Py_UNUSED(ignored)) {
  bool result = event_loop_run_once(&self->loop);
  if (PyErr_Occurred())
    return NULL;
  return PyBool_FromLong(result);
}

// stop(): set running = false so run_forever exits
static PyObject *PyEventLoop_stop(PyEventLoopObject *self,
                                  PyObject *Py_UNUSED(ignored)) {
  event_loop_stop(&self->loop);
  Py_RETURN_NONE;
}

// run_forever(): runs until stop() is called.
// reimplemented here (instead of calling event_loop_run_forever) so we can
// release the GIL during nanosleep — otherwise sleeping blocks all threads.
static PyObject *PyEventLoop_run_forever(PyEventLoopObject *self,
                                         PyObject *Py_UNUSED(ignored)) {
  EventLoop *e = &self->loop;

  while (e->running) {
    if (heap_size(&e->q) == 0) {
      struct timespec ts = {0, 1000000}; // 1ms idle sleep
      Py_BEGIN_ALLOW_THREADS;
      nanosleep(&ts, NULL);
      Py_END_ALLOW_THREADS;
      continue;
    }

    // run_once needs the GIL since it calls Python callbacks
    bool ok = event_loop_run_once(e);
    if (PyErr_Occurred())
      return NULL;
    if (!ok)
      break;

    // sleep until next scheduled item, releasing GIL during sleep
    double next_time = heap_peek_time(&e->q);
    if (next_time < 0)
      continue;

    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
      break;

    double current = now.tv_sec + now.tv_nsec / 1e9;
    double wait = next_time - current;
    if (wait > 0) {
      struct timespec sleep_ts;
      sleep_ts.tv_sec = (time_t)wait;
      sleep_ts.tv_nsec = (long)((wait - sleep_ts.tv_sec) * 1e9);
      Py_BEGIN_ALLOW_THREADS;
      nanosleep(&sleep_ts, NULL);
      Py_END_ALLOW_THREADS;
    }
  }

  Py_RETURN_NONE;
}
