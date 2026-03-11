import { useEffect, useState } from 'react'
import { Download, Image as ImageIcon, Wand2, Settings, Users, Plus, Frame, Crop } from 'lucide-react'
import axios from 'axios'

// Components
import { Gallery } from './components/Gallery'
import { SettingsModal } from './components/SettingsModal'
import { SafetyModal } from './components/SafetyModal'
import { DownloadTab } from './components/DownloadTab'
import { VideoProcessingTab } from './components/VideoProcessingTab'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://localhost:8000'

function App() {
  const [activeTab, setActiveTab] = useState('characters')
  const [url, setUrl] = useState('')
  const [status, setStatus] = useState('')
  const [characters, setCharacters] = useState<string[]>([])
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null)

  // Video States
  const [videoPath, setVideoPath] = useState('')
  const [videoInterval, setVideoInterval] = useState('1')
  const [maxFrames, setMaxFrames] = useState('')
  const [availableVideos, setAvailableVideos] = useState<any[]>([])

  // Modal States
  const [showSafetyModal, setShowSafetyModal] = useState(false)
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [cookieConfig, setCookieConfig] = useState({ vsco: '', tiktok: '', instagram: '' })
  const [cookieStatus, setCookieStatus] = useState('')
  const [vscoSessionStatus, setVscoSessionStatus] = useState('')

  // Job Tracker States
  const [jobId, setJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [logs, setLogs] = useState<string[]>([])
  const [isDownloading, setIsDownloading] = useState(false)

  // Initialization
  useEffect(() => {
    if (localStorage.getItem('lora_pack_disclaimer_v1') !== '1') {
      setShowSafetyModal(true)
    }
    loadCookieConfig()
  }, [])

  // Job Polling Logic
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/download/status/${jobId}`)
        if (res.data?.status === 'success') {
          const job = res.data.job
          setProgress(job.progress)
          setLogs(job.logs || [])

          if (job.status === 'success' || job.status === 'error') {
            setIsDownloading(false)
            setJobId(null)
            setStatus(job.message)
            clearInterval(timer)
          } else {
            setStatus(`Downloading: ${job.message}`)
          }
        }
      } catch (e) {
        clearInterval(timer)
        setIsDownloading(false)
      }
    }, 1500)
    return () => clearInterval(timer)
  }, [jobId])

  const loadCookieConfig = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/cookies/config`)
      setCookieConfig(res.data.config)
    } catch (e) { console.error(e) }
  }

  const saveCookieConfig = async () => {
    setCookieStatus('Saving...')
    try {
      await axios.post(`${API_BASE}/api/cookies/config`, cookieConfig)
      setCookieStatus('Success: Settings saved.')
    } catch (e) { setCookieStatus('Error saving config.') }
  }

  const loadVideos = async () => {
    if (!selectedCharacter) return
    try {
      const res = await axios.get(`${API_BASE}/api/videos/${selectedCharacter}`)
      setAvailableVideos(res.data.videos || [])
    } catch (e) { console.error(e) }
  }

  const openVscoLogin = async () => {
    setVscoSessionStatus('Opening helper...')
    try {
      await axios.post(`${API_BASE}/api/vsco/session/open-login`)
      setVscoSessionStatus('Success: Helper active.')
    } catch (e) { setVscoSessionStatus('Failed to open helper.') }
  }

  const checkVscoSession = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/vsco/session/status`)
      setVscoSessionStatus(res.data.message)
    } catch (e) { console.error(e) }
  }

  return (
    <div className="app-container animate-fade-in">
      {/* Modals */}
      {showSafetyModal && (
        <SafetyModal
          onContinue={() => setShowSafetyModal(false)}
          onDontShowAgain={() => {
            localStorage.setItem('lora_pack_disclaimer_v1', '1')
            setShowSafetyModal(false)
          }}
        />
      )}
      {showSettingsModal && (
        <SettingsModal
          config={cookieConfig}
          setConfig={setCookieConfig}
          onSave={saveCookieConfig}
          onClose={() => setShowSettingsModal(false)}
          status={cookieStatus}
        />
      )}

      <header className="header">
        <div className="header-title">
          <div className="glass-panel btn-icon" style={{ padding: '12px', border: 'none' }}>
            <Wand2 className="header-icon" size={32} />
          </div>
          <div>
            <h1>LoRA Pack <span className="text-gradient">Studio</span></h1>
            <p className="subtitle">Premium Image Preparation & Dataset Curation</p>
          </div>
        </div>
        <div>
          <button className="btn" onClick={() => setShowSettingsModal(true)}>
            <Settings size={20} />
            Global Settings
          </button>
        </div>
      </header>

      <div className="grid-layout">
        {/* Sidebar */}
        <nav className="sidebar glass-panel" style={{ padding: '16px' }}>
          <button className={`nav-item ${activeTab === 'characters' ? 'active' : ''}`} onClick={() => setActiveTab('characters')}>
            <Users size={20} />
            Characters
          </button>

          <div style={{ margin: '16px 0', borderBottom: '1px solid var(--glass-border)' }}></div>
          <div className="sidebar-section-label">
            {selectedCharacter ? `Target: ${selectedCharacter}` : 'Workflow'}
          </div>

          <button className={`nav-item ${activeTab === 'download' ? 'active' : ''}`} onClick={() => setActiveTab('download')}>
            <Download size={20} /> Data Collection
          </button>
          <button className={`nav-item ${activeTab === 'video-frames' ? 'active' : ''}`} onClick={() => { setActiveTab('video-frames'); loadVideos(); }}>
            <Frame size={20} /> Video Processing
          </button>
          <button className={`nav-item ${activeTab === 'process' ? 'active' : ''}`} onClick={() => setActiveTab('process')}>
            <Crop size={20} /> Auto-Cropping
          </button>
          <button className={`nav-item ${activeTab === 'gallery' ? 'active' : ''}`} onClick={() => setActiveTab('gallery')}>
            <ImageIcon size={20} /> Curation Gallery
          </button>
        </nav>

        {/* Main Content */}
        <main className="glass-panel main-content">
          {activeTab === 'characters' && (
            <div className="animate-fade-in">
              <div className="content-header-row">
                <div>
                  <h2>Character Database</h2>
                  <p className="subtitle">Choose your subject to initialize the dataset workspace.</p>
                </div>
                <button className="btn btn-primary" onClick={() => {
                  const name = prompt('New Character Name:')
                  if (name) {
                    setCharacters([...characters, name])
                    setSelectedCharacter(name)
                  }
                }}>
                  <Plus size={20} /> New Character
                </button>
              </div>

              <div className="stats-grid" style={{ marginTop: '32px' }}>
                {characters.map(char => (
                  <div
                    key={char}
                    className={`glass-panel stat-card char-card ${selectedCharacter === char ? 'selected' : ''}`}
                    onClick={() => setSelectedCharacter(char)}
                  >
                    <Users size={32} className="accent-icon" />
                    <span className="char-name">{char}</span>
                  </div>
                ))}
                {characters.length === 0 && <p className="subtitle">Launch your first character to begin.</p>}
              </div>
            </div>
          )}

          {activeTab === 'download' && (
            <DownloadTab
              selectedCharacter={selectedCharacter}
              vscoCookiesFile={cookieConfig.vsco}
              tiktokCookiesFile={cookieConfig.tiktok}
              isVscoUrl={url.includes('vsco.co')}
              isTiktokUrl={url.includes('tiktok.com')}
              url={url}
              setUrl={setUrl}
              onDownloadStarted={(id) => { setJobId(id); setIsDownloading(true); }}
              status={status}
              setStatus={setStatus}
              isDownloading={isDownloading}
              downloadProgress={progress}
              downloadLogs={logs}
              apiBase={API_BASE}
              onOpenVscoLogin={openVscoLogin}
              onCheckVscoSession={checkVscoSession}
              vscoSessionStatus={vscoSessionStatus}
              setDownloadLogs={setLogs}
            />
          )}

          {activeTab === 'video-frames' && (
            <VideoProcessingTab
              selectedCharacter={selectedCharacter}
              availableVideos={availableVideos}
              videoPath={videoPath}
              setVideoPath={setVideoPath}
              videoInterval={videoInterval}
              setVideoInterval={setVideoInterval}
              maxFrames={maxFrames}
              setMaxFrames={setMaxFrames}
              status={status}
              setStatus={setStatus}
              onRefresh={loadVideos}
              apiBase={API_BASE}
            />
          )}

          {activeTab === 'gallery' && (
            <div className="animate-fade-in">
              <h2>Media Curation</h2>
              <p className="subtitle" style={{ marginBottom: '32px' }}>Workspace: <strong>{selectedCharacter || 'Global'}</strong></p>
              <Gallery character={selectedCharacter || 'Unsorted'} />
            </div>
          )}

          {activeTab === 'process' && (
            <div className="animate-fade-in placeholder-view">
              <Crop size={64} style={{ opacity: 0.1, marginBottom: '24px' }} />
              <h3>Crop Engine Loading</h3>
              <p className="subtitle">The smart 1:1 adjustment module is being optimized for premium framing.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
