import React from 'react';
import { createRoot } from 'react-dom/client';
import './popup.css';

const Popup: React.FC = () => {
  return (
    <div className="popup-container">
      <div className="popup-header">
        <h1>My Dealer</h1>
        <p className="popup-subtitle">Amazon Price Tracker</p>
      </div>
      
      <div className="popup-content">
        <p className="popup-description">
          Track Amazon product prices with a clean, intuitive interface.
        </p>
        
        <div className="popup-features">
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <span>Price History Charts</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔔</span>
            <span>Price Alerts</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔒</span>
            <span>Privacy First</span>
          </div>
        </div>

        <div className="popup-privacy">
          <h3>Privacy Policy</h3>
          <p>
            My Dealer only tracks product prices. We do not collect, store, or share
            your personal browsing data, search history, or any personally identifiable information.
          </p>
          <p>
            <strong>Data We Access:</strong> Product IDs from Amazon URLs (only when you visit product pages)
          </p>
          <p>
            <strong>Data We Don't Access:</strong> Your Amazon account, purchase history, search queries, or any personal information
          </p>
        </div>

        <div className="popup-footer">
          <a 
            href="https://github.com" 
            target="_blank" 
            rel="noopener noreferrer"
            className="popup-link"
          >
            Learn More
          </a>
        </div>
      </div>
    </div>
  );
};

// Render popup
const container = document.getElementById('popup-root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <Popup />
    </React.StrictMode>
  );
}

