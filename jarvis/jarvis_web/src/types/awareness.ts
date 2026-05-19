export type AwarenessTier =
  | 'embodied'
  | 'workspace'
  | 'network'
  | 'cloud'
  | 'global'
  | 'learning'

export type GlobalLayer =
  | 'news'
  | 'markets'
  | 'weather'
  | 'geopolitical'
  | 'aviation'
  | 'maritime'
  | 'infrastructure'
  | 'satellite'
  | 'cyber'
  | 'scientific'
  | 'government'
  | 'custom-feeds'

export interface GlobalEvent {
  id: string
  layer: GlobalLayer
  title: string
  summary: string
  severity: 'info' | 'warning' | 'critical'
  timestamp: string
  coordinates?: { lat: number; lng: number }
  source: string
  relevance: number
}

export interface AISynthesis {
  id: string
  title: string
  body: string
  relatedEvents: string[]
  confidence: number
  timestamp: string
}
