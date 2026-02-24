#include "heap.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

static bool heap_cmp(const HeapItem *a, const HeapItem *b) {
  // returns true if a should be below b in the heap (a is lower priority)
  if (a->priority != b->priority)
    return a->priority > b->priority;

  if (a->scheduled_time != b->scheduled_time)
    return a->scheduled_time > b->scheduled_time;

  return a->insertion_order > b->insertion_order;
}

static void swap(HeapItem *entries, size_t i, size_t j) {
  HeapItem tmp = entries[i];
  entries[i] = entries[j];
  entries[j] = tmp;
}

static void sift_down(HeapItem *entries, size_t size, size_t idx) {
  while (1) {
    size_t smallest = idx;
    size_t left = 2 * idx + 1;
    size_t right = 2 * idx + 2;

    if (left < size && heap_cmp(&entries[smallest], &entries[left]))
      smallest = left;
    if (right < size && heap_cmp(&entries[smallest], &entries[right]))
      smallest = right;

    if (smallest == idx)
      break;

    swap(entries, idx, smallest);
    idx = smallest;
  }
}

static void sift_up(HeapItem *entries, size_t idx) {
  while (idx > 0) {
    size_t parent = (idx - 1) / 2;
    if (heap_cmp(&entries[parent], &entries[idx])) {
      swap(entries, idx, parent);
      idx = parent;
    } else {
      break;
    }
  }
}

bool heap_init(PriorityHeap *h) {
  // malloc since heap is initially small and for flexible reallocation
  void *mem = malloc(HEAP_INITIAL_CAPACITY * sizeof(HeapItem));
  if (mem == NULL)
    return false;
  HeapItem *items = (HeapItem *)mem;
  h->entries = items;

  h->size = 0;
  h->capacity = HEAP_INITIAL_CAPACITY;
  h->insert_counter = 0;
  h->last_age_check = 0.0;

  return true;
}

void heap_destroy(PriorityHeap *h) {
  // release ownership of PyObjects so they may be garabage collected
  for (size_t i = 0; i < h->size; ++i) {
    Py_XDECREF(h->entries[i].callback);
    Py_XDECREF(h->entries[i].args);
  }
  free(h->entries);
  h->entries = NULL;
  h->capacity = 0;
  h->size = 0;
}

bool heap_push(PriorityHeap *h, int16_t priority, double scheduled_time,
               double now, PyObject *callback, PyObject *args) {
  if (h->size >= h->capacity) {
    size_t new_capacity = 2 * h->capacity;
    void *new_entries = realloc(h->entries, new_capacity * sizeof(HeapItem));
    if (new_entries == NULL)
      return false;
    HeapItem *entries = (HeapItem *)new_entries;
    h->entries = entries;
    h->capacity = new_capacity;
  }

  HeapItem *entry = &h->entries[h->size];
  entry->priority = priority;
  entry->scheduled_time = scheduled_time;
  entry->insert_time = now;
  entry->insertion_order = h->insert_counter++;
  entry->cancelled = false;

  Py_INCREF(callback);
  entry->callback = callback;
  Py_XINCREF(args);
  entry->args = args;

  sift_up(h->entries, h->size);
  h->size++;

  return true;
}

bool heap_pop(PriorityHeap *h, HeapItem *out) {
  while (h->size > 0 && h->entries[0].cancelled) {
    // skip cancelled callbacks
    HeapItem *pop = &h->entries[0];
    Py_XDECREF(pop->callback);
    Py_XDECREF(pop->args);
    h->entries[0] = h->entries[h->size - 1];
    h->size--;
    if (h->size > 0)
      sift_down(h->entries, h->size, 0);
  }

  if (h->size == 0)
    return false;

  *out = h->entries[0];
  h->entries[0] = h->entries[h->size - 1];
  h->size--;

  if (h->size > 0)
    sift_down(h->entries, h->size, 0);

  return true;
}

double heap_peek_time(const PriorityHeap *h) {
  if (h->size == 0)
    return -1.0;
  const HeapItem *top = &h->entries[0];
  return top->scheduled_time;
}

size_t heap_size(const PriorityHeap *h) { return h->size; }

void heap_age(PriorityHeap *h, double now) {
  if (now - h->last_age_check < AGE_INTERVAL)
    return;

  h->last_age_check = now;
  bool needs_heapify = false;
  for (size_t i = 0; i < h->size; ++i) {
    double wait_time = now - h->entries[i].insert_time;
    HeapItem *entry = &h->entries[i];
    if (wait_time > AGE_INTERVAL && entry->priority > HIGHEST_PRIORITY) {
      entry->priority--;
      needs_heapify = true;
    }
  }

  if (needs_heapify) {
    for (size_t i = h->size / 2; i > 0; --i) {
      sift_down(h->entries, h->size, 0);
    }
  }
}
