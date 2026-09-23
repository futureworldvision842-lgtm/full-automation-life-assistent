/**
 * Provider boundaries are deliberately small. The demo repository is local,
 * while production can install Firebase, Maps, AI and integrity adapters
 * without allowing a UI component to own privileged business logic.
 */
export type Citation = { label: string; url?: string; retrievedAt: string; confidence: 'high' | 'medium' | 'low' };

export interface PublicSourceAdapter {
  id: string;
  fetchPulse(input: { categories: string[]; geography?: string }): Promise<Array<{ title: string; summary: string; citations: Citation[] }>>;
}

export interface MapProviderAdapter {
  id: string;
  getStyleUrl(): string;
  geocode(query: string): Promise<Array<{ label: string; latitude: number; longitude: number }>>;
}

export interface AiGatewayAdapter {
  id: string;
  draft(input: { instruction: string; authorizedContext: string[]; citations: Citation[] }): Promise<{ text: string; citations: Citation[]; uncertainty: string }>;
}

export interface IntegrityAnchorAdapter {
  id: string;
  anchor(input: { headHash: string; eventCount: number }): Promise<{ network: 'local' | 'ethereum-testnet'; transactionId: string; anchoredAt: string }>;
}

export const localMapAdapter: MapProviderAdapter = {
  id: 'maplibre-openstreetmap-ready',
  getStyleUrl: () => import.meta.env.VITE_MAP_STYLE_URL || 'https://demotiles.maplibre.org/style.json',
  geocode: async (query) => query.trim() ? [{ label: query.trim(), latitude: 33.6844, longitude: 73.0479 }] : []
};

export const localIntegrityAdapter: IntegrityAnchorAdapter = {
  id: 'local-append-only-demo',
  anchor: async ({ headHash, eventCount }) => ({ network: 'local', transactionId: `local:${headHash.slice(-12)}`, anchoredAt: new Date().toISOString() })
};
