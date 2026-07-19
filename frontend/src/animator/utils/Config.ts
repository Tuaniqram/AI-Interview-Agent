export const CONFIG = {
  Breathing: {
    CycleTime: 5.0,
    SpineAmplitude: 0.008,
    ShoulderAmplitude: 0.005,
    UpperSpineAmplitude: 0.004,
  },

  Eye: {
    SaccadeMinInterval: 1.0,
    SaccadeMaxInterval: 5.0,
    SaccadeMagnitude: 0.015,
    SaccadeHoldMin: 0.3,
    SaccadeHoldMax: 2.0,
    ConvergenceAmount: 0.005,
  },

  Blink: {
    MinInterval: 2.0,
    MaxInterval: 6.0,
    Duration: 0.08,
    DoubleBlinkGap: 0.15,
    SlowBlinkDuration: 0.18,
    DoubleBlinkProbability: 0.15,
    SlowBlinkProbability: 0.1,
  },

  Head: {
    NodSpeed: 2.0,
    NodAmplitude: 0.025,
    ListeningTilt: 0.04,
    ThinkingTiltX: 0.06,
    ThinkingTiltY: 0.08,
    MicroCorrectionIntervalMin: 20.0,
    MicroCorrectionIntervalMax: 60.0,
    CorrectionSpeed: 1.5,
    SpeakingEmphasisMinInterval: 3.0,
    SpeakingEmphasisMaxInterval: 8.0,
  },

  Gesture: {
    CooldownMin: 4.0,
    CooldownMax: 12.0,
    AttackDuration: 0.3,
    HoldDuration: 0.6,
    ReleaseDuration: 0.4,
    ArmMovementAmplitude: 0.08,
    ForearmMovementAmplitude: 0.12,
    Probability: 0.4,
    MaxPerMinute: 6,
  },

  Posture: {
    AdjustmentIntervalMin: 20.0,
    AdjustmentIntervalMax: 60.0,
    SpineCorrectionAmount: 0.01,
    ShoulderRelaxAmount: 0.008,
    TorsoStraightenAmount: 0.006,
  },

  WeightShift: {
    IntervalMin: 40.0,
    IntervalMax: 90.0,
    DefaultWeight: 0.53,
    ShoulderDropAmount: 0.006,
    SpineShiftAmount: 0.004,
    ShiftDuration: 1.5,
  },

  Micro: {
    AdjustmentIntervalMin: 20.0,
    AdjustmentIntervalMax: 60.0,
    NeckAdjustAmount: 0.005,
    ShoulderRelaxAmount: 0.004,
    TorsoCorrectionAmount: 0.003,
  },

  Listening: {
    LeanForwardAngle: 0.035,
    HeadTiltAngle: 0.04,
    NodMinInterval: 8.0,
    NodMaxInterval: 20.0,
    NodAmount: 0.03,
  },

  Thinking: {
    LookUpAngle: 0.06,
    HeadTurnAngle: 0.1,
    InhaleAmount: 0.003,
    ReturnDelay: 2.0,
    MinDuration: 3.0,
    MaxDuration: 7.0,
  },

  Speaking: {
    HeadNodMinInterval: 5.0,
    HeadNodMaxInterval: 15.0,
    HeadEmphasisAmount: 0.02,
    PostureForwardAmount: 0.01,
  },

  LipSync: {
    JawOpenMorph: 'jawOpen',
    SmoothTime: 0.05,
  },

  Idle: {
    PostureCorrectionIntervalMin: 20.0,
    PostureCorrectionIntervalMax: 60.0,
    WeightShiftIntervalMin: 40.0,
    WeightShiftIntervalMax: 90.0,
    HeadCorrectionIntervalMin: 15.0,
    HeadCorrectionIntervalMax: 45.0,
  },

  StateTransition: {
    BlendDuration: 0.8,
    MinBlendSpeed: 1.5,
  },

  Bones: {
    Names: [
      'spine', 'spine1', 'spine2', 'head', 'neck',
      'leftEye', 'rightEye', 'leftArm', 'rightArm',
      'leftForeArm', 'rightForeArm', 'leftShoulder', 'rightShoulder',
    ] as const,
  },
} as const
