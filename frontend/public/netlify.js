// This script fixes issues with Netlify deployment
// It ensures that no custom scripts are loaded that might cause the appendChild error

window.addEventListener('DOMContentLoaded', () => {
  // Check if we're on Netlify
  const isNetlify = window.location.hostname.includes('netlify.app');
  
  if (isNetlify) {
    // Remove any problematic scripts that might be injected by Netlify
    document.querySelectorAll('script').forEach(script => {
      if (script.src.includes('featureScript.js') || script.src.includes('index.js')) {
        script.remove();
      }
    });
    
    console.log('Netlify deployment script initialized');
  }
});