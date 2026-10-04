import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { AppNav, BottomNav, buildStudentNavItems, isCoursePracticalLocation, isNavItemActive } from './App';

afterEach(cleanup);

describe('student navigation', () => {
  it('keeps beginner destinations primary and legacy routes secondary', () => {
    const items = buildStudentNavItems(true);
    expect(items.slice(0, 4).map((item) => [item.label, item.to])).toEqual([
      ['Today', '/'], ['My Course', '/learning-v2'], ['Service Desk', '/service-desk'], ['Progress', '/progress'],
    ]);
    expect(items.some((item) => item.label === 'Learning V2')).toBe(false);
    expect(items.find((item) => item.label === 'Extra Practice')?.children).toContainEqual({ to: '/learning-path', label: 'Practice path' });
  });

  it('shows every learner destination in the mobile primary navigation', () => {
    render(<MemoryRouter initialEntries={['/learning-v2']}><BottomNav items={buildStudentNavItems(true)} /></MemoryRouter>);
    const nav = screen.getByRole('navigation', { name: 'Mobile primary navigation' });
    expect(nav.querySelectorAll('a')).toHaveLength(5);
    expect(screen.getByRole('link', { name: 'My Course', current: 'page' })).toHaveAttribute('href', '/learning-v2');
    expect(screen.getByRole('link', { name: 'Extra Practice' })).toHaveAttribute('href', '/learning-path');
    expect(screen.getByRole('link', { name: 'Service Desk' })).toHaveAttribute('href', '/service-desk');
    expect(nav).not.toHaveTextContent('Network+');
    expect(nav).not.toHaveTextContent('Security+');
  });

  it('marks the Progress destination active at its existing /skills route', () => {
    render(<MemoryRouter initialEntries={['/skills']}><AppNav items={buildStudentNavItems(true)} isAdminRoute={false} /></MemoryRouter>);
    expect(screen.getByRole('link', { name: 'Progress', current: 'page' })).toBeInTheDocument();
  });

  it('keeps the admin review queue distinct from the lab management destination', () => {
    const review = { to: '/admin/labs#pending-reviews', label: 'Pending Reviews' };
    const labs = { to: '/admin/labs', label: 'Labs' };
    expect(isNavItemActive(review, { pathname: '/admin/labs', search: '', hash: '#pending-reviews' })).toBe(true);
    expect(isNavItemActive(labs, { pathname: '/admin/labs', search: '', hash: '#pending-reviews' })).toBe(false);
    expect(isNavItemActive(review, { pathname: '/admin/labs', search: '', hash: '' })).toBe(false);
    expect(isNavItemActive(labs, { pathname: '/admin/labs', search: '', hash: '' })).toBe(true);
  });

  it('marks a required course practical as My Course on desktop and mobile', () => {
    const path = '/labs/55?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation';
    expect(isCoursePracticalLocation({ pathname: '/labs/55', search: '?v2Module=stage4&v2Assessment=practical' })).toBe(true);
    expect(isCoursePracticalLocation({ pathname: '/labs/55', search: '' })).toBe(false);
    const items = buildStudentNavItems(true);
    render(<MemoryRouter initialEntries={[path]}><AppNav items={items} isAdminRoute={false} /><AppNav items={items} isAdminRoute={false} mobile /><BottomNav items={items} /></MemoryRouter>);
    expect(screen.getAllByRole('link', { name: 'My Course', current: 'page' })).toHaveLength(3);
    expect(screen.queryByRole('link', { name: 'Labs', current: 'page' })).not.toBeInTheDocument();
  });
});
