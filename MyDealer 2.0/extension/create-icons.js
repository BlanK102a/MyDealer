const fs = require('fs');
const path = require('path');

// Create icons directory if it doesn't exist
const iconsDir = path.join(__dirname, 'dist', 'icons');
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

// Create simple placeholder icons (SVG)
// In production, replace with proper PNG icon files
const createPlaceholderIcon = (size) => {
  // Simple SVG icon - price chart representation
  return `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
    <rect width="${size}" height="${size}" fill="#2563eb" rx="${size/8}"/>
    <path d="M ${size*0.2} ${size*0.7} L ${size*0.4} ${size*0.5} L ${size*0.6} ${size*0.6} L ${size*0.8} ${size*0.3}" 
          stroke="white" stroke-width="${size/20}" fill="none" stroke-linecap="round"/>
    <circle cx="${size*0.2}" cy="${size*0.7}" r="${size/16}" fill="white"/>
    <circle cx="${size*0.4}" cy="${size*0.5}" r="${size/16}" fill="white"/>
    <circle cx="${size*0.6}" cy="${size*0.6}" r="${size/16}" fill="white"/>
    <circle cx="${size*0.8}" cy="${size*0.3}" r="${size/16}" fill="white"/>
  </svg>`;
};

// Create placeholder icons
// Note: Manifest requires PNG, but we create SVG as placeholders
// Users should replace with proper PNG files
[16, 48, 128].forEach(size => {
  const svgPath = path.join(iconsDir, `icon${size}.svg`);
  const pngPath = path.join(iconsDir, `icon${size}.png`);
  
  // Create SVG placeholder
  fs.writeFileSync(svgPath, createPlaceholderIcon(size));
  
  console.log(`Created icon${size}.svg (PNG required for production)`);
});

console.log('Icons created successfully!');
console.log('Note: Replace with proper PNG icons for production.');

