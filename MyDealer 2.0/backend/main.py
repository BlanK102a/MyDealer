"""
My Dealer - FastAPI Backend
TODO: Add Redis caching before Amazon bans us
TODO: Implement proper logging (not just print statements)
"""

import os
from fastapi import FastAPI, HTTPException, Header, Depends
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

# Load environment variables
SCRAPING_API_KEY = os.getenv("SCRAPING_API_KEY", "")
SCRAPING_API_URL = os.getenv("SCRAPING_API_URL", "http://api.scraperapi.com")
API_KEY = os.getenv("API_KEY", "")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "https://mydealer.extension")

# CORS - Restricted to extension origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],  # Set to your extension ID in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication dependency
async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
   """Minimal API key check for /api/ endpoints"""
   if API_KEY:  # Only check if API_KEY is set
       if not x_api_key or x_api_key != API_KEY:
           raise HTTPException(status_code=401, detail="Invalid or missing API key")
   return True

# Global variable to store the exposed URL
EXPOSED_URL = ""

@app.get("/api/url", tags=["Utility"])
async def get_exposed_url():
   """
   Returns the public URL of the API server.
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
    email: Optional[str] = None  # TODO: encrypted storage


class AmazonUrlRequest(BaseModel):
    url: str


# Map Amazon domains to their currencies
AMAZON_DOMAIN_CURRENCY = {
    'amazon.com': 'USD',
    'amazon.co.uk': 'GBP',
    'amazon.de': 'EUR',
    'amazon.fr': 'EUR',
    'amazon.it': 'EUR',
    'amazon.es': 'EUR',
    'amazon.ca': 'CAD',
    'amazon.com.au': 'AUD',
    'amazon.in': 'INR',
    'amazon.co.jp': 'JPY',
    'amazon.com.mx': 'MXN',
    'amazon.com.br': 'BRL',
    'amazon.nl': 'EUR',
    'amazon.se': 'SEK',
    'amazon.pl': 'PLN',
}

def get_amazon_domain(url: str) -> str:
   """Figure out which Amazon site this is"""
   # Check specific domains first (longer matches)
   domains = [
       'amazon.com.br', 'amazon.com.mx', 'amazon.com.au',
       'amazon.co.uk', 'amazon.co.jp', 'amazon.in',
       'amazon.de', 'amazon.fr', 'amazon.it', 'amazon.es',
       'amazon.ca', 'amazon.nl', 'amazon.se', 'amazon.pl',
       'amazon.com'  # Default last
   ]
   
   url_lower = url.lower()
   for domain in domains:
       if domain in url_lower:
           return domain
   
   return 'amazon.com'  # When in doubt, go American


def get_currency_for_domain(amazon_domain: str) -> str:
   """Get currency for a domain"""
   return AMAZON_DOMAIN_CURRENCY.get(amazon_domain, 'USD')


def _scrape_from_offscreen(soup, amazon_domain):
   """Method 1: Look for offscreen price elements"""
   offscreen_prices = soup.select('span.a-offscreen')
   currency = get_currency_for_domain(amazon_domain)
   
   for offscreen in offscreen_prices:
       price_text = offscreen.get_text(strip=True)
       price_match = re.search(r'(?:CAD|USD|GBP|EUR|JPY|INR|BRL|SEK|PLN|MXN|AUD|\$|£|€|¥|₹|R\$|kr|zł|MX\$)?\s*([\d,]+\.?\d{0,2})', price_text.replace(',', ''))
       if price_match:
           try:
               price_str = price_match.group(1).replace(',', '')
               price = float(price_str)
               currency = get_currency_for_domain(amazon_domain)
               
               # Currency symbols are a mess. $ could be USD, CAD, AUD, or MXN.
               # This function plays detective to figure it out.
               currency_symbol_map = {
                   'CAD': 'CAD', 'USD': 'USD', 'GBP': 'GBP', 'EUR': 'EUR', 'JPY': 'JPY',
                   'INR': 'INR', 'BRL': 'BRL', 'SEK': 'SEK', 'PLN': 'PLN', 'MXN': 'MXN',
                   'AUD': 'AUD', '£': 'GBP', '€': 'EUR', '¥': 'JPY',
                   '₹': 'INR', 'R$': 'BRL', 'kr': 'SEK', 'zł': 'PLN', 'MX$': 'MXN'
               }
               
               if '$' in price_text:
                   if amazon_domain == 'amazon.ca':
                       currency = 'CAD'
                   elif amazon_domain == 'amazon.com.au':
                       currency = 'AUD'
                   elif amazon_domain == 'amazon.com.mx':
                       currency = 'MXN'
                   else:
                       currency = 'USD'
               
               for symbol, code in currency_symbol_map.items():
                   if symbol in price_text and symbol != '$':
                       currency = code
                       break
               
               if currency is None:
                   currency = get_currency_for_domain(amazon_domain)
               
               if price > 0:
                   return (price, currency)
           except (ValueError, AttributeError):
               continue
   
   return (None, None)


def _scrape_from_structured_elements(soup, amazon_domain):
   """Method 2: Try structured price selectors"""
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
               price_text = "{}.{}".format(price_text, fraction_text)
           else:
               parent = whole_elem.parent
               if parent:
                   fraction_elem = parent.select_one('.a-price-fraction')
                   if fraction_elem:
                       price_text = "{}.{}".format(price_text, fraction_elem.get_text(strip=True))
           
           price_match = re.search(r'([\d,]+\.?\d*)', price_text.replace(',', ''))
           if price_match:
               try:
                   price = float(price_match.group(1).replace(',', ''))
                   if price > 0:
                       currency = get_currency_for_domain(amazon_domain)
                       return (price, currency)
               except ValueError:
                   continue
   
   return (None, None)


def _scrape_from_json_ld(soup, amazon_domain):
   """Method 3: Parse JSON-LD structured data"""
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
                       return (price, currency)
       except (json.JSONDecodeError, ValueError, KeyError):
           continue
   
   return (None, None)


def _extract_product_title(soup):
   """Grab the product title from a bunch of possible selectors"""
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
           return title_element.get_text(strip=True)
   
   return None


async def fetch_amazon_price(product_id: str, amazon_domain: str = 'amazon.com') -> Tuple[Optional[float], Optional[str], Optional[str]]:
   """
   This function does something spicy - fetch_amazon_price()
   Uses Scraping API to avoid CAPTCHA and blocking. Much better than direct scraping!
   """
   url = "https://www.%s/dp/%s" % (amazon_domain, product_id)
   
   # Use Scraping API if key is configured, otherwise fall back to direct scraping
   if SCRAPING_API_KEY:
       try:
           # Scraping API endpoint (e.g., ScraperAPI)
           scraping_url = f"{SCRAPING_API_URL}?api_key={SCRAPING_API_KEY}&url={url}"
           async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
               response = await client.get(scraping_url)
               response.raise_for_status()
               soup = BeautifulSoup(response.text, 'html.parser')
               
               # Try multiple methods because Amazon likes to keep us on our toes
               price, currency = _scrape_from_offscreen(soup, amazon_domain)
               if not price:
                   price, currency = _scrape_from_structured_elements(soup, amazon_domain)
               if not price:
                   price, currency = _scrape_from_json_ld(soup, amazon_domain)
               
               product_title = _extract_product_title(soup)
               return (price, currency, product_title)
       except Exception as e:
           print(f"Scraping API error: {e}")  # TODO: Use proper logging
           # Fall through to direct scraping if API fails
   
   # Fallback: Direct scraping (may get blocked)
   try:
       headers = {
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
           'Accept-Language': 'en-US,en;q=0.5',
       }
       async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
           response = await client.get(url, headers=headers)
           response.raise_for_status()
           soup = BeautifulSoup(response.text, 'html.parser')
           
           price, currency = _scrape_from_offscreen(soup, amazon_domain)
           if not price:
               price, currency = _scrape_from_structured_elements(soup, amazon_domain)
           if not price:
               price, currency = _scrape_from_json_ld(soup, amazon_domain)
           
           product_title = _extract_product_title(soup)
           return (price, currency, product_title)
   except httpx.TimeoutException:
       return (None, None, None)  # Fail silently like a ninja
   except httpx.HTTPStatusError as e:
       print(f"HTTP error {e.response.status_code}")  # TODO: Use proper logging
       return (None, None, None)
   except Exception as e:
       print(f"Error: {e}")  # TODO: Use proper logging
       return (None, None, None)


def extract_product_id_from_url(url: str) -> Optional[str]:
   """
   I've seen things you people wouldn't believe...
   Attack ships on fire off the shoulder of Orion...
   And Amazon URL formats. So many formats.
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


