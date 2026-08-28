import IconButton from '@/components/presentation/foundation/icon-button';
import { useAppTheme } from '@/hooks/useAppTheme';
import { useTranslate } from '@tolgee/react';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { View } from 'react-native';
import { Icon, Tooltip } from 'react-native-paper';

const DRAG_STEP_PX = 64;

export function ExerciseReorderControls(props: {
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onReorderDrag: (steps: number) => void;
}) {
  const { t } = useTranslate();
  const { colors } = useAppTheme();

  const pan = Gesture.Pan()
    .runOnJS(true)
    .activeOffsetY([-8, 8])
    .failOffsetX([-24, 24])
    .onEnd((event) => {
      const steps = Math.trunc(event.translationY / DRAG_STEP_PX);
      if (steps !== 0) {
        props.onReorderDrag(steps);
      }
    });

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
      <GestureDetector gesture={pan}>
        <View
          testID="exercise-drag-handle"
          accessibilityLabel={t('workout.exercise.reorder_handle.label')}
          accessibilityRole="adjustable"
          style={{ paddingHorizontal: 4, justifyContent: 'center' }}
        >
          <Icon source={'dragHandle'} size={24} color={colors.onSurfaceVariant} />
        </View>
      </GestureDetector>
      <Tooltip title={t('workout.exercise.move_up.button')}>
        <IconButton
          testID="exercise-move-up-btn"
          icon={'arrowUpward'}
          disabled={!props.canMoveUp}
          onPress={props.onMoveUp}
        />
      </Tooltip>
      <Tooltip title={t('workout.exercise.move_down.button')}>
        <IconButton
          testID="exercise-move-down-btn"
          icon={'arrowDownward'}
          disabled={!props.canMoveDown}
          onPress={props.onMoveDown}
        />
      </Tooltip>
    </View>
  );
}
