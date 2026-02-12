import SearchSection from './SearchSection'

function ChatView({ messages, query, setQuery, onSend, isThinking, searchMode, setSearchMode }) {
  return (
    <div className="flex-1 w-full max-w-4xl mx-auto flex flex-col">
      <div className="flex-1 overflow-y-auto space-y-4 pb-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm sm:text-base shadow-sm ${
                message.role === 'user'
                  ? 'bg-red-500 text-white'
                  : 'bg-white text-slate-700 border border-slate-200'
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="flex justify-start">
            <div className="px-4 py-3 text-sm text-slate-400 italic animate-pulse">
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div className="pt-2 flex justify-center">
        <SearchSection query={query} setQuery={setQuery} onSearch={onSend} searchMode={searchMode} setSearchMode={setSearchMode} />
      </div>
    </div>
  )
}

export default ChatView
