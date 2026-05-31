import { useState, useEffect } from 'react';

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Initial check
    checkIfMobile();
    
    // Add event listener for window resize
    window.addEventListener('resize', checkIfMobile);
    
    // Remove event listener on cleanup
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  function checkIfMobile() {
    setIsMobile(window.innerWidth < 768);
  }

  return isMobile;
}