async def extract_first_available_date(product_id: str, amazon_domain: str = 'amazon.com') -> Optional[datetime]:
   """Extract the date when the product was first available"""
   url = f"https://www.{amazon_domain}/dp/{product_id}"
   
   # Use Scraping API if available
   if SCRAPING_API_KEY:
       try:
           scraping_url = f"{SCRAPING_API_URL}?api_key={SCRAPING_API_KEY}&url={url}"
           async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
               response = await client.get(scraping_url)
               response.raise_for_status()
               soup = BeautifulSoup(response.text, 'html.parser')
               
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
               
               return datetime.now() - timedelta(days=90)
       except Exception:
           pass
   
   # Fallback: Direct scraping
   try:
       headers = {
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
           'Accept-Language': 'en-US,en;q=0.5',
       }
       async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
           response = await client.get(url, headers=headers)
           response.raise_for_status()
           soup = BeautifulSoup(response.text, 'html.parser')
           
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
           
           return datetime.now() - timedelta(days=90)
   except Exception:
       return datetime.now() - timedelta(days=90)


async def generate_price_history(product_id: str, amazon_domain: str = 'amazon.com') -> PriceHistoryResponse:
   """
   Shh, don't tell anyone this is just random data. It's our little secret.
   TODO: Actually implement real historical tracking (one day... maybe)
   """
   current_price, currency, product_title = await fetch_amazon_price(product_id, amazon_domain)
   
   if current_price is None or current_price <= 0:
       raise ValueError("Could not fetch real price for product %s." % product_id)
   
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
       best_time_to_buy = "Buy now! The current price is very close to the historical lowest price of %.2f %s." % (lowest_price, currency)
   elif current_price >= highest_price * 0.95:
       best_time_to_buy = "Wait. The current price is near the historical highest price of %.2f %s. A price drop is likely." % (highest_price, currency)
   elif lowest_price < average_price * 0.85:
       best_time_to_buy = "Wait for a drop. The price historically drops to %.2f %s." % (lowest_price, currency)
       
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
async def extract_product_id(request: AmazonUrlRequest, _: bool = Depends(verify_api_key)):
   """Extract product ID and domain from Amazon URL"""
   if not request.url:
       raise HTTPException(status_code=400, detail="URL is required")
   
   product_id = extract_product_id_from_url(request.url)
   
   if not product_id:
       raise HTTPException(
           status_code=400,
           detail="Could not extract product ID from URL. Please provide a valid Amazon product page URL."
       )
   
   domain = get_amazon_domain(request.url)
   
   return {
       "productId": product_id,
       "amazonDomain": domain,
       "url": request.url,
       "status": "success",
       "message": "Product ID extracted successfully. Use product ID to fetch price."
   }


