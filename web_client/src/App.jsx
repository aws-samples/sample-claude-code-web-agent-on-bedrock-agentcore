import { useState, useEffect, useRef } from 'react'
import Header from './components/Header'
import ChatContainer from './components/ChatContainer'
import PermissionModal from './components/PermissionModal'
import SessionList from './components/SessionList'
import FileBrowser from './components/FileBrowser'
import GitPanel from './components/GitPanel'
import ProjectPanel from './components/ProjectPanel'
import FilePreview from './components/FilePreview'
import SettingsModal from './components/SettingsModal'
import TerminalPTY from './components/TerminalPTY'
import Login from './components/Login'
import Signup from './components/Signup'
import ProjectSwitcher from './components/ProjectSwitcher'
import { useClaudeAgent } from './hooks/useClaudeAgent'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { setAuthErrorHandler, getAgentCoreSessionId } from './utils/authUtils'
import { createAPIClient } from './api/client'
import { Loader2 } from 'lucide-react'

const SETTINGS_STORAGE_KEY = 'claude-agent-settings'
const SERVER_DISCONNECTED_KEY = 'claude-agent-server-disconnected'

// Read environment variables
const hideSettingsButton = import.meta.env.VITE_HIDE_SETTINGS_BUTTON === 'true'

// Read default settings from environment variables
const DEFAULT_SETTINGS = {
  serverUrl: import.meta.env.VITE_DEFAULT_SERVER_URL || 'http://127.0.0.1:8000',
  cwd: import.meta.env.VITE_DEFAULT_CWD || '/workspace',
  model: import.meta.env.VITE_DEFAULT_MODEL || 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
  backgroundModel: import.meta.env.VITE_DEFAULT_BACKGROUND_MODEL || 'global.anthropic.claude-haiku-4-5-20251001-v1:0',
  enableProxy: import.meta.env.VITE_DEFAULT_ENABLE_PROXY === 'true'
}

