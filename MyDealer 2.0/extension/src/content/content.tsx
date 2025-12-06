import React from 'react';
import { createRoot } from 'react-dom/client';
import PriceChart from '../components/PriceChart';

// Grab the product ID. That's it. We're not creepy.
function extractProductId(): string | null {
  const url = window.location.href;
  
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

function getCurrentAmazonUrl(): string {
  return window.location.href;
}

// Hunt for a good spot to inject our chart. Amazon's DOM is a jungle.
function findInsertionPoint(): HTMLElement | null {
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
    if(element) {
      const parent = element.parentElement;
      if (parent) {
        const container = document.createElement('div');
        container.id = 'my-dealer-price-chart';
        container.setAttribute('data-my-dealer', 'true');
        
        if (element.nextSibling) {
          parent.insertBefore(container, element.nextSibling);
        } else {
          parent.appendChild(container);
        }
        
        return container;
      }
    }
  }

  // Fallback selectors
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

function injectPriceChart() {
  // Check if already injected to avoid duplicates
  if(document.getElementById('my-dealer-price-chart')) {
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
    const url = getCurrentAmazonUrl();
    root.render(
      <React.StrictMode>
        <PriceChart productId={productId} amazonUrl={url} />
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

// Watch for Amazon's SPA shenanigans. They love changing pages without reloading.
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    setTimeout(injectPriceChart, 500);
  }
}).observe(document, { subtree: true, childList: true });
