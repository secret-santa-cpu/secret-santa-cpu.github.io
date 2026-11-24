import { describe, it, expect } from 'vitest';

import { buildEmailExport } from './links';

describe('buildEmailExport', () => {
  it('should export givers with their email and link', () => {
    const result = buildEmailExport([
      { giver: 'Alice', email: 'alice@example.com', link: 'https://example.com/pairing?from=Alice&to=abc' },
      { giver: 'Bob', email: ' bob@example.com ', link: 'https://example.com/pairing?from=Bob&to=def' },
    ]);

    expect(result).toEqual({
      version: 1,
      assignments: [
        { giver: 'Alice', email: 'alice@example.com', link: 'https://example.com/pairing?from=Alice&to=abc' },
        { giver: 'Bob', email: 'bob@example.com', link: 'https://example.com/pairing?from=Bob&to=def' },
      ],
    });
  });

  it('should export missing or invalid emails as null', () => {
    const result = buildEmailExport([
      { giver: 'Alice', link: 'https://example.com/pairing?from=Alice&to=abc' },
      { giver: 'Bob', email: 'not-an-email', link: 'https://example.com/pairing?from=Bob&to=def' },
    ]);

    expect(result.assignments.map(entry => entry.email)).toEqual([null, null]);
  });
});
