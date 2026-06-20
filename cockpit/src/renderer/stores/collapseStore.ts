import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface CollapseState {
  sections: Record<string, boolean>
  isOpen: (key: string, defaultOpen?: boolean) => boolean
  toggle: (key: string) => void
  setOpen: (key: string, open: boolean) => void
}

export const useCollapseStore = create<CollapseState>()(
  persist(
    (set, get) => ({
      sections: {},
      isOpen: (key: string, defaultOpen = false): boolean => {
        const v = get().sections[key]
        return v === undefined ? defaultOpen : v
      },
      toggle: (key: string) =>
        set((s) => ({
          sections: { ...s.sections, [key]: !get().isOpen(key) },
        })),
      setOpen: (key: string, open: boolean) =>
        set((s) => ({
          sections: { ...s.sections, [key]: open },
        })),
    }),
    {
      name: 'cockpit:collapse-state',
      partialize: (state) => ({ sections: state.sections }),
    },
  ),
)
