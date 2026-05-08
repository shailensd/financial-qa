import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import QueryInput from './QueryInput';

describe('QueryInput Component', () => {
  const mockOnSubmit = vi.fn();
  const mockSessionId = 'test-session-123';

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('renders all form elements correctly', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    // Check for company dropdown
    expect(screen.getByLabelText('Company')).toBeInTheDocument();

    // Check for question input
    expect(screen.getByLabelText('Question')).toBeInTheDocument();

    // Check for model checkboxes
    expect(screen.getByLabelText(/Llama 3.3 70B/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Llama 4 Scout/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Gemini 2.5 Flash/i)).toBeInTheDocument();

    // Check for submit button
    expect(screen.getByRole('button', { name: /Ask/i })).toBeInTheDocument();
  });

  it('has Gemini selected by default', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const geminiCheckbox = screen.getByLabelText(/Gemini 2.5 Flash/i);
    expect(geminiCheckbox).toBeChecked();

    const llamaCheckbox = screen.getByLabelText(/Llama 3.3 70B/i);
    expect(llamaCheckbox).not.toBeChecked();

    const gemmaCheckbox = screen.getByLabelText(/Llama 4 Scout/i);
    expect(gemmaCheckbox).not.toBeChecked();
  });

  it('allows selecting and deselecting models', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const llamaCheckbox = screen.getByLabelText(/Llama 3.3 70B/i);
    const gemmaCheckbox = screen.getByLabelText(/Llama 4 Scout/i);

    // Select Llama
    fireEvent.click(llamaCheckbox);
    expect(llamaCheckbox).toBeChecked();

    // Select Gemma
    fireEvent.click(gemmaCheckbox);
    expect(gemmaCheckbox).toBeChecked();

    // Deselect Llama
    fireEvent.click(llamaCheckbox);
    expect(llamaCheckbox).not.toBeChecked();
  });

  it('allows typing in the question input', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const input = screen.getByLabelText('Question');
    const testQuestion = "What was Apple's revenue in 2023?";

    fireEvent.change(input, { target: { value: testQuestion } });
    expect(input.value).toBe(testQuestion);
  });

  it('allows selecting a company from dropdown', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Company');

    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });
    expect(companySelect.value).toBe('Apple Inc.');
  });

  it('shows inline validation when submitting without company selection', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const input = screen.getByLabelText('Question');
    fireEvent.change(input, { target: { value: 'Test question' } });

    const submitButton = screen.getByRole('button', { name: /Ask/i });
    fireEvent.click(submitButton);

    expect(screen.getByText('Please select a company.')).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows inline validation when submitting without question', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const submitButton = screen.getByRole('button', { name: /Ask/i });
    fireEvent.click(submitButton);

    expect(screen.getByText('Please enter a question.')).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows inline validation when submitting without any model selected', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const input = screen.getByLabelText('Question');
    fireEvent.change(input, { target: { value: 'Test question' } });

    // Deselect the default Gemini model
    const geminiCheckbox = screen.getByLabelText(/Gemini 2.5 Flash/i);
    fireEvent.click(geminiCheckbox);

    const submitButton = screen.getByRole('button', { name: /Ask/i });
    fireEvent.click(submitButton);

    expect(screen.getByText('Please select at least one model.')).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits correct payload when form is valid', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    // Fill in the form
    const companySelect = screen.getByLabelText('Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const input = screen.getByLabelText('Question');
    const testQuestion = "What was Apple's revenue in 2023?";
    fireEvent.change(input, { target: { value: testQuestion } });

    // Select additional models
    const llamaCheckbox = screen.getByLabelText(/Llama 3.3 70B/i);
    fireEvent.click(llamaCheckbox);

    // Submit
    const submitButton = screen.getByRole('button', { name: /Ask/i });
    fireEvent.click(submitButton);

    // Verify the payload
    expect(mockOnSubmit).toHaveBeenCalledWith({
      session_id: mockSessionId,
      query_text: testQuestion,
      models: expect.arrayContaining(['gemini', 'llama']),
      company: 'Apple Inc.',
    });
  });

  it('disables all inputs when loading is true', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={true}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Company');
    expect(companySelect).toBeDisabled();

    const input = screen.getByLabelText('Question');
    expect(input).toBeDisabled();

    const llamaCheckbox = screen.getByLabelText(/Llama 3.3 70B/i);
    expect(llamaCheckbox).toBeDisabled();

    const submitButton = screen.getByRole('button');
    expect(submitButton).toBeDisabled();
  });

  it('shows loading state in submit button', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={true}
        sessionId={mockSessionId}
      />
    );

    expect(screen.getByText('Running…')).toBeInTheDocument();
    expect(screen.queryByText('Ask')).not.toBeInTheDocument();
  });

  it('includes all 5 primary companies from spec', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Company');
    const options = Array.from(companySelect.options).map(opt => opt.textContent);

    // Check for the 5 primary companies mentioned in the spec
    expect(options.some(opt => opt.includes('AAPL'))).toBe(true);
    expect(options.some(opt => opt.includes('MSFT'))).toBe(true);
    expect(options.some(opt => opt.includes('GOOGL'))).toBe(true);
    expect(options.some(opt => opt.includes('AMZN'))).toBe(true);
    expect(options.some(opt => opt.includes('TSLA'))).toBe(true);
  });

  it('trims whitespace from question before submission', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const input = screen.getByLabelText('Question');
    fireEvent.change(input, { target: { value: '  Test question  ' } });

    const submitButton = screen.getByRole('button', { name: /Ask/i });
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        query_text: 'Test question',
      })
    );
  });
});
