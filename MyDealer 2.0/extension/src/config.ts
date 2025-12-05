// Configuration for My Dealer extension
// Privacy note: No user data is stored in this configuration

export const config = {
  // Backend API URL
  // In production, this should be configurable or use environment variables
  apiUrl: process.env.API_URL || 'http://localhost:8000',
  
  // Extension version
  version: '1.0.0',
  
  // Feature flags (for future use)
  features: {
    priceAlerts: false, // Coming soon
    userAccounts: false, // Coming soon
    notifications: false, // Coming soon
  },
};

// Security note: In production, implement:
// - API key authentication
// - Request signing
// - Rate limiting on client side
// - Secure storage for user preferences

