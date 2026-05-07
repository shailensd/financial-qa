import './App.css'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            FinDoc Intelligence
          </h1>
          <p className="text-lg text-gray-600">
            Financial Q&A System for SEC Filings
          </p>
        </header>

        <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-6">
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              Frontend Setup Complete
            </h2>
            <p className="text-gray-600 mb-4">
              Vite + React + Tailwind CSS configured successfully
            </p>
            <div className="flex justify-center gap-4">
              <span className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                React 19.2.5
              </span>
              <span className="px-4 py-2 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
                Vite 8.0.10
              </span>
              <span className="px-4 py-2 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                Tailwind CSS
              </span>
            </div>
          </div>
        </div>

        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Components
            </h3>
            <p className="text-gray-600 text-sm">
              Directory created for React components
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Hooks
            </h3>
            <p className="text-gray-600 text-sm">
              Directory created for custom React hooks
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Services
            </h3>
            <p className="text-gray-600 text-sm">
              Directory created for API services
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
