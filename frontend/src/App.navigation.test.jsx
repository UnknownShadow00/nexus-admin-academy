import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppNav, buildStudentNavItems, isCoursePracticalLocation } from './App';

describe('student navigation', () => {
  it('keeps beginner destinations primary and legacy routes secondary', () => {
    const items = buildStudentNavItems(true);
    expect(items.slice(0, 4).map((item) => [item.label, item.to])).toEqual([
      ['Today', '/'], ['Service Desk', '/service-desk'], ['Progress', '/progress'], ['My Course', '/learning-v2'],
    ]);
    expect(items.some((item) => item.label === 'Learning V2')).toBe(false);
    expect(items.find((item) => item.label === 'Extra Practice')?.children).toContainEqual({ to: '/learning-path', label: 'Practice path' });
  });

  it('marks a required course practical as My Course on desktop and mobile', () => {
    const path = '/labs/55?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation';
    expect(isCoursePracticalLocation({ pathname: '/labs/55', search: '?v2Module=stage4&v2Assessment=practical' })).toBe(true);
    expect(isCoursePracticalLocation({ pathname: '/labs/55', search: '' })).toBe(false);
    const items = buildStudentNavItems(true);
    render(<MemoryRouter initialEntries={[path]}><AppNav items={items} isAdminRoute={false} /><AppNav items={items} isAdminRoute={false} mobile /></MemoryRouter>);
    expect(screen.getAllByRole('link', { name: 'My Course', current: 'page' })).toHaveLength(2);
    expect(screen.queryByRole('link', { name: 'Labs', current: 'page' })).not.toBeInTheDocument();
  });
});
