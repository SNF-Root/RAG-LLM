import { useEffect, useMemo, useRef, useState } from 'react'
import {
  UploadCloud,
  FolderUp,
  FileText,
  CheckCircle2,
  AlertTriangle,
  X,
} from 'lucide-react'

const VALID_EXTENSIONS = ['.pdf', '.docx']

const getExtension = (name) => {
  const lower = (name || '').toLowerCase()
  const dot = lower.lastIndexOf('.')
  return dot === -1 ? '' : lower.slice(dot)
}

const getDisplayPath = (file) => file?.webkitRelativePath || file?.name || ''

const registerFilename = async (path) => {
  const url = `/upload/prom?filename=${encodeURIComponent(path)}`
  const res = await fetch(url, { method: 'GET' })
  if (!res.ok) throw new Error(`Register failed (${res.status})`)
  return res.json()
}

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

export default function UploadPromPage() {
  const fileInputRef = useRef(null)
  const folderInputRef = useRef(null)
  const timersRef = useRef(new Map())

  const [items, setItems] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')

  const counts = useMemo(() => {
    let valid = 0
    let invalid = 0
    let done = 0
    let uploading = 0
    for (const it of items) {
      if (it.status === 'invalid') invalid += 1
      else valid += 1
      if (it.status === 'done') done += 1
      if (it.status === 'uploading') uploading += 1
    }
    return { valid, invalid, done, uploading }
  }, [items])

  useEffect(() => {
    return () => {
      for (const timer of timersRef.current.values()) clearInterval(timer)
      timersRef.current.clear()
    }
  }, [])

  const startFakeUpload = (id) => {
    setItems((prev) =>
      prev.map((it) =>
        it.id === id ? { ...it, status: 'uploading', progress: 1 } : it,
      ),
    )

    const existing = timersRef.current.get(id)
    if (existing) clearInterval(existing)

    const timer = setInterval(() => {
      setItems((prev) =>
        prev.map((it) => {
          if (it.id !== id) return it
          if (it.status !== 'uploading') return it
          const increment = 6 + Math.random() * 14
          const next = Math.min(100, Math.round(it.progress + increment))
          if (next >= 100) {
            const t = timersRef.current.get(id)
            if (t) clearInterval(t)
            timersRef.current.delete(id)
            return { ...it, status: 'done', progress: 100 }
          }
          return { ...it, progress: next }
        }),
      )
    }, 220 + Math.round(Math.random() * 140))

    timersRef.current.set(id, timer)
  }

  const addFilePaths = async (paths) => {
    setError('')
    const next = []

    for (const path of paths) {
      if (!path) continue
      const ext = getExtension(path)
      const id = makeId()
      const isValid = VALID_EXTENSIONS.includes(ext)

      next.push({
        id,
        path,
        filename: path.split('/').pop() || path,
        ext,
        status: isValid ? 'queued' : 'invalid',
        progress: 0,
        message: isValid ? '' : 'Only .pdf and .docx are allowed',
      })
    }

    if (next.length === 0) return

    let inserted = []
    setItems((prev) => {
      const existing = new Set(prev.map((p) => p.path))
      inserted = next.filter((n) => !existing.has(n.path))
      return [...inserted, ...prev]
    })

    const validItems = inserted.filter((n) => n.status === 'queued')
    await Promise.allSettled(
      validItems.map(async (n) => {
        try {
          await registerFilename(n.path)
          startFakeUpload(n.id)
        } catch (e) {
          setItems((prev) =>
            prev.map((it) =>
              it.id === n.id
                ? {
                    ...it,
                    status: 'error',
                    message: 'Could not reach server (filename not registered)',
                  }
                : it,
            ),
          )
        }
      }),
    )
  }

  const addFiles = (files) => {
    const paths = files.map(getDisplayPath).filter(Boolean)
    return addFilePaths(paths)
  }

  const onPickFiles = (e) => {
    const files = Array.from(e.target.files || [])
    e.target.value = ''
    addFiles(files)
  }

  const onDrop = async (e) => {
    e.preventDefault()
    setIsDragging(false)
    setError('')

    const dt = e.dataTransfer
    if (!dt) return

    const items = Array.from(dt.items || [])
    const canUseEntries = items.some((i) => i.webkitGetAsEntry)

    if (!canUseEntries) {
      addFiles(Array.from(dt.files || []))
      return
    }

    const collectedPaths = []

    const walkEntry = (entry, prefix = '') =>
      new Promise((resolve) => {
        if (!entry) return resolve()
        if (entry.isFile) {
          entry.file((file) => {
            collectedPaths.push(`${prefix}${file.name}`)
            resolve()
          })
          return
        }
        if (entry.isDirectory) {
          const reader = entry.createReader()
          const readAll = async () => {
            reader.readEntries(async (entries) => {
              if (!entries || entries.length === 0) return resolve()
              for (const child of entries) {
                await walkEntry(child, `${prefix}${entry.name}/`)
              }
              readAll()
            })
          }
          readAll()
          return
        }
        resolve()
      })

    for (const it of items) {
      const entry = it.webkitGetAsEntry?.()
      if (!entry) continue
      await walkEntry(entry, '')
    }

    if (collectedPaths.length === 0) {
      setError('Nothing to upload. Try dropping a folder with .pdf/.docx files.')
      return
    }

    addFilePaths(collectedPaths)
  }

  const clearAll = () => {
    for (const timer of timersRef.current.values()) clearInterval(timer)
    timersRef.current.clear()
    setItems([])
  }

  const removeItem = (id) => {
    setItems((prev) => {
      const t = timersRef.current.get(id)
      if (t) clearInterval(t)
      timersRef.current.delete(id)
      return prev.filter((p) => p.id !== id)
    })
  }

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="flex flex-col gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold tracking-wide uppercase text-red-700 bg-red-50 border border-red-100 px-3 py-1 rounded-full">
            PROM forms
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-slate-900 mt-3">
            Upload PROM documents
          </h1>
          <p className="text-slate-600 mt-2">
            Accepted extensions: <span className="font-medium">.pdf</span>,{' '}
            <span className="font-medium">.docx</span>. Folder upload is supported.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div
            className={[
              'relative overflow-hidden rounded-3xl border bg-white shadow-sm',
              isDragging ? 'border-red-300 ring-4 ring-red-100' : 'border-slate-200',
            ].join(' ')}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-red-50/40 via-white to-slate-50/70" />
            <div className="relative p-8 md:p-10">
              <div
                onDragEnter={(e) => {
                  e.preventDefault()
                  setIsDragging(true)
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsDragging(true)
                }}
                onDragLeave={(e) => {
                  e.preventDefault()
                  setIsDragging(false)
                }}
                onDrop={onDrop}
                className="rounded-2xl border-2 border-dashed border-slate-200 bg-white/60 backdrop-blur-sm p-10 md:p-12 text-center"
              >
                <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-200 flex items-center justify-center mb-5">
                  <UploadCloud className="w-7 h-7 text-white" />
                </div>

                <h2 className="text-xl font-semibold text-slate-900">
                  Drag and drop files or a folder
                </h2>
                <p className="text-slate-600 mt-2">
                  The frontend registers filenames with the server (no file contents yet).
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-6">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-red-600 text-white hover:bg-red-700 transition-colors inline-flex items-center justify-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    Choose files
                  </button>
                  <button
                    onClick={() => folderInputRef.current?.click()}
                    className="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-colors inline-flex items-center justify-center gap-2"
                  >
                    <FolderUp className="w-4 h-4" />
                    Choose folder
                  </button>
                </div>

                {error ? (
                  <div className="mt-5 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                    {error}
                  </div>
                ) : null}

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={VALID_EXTENSIONS.join(',')}
                  className="hidden"
                  onChange={onPickFiles}
                />
                <input
                  ref={folderInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={onPickFiles}
                  {...{ webkitdirectory: '' }}
                />
              </div>

              <div className="mt-7 text-xs text-slate-500">
                Tip: dropping folders works best in Chromium-based browsers.
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <div>
                <div className="text-sm font-semibold text-slate-900">Upload queue</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Showing progress bars for each file (animation only).
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-xs text-slate-500">
                  {counts.done}/{counts.valid} completed
                </div>
                {items.length > 0 ? (
                  <button
                    onClick={clearAll}
                    className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    Clear
                  </button>
                ) : null}
              </div>
            </div>

            <div className="max-h-[420px] overflow-auto">
              {items.length === 0 ? (
                <div className="px-6 py-10 text-sm text-slate-500">
                  No files yet. Add a folder or drag files into the upload box.
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {items.map((it) => {
                    const isDone = it.status === 'done'
                    const isInvalid = it.status === 'invalid'
                    const isError = it.status === 'error'
                    const statusLabel = isDone
                      ? 'Completed'
                      : it.status === 'uploading'
                        ? 'Uploading'
                        : it.status === 'queued'
                          ? 'Queued'
                          : isInvalid
                            ? 'Invalid'
                            : isError
                              ? 'Error'
                              : it.status

                    return (
                      <li key={it.id} className="px-6 py-4">
                        <div className="flex items-start gap-3">
                          <div
                            className={[
                              'mt-0.5 w-10 h-10 rounded-2xl flex items-center justify-center',
                              isDone
                                ? 'bg-emerald-50 text-emerald-600'
                                : isInvalid || isError
                                  ? 'bg-red-50 text-red-600'
                                  : 'bg-slate-50 text-slate-600',
                            ].join(' ')}
                          >
                            {isDone ? (
                              <CheckCircle2 className="w-5 h-5" />
                            ) : isInvalid || isError ? (
                              <AlertTriangle className="w-5 h-5" />
                            ) : (
                              <FileText className="w-5 h-5" />
                            )}
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="text-sm font-medium text-slate-900 truncate">
                                  {it.filename}
                                </div>
                                <div className="text-xs text-slate-500 truncate mt-0.5">
                                  {it.path}
                                </div>
                              </div>

                              <div className="flex items-center gap-3">
                                <span
                                  className={[
                                    'text-xs px-2.5 py-1 rounded-full border',
                                    isDone
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
                                      : isInvalid || isError
                                        ? 'bg-red-50 text-red-700 border-red-100'
                                        : 'bg-slate-50 text-slate-700 border-slate-200',
                                  ].join(' ')}
                                >
                                  {statusLabel}
                                </span>
                                <button
                                  onClick={() => removeItem(it.id)}
                                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
                                  aria-label={`Remove ${it.filename}`}
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>
                            </div>

                            <div className="mt-3">
                              <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
                                <div
                                  className={[
                                    'h-full rounded-full transition-[width] duration-200',
                                    isDone
                                      ? 'bg-emerald-500'
                                      : isInvalid || isError
                                        ? 'bg-red-400'
                                        : 'bg-gradient-to-r from-red-500 via-red-500 to-red-600',
                                  ].join(' ')}
                                  style={{
                                    width: `${isInvalid || isError ? 100 : it.progress}%`,
                                  }}
                                />
                              </div>
                              <div className="flex items-center justify-between mt-1.5 text-xs text-slate-500">
                                <div className="truncate">
                                  {it.message ? it.message : ' '}
                                </div>
                                <div className="tabular-nums">
                                  {isInvalid || isError ? '—' : `${it.progress}%`}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-1">
          <div className="rounded-3xl border border-slate-200 bg-white shadow-sm p-6">
            <div className="text-sm font-semibold text-slate-900">Summary</div>
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">Valid files</span>
                <span className="font-medium text-slate-900 tabular-nums">
                  {counts.valid}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">Invalid files</span>
                <span className="font-medium text-slate-900 tabular-nums">
                  {counts.invalid}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">Uploading</span>
                <span className="font-medium text-slate-900 tabular-nums">
                  {counts.uploading}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">Completed</span>
                <span className="font-medium text-slate-900 tabular-nums">
                  {counts.done}
                </span>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-600 leading-relaxed">
              This upload box is for <span className="font-medium">PROM forms</span>{' '}
              only. The server endpoint currently accepts and validates filenames via GET
              requests.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