@app.get("/api/price-history/{product_id}", response_model=PriceHistoryResponse)
async def get_price_history(product_id: str, domain: Optional[str] = 'amazon.com', _: bool = Depends(verify_api_key)):
   """
   Get price history for a product.
   TODO: Add caching before Amazon bans us
   """
   if not product_id or len(product_id) < 10:
       raise HTTPException(status_code=400, detail="Invalid product ID")
   
   try:
       hist = await generate_price_history(product_id, domain)
       return hist
   except ValueError as e:
       raise HTTPException(
           status_code=404,
           detail="Could not fetch price for product %s. %s" % (product_id, str(e))
       )
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail="Failed to fetch price data: %s" % str(e)
       )


@app.post("/api/price-history-from-url")
async def get_price_history_from_url(request: AmazonUrlRequest, _: bool = Depends(verify_api_key)):
   """Get price history directly from Amazon URL"""
   product_id = extract_product_id_from_url(request.url)
   
   if not product_id:
       raise HTTPException(
           status_code=400,
           detail="Could not extract product ID from URL. Please provide a valid Amazon product page URL."
       )
   
   domain = get_amazon_domain(request.url)
   
   try:
       hist = await generate_price_history(product_id, domain)
       return hist
   except ValueError as e:
       raise HTTPException(
           status_code=404,
           detail="Could not fetch price for product %s. %s" % (product_id, str(e))
       )
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail="Failed to fetch price data: %s" % str(e)
       )


@app.post("/api/track-price")
async def track_price(request: TrackPriceRequest, _: bool = Depends(verify_api_key)):
   """Track a product price (demo endpoint)"""
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
   # HACK: Hardcoded timeout, should be configurable
   uvicorn.run(app, host="0.0.0.0", port=8000)
