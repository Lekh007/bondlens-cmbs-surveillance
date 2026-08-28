import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// jsdom does not implement IntersectionObserver (used by Sidebar's
// scroll-spy nav highlighting) - stub it so component tests don't crash.
class IntersectionObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}

vi.stubGlobal('IntersectionObserver', IntersectionObserverStub)
