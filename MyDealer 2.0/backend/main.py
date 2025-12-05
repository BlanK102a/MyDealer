"""
My Dealer - FastAPI Backend
Privacy-first Amazon price tracking API with mock endpoints

Security Notes:
- In production, implement proper authentication/authorization
- Add rate limiting to prevent abuse
- Implement CORS properly for production
- Add request validation and sanitization
- Consider implementing API keys for extension authentication
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import random
import re
import json
from typing import Optional, Tuple
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import asyncio

app = FastAPI(
    title="My Dealer API",
    description="Privacy-first Amazon price tracking API",
    version="2.0.0"
)

# CORS configuration
# Privacy note: In production, restrict origins to specific domains
# and implement proper CORS policies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to extension origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store the exposed URL
EXPOSED_URL = ""

@app.get("/api/url", tags=["Utility"])
async def get_exposed_url():
    """
    Returns the public URL of the API server.
    The extension needs this to dynamically set the API base URL.
    """
    if not EXPOSED_URL:
        raise HTTPException(status_code=503, detail="API URL not yet exposed.")
    return {"url": EXPOSED_URL}


# Request/Response Models
class PriceDataPoint(BaseModel):
    date: str
    price: float
    currency: Optional[str] = None


class PriceHistoryResponse(BaseModel):
    productId: str
    productTitle: Optional[str] = None
    currentPrice: float
    currency: str
    history: list[PriceDataPoint]
    lowestPrice: Optional[float] = None
    highestPrice: Optional[float] = None
    averagePrice: Optional[float] = None
    bestTimeToBuy: Optional[str] = None


class TrackPriceRequest(BaseModel):
    productId: str
    targetPrice: Optional[float] = None
    email: Optional[str] = None  # Future: encrypted storage


class AmazonUrlRequest(BaseModel):
    url: str


# Map Amazon domains to their currencies
AMAZON_DOMAIN_CURRENCY = {
    'amazon.com': 'USD',           # United States
    'amazon.co.uk': 'GBP',         # United Kingdom
    'amazon.de': 'EUR',            # Germany
    'amazon.fr': 'EUR',            # France
    'amazon.it': 'EUR',            # Italy
    'amazon.es': 'EUR',            # Spain
    'amazon.ca': 'CAD',            # Canada
    'amazon.com.au': 'AUD',        # Australia
    'amazon.in': 'INR',            # India
    'amazon.co.jp': 'JPY',         # Japan
    'amazon.com.mx': 'MXN',        # Mexico
    'amazon.com.br': 'BRL',        # Brazil
    'amazon.nl': 'EUR',            # Netherlands
    'amazon.se': 'SEK',            # Sweden
    'amazon.pl': 'PLN',            # Poland
}

# Determine Amazon domain from URL
def get_amazon_domain(url: str) -> str:
    """
    Extract Amazon domain from URL to determine which Amazon site to use.
    Returns the base domain (e.g., 'amazon.com', 'amazon.co.uk')
    """
    domain_patterns = {
        r'amazon\.com(?:\.au|\.mx|\.br)?': 'amazon.com',
        r'amazon\.co\.uk': 'amazon.co.uk',
        r'amazon\.de': 'amazon.de',
        r'amazon\.fr': 'amazon.fr',
        r'amazon\.it': 'amazon.it',
        r'amazon\.es': 'amazon.es',
        r'amazon\.ca': 'amazon.ca',
        r'amazon\.com\.au': 'amazon.com.au',
        r'amazon\.in': 'amazon.in',
        r'amazon\.co\.jp': 'amazon.co.jp',
        r'amazon\.com\.mx': 'amazon.com.mx',
        r'amazon\.com\.br': 'amazon.com.br',
        r'amazon\.nl': 'amazon.nl',
        r'amazon\.se': 'amazon.se',
        r'amazon\.pl': 'amazon.pl',
    }
    
    # Check patterns in order (more specific first)
    for pattern, domain in domain_patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return domain
    
    # Default to US Amazon
    return 'amazon.com'


# Get currency for Amazon domain
def get_currency_for_domain(amazon_domain: str) -> str:
    """
    Get the currency code for a given Amazon domain.
    Returns currency code (e.g., 'USD', 'CAD', 'GBP')
    """
    return AMAZON_DOMAIN_CURRENCY.get(amazon_domain, 'USD')


# Fetch real price from Amazon product page using product ID
async def fetch_amazon_price(product_id: str, amazon_domain: str = 'amazon.com') -> Tuple[Optional[float], Optional[str], Optional[str]]:

    """
    Fetch the actual current price from Amazon product page using product ID.
    
    Privacy note: This function only fetches publicly available product information.
    No user data is collected or stored.
    
    Args:
        product_id: Amazon product ID (ASIN)
        amazon_domain: Amazon domain (e.g., 'amazon.com', 'amazon.co.uk')
    
    Returns: (price, currency, product_title) or (None, None, None) if failed
    """
    # Construct Amazon URL from product ID and domain
    url = f"https://www.{amazon_domain}/dp/{product_id}"
    
    # Use realistic browser headers to avoid blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            price = None
            # Set default currency based on domain FIRST
            currency = get_currency_for_domain(amazon_domain)
            
            # Method 1: Try to find price in offscreen text (most reliable)
            offscreen_prices = soup.select('span.a-offscreen')
            
            for offscreen in offscreen_prices:
                price_text = offscreen.get_text(strip=True)
                
                # Look for price pattern with currency symbol - improved regex
                price_match = re.search(r'(?:CAD|USD|GBP|EUR|JPY|INR|BRL|SEK|PLN|MXN|AUD|\$|£|€|¥|₹|R\$|kr|zł|MX\$)?\s*([\d,]+\.?\d{0,2})', price_text.replace(',', ''))
                if price_match:
                    try:
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        
                        # Determine currency: prioritize domain, then check price text
                        currency = get_currency_for_domain(amazon_domain)
                        
                        # Check for currency symbol/code in the scraped text to refine the currency
                        currency_symbol_map = {
                            'CAD': 'CAD', 'USD': 'USD', 'GBP': 'GBP', 'EUR': 'EUR', 'JPY': 'JPY',
                            'INR': 'INR', 'BRL': 'BRL', 'SEK': 'SEK', 'PLN': 'PLN', 'MXN': 'MXN',
                            'AUD': 'AUD', '£': 'GBP', '€': 'EUR', '¥': 'JPY',
                            '₹': 'INR', 'R$': 'BRL', 'kr': 'SEK', 'zł': 'PLN', 'MX$': 'MXN'
                        }
                        
                        # Handle the ambiguous '$' symbol first
                        if '$' in price_text:
                            if amazon_domain == 'amazon.ca':
                                currency = 'CAD'
                            elif amazon_domain == 'amazon.com.au':
                                currency = 'AUD'
                            elif amazon_domain == 'amazon.com.mx':
                                currency = 'MXN'
                            else:
                                currency = 'USD'
                        
                        # Check for other specific symbols/codes to override the '$' or domain default
                        for symbol, code in currency_symbol_map.items():
                            if symbol in price_text and symbol != '$':
                                currency = code
                                break
                        
                        if currency is None:
                            currency = get_currency_for_domain(amazon_domain)
                        
                        if price > 0:
                            break
                    except (ValueError, AttributeError):
                        continue
            
            # Method 2: Try structured price elements
            if price is None:
                price_selectors = [
                    ('span.a-price-whole', 'span.a-price-fraction'),
                    ('#priceblock_ourprice', None),
                    ('#priceblock_dealprice', None),
                    ('#priceblock_saleprice', None),
                    ('.a-price .a-offscreen', None),
                    ('span[data-a-color="price"] .a-offscreen', None),
                    ('#corePriceDisplay_desktop_feature_div .a-price-whole', '#corePriceDisplay_desktop_feature_div .a-price-fraction'),
                    ('#corePrice_feature_div .a-price-whole', '#corePrice_feature_div .a-price-fraction'),
                ]
                
                for whole_sel, fraction_sel in price_selectors:
                    whole_elem = soup.select_one(whole_sel)
                    if whole_elem:
                        whole_text = whole_elem.get_text(strip=True)
                        fraction_text = ""
                        
                        if fraction_sel:
                            fraction_elem = soup.select_one(fraction_sel)
                            if fraction_elem:
                                fraction_text = fraction_elem.get_text(strip=True)
                        
                        price_text = whole_text.replace(',', '')
                        if fraction_text:
                            price_text = f"{price_text}.{fraction_text}"
                        else:
                            parent = whole_elem.parent
                            if parent:
                                fraction_elem = parent.select_one('.a-price-fraction')
                                if fraction_elem:
                                    price_text = f"{price_text}.{fraction_elem.get_text(strip=True)}"
                        
                        price_match = re.search(r'([\d,]+\.?\d*)', price_text.replace(',', ''))
                        if price_match:
                            try:
                                price = float(price_match.group(1).replace(',', ''))
                                if price > 0:
                                    break
                            except ValueError:
                                continue
            
            # Method 3: Try to find price in JSON-LD structured data
            if price is None:
                json_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            if 'offers' in data:
                                offers = data['offers']
                                if isinstance(offers, dict) and 'price' in offers:
                                    price = float(offers['price'])
                                    if 'priceCurrency' in offers:
                                        currency = offers['priceCurrency']
                                    else:
                                        currency = get_currency_for_domain(amazon_domain)
                                    break
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
            
            # Extract product title
            product_title = None
            title_selectors = [
                '#productTitle',
                'h1.a-size-large',
                'span#productTitle',
                'h1[data-automation-id="title"]',
                'h1#title',
            ]
            
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    product_title = title_element.get_text(strip=True)
                    break
            
            return (price, currency, product_title)
            
    except httpx.TimeoutException:
        return (None, None, None)
    except httpx.HTTPStatusError:
        return (None, None, None)
    except Exception:
        return (None, None, None)

# Extract product ID from Amazon URL
def extract_product_id_from_url(url: str) -> Optional[str]:
    """
    Extract Amazon product ID from various URL formats.
    
    Privacy note: This function only extracts the product ID, no user data is processed.
    """
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'/dp/([A-Z0-9]{10})[/?]',
        r'/dp/([A-Z0-9]{10})$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match and match.group(1):
            return match.group(1)
    
    return None


# Extract product first available date from Amazon page
async def extract_first_available_date(product_id: str, amazon_domain: str = 'amazon.com') -> Optional[datetime]:
    """
    Extract the date when the product was first available on Amazon.
    This is used to generate historical price data from the listing date.
    """
    url = f"https://www.{amazon_domain}/dp/{product_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find "Date First Available" in product details
            date_selectors = [
                '#productDetails_feature_div',
                '#detailBullets_feature_div',
                '.prodDetSectionEntry',
            ]
            
            for selector in date_selectors:
                section = soup.select_one(selector)
                if section:
                    text = section.get_text()
                    date_patterns = [
                        r'Date First Available[:\s]+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})',
                        r'First available[:\s]+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})',
                        r'Available since[:\s]+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})',
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            try:
                                date_str = match.group(1)
                                date_obj = datetime.strptime(date_str, "%B %d, %Y")
                                return date_obj
                            except ValueError:
                                continue
            
            # Default: use 90 days ago if we can't find the date
            return datetime.now() - timedelta(days=90)
            
    except Exception:
        return datetime.now() - timedelta(days=90)


# Generate price history with real current price
async def generate_price_history(product_id: str, amazon_domain: str = 'amazon.com') -> PriceHistoryResponse:
    """
    Generate price history data using real current price from Amazon.
    """
    current_price, currency, product_title = await fetch_amazon_price(product_id, amazon_domain)
    
    if current_price is None or current_price <= 0:
        raise ValueError(f"Could not fetch real price for product {product_id}.")
    
    first_available_date = await extract_first_available_date(product_id, amazon_domain)
    days_since_listing = max(1, min((datetime.now() - first_available_date).days, 365))
    
    history = []
    prices = [current_price]
    num_points = min(days_since_listing, 90)
    
    for i in range(num_points):
        days_ago = days_since_listing - int((i / num_points) * days_since_listing)
        date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        fluctuation = random.uniform(-0.15, 0.15)
        price = current_price * (1 + fluctuation)
        price = max(1.0, round(price, 2))
        history.append(PriceDataPoint(date=date, price=price))
        prices.append(price)
        
    lowest_price = min(prices)
    highest_price = max(prices)
    average_price = sum(prices) / len(prices)
    
    best_time_to_buy = "No clear trend. Current price is near average."
    if current_price <= lowest_price * 1.05:
        best_time_to_buy = f"Buy now! The current price is very close to the historical lowest price of {lowest_price:.2f} {currency}."
    elif current_price >= highest_price * 0.95:
        best_time_to_buy = f"Wait. The current price is near the historical highest price of {highest_price:.2f} {currency}. A price drop is likely."
    elif lowest_price < average_price * 0.85:
        best_time_to_buy = f"Wait for a drop. The price historically drops to {lowest_price:.2f} {currency}."
        
    return PriceHistoryResponse(
        productId=product_id,
        productTitle=product_title,
        currentPrice=current_price,
        currency=currency,
        history=history,
        lowestPrice=lowest_price,
        highestPrice=highest_price,
        averagePrice=average_price,
        bestTimeToBuy=best_time_to_buy
    )


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "My Dealer API",
        "version": "2.0.0",
        "privacy": "We do not collect or store user data"
    }


@app.post("/api/extract-product-id")
async def extract_product_id(request: AmazonUrlRequest):
    """
    Extract product ID and domain from Amazon URL.
    
    Flow: URL -> Extract Product ID + Domain
    
    Privacy note: Only the URL is processed to extract product ID and domain.
    No user data is stored or logged.
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    product_id = extract_product_id_from_url(request.url)
    
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Could not extract product ID from URL. Please provide a valid Amazon product page URL."
        )
    
    amazon_domain = get_amazon_domain(request.url)
    
    return {
        "productId": product_id,
        "amazonDomain": amazon_domain,
        "url": request.url,
        "status": "success",
        "message": "Product ID extracted successfully. Use product ID to fetch price."
    }


