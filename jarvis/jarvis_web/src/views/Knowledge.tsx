import { BookOpen } from 'lucide-react'
import { ViewStub } from '../components/ViewStub.tsx'

export function Knowledge() {
  return (
    <ViewStub
      title="Knowledge"
      icon={BookOpen}
      description="Memory and library browser. Search, explore, and manage the substrate's persistent knowledge store."
      features={[
        'Memory store browser with filters',
        'Document library and ingestion status',
        'Search across all memory types',
        'Authority tier indicators',
        'Knowledge gap identification',
      ]}
    />
  )
}
