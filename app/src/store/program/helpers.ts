import { diffSessionBlueprints, isReorderOnlyDiff, PlanDiff, withoutReorderedExercises } from '@/models/blueprint-diff';
import { ProgramBlueprint } from '@/models/blueprint-models';
import { EmptySession, Session } from '@/models/session-models';

/**
 * Computes how a finished session differs from the active plan, or `undefined`
 * if the session already matches a workout in the plan.
 */
export function getPlanDiff(program: ProgramBlueprint, session: Session, programId: string): PlanDiff | undefined {
  const sessionInPlan = program.sessions.some((x) => x.equals(session.blueprint));
  if (sessionInPlan) {
    return undefined;
  }

  const sessionWithSameNameInPlan = program.sessions.find((x) => x.name === session.blueprint.name);
  return sessionWithSameNameInPlan
    ? {
        type: 'diff',
        programId,
        diff: diffSessionBlueprints(sessionWithSameNameInPlan, session.blueprint),
        sessionIndex: program.sessions.indexOf(sessionWithSameNameInPlan),
      }
    : {
        type: 'add',
        programId,
        diff: diffSessionBlueprints(EmptySession.blueprint, session.blueprint),
      };
}

export type FinishPlanSource = 'live' | 'history';

export type FinishPlanAction =
  | { kind: 'none' }
  | { kind: 'prompt'; diff: PlanDiff }
  | { kind: 'silent-apply'; diff: PlanDiff };

/**
 * Live finish writes reorder-only diffs to a same-named plan workout with no dialog.
 * History never writes plan order. Unmatched names never silent-apply.
 */
export function planDiffForFinish(
  program: ProgramBlueprint,
  session: Session,
  programId: string,
  source: FinishPlanSource,
): FinishPlanAction {
  const diff = getPlanDiff(program, session, programId);
  if (!diff) {
    return { kind: 'none' };
  }

  if (source === 'history') {
    if (diff.type === 'add') {
      return { kind: 'prompt', diff };
    }
    const stripped = withoutReorderedExercises(diff.diff);
    if (!stripped.hasChanges) {
      return { kind: 'none' };
    }
    return { kind: 'prompt', diff: { ...diff, diff: stripped } };
  }

  if (diff.type === 'diff' && isReorderOnlyDiff(diff.diff)) {
    return { kind: 'silent-apply', diff };
  }
  return { kind: 'prompt', diff };
}
