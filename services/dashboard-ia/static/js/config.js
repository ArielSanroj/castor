// API Configuration for Castor Elecciones
// This file provides a configurable API base URL that can be set via environment variable
// For Vercel deployment, set NEXT_PUBLIC_API_BASE_URL in Vercel environment variables
// For local development, it defaults to empty string (relative URLs)

(function() {
    'use strict';
    
    // Get API base URL from environment variable or use default
    // In Vercel, we'll inject this via a script tag in the HTML templates
    // For now, check if it's set in window object (injected by HTML)
    const getApiBaseUrl = function() {
        // Check if API_BASE_URL is set in window (injected by HTML template)
        if (window.API_BASE_URL) {
            // If it's empty or just whitespace, return empty string
            const url = String(window.API_BASE_URL).trim();
            return url === '' ? '' : url;
        }
        
        // Check meta tag for API base URL (for Vercel static deployment)
        const metaTag = document.querySelector('meta[name="api-base-url"]');
        if (metaTag && metaTag.content) {
            return metaTag.content.trim();
        }
        
        // Check if NEXT_PUBLIC_API_BASE_URL is available (Vercel convention)
        if (typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_API_BASE_URL) {
            return process.env.NEXT_PUBLIC_API_BASE_URL;
        }
        
        // Default: empty string for relative URLs (works with same-origin)
        // For ngrok backend, this should be set to the ngrok URL: https://castorelecciones.ngrok.app
        return '';
    };
    
    // Export API base URL
    window.API_CONFIG = {
        baseUrl: getApiBaseUrl(),
        
        // Helper function to build full API URL
        apiUrl: function(path) {
            const base = this.baseUrl;
            // Remove trailing slash from base if present
            const cleanBase = base.endsWith('/') ? base.slice(0, -1) : base;
            // Ensure path starts with /
            const cleanPath = path.startsWith('/') ? path : '/' + path;
            return cleanBase + cleanPath;
        }
    };
    
    // Log configuration in development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('API Configuration:', window.API_CONFIG);
    }
})();

