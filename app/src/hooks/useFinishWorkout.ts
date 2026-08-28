import { useAppSelector, useAppSelectorWithArg } from '@/store';
import { FinishPlanSource, planDiffForFinish } from '@/store/program/helpers';
import { applyDiffToPlan, selectActiveProgram, setPendingPlanDiff } from '@/store/program';
import { selectSession, sessionFinished } from '@/store/stored-sessions';
import { useDispatch } from 'react-redux';

/**
 * Finishes the given session and returns whether the caller should open the
 * diff-save modal. Live reorder-only diffs against a same-named plan workout
 * are applied immediately. History never writes plan order.
 */
export function useFinishWorkout(sessionId: string | undefined, source: FinishPlanSource) {
  const dispatch = useDispatch();
  const session = useAppSelectorWithArg(selectSession, sessionId ?? '');
  const program = useAppSelector(selectActiveProgram);
  const programId = useAppSelector((x) => x.program.activePlanId);
  return (): boolean => {
    if (!sessionId || !session) {
      return false;
    }
    const action = planDiffForFinish(program, session, programId, source);
    if (action.kind === 'silent-apply') {
      dispatch(applyDiffToPlan(action.diff));
    } else if (action.kind === 'prompt') {
      dispatch(setPendingPlanDiff(action.diff));
    }
    dispatch(sessionFinished(sessionId));
    return action.kind === 'prompt';
  };
}
