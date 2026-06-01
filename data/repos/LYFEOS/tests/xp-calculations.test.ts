import { describe, it, expect } from 'vitest';

function calculateXPForLevel(level: number): number {
  if (level <= 1) return 1000;
  if (level <= 10) {
    return Math.floor(1000 * Math.pow(1.0372, level - 1));
  } else if (level <= 50) {
    const level10XP = calculateXPForLevel(10);
    return Math.floor(level10XP * Math.pow(1.0572, level - 10));
  } else {
    const level50XP = calculateXPForLevel(50);
    return Math.floor(level50XP * Math.pow(1.0872, level - 50));
  }
}

function calculateTotalXPForLevel(level: number): number {
  if (level <= 1) return 0;
  let totalXP = 0;
  for (let i = 1; i < level; i++) {
    totalXP += calculateXPForLevel(i);
  }
  return totalXP;
}

function calculateLevelFromTotalXP(totalXP: number): { level: number; current: number; max: number } {
  let level = 1;
  while (calculateTotalXPForLevel(level + 1) <= totalXP) {
    level++;
    if (level >= 100) break;
  }
  const xpForThisLevel = calculateTotalXPForLevel(level);
  const xpForNextLevel = calculateTotalXPForLevel(level + 1);
  const current = totalXP - xpForThisLevel;
  const max = xpForNextLevel - xpForThisLevel;
  return { level, current, max };
}

describe('XP Calculations', () => {
  describe('calculateXPForLevel', () => {
    it('returns 1000 XP for level 1', () => {
      expect(calculateXPForLevel(1)).toBe(1000);
    });

    it('returns 1000 XP for levels <= 0', () => {
      expect(calculateXPForLevel(0)).toBe(1000);
      expect(calculateXPForLevel(-1)).toBe(1000);
    });

    it('applies tier 1 growth for levels 2-10', () => {
      const level2 = calculateXPForLevel(2);
      expect(level2).toBeGreaterThan(1000);
      expect(level2).toBeLessThan(1100);

      const level10 = calculateXPForLevel(10);
      expect(level10).toBeGreaterThan(1000);
      expect(level10).toBeLessThan(1500);
    });

    it('applies tier 2 growth for levels 11-50', () => {
      const level11 = calculateXPForLevel(11);
      const level10 = calculateXPForLevel(10);
      expect(level11).toBeGreaterThan(level10);

      const level50 = calculateXPForLevel(50);
      expect(level50).toBeGreaterThan(level11);
    });

    it('applies tier 3 growth for levels 51+', () => {
      const level51 = calculateXPForLevel(51);
      const level50 = calculateXPForLevel(50);
      expect(level51).toBeGreaterThan(level50);

      const level100 = calculateXPForLevel(100);
      expect(level100).toBeGreaterThan(level51);
    });

    it('XP grows monotonically across all levels', () => {
      let prevXP = 0;
      for (let level = 1; level <= 100; level++) {
        const xp = calculateXPForLevel(level);
        expect(xp).toBeGreaterThan(prevXP);
        prevXP = xp;
      }
    });
  });

  describe('calculateTotalXPForLevel', () => {
    it('returns 0 for level 1', () => {
      expect(calculateTotalXPForLevel(1)).toBe(0);
    });

    it('returns 1000 for level 2 (need to complete level 1)', () => {
      expect(calculateTotalXPForLevel(2)).toBe(1000);
    });

    it('grows monotonically', () => {
      let prevTotal = 0;
      for (let level = 2; level <= 50; level++) {
        const total = calculateTotalXPForLevel(level);
        expect(total).toBeGreaterThan(prevTotal);
        prevTotal = total;
      }
    });
  });

  describe('calculateLevelFromTotalXP', () => {
    it('returns level 1 with 0 XP', () => {
      const result = calculateLevelFromTotalXP(0);
      expect(result.level).toBe(1);
      expect(result.current).toBe(0);
      expect(result.max).toBe(1000);
    });

    it('returns level 1 with partial XP', () => {
      const result = calculateLevelFromTotalXP(500);
      expect(result.level).toBe(1);
      expect(result.current).toBe(500);
      expect(result.max).toBe(1000);
    });

    it('returns level 2 with exactly 1000 XP', () => {
      const result = calculateLevelFromTotalXP(1000);
      expect(result.level).toBe(2);
      expect(result.current).toBe(0);
    });

    it('handles high XP values without infinite loops', () => {
      const result = calculateLevelFromTotalXP(999999999);
      expect(result.level).toBeLessThanOrEqual(100);
      expect(result.level).toBeGreaterThan(1);
    });

    it('level progress is always >= 0 and < max', () => {
      for (let xp = 0; xp <= 50000; xp += 500) {
        const result = calculateLevelFromTotalXP(xp);
        expect(result.current).toBeGreaterThanOrEqual(0);
        expect(result.current).toBeLessThan(result.max);
        expect(result.max).toBeGreaterThan(0);
      }
    });
  });
});
