# My Dealer 2.0 - Streamlined Extension

A lightweight, optimized version of the My Dealer Amazon Price Tracker browser extension. This version contains only the essential files needed for the extension to function, with all unnecessary files removed.

## What's Different in 2.0

- ✅ **Removed** all documentation files (historical .md files)
- ✅ **Removed** source maps and TypeScript declarations from dist
- ✅ **Removed** unused scripts (copy-assets.js, extension_logic.js)
- ✅ **Removed** redundant icon files (SVG placeholders)
- ✅ **Removed** unused virtual environments
- ✅ **Optimized** build configuration (no source maps in production)
- ✅ **Streamlined** project structure

## Project Structure

```
MyDealer 2.0/
├── extension/          # Browser extension
│   ├── src/           # Source files (TypeScript/React)
│   ├── dist/          # Built files (runtime)
│   ├── webpack.config.js
│   ├── tsconfig.json
│   ├── package.json
│   └── manifest.json
└── backend/           # FastAPI backend
    ├── main.py
    └── requirements.txt
```

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000`

### 2. Extension Setup

```bash
cd extension
npm install
npm run build
```

### 3. Load Extension

1. Open Chrome/Edge/Brave
2. Go to `chrome://extensions/`
3. Enable **Developer mode**
4. Click **Load unpacked**
5. Select the `extension/dist` folder

## Building

- **Production build:** `npm run build` (no source maps, optimized)
- **Development build:** `npm run dev` (with source maps, watch mode)

## Files Included

### Extension Source (`extension/src/`)
- `content/` - Content script that injects price chart
- `popup/` - Extension popup UI
- `components/` - React components (PriceChart)
- `types/` - TypeScript type definitions
- `config.ts` - Configuration

### Extension Build Config
- `webpack.config.js` - Build configuration
- `tsconfig.json` - TypeScript configuration
- `package.json` - Dependencies
- `manifest.json` - Extension manifest
- `create-icons.js` - Icon generation script

### Extension Runtime (`extension/dist/`)
- `content.js` - Compiled content script
- `content.css` - Content styles
- `popup.js` - Compiled popup script
- `popup.html` - Popup HTML
- `manifest.json` - Extension manifest
- `icons/` - Extension icons (PNG)

### Backend
- `main.py` - FastAPI server
- `requirements.txt` - Python dependencies

## What Was Removed

- Documentation files (all .md files except this README)
- Source maps (.map files) in production builds
- TypeScript declarations (.d.ts files) in dist
- License text files in dist
- Unused scripts (copy-assets.js, extension_logic.js)
- Redundant icon files (SVG if PNG exists)
- Virtual environments (venv/)
- node_modules (regenerate with npm install)

## Performance Benefits

- **Smaller bundle size** - No source maps or declarations
- **Faster load time** - Fewer files to process
- **Cleaner structure** - Only essential files
- **Reduced disk space** - ~200-500 MB saved

## Notes

- The extension requires the backend API to be running
- Icons are generated as SVG placeholders - replace with PNG for production
- Source files are needed for building, but not for runtime
- The `dist/` folder contains what the browser actually uses

## Version

**2.0.0** - Streamlined and optimized version

