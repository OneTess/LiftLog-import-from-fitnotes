import { IndexOutOfBoundsError } from '@/utils/index-out-of-bounds';

type WithOptionalSuperset = {
  readonly blueprint: { readonly type: string; readonly supersetWithNext?: boolean };
};

function supersetsWithNext(exercise: WithOptionalSuperset): boolean {
  return exercise.blueprint.supersetWithNext === true;
}

/**
 * Inclusive-start, exclusive-end range of the superset chain containing `index`.
 * A 2-row pair is the usual case; a longer run of `supersetWithNext` moves as one block.
 * Cardio has no flag and is always a singleton.
 */
export function supersetBlockRange(
  exercises: readonly WithOptionalSuperset[],
  index: number,
): { start: number; end: number } {
  if (index < 0 || index >= exercises.length) {
    throw new IndexOutOfBoundsError(index, exercises as unknown[]);
  }
  let start = index;
  while (start > 0 && supersetsWithNext(exercises[start - 1]!)) {
    start--;
  }
  let end = start + 1;
  while (end < exercises.length && supersetsWithNext(exercises[end - 1]!)) {
    end++;
  }
  return { start, end };
}

export function canMoveBlockUp(exercises: readonly WithOptionalSuperset[], index: number): boolean {
  return supersetBlockRange(exercises, index).start > 0;
}

export function canMoveBlockDown(exercises: readonly WithOptionalSuperset[], index: number): boolean {
  return supersetBlockRange(exercises, index).end < exercises.length;
}

export function moveBlockUp<T extends WithOptionalSuperset>(exercises: readonly T[], index: number): readonly T[] {
  const { start, end } = supersetBlockRange(exercises, index);
  if (start === 0) {
    return exercises;
  }
  const prev = supersetBlockRange(exercises, start - 1);
  return [
    ...exercises.slice(0, prev.start),
    ...exercises.slice(start, end),
    ...exercises.slice(prev.start, start),
    ...exercises.slice(end),
  ];
}

export function moveBlockDown<T extends WithOptionalSuperset>(exercises: readonly T[], index: number): readonly T[] {
  const { start, end } = supersetBlockRange(exercises, index);
  if (end >= exercises.length) {
    return exercises;
  }
  const next = supersetBlockRange(exercises, end);
  return [
    ...exercises.slice(0, start),
    ...exercises.slice(next.start, next.end),
    ...exercises.slice(start, end),
    ...exercises.slice(next.end),
  ];
}

/** After moving the block at `index` down once, the index of that same block's first row. */
export function indexAfterMoveDown(exercises: readonly WithOptionalSuperset[], index: number): number {
  const { start, end } = supersetBlockRange(exercises, index);
  if (end >= exercises.length) {
    return start;
  }
  const next = supersetBlockRange(exercises, end);
  return start + (next.end - next.start);
}

/** After moving the block at `index` up once, the index of that same block's first row. */
export function indexAfterMoveUp(exercises: readonly WithOptionalSuperset[], index: number): number {
  const { start } = supersetBlockRange(exercises, index);
  if (start === 0) {
    return start;
  }
  return supersetBlockRange(exercises, start - 1).start;
}