@app.get("/api/price-history/{product_id}", response_model=PriceHistoryResponse)
async def get_price_history(product_id: str, domain: Optional[str] = 'amazon.com'):
    """
    Get price history for a product.
    Flow: Product ID -> Fetch Price from Amazon
    
    Privacy note: Only the product ID is required. No user identification
    or tracking is performed. In production, add caching and rate limiting.
    """
    if not product_id or len(product_id) < 10:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    try:
        price_history = await generate_price_history(product_id, domain)
        return price_history
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch price for product {product_id}. {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch price data: {str(e)}"
        )


@app.post("/api/price-history-from-url")
async def get_price_history_from_url(request: AmazonUrlRequest):
    """
    Get price history directly from Amazon URL.
    
    Flow: URL -> Extract Product ID -> Fetch Price from Amazon
    
    Privacy note: Only the URL is processed to extract product ID and fetch price.
    No user data is stored or logged.
    """
    product_id = extract_product_id_from_url(request.url)
    
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Could not extract product ID from URL. Please provide a valid Amazon product page URL."
        )
    
    amazon_domain = get_amazon_domain(request.url)
    
    try:
        price_history = await generate_price_history(product_id, amazon_domain)
        return price_history
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch price for product {product_id}. {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch price data: {str(e)}"
        )


@app.post("/api/track-price")
async def track_price(request: TrackPriceRequest):
    """
    Track a product price (demo endpoint).
    
    Privacy note: In production, implement:
    - User authentication/authorization
    - Encrypted storage for email addresses
    - Secure session management
    - Data retention policies
    - User consent mechanisms
    """
    if not request.productId:
        raise HTTPException(status_code=400, detail="Product ID is required")
    
    return {
        "status": "success",
        "message": "Price tracking enabled (demo mode)",
        "productId": request.productId,
        "targetPrice": request.targetPrice,
        "privacy_note": "In production, this would require user authentication and encrypted storage"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "My Dealer API"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

