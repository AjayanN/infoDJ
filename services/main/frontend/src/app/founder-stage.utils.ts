export type FounderStage = 'validate' | 'build' | 'launch' | 'grow' | 'scale';

const stageLabels: Record<FounderStage, string> = {
  validate: 'Validation',
  build: 'Build',
  launch: 'Launch',
  grow: 'Growth',
  scale: 'Scale'
};

const stageProgress: Record<FounderStage, number> = {
  validate: 18,
  build: 36,
  launch: 54,
  grow: 72,
  scale: 90
};

const stageCheckpoints: Record<FounderStage, string> = {
  validate: 'Prove the problem is worth solving',
  build: 'Make one workflow indispensable',
  launch: 'Turn first value into a repeatable habit',
  grow: 'Make retention power the growth engine',
  scale: 'Compound the advantage without losing focus'
};

export const founderStageLabel = (stage: FounderStage): string => stageLabels[stage];
export const founderStageProgress = (stage: FounderStage): number => stageProgress[stage];
export const founderStageCheckpoint = (stage: FounderStage): string => stageCheckpoints[stage];
