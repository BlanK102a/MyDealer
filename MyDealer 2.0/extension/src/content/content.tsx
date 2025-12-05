import React from 'react';
import { createRoot } from 'react-dom/client';
import PriceChart from '../components/PriceChart';
// Note: content.css is loaded separately via manifest.json

// Extract Amazon product ID from URL
// Privacy note: We only extract the product ID, no other user data
function extractProductId(): string | null {
  const url = window.location.href;
  
  // Match various Amazon URL patterns
  const patterns = [
    /\/dp\/([A-Z0-9]{10})/,
    /\/gp\/product\/([A-Z0-9]{10})/,
    /\/product\/([A-Z0-9]{10})/,
    /\/dp\/([A-Z0-9]{10})\//,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }

  return null;
}

// Get current Amazon URL for API call
// Privacy note: We only use this to extract domain and product ID
function getCurrentAmazonUrl(): string {
  return window.location.href;
}

// Find the insertion point below product description
// This targets the common Amazon product page structure
function findInsertionPoint(): HTMLElement | null {
  // Try multiple selectors to find the product description area
  const selectors = [
    '#productDescription',
    '#feature-bullets',
    '#productDescription_feature_div',
    '[data-feature-name="productDescription"]',
    '#productDescription_feature_div',
    '#aplus_feature_div',
    '#productDescription_feature_div_feature_div',
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      // Insert after the description section
      const parent = element.parentElement;
      if (parent) {
        const container = document.createElement('div');
        container.id = 'my-dealer-price-chart';
        container.setAttribute('data-my-dealer', 'true');
        
        // Insert after the found element
        if (element.nextSibling) {
          parent.insertBefore(container, element.nextSibling);
        } else {
          parent.appendChild(container);
        }
        
        return container;
      }
    }
  }

  // Fallback: Try to find a common container and append
  const fallbackSelectors = [
    '#productDetails_feature_div',
    '#centerCol',
    '#main-content',
  ];

  for (const selector of fallbackSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      const container = document.createElement('div');
      container.id = 'my-dealer-price-chart';
      container.setAttribute('data-my-dealer', 'true');
      element.appendChild(container);
      return container;
    }
  }

  return null;
}

// Main injection function
function injectPriceChart() {
  // Check if already injected to avoid duplicates
  if (document.getElementById('my-dealer-price-chart')) {
    return;
  }

  const productId = extractProductId();
  if (!productId) {
    console.log('My Dealer: Could not extract product ID from URL');
    return;
  }

  const container = findInsertionPoint();
  if (!container) {
    console.log('My Dealer: Could not find insertion point on page');
    // Retry after a short delay in case page is still loading
    setTimeout(() => {
      const retryContainer = findInsertionPoint();
      if (retryContainer) {
        renderChart(retryContainer, productId);
      }
    }, 1000);
    return;
  }

  renderChart(container, productId);
}

function renderChart(container: HTMLElement, productId: string) {
  try {
    const root = createRoot(container);
    // Pass the full URL so backend can extract domain and determine currency
    const amazonUrl = getCurrentAmazonUrl();
    root.render(
      <React.StrictMode>
        <PriceChart productId={productId} amazonUrl={amazonUrl} />
      </React.StrictMode>
    );
  } catch (error) {
    console.error('My Dealer: Error rendering price chart:', error);
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectPriceChart);
} else {
  injectPriceChart();
}

// Handle dynamic page navigation (SPA behavior)
// Privacy note: We only observe URL changes, not user behavior
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    // Small delay to let Amazon's page update
    setTimeout(injectPriceChart, 500);
  }
}).observe(document, { subtree: true, childList: true });

