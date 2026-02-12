import { Paperclip, Mic, ArrowUp } from 'lucide-react'

function SearchSection({ query, setQuery, onSearch, searchMode, setSearchMode }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="w-full max-w-2xl">
      <form onSubmit={handleSubmit}>
        <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-200 p-4 hover:shadow-xl hover:border-slate-300 transition-all duration-300">
          {/* Input Row */}
          <div className="flex items-center gap-3 mb-3">
            <button 
              type="button"
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about any past SNF internal document"
              className="flex-1 text-slate-700 placeholder-slate-400 outline-none text-lg"
            />
          </div>

          {/* Bottom Row */}
          <div className="flex items-center justify-between">
            {/* Mode Toggle */}
            <div className="flex items-center bg-slate-100 rounded-lg border border-slate-200 p-0.5">
              <button
                type="button"
                onClick={() => setSearchMode('emails')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-all duration-200 ${
                  searchMode === 'emails'
                    ? 'bg-white text-slate-800 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                Emails
              </button>
              <button
                type="button"
                onClick={() => setSearchMode('proms')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-all duration-200 ${
                  searchMode === 'proms'
                    ? 'bg-white text-slate-800 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                PROMs
              </button>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <button 
                type="button"
                className="p-3 bg-slate-800 text-white rounded-full hover:bg-slate-700 transition-colors"
              >
                <Mic className="w-5 h-5" />
              </button>
              <button 
                type="submit"
                disabled={!query.trim()}
                className="p-3 bg-slate-200 text-slate-400 rounded-full hover:bg-red-500 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              >
                <ArrowUp className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}

export default SearchSection
