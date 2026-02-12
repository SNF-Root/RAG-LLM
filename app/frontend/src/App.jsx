import { useState } from 'react'
import Header from './components/Header'
import SearchSection from './components/SearchSection'
import SuggestedQueries from './components/SuggestedQueries'
import Footer from './components/Footer'
import ChatView from './components/ChatView'

function App() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [searchMode, setSearchMode] = useState('emails') 

  const sendEmbedRequest = async (text) => {
    setIsThinking(true)
    try {
      const endpoint = searchMode === 'proms' ? '/embed/proms' : '/embed/emails'
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      })

      if (!response.ok) {
        console.error('Embed request failed:', response.status)
        setMessages((prev) => [
          ...prev,
          {
            id: `${Date.now()}-err`,
            role: 'assistant',
            text: 'Sorry, something went wrong. Please try again.',
          },
        ])
        return
      }

      const data = await response.json()
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          role: 'assistant',
          text: data.text,
        },
      ])
    } catch (error) {
      console.error('Embed request error:', error)
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-err`,
          role: 'assistant',
          text: 'Could not reach the server. Please try again.',
        },
      ])
    } finally {
      setIsThinking(false)
    }
  }

  const handleSearch = (searchQuery) => {
    const trimmed = searchQuery.trim()
    if (!trimmed) return

    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        role: 'user',
        text: trimmed,
      },
    ])
    setQuery('')
    sendEmbedRequest(trimmed)
  }

  const handleSuggestionClick = (suggestion) => {
    handleSearch(suggestion)
  }

  const hasMessages = messages.length > 0

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-50 to-slate-100">
      <Header />
      
      <main
        className={`flex-1 flex flex-col px-4 ${
          hasMessages ? 'items-stretch py-6' : 'items-center justify-center py-12'
        }`}
      >
        {hasMessages ? (
          <ChatView
            messages={messages}
            query={query}
            setQuery={setQuery}
            onSend={handleSearch}
            isThinking={isThinking}
            searchMode={searchMode}
            setSearchMode={setSearchMode}
          />
        ) : (
          <>
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
            <SearchSection query={query} setQuery={setQuery} onSearch={handleSearch} searchMode={searchMode} setSearchMode={setSearchMode} />

            {/* Suggested Queries */}
            <SuggestedQueries onSuggestionClick={handleSuggestionClick} />
          </>
        )}
      </main>

      <Footer />
    </div>
  )
}

export default App
