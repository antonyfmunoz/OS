// lib/react-gen/design-tokens.ts
// Design token constants and mandatory rules enforced in every generated component.

export const DESIGN_TOKENS = {
  colors: {
    primary: '#6a37d4',
    primaryHover: '#5a2dc0',
    secondary: '#6448b2',
    tertiary: '#ae8dff',
    surface: '#f5f6f7',
    background: '#ffffff',
    onSurface: '#2c2f30',
    onSurfaceVariant: '#595c5d',
    outlineVariant: '#abadae',
    surfaceContainerLow: '#eff1f2',
  },
  glassmorphism: {
    background: 'rgba(255,255,255,0.7)',
    backdropFilter: 'blur(16px)',
    shadow: '0 8px 32px rgba(106,55,212,0.08)',
  },
  borderRadius: '12px',
  font: 'Inter',
  spacing: {
    cardPadding: '32px',
  },
} as const;

export const DESIGN_RULES = `
MANDATORY DESIGN RULES — violating any of these is a build failure:

1. NO gradients anywhere. Primary buttons use solid #6a37d4 only.
2. Glassmorphism on all floating elements: background rgba(255,255,255,0.7), backdrop-filter blur(16px)
3. Ambient shadow only: 0 8px 32px rgba(106,55,212,0.08). Never standard drop shadows.
4. NO 1px solid borders for structural separation. Use background color shifts instead.
5. Inter font exclusively. No other fonts.
6. lucide-react icons exclusively. No Material Symbols, no emoji as icons.
7. shadcn/ui primitives for all base components (Button, Input, Card, Dialog, etc.)
8. 12px border radius throughout.
9. Never use pure black (#000000). Use #2c2f30 for text.
10. Cards: 32px padding, no internal dividers, glassmorphism on hover.
11. Left rail navigation: surface-container-low background (#eff1f2), no dividers between items.
12. All authenticated pages use UniversalLayout wrapper.
13. Every page must handle: loading state, error state, empty state.
14. Mobile responsive — every layout must work on 375px width.
`;
