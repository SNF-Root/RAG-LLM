import { useState } from 'react'
import Header from './components/Header'
import SearchSection from './components/SearchSection'
import SuggestedQueries from './components/SuggestedQueries'
import Footer from './components/Footer'
import ChatView from './components/ChatView'
import UploadPromPage from './components/UploadPromPage'

function App() {
  const [view, setView] = useState('search') // 'search' | 'upload'
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [searchMode, setSearchMode] = useState('emails')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)

  // Lightweight search — returns top 5 results with titles
  const handleSearch = async (searchQuery) => {
    const trimmed = searchQuery.trim()
    if (!trimmed) return

    setIsSearching(true)
    setSearchResults([])

    try {
      const endpoint =
        searchMode === 'proms' ? '/search/proms' : '/search/emails'
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed }),
      })

      if (!response.ok) {
        console.error('Search request failed:', response.status)
        return
      }

      const data = await response.json()
      setSearchResults(data.results || [])
    } catch (error) {
      console.error('Search request error:', error)
    } finally {
      setIsSearching(false)
    }
  }

  // Full embed + chat completion for a selected result
  const handleStartChat = async (result) => {
    const userQuery = query.trim() || result.title
    setSearchResults([])
    setQuery('')

    // Show the original search query as the user message
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        role: 'user',
        text: userQuery,
      },
    ])

    setIsThinking(true)

    try {
      const endpoint =
        searchMode === 'proms' ? '/embed/proms' : '/embed/emails'
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: result.title }),
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

  // Send a follow-up message from within ChatView
  const sendChatMessage = async (text) => {
    const trimmed = text.trim()
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
    setIsThinking(true)

    try {
      const endpoint =
        searchMode === 'proms' ? '/embed/proms' : '/embed/emails'
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed }),
      })

      if (!response.ok) {
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

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion)
    handleSearch(suggestion)
  }

  const hasMessages = messages.length > 0

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-50 to-slate-100">
      <Header view={view} setView={setView} />

      <main
        className={`flex-1 flex flex-col px-4 ${
          view === 'upload'
            ? 'items-stretch py-6 min-h-0 overflow-hidden'
            : hasMessages
              ? 'items-stretch py-6'
              : 'items-center justify-center py-12'
        }`}
      >
        {view === 'upload' ? (
          <UploadPromPage />
        ) : hasMessages ? (
          <ChatView
            messages={messages}
            query={query}
            setQuery={setQuery}
            onSend={sendChatMessage}
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
            <SearchSection
              query={query}
              setQuery={setQuery}
              onSearch={handleSearch}
              searchMode={searchMode}
              setSearchMode={setSearchMode}
              searchResults={searchResults}
              isSearching={isSearching}
              onStartChat={handleStartChat}
            />

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
