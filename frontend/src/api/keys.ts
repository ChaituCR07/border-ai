export const keys = {
  cameras: ['cameras'] as const,
  cameraDetail: (id: string) => ['cameras', id] as const,
  cameraActivity: ['analytics', 'cameras'] as const,
  threats: (windowStr: string) => ['analytics', 'threats', windowStr] as const,
  openAlerts: (priority?: string | null, camera?: string | null) =>
    ['alerts', 'open', priority ?? 'ALL', camera ?? 'ALL'] as const,
  recentEvents: (limit: number = 10) => ['events', 'recent', limit] as const,
  health: ['health'] as const,
  ready: ['ready'] as const,
};
