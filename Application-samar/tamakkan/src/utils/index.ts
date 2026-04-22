import type { DrivingSession } from '../types';

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-SA', { month: 'short', day: 'numeric' });
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} mins`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function getScoreLabel(score: number, max = 100): string {
  const pct = (score / max) * 100;
  if (pct >= 90) return 'EXCELLENT';
  if (pct >= 75) return 'GOOD';
  if (pct >= 60) return 'IMPROVING';
  return 'NEEDS WORK';
}

export function getScoreColor(score: number, max = 100): string {
  const pct = (score / max) * 100;
  if (pct >= 90) return '#006565';
  if (pct >= 75) return '#006c4f';
  if (pct >= 60) return '#775400';
  return '#ba1a1a';
}

export function getMistakeLabel(type: string): string {
  const labels: Record<string, string> = {
    'harsh-braking': 'Harsh Braking',
    'harsh-acceleration': 'Harsh Acceleration',
    speeding: 'Speeding',
    'lane-departure': 'Lane Departure',
    tailgating: 'Tailgating',
    'phone-use': 'Phone Use',
  };
  return labels[type] ?? type;
}

export function validateSaudiId(id: string): boolean {
  return /^\d{10}$/.test(id);
}

export function validateSaudiPhone(phone: string): boolean {
  return /^(\+966|0)?5\d{8}$/.test(phone.replace(/\s/g, ''));
}

export function scoreToOffset(score: number, max: number, radius = 40): number {
  const circumference = 2 * Math.PI * radius;
  const progress = score / max;
  return circumference * (1 - progress);
}
