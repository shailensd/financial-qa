import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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

    // Check for main heading
    expect(screen.getByText('Ask a Question')).toBeInTheDocument();

    // Check for company dropdown
    expect(screen.getByLabelText('Select Company')).toBeInTheDocument();

    // Check for question textarea
    expect(screen.getByLabelText('Your Question')).toBeInTheDocument();

    // Check for model checkboxes
    expect(screen.getByLabelText(/Llama 3.2 3B/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Gemma 2 9B/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Gemini 2.0 Flash/i)).toBeInTheDocument();

    // Check for submit button
    expect(screen.getByRole('button', { name: /Submit Query/i })).toBeInTheDocument();
  });

  it('has Gemini selected by default', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const geminiCheckbox = screen.getByLabelText(/Gemini 2.0 Flash/i);
    expect(geminiCheckbox).toBeChecked();

    const llamaCheckbox = screen.getByLabelText(/Llama 3.2 3B/i);
    expect(llamaCheckbox).not.toBeChecked();

    const gemmaCheckbox = screen.getByLabelText(/Gemma 2 9B/i);
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

    const llamaCheckbox = screen.getByLabelText(/Llama 3.2 3B/i);
    const gemmaCheckbox = screen.getByLabelText(/Gemma 2 9B/i);

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

  it('allows typing in the question textarea', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const textarea = screen.getByLabelText('Your Question');
    const testQuestion = "What was Apple's revenue in 2023?";

    fireEvent.change(textarea, { target: { value: testQuestion } });
    expect(textarea.value).toBe(testQuestion);
  });

  it('allows selecting a company from dropdown', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Select Company');

    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });
    expect(companySelect.value).toBe('Apple Inc.');
  });

  it('shows alert when submitting without company selection', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const textarea = screen.getByLabelText('Your Question');
    fireEvent.change(textarea, { target: { value: 'Test question' } });

    const submitButton = screen.getByRole('button', { name: /Submit Query/i });
    fireEvent.click(submitButton);

    expect(alertSpy).toHaveBeenCalledWith('Please select a company');
    expect(mockOnSubmit).not.toHaveBeenCalled();

    alertSpy.mockRestore();
  });

  it('shows alert when submitting without question', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Select Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const submitButton = screen.getByRole('button', { name: /Submit Query/i });
    fireEvent.click(submitButton);

    expect(alertSpy).toHaveBeenCalledWith('Please enter a question');
    expect(mockOnSubmit).not.toHaveBeenCalled();

    alertSpy.mockRestore();
  });

  it('shows alert when submitting without any model selected', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Select Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const textarea = screen.getByLabelText('Your Question');
    fireEvent.change(textarea, { target: { value: 'Test question' } });

    // Deselect the default Gemini model
    const geminiCheckbox = screen.getByLabelText(/Gemini 2.0 Flash/i);
    fireEvent.click(geminiCheckbox);

    const submitButton = screen.getByRole('button', { name: /Submit Query/i });
    fireEvent.click(submitButton);

    expect(alertSpy).toHaveBeenCalledWith('Please select at least one model');
    expect(mockOnSubmit).not.toHaveBeenCalled();

    alertSpy.mockRestore();
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
    const companySelect = screen.getByLabelText('Select Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const textarea = screen.getByLabelText('Your Question');
    const testQuestion = "What was Apple's revenue in 2023?";
    fireEvent.change(textarea, { target: { value: testQuestion } });

    // Select additional models
    const llamaCheckbox = screen.getByLabelText(/Llama 3.2 3B/i);
    fireEvent.click(llamaCheckbox);

    // Submit
    const submitButton = screen.getByRole('button', { name: /Submit Query/i });
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

    const companySelect = screen.getByLabelText('Select Company');
    expect(companySelect).toBeDisabled();

    const textarea = screen.getByLabelText('Your Question');
    expect(textarea).toBeDisabled();

    const llamaCheckbox = screen.getByLabelText(/Llama 3.2 3B/i);
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

    expect(screen.getByText('Processing Query...')).toBeInTheDocument();
    expect(screen.queryByText('Submit Query')).not.toBeInTheDocument();
  });

  it('includes all 5 primary companies from spec', () => {
    render(
      <QueryInput
        onSubmit={mockOnSubmit}
        loading={false}
        sessionId={mockSessionId}
      />
    );

    const companySelect = screen.getByLabelText('Select Company');
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

    const companySelect = screen.getByLabelText('Select Company');
    fireEvent.change(companySelect, { target: { value: 'Apple Inc.' } });

    const textarea = screen.getByLabelText('Your Question');
    fireEvent.change(textarea, { target: { value: '  Test question  ' } });

    const submitButton = screen.getByRole('button', { name: /Submit Query/i });
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        query_text: 'Test question',
      })
    );
  });
});
