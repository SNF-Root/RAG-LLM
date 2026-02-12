import { Search, FileText } from 'lucide-react'

const suggestions = [
  {
    type: 'search',
    text: 'Has precursor Trimethylaluminum (TMA) been approved?',
    icon: Search,
  },
  {
    type: 'document',
    text: 'What were the safety concerns for Silane gas?',
    icon: FileText,
  },
  {
    type: 'search',
    text: 'Has precursor Tetrakis(dimethylamido)titanium been used?',
    icon: Search,
  },
  {
    type: 'document',
    text: 'What were the safety concerns for Dichlorosilane?',
    icon: FileText,
  },
]

function SuggestedQueries({ onSuggestionClick }) {
  return (
    <div className="w-full max-w-2xl mt-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {suggestions.map((suggestion, index) => {
          const Icon = suggestion.icon
          return (
            <button
              key={index}
              onClick={() => onSuggestionClick(suggestion.text)}
              className="flex items-center gap-3 px-4 py-3 bg-white rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-md text-left transition-all duration-200 group"
            >
              <Icon className="w-4 h-4 text-slate-400 group-hover:text-red-500 transition-colors flex-shrink-0" />
              <span className="text-sm text-slate-600 truncate group-hover:text-slate-800">
                {suggestion.text}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default SuggestedQueries
