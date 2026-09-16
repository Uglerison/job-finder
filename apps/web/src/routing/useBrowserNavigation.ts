import { useCallback, useEffect, useState } from 'react';
import { normalizePath, type AppPath } from '../routes';

function currentPath(): AppPath {
  return normalizePath(globalThis.location?.pathname ?? '/');
}

function scrollToTop(): void {
  if (globalThis.navigator?.userAgent.toLowerCase().includes('jsdom')) {
    return;
  }
  try {
    window.scrollTo({ behavior: 'auto', top: 0 });
  } catch {
    // Scrolling is a progressive enhancement for browser navigation.
  }
}

export function useBrowserNavigation() {
  const [pathname, setPathname] = useState<AppPath>(currentPath);

  useEffect(() => {
    const handlePopState = () => {
      setPathname(currentPath());
      scrollToTop();
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = useCallback((path: AppPath) => {
    if (currentPath() !== path) {
      window.history.pushState({}, '', path);
    }
    setPathname(path);
    scrollToTop();
  }, []);

  return { navigate, pathname };
}