function AppContent() {
  const [showSettings, setShowSettings] = useState(false)
  const [authView, setAuthView] = useState('login') // 'login' or 'signup'
  const { user, initializing, logout } = useAuth()

  // Set up global authentication error handler
  useEffect(() => {
    setAuthErrorHandler(async () => {
      console.warn('🔐 Authentication error detected - logging out user')
      await logout()
    })
  }, [logout])

  // Load settings from localStorage or use defaults
  const [settings, setSettings] = useState(() => {
    try {
      const saved = localStorage.getItem(SETTINGS_STORAGE_KEY)
      if (saved) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
      }
    } catch (error) {
      console.error('Failed to load settings from localStorage:', error)
    }
    return DEFAULT_SETTINGS
  })

  // Store the working directory from settings (configuration, not changed by browsing)
  const [workingDirectory, setWorkingDirectory] = useState(settings.cwd)

  // Separate browsing path from configured working directory
  const [currentBrowsePath, setCurrentBrowsePath] = useState(settings.cwd)

  // File preview state
  const [previewFilePath, setPreviewFilePath] = useState(null)

  // File refresh trigger (incremented to trigger FileBrowser refresh)
  const [fileRefreshTrigger, setFileRefreshTrigger] = useState(0)

  // Sidebar width state
  const [sidebarWidth, setSidebarWidth] = useState(300) // Default 300px
  const [isResizingSidebar, setIsResizingSidebar] = useState(false)

  // Terminal state
  const [showTerminal, setShowTerminal] = useState(false)
  const [terminalWidth, setTerminalWidth] = useState(600) // Default 600px
  const [isResizingTerminal, setIsResizingTerminal] = useState(false)

  // Project state - infer from settings.cwd
  const [currentProject, setCurrentProject] = useState(() => {
    // If cwd is /workspace/project_name, extract project_name
    if (settings.cwd.startsWith('/workspace/') && settings.cwd !== '/workspace') {
      const projectName = settings.cwd.replace('/workspace/', '')
      // Only set if it's a simple project name (no further slashes)
      if (projectName && !projectName.includes('/')) {
        return projectName
      }
    }
    return null // Default workspace
  })
  const [availableProjects, setAvailableProjects] = useState([])
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [showProjectSwitcher, setShowProjectSwitcher] = useState(false)

  // Sidebar tab state
  const [activeTab, setActiveTab] = useState('sessions') // 'files' | 'git' | 'sessions' | 'projects'

  // GitHub auth state
  const [githubAuthStatus, setGithubAuthStatus] = useState(null) // null | 'success' | 'pending' | 'error'
  const [githubAuthMessage, setGithubAuthMessage] = useState('')

  // Server disconnect state - load from localStorage on mount
  const [serverDisconnected, setServerDisconnected] = useState(() => {
    try {
      const saved = localStorage.getItem(SERVER_DISCONNECTED_KEY)
      // Default to disconnected (true) if not set, so user must explicitly connect
      return saved ? JSON.parse(saved) : true
    } catch (error) {
      console.error('Failed to load server disconnect state:', error)
      return true // Default to disconnected on error
    }
  })
  const [disconnecting, setDisconnecting] = useState(false)

  const {
    connected,
    connecting,
    sessionId,
    sessionInfo,
    messages,
    pendingPermission,
    serverConnected,
    sessionError,
    githubAuthStatus: githubAuthFromHealth,
    serverUrl,
    connect,
    disconnect,
    clearSession,
    sendMessage,
    respondToPermission,
    loadSession,
    retrySession
  } = useClaudeAgent(settings.serverUrl, user?.userId, currentProject, serverDisconnected)

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
    } catch (error) {
      console.error('Failed to save settings to localStorage:', error)
    }
  }, [settings])

  // Save server disconnect state to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(SERVER_DISCONNECTED_KEY, JSON.stringify(serverDisconnected))
    } catch (error) {
      console.error('Failed to save server disconnect state:', error)
    }
  }, [serverDisconnected])

  // Load available projects when user logs in and server is connected
  useEffect(() => {
    if (!user?.userId || serverDisconnected) return
    loadProjects()
  }, [user?.userId, settings.serverUrl, serverDisconnected])

  const loadProjects = async () => {
    if (!user?.userId || serverDisconnected) return

    setProjectsLoading(true)
    try {
      const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
      const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
      const result = await apiClient.listProjects(user.userId)
      setAvailableProjects(result.projects || [])
      console.log(`📁 Loaded ${result.projects?.length || 0} projects`)
    } catch (error) {
      console.error('Failed to load projects:', error)
      setAvailableProjects([])
    } finally {
      setProjectsLoading(false)
    }
  }

  const handleProjectChange = async (projectName) => {
    if (projectName === currentProject) return

    console.log(`📁 Switching to project: ${projectName || 'Default Workspace'}`)

    // Backup current project to S3 before switching (if not default workspace)
    if (currentProject) {
      try {
        console.log(`💾 Backing up current project "${currentProject}" to S3...`)
        const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
        const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
        const backupResult = await apiClient.backupProject(user.userId, currentProject)

        if (backupResult.status === 'success') {
          console.log(`✅ Backed up ${backupResult.files_synced} files to S3`)
        } else if (backupResult.status === 'skipped') {
          console.log(`⏭️  No files to backup for project "${currentProject}"`)
        }
      } catch (error) {
        console.error(`Failed to backup project "${currentProject}":`, error)
        // Continue with switch even if backup fails
      }
    }

    setCurrentProject(projectName)

    // Update working directory based on project
    const newWorkingDir = projectName ? `/workspace/${projectName}` : '/workspace'
    setWorkingDirectory(newWorkingDir)
    setCurrentBrowsePath(newWorkingDir)

    // IMPORTANT: Update settings.cwd so new sessions use the correct working directory
    setSettings(prev => ({
      ...prev,
      cwd: newWorkingDir
    }))

    console.log(`📂 Working directory changed to: ${newWorkingDir}`)

    // Disconnect current session when switching projects
    if (connected) {
      clearSession()
    }
  }

  const handleCreateProject = async (projectName) => {
    const agentCoreSessionId = await getAgentCoreSessionId(projectName)
    const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
    const result = await apiClient.createProject(user.userId, projectName)
    console.log(`✅ Created project: ${projectName}`)

    // Reload projects list
    const projects = await apiClient.listProjects(user.userId)
    setAvailableProjects(projects.projects || [])

    // Switch to the new project (this will also update working directory)
    handleProjectChange(projectName)
  }

  const handleGithubAuth = async () => {
    setGithubAuthStatus('pending')
    setGithubAuthMessage('Requesting GitHub authentication...')

    try {
      const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
      const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
      const result = await apiClient.getGithubToken()

      console.log('GitHub auth result:', result)

      // Check if we got an access token and gh auth was successful
      if (result.access_token) {
        if (result.gh_auth?.status === 'success') {
          setGithubAuthStatus('success')
          setGithubAuthMessage('GitHub connected successfully!')
          console.log('✅ GitHub authenticated successfully')
          // Keep green state persistent - don't auto-clear
          return
        } else if (result.gh_auth?.status === 'skipped') {
          setGithubAuthStatus('success')
          setGithubAuthMessage('GitHub token obtained (gh CLI not installed)')
          console.log('⚠️  GitHub token obtained but gh CLI not installed')
        } else if (result.gh_auth?.status === 'failed') {
          // Server will retry with forceAuthentication=True
          // Check if retry was successful
          if (result.retried_with_force) {
            if (result.authorization_url) {
              // Retry needs user authorization
              setGithubAuthStatus('pending')
              setGithubAuthMessage('Re-authentication required. Opening authorization page...')
              console.log('🔗 Retry: Opening GitHub authorization URL:', result.authorization_url)
              window.open(result.authorization_url, '_blank')
            } else {
              setGithubAuthStatus('error')
              setGithubAuthMessage('GitHub authentication failed. Please try again.')
              console.error('GitHub CLI authentication failed after retry')
            }
          } else {
            setGithubAuthStatus('error')
            setGithubAuthMessage('GitHub authentication failed. Please try again.')
            console.error('GitHub CLI authentication failed:', result.gh_auth)
          }
        } else {
          setGithubAuthStatus('error')
          setGithubAuthMessage(`GitHub CLI auth failed: ${result.gh_auth?.message || 'Unknown error'}`)
          console.error('GitHub CLI authentication failed:', result.gh_auth)
        }
      } else if (result.authorization_url) {
        // Need user to complete authorization
        setGithubAuthStatus('pending')
        setGithubAuthMessage('Opening authorization page...')
        console.log('🔗 Opening GitHub authorization URL:', result.authorization_url)
        window.open(result.authorization_url, '_blank')
      } else if (result.session_status === 'FAILED') {
        setGithubAuthStatus('error')
        setGithubAuthMessage('GitHub authorization failed. Please try again.')
        console.error('GitHub authorization failed')
      } else {
        setGithubAuthStatus('error')
        setGithubAuthMessage('Unexpected response from server')
        console.error('Unexpected GitHub auth response:', result)
      }
    } catch (error) {
      setGithubAuthStatus('error')
      setGithubAuthMessage(`Failed to authenticate: ${error.message}`)
      console.error('GitHub auth error:', error)
    }

    // Clear error/pending status after 8 seconds (but keep success state)
    setTimeout(() => {
      if (githubAuthStatus !== 'success') {
        setGithubAuthStatus(null)
        setGithubAuthMessage('')
      }
    }, 8000)
  }

  // Update GitHub auth status from health check
  useEffect(() => {
    if (githubAuthFromHealth) {
      if (githubAuthFromHealth.authenticated) {
        setGithubAuthStatus('success')
        const username = githubAuthFromHealth.username ? ` as ${githubAuthFromHealth.username}` : ''
        setGithubAuthMessage(`GitHub connected${username}`)
      } else if (githubAuthFromHealth.message === 'gh CLI not installed') {
        // Don't show as error if gh is not installed
        setGithubAuthStatus(null)
        setGithubAuthMessage('')
      } else {
        // Not authenticated but gh is installed
        setGithubAuthStatus(null)
        setGithubAuthMessage('Click to authenticate with GitHub')
      }
    }
  }, [githubAuthFromHealth])

  // Refresh files once when initially connected
  const prevConnectedRef = useRef(false)
  useEffect(() => {
    // Only trigger refresh when transitioning from disconnected to connected
    if (connected && !prevConnectedRef.current && !serverDisconnected) {
      console.log('🔄 Session connected, refreshing file browser')
      // Increment trigger to cause FileBrowser to refresh
      setFileRefreshTrigger(prev => prev + 1)
    }
    prevConnectedRef.current = connected
  }, [connected, serverDisconnected])

  const handleDisconnectServer = async () => {
    if (!serverConnected) {
      console.warn('Server already disconnected')
      return
    }

    if (!window.confirm('Disconnect from server?\n\nThis will stop all background requests and close any active sessions.')) {
      return
    }

    setDisconnecting(true)
    console.log('🛑 Disconnecting from server...')

    try {
      // If there's an active session, try to stop it
      if (connected) {
        try {
          const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
          const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
          await apiClient.stopAgentCoreSession('DEFAULT')
          console.log('✅ Stopped AgentCore session')
        } catch (error) {
          console.warn('Failed to stop AgentCore session:', error)
          // Continue with disconnect even if this fails
        }

        // Disconnect from agent session
        disconnect()
      }

      // Set server disconnected flag - this will stop all background requests
      setServerDisconnected(true)

      console.log('✅ Disconnected from server')
    } catch (error) {
      console.error('Failed to disconnect:', error)
      alert(`Failed to disconnect: ${error.message}`)
    } finally {
      setDisconnecting(false)
    }
  }

  const handleReconnectServer = () => {
    console.log('🔄 Reconnecting to server...')
    setServerDisconnected(false)
  }

  const handleNewSession = () => {
    if (connected) {
      clearSession()
    } else {
      // Auto-connect with current settings
      connect(settings)
    }
  }

  const handleSaveSettings = (newSettings) => {
    setSettings(newSettings)
    // Update working directory when settings change
    setWorkingDirectory(newSettings.cwd)
    // Also update current browse path to match new working directory
    setCurrentBrowsePath(newSettings.cwd)
  }

  const handleSessionSelect = async (sessionId) => {
    // Load session with current settings
    await loadSession(sessionId, settings)
  }

  const handleBrowsePathChange = (newPath) => {
    // Only change the browsing path, don't modify settings
    setCurrentBrowsePath(newPath)
  }

  const handleFileClick = (filePath) => {
    setPreviewFilePath(filePath)
  }

  const handleClosePreview = () => {
    setPreviewFilePath(null)
  }

  // Check if a model is from Anthropic
  const isAnthropicModel = (model) => {
    if (!model) return true
    const modelLower = model.toLowerCase()
    return modelLower.includes('anthropic') || modelLower.includes('claude')
  }

  // Handle model change - use set_model API or restart if proxy mode changes
  const handleModelChange = async (newModel) => {
    console.log(`Switching model from ${settings.model} to ${newModel}`)

    if (!sessionId) {
      console.error('No active session to change model')
      return
    }

    try {
      // Check if proxy mode needs to change
      const currentNeedsProxy = settings.enableProxy
      const newNeedsProxy = !isAnthropicModel(newModel)

      // If proxy mode changes, need to restart session
      if (currentNeedsProxy !== newNeedsProxy) {
        console.log('Proxy mode change detected, restarting session...')

        // Update settings with new model and proxy setting
        const newSettings = {
          ...settings,
          model: newModel,
          enableProxy: newNeedsProxy
        }

        setSettings(newSettings)

        // Disconnect current session
        await disconnect()

        // Reconnect with new model
        setTimeout(() => {
          connect(newSettings)
        }, 500)
      } else {
        // Proxy mode unchanged, just update model via API
        const agentCoreSessionId = await getAgentCoreSessionId(currentProject)
        const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
        await apiClient.setModel(sessionId, newModel)

        // Update settings with new model
        const newSettings = {
          ...settings,
          model: newModel
        }

        setSettings(newSettings)

        console.log(`✓ Model changed to ${newModel} without restart`)
      }
    } catch (error) {
      console.error('Failed to change model:', error)
      alert(`Failed to change model: ${error.message}`)
    }
  }

  // Handle sidebar resize
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizingSidebar) return

      const newWidth = e.clientX
      // Constrain width between 200px and 600px
      if (newWidth >= 200 && newWidth <= 600) {
        setSidebarWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsResizingSidebar(false)
    }

    if (isResizingSidebar) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingSidebar])

  const handleResizeStart = (e) => {
    e.preventDefault()
    setIsResizingSidebar(true)
  }

  // Handle terminal resize
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizingTerminal) return

      const newWidth = window.innerWidth - e.clientX
      // Constrain width between 400px and 1000px
      if (newWidth >= 400 && newWidth <= 1000) {
        setTerminalWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsResizingTerminal(false)
    }

    if (isResizingTerminal) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingTerminal])

  const handleTerminalResizeStart = (e) => {
    e.preventDefault()
    setIsResizingTerminal(true)
  }

  // Show loading spinner during initial auth check only
  if (initializing) {
    return (
      <div className="auth-loading">
        <Loader2 size={48} className="spinning" />
        <p>Loading...</p>
      </div>
    )
  }

  // Show auth screens if not logged in
  if (!user) {
    if (authView === 'signup') {
      return <Signup onSwitchToLogin={() => setAuthView('login')} />
    }
    return <Login onSwitchToSignup={() => setAuthView('signup')} />
  }

  // Main app content (user is authenticated)
  return (
    <div className="app-layout">
      {serverDisconnected && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            textAlign: 'center',
            maxWidth: '500px'
          }}>
            <h2 style={{ marginBottom: '1rem' }}>Connect to Server</h2>
            <p style={{ marginBottom: '1.5rem', color: '#666', lineHeight: '1.6' }}>
              Click the button below to connect to the server and start background services
              (health checks, session polling, etc.).
            </p>
            <button
              onClick={handleReconnectServer}
              style={{
                padding: '0.75rem 2rem',
                backgroundColor: 'var(--primary-color)',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '500'
              }}
            >
              Connect to Server
            </button>
            <p style={{ marginTop: '1rem', color: '#999', fontSize: '0.875rem' }}>
              Server: {settings.serverUrl}
            </p>
          </div>
        </div>
      )}

      <Header
        serverConnected={serverConnected}
        connected={connected}
        onSettingsClick={() => setShowSettings(true)}
        user={user}
        onLogout={logout}
        workingDirectory={workingDirectory}
        showTerminal={showTerminal}
        onTerminalToggle={() => setShowTerminal(!showTerminal)}
        currentProject={currentProject}
        onProjectSwitcherOpen={() => setShowProjectSwitcher(true)}
        onGithubAuthClick={handleGithubAuth}
        githubAuthStatus={githubAuthStatus}
        githubAuthMessage={githubAuthMessage}
        onCloseProject={handleDisconnectServer}
        closingProject={disconnecting}
      />

      <div className="main-content">
        <aside className="sidebar" style={{ width: `${sidebarWidth}px` }}>
          <div className="sidebar-tabs">
            <button
              className={`sidebar-tab ${activeTab === 'sessions' ? 'active' : ''}`}
              onClick={() => setActiveTab('sessions')}
              title="Sessions"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
            </button>
            <button
              className={`sidebar-tab ${activeTab === 'projects' ? 'active' : ''}`}
              onClick={() => setActiveTab('projects')}
              title="Projects"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
            </button>
            <button
              className={`sidebar-tab ${activeTab === 'files' ? 'active' : ''}`}
              onClick={() => setActiveTab('files')}
              title="Files"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                <polyline points="13 2 13 9 20 9"></polyline>
              </svg>
            </button>
            <button
              className={`sidebar-tab ${activeTab === 'git' ? 'active' : ''}`}
              onClick={() => setActiveTab('git')}
              title="Git"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="18" cy="18" r="3"></circle>
                <circle cx="6" cy="6" r="3"></circle>
                <path d="M13 6h3a2 2 0 0 1 2 2v7"></path>
                <line x1="6" y1="9" x2="6" y2="21"></line>
              </svg>
            </button>
          </div>

          <div className="sidebar-content">
            {activeTab === 'sessions' && (
              <SessionList
                serverUrl={settings.serverUrl}
                currentSessionId={sessionId}
                onSessionSelect={handleSessionSelect}
                onNewSession={handleNewSession}
                cwd={settings.cwd}
                disabled={serverDisconnected}
                isActive={activeTab === 'sessions'}
                currentProject={currentProject}
              />
            )}

            {activeTab === 'projects' && (
              <ProjectPanel
                projects={availableProjects}
                currentProject={currentProject}
                onProjectChange={handleProjectChange}
                onCreateProject={handleCreateProject}
                onRefresh={loadProjects}
                hasActiveSession={connected}
                loading={projectsLoading}
              />
            )}

            {activeTab === 'files' && (
              <FileBrowser
                serverUrl={settings.serverUrl}
                currentPath={currentBrowsePath}
                workingDirectory={workingDirectory}
                onPathChange={handleBrowsePathChange}
                onFileClick={handleFileClick}
                refreshTrigger={messages.length + fileRefreshTrigger}
                disabled={serverDisconnected}
                isActive={activeTab === 'files'}
                currentProject={currentProject}
              />
            )}

            {activeTab === 'git' && (
              <GitPanel
                serverUrl={settings.serverUrl}
                cwd={workingDirectory}
                disabled={serverDisconnected}
              />
            )}
          </div>

          <div
            className="sidebar-resize-handle"
            onMouseDown={handleResizeStart}
            title="Drag to resize sidebar"
          >
            <div className="resize-handle-bar-vertical" />
          </div>
        </aside>

        <main className="content-area">
          {!connected ? (
            <div className="welcome-screen">
              <div className="welcome-content">
                <h2>Welcome to Claude Agent</h2>
                <p>Select a session from the sidebar or create a new one to get started.</p>
                {!hideSettingsButton && (
                  <p className="welcome-hint">
                    Configure settings using the ⚙️ button in the top-right corner.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <ChatContainer
              sessionInfo={sessionInfo}
              messages={messages}
              onSendMessage={sendMessage}
              onDisconnect={disconnect}
              onClearSession={clearSession}
              onPermissionRespond={respondToPermission}
              sessionError={sessionError}
              onRetrySession={retrySession}
              currentModel={settings.model}
              onModelChange={handleModelChange}
            />
          )}
        </main>

        {previewFilePath && (
          <aside className="preview-panel">
            <FilePreview
              serverUrl={settings.serverUrl}
              filePath={previewFilePath}
              onClose={handleClosePreview}
              disabled={serverDisconnected}
              currentProject={currentProject}
            />
          </aside>
        )}

        {showTerminal && (
          <aside className="terminal-panel" style={{ width: `${terminalWidth}px` }}>
            <div
              className="terminal-resize-handle"
              onMouseDown={handleTerminalResizeStart}
              title="Drag to resize terminal"
            >
              <div className="resize-handle-bar-vertical" />
            </div>
            <TerminalPTY
              serverUrl={settings.serverUrl}
              initialCwd={workingDirectory}
              onClose={() => setShowTerminal(false)}
              disabled={serverDisconnected}
              currentProject={currentProject}
            />
          </aside>
        )}
      </div>

      {showSettings && (
        <SettingsModal
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
          settings={settings}
          onSave={handleSaveSettings}
        />
      )}

      {showProjectSwitcher && (
        <ProjectSwitcher
          isOpen={showProjectSwitcher}
          onClose={() => setShowProjectSwitcher(false)}
          projects={availableProjects}
          currentProject={currentProject}
          onProjectChange={handleProjectChange}
          onCreateProject={handleCreateProject}
          hasActiveSession={connected}
          serverUrl={settings.serverUrl}
          userId={user?.userId}
        />
      )}
    </div>
  )
}

export default function App() {
  return <AppContent />
}
