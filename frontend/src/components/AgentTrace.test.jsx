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

  it('renders empty state when no agent trace is provided', () => {
    render(<AgentTrace agentTrace={null} />);
    
    expect(screen.getByText('Agent Trace')).toBeInTheDocument();
    expect(screen.getByText('No agent trace available for this response')).toBeInTheDocument();
  });

  it('renders empty state when agentTrace prop is undefined', () => {
    render(<AgentTrace />);
    
    expect(screen.getByText('No agent trace available for this response')).toBeInTheDocument();
  });

  it('displays critic verdict badge in collapsed header', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('displays repair count badge in collapsed header', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    expect(screen.getByText('0 Repairs')).toBeInTheDocument();
  });

  it('displays singular "Repair" when repair_count is 1', () => {
    const traceWithOneRepair = {
      ...mockAgentTrace,
      repair_count: 1
    };
    
    render(<AgentTrace agentTrace={traceWithOneRepair} />);
    
    expect(screen.getByText('1 Repair')).toBeInTheDocument();
  });

  it('displays plural "Repairs" when repair_count is not 1', () => {
    const traceWithMultipleRepairs = {
      ...mockAgentTrace,
      repair_count: 2
    };
    
    render(<AgentTrace agentTrace={traceWithMultipleRepairs} />);
    
    expect(screen.getByText('2 Repairs')).toBeInTheDocument();
  });

  it('applies green color to approved verdict', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const verdictBadge = screen.getAllByText('Approved')[0];
    expect(verdictBadge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('applies yellow color to repair_numerical verdict', () => {
    const traceWithRepairNumerical = {
      ...mockAgentTrace,
      critic_verdict: 'repair_numerical'
    };
    
    render(<AgentTrace agentTrace={traceWithRepairNumerical} />);
    
    const verdictBadge = screen.getAllByText('Repair Numerical')[0];
    expect(verdictBadge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('applies orange color to repair_citation verdict', () => {
    const traceWithRepairCitation = {
      ...mockAgentTrace,
      critic_verdict: 'repair_citation'
    };
    
    render(<AgentTrace agentTrace={traceWithRepairCitation} />);
    
    const verdictBadge = screen.getAllByText('Repair Citation')[0];
    expect(verdictBadge).toHaveClass('bg-orange-100', 'text-orange-800');
  });

  it('applies green color to repair count of 0', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const repairBadge = screen.getByText('0 Repairs');
    expect(repairBadge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('applies yellow color to repair count of 1', () => {
    const traceWithOneRepair = {
      ...mockAgentTrace,
      repair_count: 1
    };
    
    render(<AgentTrace agentTrace={traceWithOneRepair} />);
    
    const repairBadge = screen.getByText('1 Repair');
    expect(repairBadge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('applies red color to repair count of 2 or more', () => {
    const traceWithMultipleRepairs = {
      ...mockAgentTrace,
      repair_count: 2
    };
    
    render(<AgentTrace agentTrace={traceWithMultipleRepairs} />);
    
    const repairBadge = screen.getByText('2 Repairs');
    expect(repairBadge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('is collapsed by default', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    // Plan steps should not be visible
    expect(screen.queryByText('Plan Steps (2)')).not.toBeInTheDocument();
    expect(screen.queryByText('Tool Results (2)')).not.toBeInTheDocument();
  });

  it('expands when header is clicked', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    // Content should now be visible
    expect(screen.getByText('Plan Steps (2)')).toBeInTheDocument();
    expect(screen.getByText('Tool Results (2)')).toBeInTheDocument();
  });

  it('collapses when header is clicked again', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    
    // Expand
    fireEvent.click(headerButton);
    expect(screen.getByText('Plan Steps (2)')).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(headerButton);
    expect(screen.queryByText('Plan Steps (2)')).not.toBeInTheDocument();
  });

  it('rotates chevron icon when expanded', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    const chevronIcon = headerButton.querySelector('svg:last-child');
    
    // Initially should not have rotation
    expect(chevronIcon).not.toHaveClass('rotate-180');
    
    // Click to expand
    fireEvent.click(headerButton);
    
    // Should now have rotation
    expect(chevronIcon).toHaveClass('rotate-180');
  });

  it('sets aria-expanded attribute correctly', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    
    // Initially collapsed
    expect(headerButton).toHaveAttribute('aria-expanded', 'false');
    
    // Click to expand
    fireEvent.click(headerButton);
    
    // Should be expanded
    expect(headerButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('displays all plan steps when expanded', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    expect(screen.getAllByText('LOOKUP').length).toBeGreaterThan(0);
    expect(screen.getAllByText('CALCULATE').length).toBeGreaterThan(0);
  });

  it('displays plan step numbers sequentially', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    // Check for step numbers in plan section
    const planSection = screen.getByText('Plan Steps (2)').closest('div');
    const stepNumbers = planSection.querySelectorAll('.bg-blue-600');
    
    expect(stepNumbers[0]).toHaveTextContent('1');
    expect(stepNumbers[1]).toHaveTextContent('2');
  });

  it('displays tool inputs as formatted JSON', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    // Check that the JSON structure contains the expected keys and values
    const planSection = screen.getByText('Plan Steps (2)').closest('div');
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

  it('displays tool result numbers sequentially', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    // Check for result numbers in tool results section
    const resultsSection = screen.getByText('Tool Results (2)').closest('div');
    const resultNumbers = resultsSection.querySelectorAll('.bg-green-600');
    
    expect(resultNumbers[0]).toHaveTextContent('1');
    expect(resultNumbers[1]).toHaveTextContent('2');
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
    
    // Should appear twice: once in header, once in detail section
    const verdictElements = screen.getAllByText('Approved');
    expect(verdictElements.length).toBeGreaterThanOrEqual(2);
  });

  it('displays repair count in detail section', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    expect(screen.getByText('0 Iterations')).toBeInTheDocument();
  });

  it('displays singular "Iteration" in detail section when repair_count is 1', () => {
    const traceWithOneRepair = {
      ...mockAgentTrace,
      repair_count: 1
    };
    
    render(<AgentTrace agentTrace={traceWithOneRepair} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    expect(screen.getByText('1 Iteration')).toBeInTheDocument();
  });

  it('handles empty plan array', () => {
    const traceWithEmptyPlan = {
      ...mockAgentTrace,
      plan: []
    };
    
    render(<AgentTrace agentTrace={traceWithEmptyPlan} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    expect(screen.getByText('Plan Steps (0)')).toBeInTheDocument();
    expect(screen.getByText('No plan steps available')).toBeInTheDocument();
  });

  it('handles empty tool_results array', () => {
    const traceWithEmptyResults = {
      ...mockAgentTrace,
      tool_results: []
    };
    
    render(<AgentTrace agentTrace={traceWithEmptyResults} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    expect(screen.getByText('Tool Results (0)')).toBeInTheDocument();
    expect(screen.getByText('No tool results available')).toBeInTheDocument();
  });

  it('handles missing plan property', () => {
    const traceWithoutPlan = {
      tool_results: mockAgentTrace.tool_results,
      critic_verdict: 'approved',
      repair_count: 0
    };
    
    render(<AgentTrace agentTrace={traceWithoutPlan} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    expect(screen.getByText('Plan Steps (0)')).toBeInTheDocument();
  });

  it('handles missing tool_results property', () => {
    const traceWithoutResults = {
      plan: mockAgentTrace.plan,
      critic_verdict: 'approved',
      repair_count: 0
    };
    
    render(<AgentTrace agentTrace={traceWithoutResults} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    expect(screen.getByText('Tool Results (0)')).toBeInTheDocument();
  });

  it('handles missing critic_verdict property', () => {
    const traceWithoutVerdict = {
      plan: mockAgentTrace.plan,
      tool_results: mockAgentTrace.tool_results,
      repair_count: 0
    };
    
    render(<AgentTrace agentTrace={traceWithoutVerdict} />);
    
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('handles missing repair_count property', () => {
    const traceWithoutRepairCount = {
      plan: mockAgentTrace.plan,
      tool_results: mockAgentTrace.tool_results,
      critic_verdict: 'approved'
    };
    
    render(<AgentTrace agentTrace={traceWithoutRepairCount} />);
    
    // Should default to 0
    expect(screen.getByText('0 Repairs')).toBeInTheDocument();
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
    // Should not crash when inputs are missing
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
    // Should not crash when output is missing
  });

  it('formats multi-word verdicts correctly', () => {
    const traceWithMultiWordVerdict = {
      ...mockAgentTrace,
      critic_verdict: 'repair_numerical'
    };
    
    render(<AgentTrace agentTrace={traceWithMultiWordVerdict} />);
    
    expect(screen.getByText('Repair Numerical')).toBeInTheDocument();
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

  it('applies gradient background to header', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    expect(headerButton).toHaveClass('bg-gradient-to-r', 'from-indigo-50', 'to-purple-50');
  });

  it('applies hover effect to header', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    expect(headerButton).toHaveClass('hover:from-indigo-100', 'hover:to-purple-100');
  });

  it('uses monospace font for JSON displays', () => {
    render(<AgentTrace agentTrace={mockAgentTrace} />);
    
    const headerButton = screen.getByRole('button', { expanded: false });
    fireEvent.click(headerButton);
    
    const jsonElements = screen.getAllByText(/entity|attribute/);
    jsonElements.forEach(element => {
      const preElement = element.closest('pre');
      expect(preElement).toHaveClass('font-mono');
    });
  });

  it('preserves whitespace in tool outputs', () => {
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
    const preElement = outputElement.closest('pre');
    expect(preElement).toHaveClass('whitespace-pre-wrap');
  });
});
