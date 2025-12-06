const path = require('path');
const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

// Webpack magic happens here
module.exports = {
  entry: {
    content: './src/content/content.tsx',
    popup: './src/popup/popup.tsx',
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js',
    clean: true,
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './src/popup/popup.html',
      filename: 'popup.html',
      chunks: ['popup'],
    }),
    new CopyWebpackPlugin({
      patterns: [
        { from: 'manifest.json', to: 'manifest.json' },
        { from: 'src/content/content.css', to: 'content.css' },
      ],
    }),
    // Inject API_URL from environment variable
    new webpack.DefinePlugin({
      'API_URL': JSON.stringify(process.env.API_URL || 'http://localhost:8000'),
    }),
  ],
  // Production: no source maps for smaller bundle
  devtool: process.env.NODE_ENV === 'production' ? false : 'source-map',
  optimization: {
    // Tree-shaking and code splitting for recharts
    usedExports: true,
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        recharts: {
          test: /[\\/]node_modules[\\/]recharts[\\/]/,
          name: 'recharts',
          priority: 20,
          enforce: true,
        },
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10,
          reuseExistingChunk: true,
        },
      },
    },
  },
};
