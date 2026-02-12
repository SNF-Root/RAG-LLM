import { useState } from 'react'
import Header from './components/Header'
import SearchSection from './components/SearchSection'
import SuggestedQueries from './components/SuggestedQueries'
import Footer from './components/Footer'

function App() {
  const [query, setQuery] = useState('')

  const handleSearch = (searchQuery) => {
    console.log('Searching for:', searchQuery)
    // TODO: Connect to backend API
  }

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion)
    handleSearch(suggestion)
  }

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-50 to-slate-100">
      <Header />
      
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        {/* Search Icon */}
        <div className="mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-red-500 to-red-600 rounded-2xl flex items-center justify-center shadow-lg shadow-red-200">
            <svg 
              className="w-10 h-10 text-white" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2.5} 
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
              />
            </svg>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-4xl font-semibold text-slate-800 mb-10">
          What are you searching for?
        </h1>

        {/* Search Section */}
        <SearchSection 
          query={query}
          setQuery={setQuery}
          onSearch={handleSearch}
        />

        {/* Suggested Queries */}
        <SuggestedQueries onSuggestionClick={handleSuggestionClick} />
      </main>

      <Footer />
    </div>
  )
}

export default App
