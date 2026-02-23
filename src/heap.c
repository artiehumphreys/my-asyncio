#include "heap.h"

#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

// returns true if a should be below b in the heap (a is lower priority)
static bool heap_cmp(const HeapItem *a, const HeapItem *b) {
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
