import { useState, useEffect, useRef } from 'react'
import { Folder, File, ChevronRight, ChevronDown, RefreshCw, FolderOpen, Home } from 'lucide-react'
import { createAPIClient } from '../api/client'
import { getAgentCoreSessionId } from '../utils/authUtils'

function FileBrowser({ serverUrl, currentPath, workingDirectory, onPathChange, onFileClick, refreshTrigger, disabled, isActive, currentProject }) {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedDirs, setExpandedDirs] = useState(new Set())
  const apiClientRef = useRef(null)
  const previousActiveRef = useRef(false)

  // Create API client
  useEffect(() => {
    if (disabled) {
      setFiles([])
      return
    }

    const initApiClient = async () => {
      if (serverUrl && (!apiClientRef.current || apiClientRef.current.baseUrl !== serverUrl)) {
        const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
        apiClientRef.current = createAPIClient(serverUrl, agentCoreSessionId)
      }
    }
    initApiClient()
  }, [serverUrl, disabled])

  // Load files when path changes
  useEffect(() => {
    if (disabled) return
    if (currentPath && apiClientRef.current) {
      loadFiles(currentPath)
    }
  }, [currentPath, disabled])

  // Auto-refresh when refreshTrigger changes (messages update)
  useEffect(() => {
    if (disabled) return
    if (refreshTrigger && currentPath && apiClientRef.current) {
      loadFiles(currentPath)
    }
  }, [refreshTrigger, disabled])

  // Auto-refresh when tab becomes active
  useEffect(() => {
    if (disabled) {
      previousActiveRef.current = isActive
      return
    }

    // Check if tab just became active (transition from false to true)
    if (isActive && !previousActiveRef.current) {
      // Use a small delay to ensure apiClient is initialized
      const timer = setTimeout(() => {
        if (currentPath && apiClientRef.current) {
          loadFiles(currentPath)
        }
      }, 100)

      // Update previous active state immediately
      previousActiveRef.current = isActive

      return () => clearTimeout(timer)
    }

    // Update previous active state
    previousActiveRef.current = isActive
  }, [isActive, disabled])

  const loadFiles = async (path) => {
    if (!apiClientRef.current) return

    setLoading(true)
    setError(null)

    try {
      const data = await apiClientRef.current.listFiles(path)
      setFiles(data.items || [])
    } catch (err) {
      console.error('Failed to load files:', err)
      setError(err.message)
      setFiles([])
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    if (currentPath) {
      loadFiles(currentPath)
    }
  }

  const handleItemClick = (item) => {
    if (item.is_directory) {
      onPathChange(item.path)
    } else {
      // It's a file, trigger file preview
      if (onFileClick) {
        onFileClick(item.path)
      }
    }
  }

  const handleParentDirectory = () => {
    if (currentPath && currentPath !== '/' && currentPath !== '.') {
      const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/'
      onPathChange(parentPath)
    }
  }

  const handleResetToWorkingDirectory = () => {
    if (workingDirectory) {
      onPathChange(workingDirectory)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }


  return (
    <div className="file-browser">
      <div className="file-browser-header">
        <div className="file-browser-title">
          <Folder size={16} />
          <span className="current-path-display" title={currentPath}>{currentPath || '/'}</span>
        </div>
        <div className="file-browser-actions">
          <button
            className="btn-icon btn-refresh"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw size={14} className={loading ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      <div className="file-browser-path">
        <button
          className="btn-path-segment"
          onClick={handleResetToWorkingDirectory}
          disabled={!workingDirectory || currentPath === workingDirectory}
          title={`Go to working directory: ${workingDirectory || ''}`}
        >
          <Home size={14} />
        </button>
        {currentPath && currentPath !== '/' && currentPath !== '.' && (
          <button
            className="btn-path-segment"
            onClick={handleParentDirectory}
            title="Parent directory"
          >
            ..
          </button>
        )}
      </div>

      <div className="file-browser-content">
        {error && (
          <div className="file-browser-error">
            <span>{error}</span>
          </div>
        )}

        {loading && files.length === 0 && (
          <div className="file-browser-loading">
            <RefreshCw size={16} className="spinning" />
            <span>Loading...</span>
          </div>
        )}

        {!loading && !error && files.length === 0 && (
          <div className="file-browser-empty">
            <Folder size={32} />
            <span>Empty directory</span>
          </div>
        )}

        {files.length > 0 && (
          <div className="file-list">
            {files.map((item, index) => (
              <div
                key={`${item.path}-${index}`}
                className={`file-item ${item.is_directory ? 'directory' : 'file'}`}
                onClick={() => handleItemClick(item)}
                title={item.path}
              >
                <div className="file-item-icon">
                  {item.is_directory ? (
                    <Folder size={16} />
                  ) : (
                    <File size={16} />
                  )}
                </div>
                <div className="file-item-content">
                  <div className="file-item-name">{item.name}</div>
                  {!item.is_directory && item.size !== null && (
                    <div className="file-item-size">{formatSize(item.size)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default FileBrowser
