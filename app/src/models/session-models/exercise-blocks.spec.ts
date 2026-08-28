import { describe, it, expect } from 'vitest';
import { IndexOutOfBoundsError } from '@/utils/index-out-of-bounds';
import {
  canMoveBlockDown,
  canMoveBlockUp,
  indexAfterMoveDown,
  indexAfterMoveUp,
  moveBlockDown,
  moveBlockUp,
  supersetBlockRange,
} from '@/models/session-models/exercise-blocks';

function row(name: string, supersetWithNext: boolean) {
  return { name, blueprint: { type: 'WeightedExerciseBlueprint', supersetWithNext } };
}

function names(rows: readonly { name: string }[]) {
  return rows.map((r) => r.name);
}

describe('supersetBlockRange', () => {
  it('treats a singleton as its own block', () => {
    const exercises = [row('A', false), row('B', false), row('C', false)];
    expect(supersetBlockRange(exercises, 1)).toEqual({ start: 1, end: 2 });
  });

  it('groups a flagged row with the next one', () => {
    const exercises = [row('A', true), row('B', false), row('C', false)];
    expect(supersetBlockRange(exercises, 0)).toEqual({ start: 0, end: 2 });
    expect(supersetBlockRange(exercises, 1)).toEqual({ start: 0, end: 2 });
    expect(supersetBlockRange(exercises, 2)).toEqual({ start: 2, end: 3 });
  });

  it('moves a longer superset run as one block', () => {
    const exercises = [row('A', true), row('B', true), row('C', false), row('D', false)];
    expect(supersetBlockRange(exercises, 0)).toEqual({ start: 0, end: 3 });
    expect(supersetBlockRange(exercises, 1)).toEqual({ start: 0, end: 3 });
    expect(supersetBlockRange(exercises, 2)).toEqual({ start: 0, end: 3 });
  });

  it('throws when the index is out of range', () => {
    expect(() => supersetBlockRange([row('A', false)], 1)).toThrow(IndexOutOfBoundsError);
  });
});

describe('moveBlockUp / moveBlockDown', () => {
  it('swaps adjacent singletons', () => {
    const exercises = [row('A', false), row('B', false), row('C', false)];
    expect(names(moveBlockDown(exercises, 0))).toEqual(['B', 'A', 'C']);
    expect(names(moveBlockUp(exercises, 2))).toEqual(['A', 'C', 'B']);
  });

  it('moves a pair as a block past a singleton', () => {
    const exercises = [row('A', true), row('B', false), row('C', false)];
    expect(names(moveBlockDown(exercises, 0))).toEqual(['C', 'A', 'B']);
    expect(names(moveBlockDown(exercises, 1))).toEqual(['C', 'A', 'B']);
    expect(names(moveBlockUp([row('C', false), row('A', true), row('B', false)], 1))).toEqual(['A', 'B', 'C']);
  });

  it('moves a pair as a block past another pair', () => {
    const exercises = [row('A', true), row('B', false), row('C', true), row('D', false)];
    expect(names(moveBlockDown(exercises, 0))).toEqual(['C', 'D', 'A', 'B']);
    expect(names(moveBlockUp(exercises, 3))).toEqual(['C', 'D', 'A', 'B']);
  });

  it('is a no-op at the ends and returns the same array', () => {
    const exercises = [row('A', true), row('B', false), row('C', false)];
    expect(moveBlockUp(exercises, 0)).toBe(exercises);
    expect(moveBlockDown(exercises, 2)).toBe(exercises);
  });

  it('reports whether a block can move', () => {
    const exercises = [row('A', true), row('B', false), row('C', false)];
    expect(canMoveBlockUp(exercises, 0)).toBe(false);
    expect(canMoveBlockDown(exercises, 0)).toBe(true);
    expect(canMoveBlockUp(exercises, 2)).toBe(true);
    expect(canMoveBlockDown(exercises, 2)).toBe(false);
  });

  it('tracks the block start after a move so a drag can step more than once', () => {
    const exercises = [row('A', false), row('B', true), row('C', false), row('D', false)];
    expect(indexAfterMoveDown(exercises, 1)).toBe(2);
    expect(indexAfterMoveUp(exercises, 3)).toBe(1);
  });
});
