// Type definitions for My Dealer extension
// Privacy-first: These types define minimal data structures
// Future enhancement: Add encryption/decryption types for sensitive data

export interface PriceDataPoint {
  date: string; // ISO date string
  price: number;
  currency?: string;
}

export interface PriceHistory {
  productId: string;
  productTitle?: string;
  currentPrice: number;
  currency: string;
  history: PriceDataPoint[];
  lowestPrice?: number;
  highestPrice?: number;
  averagePrice?: number;
}

export interface TrackPriceRequest {
  productId: string;
  targetPrice?: number;
  email?: string; // Future: encrypted storage
}

// Privacy note: In production, implement proper data anonymization
// and user consent mechanisms before storing any personal data

