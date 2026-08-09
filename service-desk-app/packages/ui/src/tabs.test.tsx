import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Tabs, TabsContent, TabsList, TabsTrigger } from './tabs';

describe('Tabs', () => {
  it('renders triggers and switches the active content', () => {
    render(
      <Tabs defaultValue="first">
        <TabsList aria-label="Example tabs">
          <TabsTrigger value="first">First</TabsTrigger>
          <TabsTrigger value="second">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="first">First panel</TabsContent>
        <TabsContent value="second">Second panel</TabsContent>
      </Tabs>,
    );

    const first = screen.getByRole('tab', { name: 'First' });
    const second = screen.getByRole('tab', { name: 'Second' });
    expect(first).toHaveClass('sd-tabs-trigger');
    expect(first).toHaveAttribute('data-state', 'active');

    fireEvent.mouseDown(second, { button: 0, ctrlKey: false });
    fireEvent.click(second);

    expect(second).toHaveAttribute('data-state', 'active');
    expect(screen.getByText('Second panel')).toBeVisible();
  });
});
