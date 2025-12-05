import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './PriceChart.css';

interface PriceDataPoint {
  date: string;
  price: number;
  currency?: string;
}

interface PriceHistory {
  productId: string;
  productTitle?: string;
  currentPrice: number;
  currency: string;
  history: PriceDataPoint[];
  lowestPrice?: number;
  highestPrice?: number;
  averagePrice?: number;
}

interface PriceChartProps {
  productId: string;
  amazonUrl?: string; // Full Amazon URL for domain detection
  apiUrl?: string;
}

// Format date for display (mobile-friendly short format)
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

// Format price with currency
const formatPrice = (price: number, currency: string = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
  }).format(price);
};

const PriceChart: React.FC<PriceChartProps> = ({ productId, amazonUrl, apiUrl = 'http://localhost:8000' }) => {
  const [priceHistory, setPriceHistory] = useState<PriceHistory | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPriceHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        
        let response: Response;
        
        // Use POST endpoint with full URL if available (recommended - automatically handles domain)
        // Otherwise fall back to GET endpoint with domain parameter
        if (amazonUrl) {
          // POST /api/price-history-from-url - automatically extracts domain and currency
          response = await fetch(`${apiUrl}/api/price-history-from-url`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              url: amazonUrl
            })
          });
        } else {
          // Fallback: GET endpoint (requires domain parameter)
          // Extract domain from current URL if amazonUrl not provided
          const currentUrl = window.location.href;
          const domain = extractAmazonDomain(currentUrl);
          const domainParam = domain ? `?domain=${encodeURIComponent(domain)}` : '';
          
          response = await fetch(`${apiUrl}/api/price-history/${productId}${domainParam}`);
        }
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch price history' }));
          throw new Error(errorData.detail || 'Failed to fetch price history');
        }
        
        const data = await response.json();
        setPriceHistory(data);
        
        // Log currency for debugging
        if (data.currency) {
          console.log(`My Dealer: Price history loaded with currency: ${data.currency}`);
        }
      } catch (err) {
        console.error('Error fetching price history:', err);
        setError(err instanceof Error ? err.message : 'Unable to load price history. Please check your connection.');
      } finally {
        setLoading(false);
      }
    };

    if (productId) {
      fetchPriceHistory();
    }
  }, [productId, amazonUrl, apiUrl]);

  // Helper function to extract Amazon domain from URL
  function extractAmazonDomain(url: string): string | null {
    const domains = [
      'amazon.com.br',
      'amazon.com.mx',
      'amazon.com.au',
      'amazon.co.uk',
      'amazon.co.jp',
      'amazon.in',
      'amazon.de',
      'amazon.fr',
      'amazon.it',
      'amazon.es',
      'amazon.ca',
      'amazon.nl',
      'amazon.se',
      'amazon.pl',
      'amazon.com'
    ];
    
    // Check more specific domains first
    for (const domain of domains) {
      if (url.includes(domain)) {
        return domain;
      }
    }
    
    return null;
  }

  const handleTrackPrice = () => {
    // Privacy-first: This is a demo alert. In production, implement proper
    // user consent and secure storage before saving any user preferences
    alert(`Price tracking for this product will be available soon!\n\nProduct ID: ${productId}\n\nPrivacy Note: We only track prices, not your personal browsing data.`);
  };

  if (loading) {
    return (
      <div className="price-chart-container">
        <div className="price-chart-loading">
          <div className="spinner"></div>
          <p>Loading price history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="price-chart-container">
        <div className="price-chart-error">
          <p>{error}</p>
          <button onClick={() => window.location.reload()} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!priceHistory || !priceHistory.history.length) {
    return (
      <div className="price-chart-container">
        <div className="price-chart-empty">
          <p>No price history available for this product.</p>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const chartData = priceHistory.history.map((point) => ({
    date: formatDate(point.date),
    price: point.price,
    fullDate: point.date,
  }));

  return (
    <div className="price-chart-container">
      <div className="price-chart-header">
        <h2 className="price-chart-title">Price History</h2>
        <button onClick={handleTrackPrice} className="track-price-button">
          📊 Track Price
        </button>
      </div>

      <div className="price-stats">
        <div className="stat-item">
          <span className="stat-label">Current</span>
          <span className="stat-value current">
            {formatPrice(priceHistory.currentPrice, priceHistory.currency)}
          </span>
        </div>
        {priceHistory.lowestPrice && (
          <div className="stat-item">
            <span className="stat-label">Lowest</span>
            <span className="stat-value lowest">
              {formatPrice(priceHistory.lowestPrice, priceHistory.currency)}
            </span>
          </div>
        )}
        {priceHistory.highestPrice && (
          <div className="stat-item">
            <span className="stat-label">Highest</span>
            <span className="stat-value highest">
              {formatPrice(priceHistory.highestPrice, priceHistory.currency)}
            </span>
          </div>
        )}
        {priceHistory.averagePrice && (
          <div className="stat-item">
            <span className="stat-label">Average</span>
            <span className="stat-value average">
              {formatPrice(priceHistory.averagePrice, priceHistory.currency)}
            </span>
          </div>
        )}
      </div>

      <div className="price-chart-wrapper">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis 
              dataKey="date" 
              stroke="#666"
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis 
              stroke="#666"
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => formatPrice(value, priceHistory.currency)}
            />
            <Tooltip
              formatter={(value: number) => formatPrice(value, priceHistory.currency)}
              labelStyle={{ color: '#333' }}
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #ccc',
                borderRadius: '4px',
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#2563eb"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 6 }}
              name="Price"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="price-chart-footer">
        <p className="privacy-note">
          🔒 Privacy: We only track product prices, not your personal data.
        </p>
      </div>
    </div>
  );
};

export default PriceChart;

