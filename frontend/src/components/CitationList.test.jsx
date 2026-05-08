import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CitationList from './CitationList';

describe('CitationList Component', () => {
  const mockCitations = [
    {
      chunk_id: 42,
      chunk_text: 'Total revenue for fiscal year 2023 was $383,285 million, representing a 7% increase from the prior year.',
      relevance_score: 0.94
    },
    {
      chunk_id: 87,
      chunk_text: 'Net income for the fiscal year ended September 30, 2023 was $96,995 million.',
      relevance_score: 0.88
    },
    {
      chunk_id: 103,
      chunk_text: 'Operating expenses increased by 12% year-over-year to $55,013 million.',
      relevance_score: 0.65
    }
  ];

  it('renders nothing when no citations are provided', () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when citations prop is undefined', () => {
    const { container } = render(<CitationList />);
    expect(container).toBeEmptyDOMElement();
  });

  it('displays the correct number of citations in the header', () => {
    const { container } = render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('Source Citations')).toBeInTheDocument();
    const badge = container.querySelector('.badge-blue');
    expect(badge).toHaveTextContent('3');
  });

  it('renders all citation cards', () => {
    render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('chunk #42')).toBeInTheDocument();
    expect(screen.getByText('chunk #87')).toBeInTheDocument();
    expect(screen.getByText('chunk #103')).toBeInTheDocument();
  });

  it('displays citation numbers sequentially', () => {
    const { container } = render(<CitationList citations={mockCitations} />);
    
    const nums = container.querySelectorAll('.citation-num');
    expect(nums[0].textContent).toBe('1');
    expect(nums[1].textContent).toBe('2');
    expect(nums[2].textContent).toBe('3');
  });

  it('displays relevance scores as percentages', () => {
    render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('94%')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
  });

  it('applies correct color to high relevance score (>= 0.8)', () => {
    render(<CitationList citations={mockCitations} />);
    
    const highRelevanceBadge = screen.getByText('94%');
    expect(highRelevanceBadge).toHaveClass('badge', 'badge-green');
  });

  it('applies correct color to medium-high relevance score (>= 0.6, < 0.8)', () => {
    render(<CitationList citations={mockCitations} />);
    
    const mediumRelevanceBadge = screen.getByText('65%');
    expect(mediumRelevanceBadge).toHaveClass('badge', 'badge-cyan');
  });

  it('applies correct color to medium relevance score (>= 0.4, < 0.6)', () => {
    const mediumCitation = [{
      chunk_id: 1,
      chunk_text: 'Test text',
      relevance_score: 0.5
    }];
    
    render(<CitationList citations={mediumCitation} />);
    
    const mediumBadge = screen.getByText('50%');
    expect(mediumBadge).toHaveClass('badge', 'badge-yellow');
  });

  it('applies correct color to low relevance score (< 0.4)', () => {
    const lowCitation = [{
      chunk_id: 1,
      chunk_text: 'Test text',
      relevance_score: 0.3
    }];
    
    render(<CitationList citations={lowCitation} />);
    
    const lowBadge = screen.getByText('30%');
    expect(lowBadge).toHaveClass('badge', 'badge-gray');
  });

  it('does not display chunk text by default (cards are collapsed)', () => {
    render(<CitationList citations={mockCitations} />);
    
    // Chunk text should not be visible initially
    expect(screen.queryByText(/Total revenue for fiscal year 2023/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Net income for the fiscal year/)).not.toBeInTheDocument();
  });

  it('expands a card when clicked', () => {
    render(<CitationList citations={mockCitations} />);
    
    // Click the first citation card header
    const firstCardButton = screen.getByText('chunk #42').closest('button');
    fireEvent.click(firstCardButton);
    
    // Chunk text should now be visible
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
  });

  it('collapses an expanded card when clicked again', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('chunk #42').closest('button');
    
    // Expand
    fireEvent.click(firstCardButton);
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(firstCardButton);
    expect(screen.queryByText(/Total revenue for fiscal year 2023/)).not.toBeInTheDocument();
  });

  it('allows multiple cards to be expanded simultaneously', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('chunk #42').closest('button');
    const secondCardButton = screen.getByText('chunk #87').closest('button');
    
    // Expand both cards
    fireEvent.click(firstCardButton);
    fireEvent.click(secondCardButton);
    
    // Both should be visible
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
    expect(screen.getByText(/Net income for the fiscal year/)).toBeInTheDocument();
  });

  it('displays "Expand all" button when cards are collapsed', () => {
    render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('Expand all')).toBeInTheDocument();
  });

  it('expands all cards when "Expand all" is clicked', () => {
    render(<CitationList citations={mockCitations} />);
    
    const expandAllButton = screen.getByText('Expand all');
    fireEvent.click(expandAllButton);
    
    // All chunk texts should be visible
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
    expect(screen.getByText(/Net income for the fiscal year/)).toBeInTheDocument();
    expect(screen.getByText(/Operating expenses increased/)).toBeInTheDocument();
  });

  it('displays "Collapse all" button when all cards are expanded', () => {
    render(<CitationList citations={mockCitations} />);
    
    const expandAllButton = screen.getByText('Expand all');
    fireEvent.click(expandAllButton);
    
    expect(screen.getByText('Collapse all')).toBeInTheDocument();
  });

  it('collapses all cards when "Collapse all" is clicked', () => {
    render(<CitationList citations={mockCitations} />);
    
    // Expand all
    const expandAllButton = screen.getByText('Expand all');
    fireEvent.click(expandAllButton);
    
    // Collapse all
    const collapseAllButton = screen.getByText('Collapse all');
    fireEvent.click(collapseAllButton);
    
    // All chunk texts should be hidden
    expect(screen.queryByText(/Total revenue for fiscal year 2023/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Net income for the fiscal year/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Operating expenses increased/)).not.toBeInTheDocument();
  });

  it('rotates the expand icon when card is expanded', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('chunk #42').closest('button');
    // Get all SVGs and select the last one (the chevron icon)
    const icons = firstCardButton.querySelectorAll('svg');
    const chevronIcon = icons[icons.length - 1];
    
    // Initially should not have rotation class
    expect(chevronIcon).not.toHaveClass('open');
    
    // Click to expand
    fireEvent.click(firstCardButton);
    
    // Should now have rotation class
    expect(chevronIcon).toHaveClass('open');
  });

  it('sets aria-expanded attribute correctly', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('chunk #42').closest('button');
    
    // Initially collapsed
    expect(firstCardButton).toHaveAttribute('aria-expanded', 'false');
    
    // Click to expand
    fireEvent.click(firstCardButton);
    
    // Should be expanded
    expect(firstCardButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('handles single citation correctly', () => {
    const singleCitation = [mockCitations[0]];
    
    const { container } = render(<CitationList citations={singleCitation} />);
    
    const badge = container.querySelector('.badge-blue');
    expect(badge.textContent).toBe('1');
    expect(screen.getByText('chunk #42')).toBeInTheDocument();
  });

  it('handles relevance score of 1.0 correctly', () => {
    const perfectScoreCitation = [{
      chunk_id: 1,
      chunk_text: 'Perfect match',
      relevance_score: 1.0
    }];
    
    render(<CitationList citations={perfectScoreCitation} />);
    
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('handles relevance score of 0.0 correctly', () => {
    const zeroScoreCitation = [{
      chunk_id: 1,
      chunk_text: 'No relevance',
      relevance_score: 0.0
    }];
    
    render(<CitationList citations={zeroScoreCitation} />);
    
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('displays citation number correctly', () => {
    const { container } = render(<CitationList citations={mockCitations} />);
    
    const nums = container.querySelectorAll('.citation-num');
    expect(nums[0].textContent).toBe('1');
  });

  it('maintains card state independently', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('chunk #42').closest('button');
    
    // Expand first card
    fireEvent.click(firstCardButton);
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
    
    // Collapse first card
    fireEvent.click(firstCardButton);
    expect(screen.queryByText(/Total revenue for fiscal year 2023/)).not.toBeInTheDocument();
    
    // Second card should still be collapsed
    expect(screen.queryByText(/Net income for the fiscal year/)).not.toBeInTheDocument();
  });
});
