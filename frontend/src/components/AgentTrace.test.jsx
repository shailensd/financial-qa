import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AgentTrace from './AgentTrace';

describe('AgentTrace Component', () => {
  const mockAgentTrace = {
    plan: [
      {
        tool: 'LOOKUP',
        inputs: {
          entity: 'Apple',
          attribute: 'revenue'
        }
      },
      {
        tool: 'CALCULATE',
        inputs: {
          expression: '383285 / 358614'
        }
      }
    ],
    tool_results: [
      {
        tool: 'LOOKUP',
        output: 'Apple revenue was $383.3B in FY2023'
      },
      {
        tool: 'CALCULATE',
        output: { result: 1.0688 }
      }
    ],
    critic_verdict: 'approved',
    repair_count: 0
  };

  it('renders nothing when no agent trace is provided', () => {
    const { container } = render(<AgentTrace agentTrace={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when agentTrace prop is undefined', () => {
    const { container } = render(<AgentTrace />);
    expect(container).toBeEmptyDOMElement();
  });

  it('displays critic verdict badge in collapsed header', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('displays repair count badge in collapsed header', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    expect(screen.getByText('0 repairs')).toBeInTheDocument();
  });

  it('displays singular "repair" when repair_count is 1', () => {
    const traceWithOneRepair = {
      ...mockAgentTrace,
      repair_count: 1
    };
    render(<AgentTrace agentTrace={traceWithOneRepair} />);
    expect(screen.getByText('1 repair')).toBeInTheDocument();
  });

  it('displays plural "repairs" when repair_count is not 1', () => {
    const traceWithMultipleRepairs = {
      ...mockAgentTrace,
      repair_count: 2
    };
    render(<AgentTrace agentTrace={traceWithMultipleRepairs} />);
    expect(screen.getByText('2 repairs')).toBeInTheDocument();
  });

  it('applies green color to approved verdict', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const verdictBadge = screen.getAllByText('Approved')[0];
    expect(verdictBadge).toHaveClass('badge', 'badge-green');
  });

  it('applies yellow color to repair_numerical verdict', () => {
    const traceWithRepairNumerical = {
      ...mockAgentTrace,
      critic_verdict: 'repair_numerical'
    };
    render(<AgentTrace agentTrace={traceWithRepairNumerical} />);
    const verdictBadge = screen.getAllByText('Repair Numerical')[0];
    expect(verdictBadge).toHaveClass('badge', 'badge-yellow');
  });

  it('applies orange color to repair_citation verdict', () => {
    const traceWithRepairCitation = {
      ...mockAgentTrace,
      critic_verdict: 'repair_citation'
    };
    render(<AgentTrace agentTrace={traceWithRepairCitation} />);
    const verdictBadge = screen.getAllByText('Repair Citation')[0];
    expect(verdictBadge).toHaveClass('badge', 'badge-orange');
  });

  it('applies green color to repair count of 0', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const repairBadge = screen.getByText('0 repairs');
    expect(repairBadge).toHaveClass('badge', 'badge-green');
  });

  it('applies yellow color to repair count of 1', () => {
    const traceWithOneRepair = {
      ...mockAgentTrace,
      repair_count: 1
    };
    render(<AgentTrace agentTrace={traceWithOneRepair} />);
    const repairBadge = screen.getByText('1 repair');
    expect(repairBadge).toHaveClass('badge', 'badge-yellow');
  });

  it('applies red color to repair count of 2 or more', () => {
    const traceWithMultipleRepairs = {
      ...mockAgentTrace,
      repair_count: 2
    };
    render(<AgentTrace agentTrace={traceWithMultipleRepairs} />);
    const repairBadge = screen.getByText('2 repairs');
    expect(repairBadge).toHaveClass('badge', 'badge-red');
  });

  it('is collapsed by default', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    expect(screen.queryByText('Planner · 2 steps')).not.toBeInTheDocument();
    expect(screen.queryByText('Tool Results · 2')).not.toBeInTheDocument();
  });

  it('expands when header is clicked', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText('Planner · 2 steps')).toBeInTheDocument();
    expect(screen.getByText('Tool Results · 2')).toBeInTheDocument();
  });

  it('collapses when header is clicked again', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText('Planner · 2 steps')).toBeInTheDocument();
    fireEvent.click(headerButton);
    expect(screen.queryByText('Planner · 2 steps')).not.toBeInTheDocument();
  });

  it('adds "open" class to chevron icon when expanded', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    const chevronIcon = headerButton.querySelector('svg:last-child');
    expect(chevronIcon).not.toHaveClass('open');
    fireEvent.click(headerButton);
    expect(chevronIcon).toHaveClass('open');
  });

  it('sets aria-expanded attribute correctly', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    expect(headerButton).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(headerButton);
    expect(headerButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('displays all plan steps when expanded', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getAllByText('LOOKUP').length).toBeGreaterThan(0);
    expect(screen.getAllByText('CALCULATE').length).toBeGreaterThan(0);
  });

  it('displays tool inputs as formatted JSON', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    const planSection = screen.getByText('Planner · 2 steps').closest('div').parentElement;
    expect(planSection.textContent).toContain('entity');
    expect(planSection.textContent).toContain('Apple');
    expect(planSection.textContent).toContain('attribute');
    expect(planSection.textContent).toContain('revenue');
  });

  it('displays all tool results when expanded', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText(/Apple revenue was \$383.3B/)).toBeInTheDocument();
  });

  it('displays string outputs as plain text', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText(/Apple revenue was \$383.3B in FY2023/)).toBeInTheDocument();
  });

  it('displays object outputs as formatted JSON', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText(/result/)).toBeInTheDocument();
    expect(screen.getByText(/1.0688/)).toBeInTheDocument();
  });

  it('displays critic verdict in detail section', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    const verdictElements = screen.getAllByText('Approved');
    expect(verdictElements.length).toBeGreaterThanOrEqual(2);
  });

  it('displays repair count in detail section', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText('Repair iterations')).toBeInTheDocument();
    const repairCounts = screen.getAllByText('0');
    expect(repairCounts.length).toBeGreaterThan(0);
  });

  it('handles empty plan array', () => {
    const traceWithEmptyPlan = { ...mockAgentTrace, plan: [] };
    render(<AgentTrace agentTrace={traceWithEmptyPlan} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.queryByText(/Planner/)).not.toBeInTheDocument();
  });

  it('handles empty tool_results array', () => {
    const traceWithEmptyResults = { ...mockAgentTrace, tool_results: [] };
    render(<AgentTrace agentTrace={traceWithEmptyResults} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.queryByText(/Tool Results/)).not.toBeInTheDocument();
  });

  it('handles missing critic_verdict property', () => {
    const traceWithoutVerdict = {
      plan: mockAgentTrace.plan,
      tool_results: mockAgentTrace.tool_results,
      repair_count: 0
    };
    render(<AgentTrace agentTrace={traceWithoutVerdict} />);
    expect(screen.getAllByText('Unknown').length).toBeGreaterThan(0);
  });

  it('handles missing repair_count property', () => {
    const traceWithoutRepairCount = {
      plan: mockAgentTrace.plan,
      tool_results: mockAgentTrace.tool_results,
      critic_verdict: 'approved'
    };
    render(<AgentTrace agentTrace={traceWithoutRepairCount} />);
    expect(screen.getByText('0 repairs')).toBeInTheDocument();
  });

  it('handles plan step without inputs', () => {
    const traceWithNoInputs = {
      plan: [{ tool: 'LOOKUP' }],
      tool_results: [],
      critic_verdict: 'approved',
      repair_count: 0
    };
    render(<AgentTrace agentTrace={traceWithNoInputs} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText('LOOKUP')).toBeInTheDocument();
  });

  it('handles tool result without output', () => {
    const traceWithNoOutput = {
      plan: [],
      tool_results: [{ tool: 'LOOKUP' }],
      critic_verdict: 'approved',
      repair_count: 0
    };
    render(<AgentTrace agentTrace={traceWithNoOutput} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText('LOOKUP')).toBeInTheDocument();
  });

  it('handles complex nested JSON in tool inputs', () => {
    const traceWithComplexInputs = {
      plan: [{
        tool: 'COMPARE',
        inputs: {
          entity1: 'Apple',
          period1: 'FY2023',
          entity2: 'Microsoft',
          period2: 'FY2023'
        }
      }],
      tool_results: [],
      critic_verdict: 'approved',
      repair_count: 0
    };
    render(<AgentTrace agentTrace={traceWithComplexInputs} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText(/entity1/)).toBeInTheDocument();
    expect(screen.getByText(/Apple/)).toBeInTheDocument();
    expect(screen.getByText(/entity2/)).toBeInTheDocument();
    expect(screen.getByText(/Microsoft/)).toBeInTheDocument();
  });

  it('handles very long tool outputs', () => {
    const traceWithLongOutput = {
      plan: [],
      tool_results: [{
        tool: 'LOOKUP',
        output: 'A'.repeat(1000)
      }],
      critic_verdict: 'approved',
      repair_count: 0
    };
    render(<AgentTrace agentTrace={traceWithLongOutput} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    expect(screen.getByText('A'.repeat(1000))).toBeInTheDocument();
  });

  it('uses trace-pre class for outputs to preserve whitespace and style JSON', () => {
    const traceWithWhitespace = {
      plan: [],
      tool_results: [{
        tool: 'LOOKUP',
        output: 'Line 1\n\nLine 2\n\nLine 3'
      }],
      critic_verdict: 'approved',
      repair_count: 0
    };
    render(<AgentTrace agentTrace={traceWithWhitespace} />);
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    const outputElement = screen.getByText(/Line 1/);
    expect(outputElement).toHaveClass('trace-pre');
  });
});
