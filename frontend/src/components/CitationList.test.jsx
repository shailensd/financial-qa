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

  it('renders empty state when no citations are provided', () => {
    render(<CitationList citations={[]} />);
    
    expect(screen.getByText('Citations')).toBeInTheDocument();
    expect(screen.getByText('No citations available for this response')).toBeInTheDocument();
  });

  it('renders empty state when citations prop is undefined', () => {
    render(<CitationList />);
    
    expect(screen.getByText('No citations available for this response')).toBeInTheDocument();
  });

  it('displays the correct number of citations in the header', () => {
    render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('Citations (3)')).toBeInTheDocument();
  });

  it('renders all citation cards', () => {
    render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('Chunk ID: 42')).toBeInTheDocument();
    expect(screen.getByText('Chunk ID: 87')).toBeInTheDocument();
    expect(screen.getByText('Chunk ID: 103')).toBeInTheDocument();
  });

  it('displays citation numbers sequentially', () => {
    render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
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
    expect(highRelevanceBadge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('applies correct color to medium-high relevance score (>= 0.6, < 0.8)', () => {
    render(<CitationList citations={mockCitations} />);
    
    const mediumRelevanceBadge = screen.getByText('65%');
    expect(mediumRelevanceBadge).toHaveClass('bg-blue-100', 'text-blue-800');
  });

  it('applies correct color to medium relevance score (>= 0.4, < 0.6)', () => {
    const mediumCitation = [{
      chunk_id: 1,
      chunk_text: 'Test text',
      relevance_score: 0.5
    }];
    
    render(<CitationList citations={mediumCitation} />);
    
    const mediumBadge = screen.getByText('50%');
    expect(mediumBadge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('applies correct color to low relevance score (< 0.4)', () => {
    const lowCitation = [{
      chunk_id: 1,
      chunk_text: 'Test text',
      relevance_score: 0.3
    }];
    
    render(<CitationList citations={lowCitation} />);
    
    const lowBadge = screen.getByText('30%');
    expect(lowBadge).toHaveClass('bg-gray-100', 'text-gray-800');
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
    const firstCardButton = screen.getByText('Chunk ID: 42').closest('button');
    fireEvent.click(firstCardButton);
    
    // Chunk text should now be visible
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
  });

  it('collapses an expanded card when clicked again', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('Chunk ID: 42').closest('button');
    
    // Expand
    fireEvent.click(firstCardButton);
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(firstCardButton);
    expect(screen.queryByText(/Total revenue for fiscal year 2023/)).not.toBeInTheDocument();
  });

  it('allows multiple cards to be expanded simultaneously', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('Chunk ID: 42').closest('button');
    const secondCardButton = screen.getByText('Chunk ID: 87').closest('button');
    
    // Expand both cards
    fireEvent.click(firstCardButton);
    fireEvent.click(secondCardButton);
    
    // Both should be visible
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
    expect(screen.getByText(/Net income for the fiscal year/)).toBeInTheDocument();
  });

  it('displays "Expand All" button when cards are collapsed', () => {
    render(<CitationList citations={mockCitations} />);
    
    expect(screen.getByText('Expand All')).toBeInTheDocument();
  });

  it('expands all cards when "Expand All" is clicked', () => {
    render(<CitationList citations={mockCitations} />);
    
    const expandAllButton = screen.getByText('Expand All');
    fireEvent.click(expandAllButton);
    
    // All chunk texts should be visible
    expect(screen.getByText(/Total revenue for fiscal year 2023/)).toBeInTheDocument();
    expect(screen.getByText(/Net income for the fiscal year/)).toBeInTheDocument();
    expect(screen.getByText(/Operating expenses increased/)).toBeInTheDocument();
  });

  it('displays "Collapse All" button when all cards are expanded', () => {
    render(<CitationList citations={mockCitations} />);
    
    const expandAllButton = screen.getByText('Expand All');
    fireEvent.click(expandAllButton);
    
    expect(screen.getByText('Collapse All')).toBeInTheDocument();
  });

  it('collapses all cards when "Collapse All" is clicked', () => {
    render(<CitationList citations={mockCitations} />);
    
    // Expand all
    const expandAllButton = screen.getByText('Expand All');
    fireEvent.click(expandAllButton);
    
    // Collapse all
    const collapseAllButton = screen.getByText('Collapse All');
    fireEvent.click(collapseAllButton);
    
    // All chunk texts should be hidden
    expect(screen.queryByText(/Total revenue for fiscal year 2023/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Net income for the fiscal year/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Operating expenses increased/)).not.toBeInTheDocument();
  });

  it('rotates the expand icon when card is expanded', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('Chunk ID: 42').closest('button');
    // Get all SVGs and select the last one (the chevron icon)
    const icons = firstCardButton.querySelectorAll('svg');
    const chevronIcon = icons[icons.length - 1];
    
    // Initially should not have rotation
    expect(chevronIcon).not.toHaveClass('rotate-180');
    
    // Click to expand
    fireEvent.click(firstCardButton);
    
    // Should now have rotation
    expect(chevronIcon).toHaveClass('rotate-180');
  });

  it('sets aria-expanded attribute correctly', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('Chunk ID: 42').closest('button');
    
    // Initially collapsed
    expect(firstCardButton).toHaveAttribute('aria-expanded', 'false');
    
    // Click to expand
    fireEvent.click(firstCardButton);
    
    // Should be expanded
    expect(firstCardButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('preserves whitespace in chunk text', () => {
    const citationWithWhitespace = [{
      chunk_id: 1,
      chunk_text: 'Line 1\n\nLine 2\n\nLine 3',
      relevance_score: 0.9
    }];
    
    render(<CitationList citations={citationWithWhitespace} />);
    
    const cardButton = screen.getByText('Chunk ID: 1').closest('button');
    fireEvent.click(cardButton);
    
    const chunkText = screen.getByText(/Line 1/);
    expect(chunkText).toHaveClass('whitespace-pre-wrap');
  });

  it('handles single citation correctly', () => {
    const singleCitation = [mockCitations[0]];
    
    render(<CitationList citations={singleCitation} />);
    
    expect(screen.getByText('Citations (1)')).toBeInTheDocument();
    expect(screen.getByText('Chunk ID: 42')).toBeInTheDocument();
  });

  it('handles citations with very long text', () => {
    const longTextCitation = [{
      chunk_id: 999,
      chunk_text: 'A'.repeat(1000),
      relevance_score: 0.75
    }];
    
    render(<CitationList citations={longTextCitation} />);
    
    const cardButton = screen.getByText('Chunk ID: 999').closest('button');
    fireEvent.click(cardButton);
    
    expect(screen.getByText('A'.repeat(1000))).toBeInTheDocument();
  });

  it('handles citations with special characters in text', () => {
    const specialCharCitation = [{
      chunk_id: 1,
      chunk_text: 'Revenue: $100,000 (10% increase) & "significant" growth',
      relevance_score: 0.8
    }];
    
    render(<CitationList citations={specialCharCitation} />);
    
    const cardButton = screen.getByText('Chunk ID: 1').closest('button');
    fireEvent.click(cardButton);
    
    expect(screen.getByText(/Revenue: \$100,000 \(10% increase\) & "significant" growth/)).toBeInTheDocument();
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

  it('applies hover effect to card headers', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('Chunk ID: 42').closest('button');
    expect(firstCardButton).toHaveClass('hover:bg-gray-100');
  });

  it('applies shadow effect to cards on hover', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCard = screen.getByText('Chunk ID: 42').closest('button').parentElement;
    expect(firstCard).toHaveClass('hover:shadow-md');
  });

  it('displays citation number in a circular badge', () => {
    render(<CitationList citations={mockCitations} />);
    
    const badge = screen.getByText('1');
    expect(badge).toHaveClass('rounded-full', 'bg-blue-600', 'text-white');
  });

  it('maintains card state independently', () => {
    render(<CitationList citations={mockCitations} />);
    
    const firstCardButton = screen.getByText('Chunk ID: 42').closest('button');
    
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
