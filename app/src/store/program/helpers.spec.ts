import { describe, it, expect } from 'vitest';
import { LocalDate } from '@js-joda/core';
import { ProgramBlueprint, SessionBlueprint } from '@/models/blueprint-models';
import { makeSession, makeWeightedBlueprint } from '@/models/session-models/__test__/helpers';
import { applySessionBlueprintDiff } from '@/models/blueprint-diff';
import { getPlanDiff, planDiffForFinish } from '@/store/program/helpers';

function programWith(sessions: SessionBlueprint[]) {
  return new ProgramBlueprint('Plan', sessions, LocalDate.of(2025, 4, 5));
}

describe('getPlanDiff', () => {
  it('returns undefined when the session blueprint already matches the plan', () => {
    const session = makeSession([makeWeightedBlueprint({ name: 'Squat' })]);
    const program = programWith([session.blueprint]);
    expect(getPlanDiff(program, session, 'plan-id')).toBeUndefined();
  });

  it('returns a diff against the same-named session in the plan', () => {
    const original = makeSession([makeWeightedBlueprint({ name: 'Squat' })]);
    const edited = original.withAddedExercise(makeWeightedBlueprint({ name: 'Bench' }), false);
    const program = programWith([original.blueprint]);

    const result = getPlanDiff(program, edited, 'plan-id')!;

    expect(result.type).toBe('diff');
    if (result.type === 'diff') {
      expect(result.sessionIndex).toBe(0);
      expect(result.diff.hasChanges).toBe(true);
    }
  });

  it('returns an add diff when no session shares the name', () => {
    const session = makeSession([makeWeightedBlueprint({ name: 'Squat' })]);
    const program = programWith([
      makeSession([makeWeightedBlueprint({ name: 'Row' })]).withName('Cardio Day').blueprint,
    ]);

    const result = getPlanDiff(program, session, 'plan-id')!;

    expect(result.type).toBe('add');
  });

  it('records which plan the diff was computed against', () => {
    const original = makeSession([makeWeightedBlueprint({ name: 'Squat' })]);
    const edited = original.withAddedExercise(makeWeightedBlueprint({ name: 'Bench' }), false);

    expect(getPlanDiff(programWith([original.blueprint]), edited, 'plan-id')?.programId).toBe('plan-id');
    expect(getPlanDiff(programWith([]), edited, 'plan-id')?.programId).toBe('plan-id');
  });
});

describe('planDiffForFinish', () => {
  it('silently applies a live reorder-only diff to the same-named plan workout', () => {
    const original = makeSession([
      makeWeightedBlueprint({ name: 'Squat' }),
      makeWeightedBlueprint({ name: 'Bench' }),
    ]).withName('Chest');
    const reordered = original.withExerciseBlockMovedDown(0);
    const program = programWith([original.blueprint]);

    const result = planDiffForFinish(program, reordered, 'plan-id', 'live');

    expect(result.kind).toBe('silent-apply');
    if (result.kind === 'silent-apply' && result.diff.type === 'diff') {
      expect(applySessionBlueprintDiff(original.blueprint, result.diff.diff).exercises.map((ex) => ex.name)).toEqual([
        'Bench',
        'Squat',
      ]);
    }
  });

  it('does not silent-apply an unmatched live session', () => {
    const session = makeSession([
      makeWeightedBlueprint({ name: 'Squat' }),
      makeWeightedBlueprint({ name: 'Bench' }),
    ]).withName('Freeform Workout');
    const reordered = session.withExerciseBlockMovedDown(0);
    const program = programWith([makeSession([makeWeightedBlueprint({ name: 'Row' })]).withName('Back').blueprint]);

    const result = planDiffForFinish(program, reordered, 'plan-id', 'live');

    expect(result.kind).toBe('prompt');
    if (result.kind === 'prompt') {
      expect(result.diff.type).toBe('add');
    }
  });

  it('prompts when a live session has more than a reorder', () => {
    const original = makeSession([
      makeWeightedBlueprint({ name: 'Squat' }),
      makeWeightedBlueprint({ name: 'Flyes' }),
    ]).withName('Chest');
    const edited = original
      .withExerciseBlockMovedDown(0)
      .withAddedExercise(makeWeightedBlueprint({ name: 'Bench' }), false);
    const program = programWith([original.blueprint]);

    expect(planDiffForFinish(program, edited, 'plan-id', 'live').kind).toBe('prompt');
  });

  it('strips reorder from a history save so the plan order cannot change', () => {
    const original = makeSession([
      makeWeightedBlueprint({ name: 'Squat' }),
      makeWeightedBlueprint({ name: 'Bench' }),
    ]).withName('Chest');
    const reordered = original.withExerciseBlockMovedDown(0);
    const program = programWith([original.blueprint]);

    expect(planDiffForFinish(program, reordered, 'plan-id', 'history').kind).toBe('none');
  });

  it('still prompts for non-order history edits after stripping reorder', () => {
    const original = makeSession([
      makeWeightedBlueprint({ name: 'Squat' }),
      makeWeightedBlueprint({ name: 'Bench' }),
    ]).withName('Chest');
    const edited = original
      .withExerciseBlockMovedDown(0)
      .withAddedExercise(makeWeightedBlueprint({ name: 'Row' }), false);
    const program = programWith([original.blueprint]);

    const result = planDiffForFinish(program, edited, 'plan-id', 'history');
    expect(result.kind).toBe('prompt');
    if (result.kind === 'prompt' && result.diff.type === 'diff') {
      expect(result.diff.diff.reorderedExercises).toHaveLength(0);
      expect(result.diff.diff.addedExercises.length).toBeGreaterThan(0);
    }
  });
});
