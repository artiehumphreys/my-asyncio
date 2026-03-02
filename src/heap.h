#ifndef HEAP_H
#define HEAP_H

#include <Python.h>
#include <stdbool.h>
#include <stdint.h>

// PRIORITY SCALE:
// -10: CRITICAL
// 0: HIGH
// 10: NORMAL
// 20: LOW
// 50: IDLE

#define HIGHEST_PRIORITY -10
// aging for escalating task priority
#define AGE_INTERVAL 0.5
#define AGE_THRESHOLD 1.0

#define HEAP_INITIAL_CAPACITY 128

typedef struct {
  // heap ordered by (priority, time, insertion order)
  int16_t priority;
  double scheduled_time; // when callback should run
  uint64_t insertion_order;
  double insert_time;
  bool cancelled;

  PyObject *callback;
  PyObject *args;
} HeapItem;

typedef struct {
  HeapItem *entries;
  size_t size;
  size_t capacity;
  uint64_t insert_counter;
  double last_age_check;
} PriorityHeap;

bool heap_init(PriorityHeap *h);
void heap_destroy(PriorityHeap *h);

bool heap_push(PriorityHeap *h, int16_t priority, double scheduled_time,
               double now, PyObject *callback, PyObject *args);

bool heap_pop(PriorityHeap *h, HeapItem *out);

double heap_peek_time(const PriorityHeap *h);
size_t heap_size(const PriorityHeap *h);

// Aging: bumps priority of entries waiting longer than AGE_THRESHOLD
void heap_age(PriorityHeap *h, double now);

#endif
