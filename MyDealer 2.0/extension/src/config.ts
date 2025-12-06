// Configuration for My Dealer extension

// API_URL is injected by Webpack DefinePlugin during build
declare const API_URL: string | undefined;

export const config = {
  // Backend API URL - injected at build time
  apiUrl: typeof API_URL !== 'undefined' ? API_URL : 'http://localhost:8000',
  
  // Extension version
  version: '1.0.0',
  
  // Feature flags (for future use)
  features: {
    priceAlerts: false, // Coming soon
    userAccounts: false, // Coming soon
    notifications: false, // Coming soon
  },
};
