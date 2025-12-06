const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Create icons directory if it doesn't exist
const iconsDir = path.join(__dirname, 'dist', 'icons');
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

// Create simple SVG icon
const createSVGIcon = (size) => {
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

// Convert SVG to PNG using ImageMagick or sharp
function convertSVGToPNG(svgPath, pngPath, size) {
  try {
    // Try ImageMagick first (convert command)
    execSync(`convert "${svgPath}" -resize ${size}x${size} "${pngPath}"`, { stdio: 'ignore' });
    return true;
  } catch (e) {
    try {
      // Try sharp if available
      const sharp = require('sharp');
      const svgBuffer = fs.readFileSync(svgPath);
      sharp(svgBuffer)
        .resize(size, size)
        .png()
        .toFile(pngPath)
        .then(() => {
          console.log(`Created icon${size}.png`);
        })
        .catch(() => {
          return false;
        });
      return true;
    } catch (e2) {
      return false;
    }
  }
}

// Create icons
[16, 48, 128].forEach(size => {
  const svgPath = path.join(iconsDir, `icon${size}.svg`);
  const pngPath = path.join(iconsDir, `icon${size}.png`);
  
  // Create SVG
  const svg = createSVGIcon(size);
  fs.writeFileSync(svgPath, svg);
  
  // Try to convert to PNG
  const converted = convertSVGToPNG(svgPath, pngPath, size);
  
  if (!converted) {
    // If conversion failed, create a note
    const notePath = path.join(iconsDir, 'README.txt');
    if (!fs.existsSync(notePath)) {
      fs.writeFileSync(notePath, 
        `PNG Icon Conversion Required\n` +
        `============================\n\n` +
        `The extension requires PNG icons. SVG files have been created.\n\n` +
        `To convert to PNG, install ImageMagick and run:\n` +
        `  convert icon16.svg -resize 16x16 icon16.png\n` +
        `  convert icon48.svg -resize 48x48 icon48.png\n` +
        `  convert icon128.svg -resize 128x128 icon128.png\n\n` +
        `Or use an online converter like cloudconvert.com\n`
      );
    }
    console.log(`Created icon${size}.svg (PNG conversion needed)`);
  } else {
    console.log(`Created icon${size}.png`);
  }
});

console.log('Icons created successfully!');
