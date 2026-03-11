import { useEffect, useState } from 'react'
import { Download, Image as ImageIcon, Wand2, Settings, Search, Users, Plus, Frame, Crop } from 'lucide-react'
import axios from 'axios'
import { Gallery } from './components/Gallery'

type CookieConfig = {
  vsco: string
  tiktok: string
  instagram: string
}

function App() {
  const [activeTab, setActiveTab] = useState('characters')
  const [url, setUrl] = useState('')
  const [status, setStatus] = useState('')
  const [characters, setCharacters] = useState<string[]>([])
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null)

  const [videoPath, setVideoPath] = useState('')
  const [videoInterval, setVideoInterval] = useState('1')
  const [maxFrames, setMaxFrames] = useState('')
  const [frameStatus, setFrameStatus] = useState('')
  const [availableVideos, setAvailableVideos] = useState<Array<{ name: string; path: string; folder: string }>>([])

  const [showSafetyModal, setShowSafetyModal] = useState(false)
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [vscoCookiesFile, setVscoCookiesFile] = useState('')
  const [vscoSessionStatus, setVscoSessionStatus] = useState('')

  const [cookieConfig, setCookieConfig] = useState<CookieConfig>({ vsco: '', tiktok: '', instagram: '' })
  const [cookieStatus, setCookieStatus] = useState('')

  const [downloadJobId, setDownloadJobId] = useState<string | null>(null)
  const [downloadProgress, setDownloadProgress] = useState(0)
  const [downloadLogs, setDownloadLogs] = useState<string[]>([])
  const [isDownloading, setIsDownloading] = useState(false)

  useEffect(() => {
    const dismissed = localStorage.getItem('lora_pack_disclaimer_v1')
    if (dismissed !== '1') {
      setShowSafetyModal(true)
    }
    loadCookieConfig()
  }, [])


  useEffect(() => {
    if (!downloadJobId) return

    const timer = window.setInterval(async () => {
      try {
        const response = await axios.get(`http://localhost:8000/api/download/status/${downloadJobId}`)
        const ok = String(response.data?.status || '').toLowerCase() === 'success'
        if (!ok) {
          setIsDownloading(false)
          setDownloadJobId(null)
          setStatus(`Error: ${response.data?.message || 'Unknown download status error'}`)
          return
        }

        const job = response.data?.job || {}
        setDownloadProgress(Number(job.progress || 0))
        setDownloadLogs(Array.isArray(job.logs) ? job.logs : [])

        const jobStatus = String(job.status || '').toLowerCase()
        const msg = String(job.message || '').trim()

        if (jobStatus === 'success') {
          setIsDownloading(false)
          setDownloadJobId(null)
          setStatus(`Success: ${msg || 'Download completed.'}`)
          window.clearInterval(timer)
          return
        }

        if (jobStatus === 'error') {
          setIsDownloading(false)
          setDownloadJobId(null)
          setStatus(`Error: ${msg || 'Download failed.'}`)
          window.clearInterval(timer)
          return
        }

        setStatus(msg ? `Running: ${msg}` : 'Running...')
      } catch (error) {
        console.error(error)
        setIsDownloading(false)
        setDownloadJobId(null)
        setStatus('Error: Lost connection while reading download progress.')
        window.clearInterval(timer)
      }
    }, 1200)

    return () => window.clearInterval(timer)
  }, [downloadJobId])
  const isVscoUrl = url.toLowerCase().includes('vsco.co')
  const isTiktokUrl = url.toLowerCase().includes('tiktok.com')

  const loadCookieConfig = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/cookies/config')
      const cfg = response.data?.config || { vsco: '', tiktok: '', instagram: '' }
      setCookieConfig({
        vsco: cfg.vsco || '',
        tiktok: cfg.tiktok || '',
        instagram: cfg.instagram || '',
      })
      if (!vscoCookiesFile && cfg.vsco) {
        setVscoCookiesFile(cfg.vsco)
      }
    } catch (error) {
      console.error(error)
    }
  }

  const saveCookieConfig = async () => {
    setCookieStatus('Saving cookie configuration...')
    try {
      const response = await axios.post('http://localhost:8000/api/cookies/config', cookieConfig)
      const ok = String(response.data?.status || '').toLowerCase() === 'success'
      setCookieStatus(`${ok ? 'Success' : 'Error'}: ${response.data?.message || 'Unknown response'}`)
      if (cookieConfig.vsco) {
        setVscoCookiesFile(cookieConfig.vsco)
      }
    } catch (error) {
      console.error(error)
      setCookieStatus('Error: Could not save cookie configuration.')
    }
  }

  const handleDownload = async () => {
    if (!url) return
    setStatus('Starting download...')
    setIsDownloading(true)
    setDownloadProgress(5)
    setDownloadLogs([])

    try {
      const response = await axios.post('http://localhost:8000/api/download/start', {
        url: url,
        platform: 'auto',
        character: selectedCharacter || 'Unsorted',
        vsco_cookies_file: isVscoUrl && vscoCookiesFile.trim() ? vscoCookiesFile.trim() : null,
        tiktok_cookies_file: isTiktokUrl && cookieConfig.tiktok.trim() ? cookieConfig.tiktok.trim() : null,
      })

      const ok = String(response.data?.status || '').toLowerCase() === 'success'
      if (!ok || !response.data?.job_id) {
        setIsDownloading(false)
        setStatus(`Error: ${response.data?.message || 'Could not start download job.'}`)
        return
      }

      setDownloadJobId(String(response.data.job_id))
      setStatus('Queued download...')
    } catch (error) {
      console.error(error)
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        setIsDownloading(false)
        setStatus('Error: Connected to an older/wrong backend on :8000. Close other backend windows and run run.cmd in this folder.')
        return
      }
      setIsDownloading(false)
      setStatus('Error connecting to backend.')
    }
  }

  const loadCharacterVideos = async () => {
    if (!selectedCharacter) return
    try {
      const response = await axios.get(`http://localhost:8000/api/videos/${selectedCharacter}`)
      setAvailableVideos(response.data.videos || [])
      if ((response.data.videos || []).length === 0) {
        setFrameStatus('No videos found yet for this character. Download TikTok first.')
      }
    } catch (error) {
      console.error(error)
      setAvailableVideos([])
      setFrameStatus('Could not load videos from backend.')
    }
  }

  const handleExtractFrames = async () => {
    if (!selectedCharacter) {
      setFrameStatus('Please select a character first.')
      return
    }
    if (!videoPath.trim()) {
      setFrameStatus('Please select or paste a video path.')
      return
    }

    setFrameStatus('Extracting frames...')
    try {
      const response = await axios.post('http://localhost:8000/api/video/extract-frames', {
        video_path: videoPath.trim(),
        character: selectedCharacter,
        interval: Number(videoInterval) || 1,
        max_frames: maxFrames.trim() ? Number(maxFrames) : null,
      })
      setFrameStatus(response.data.message || 'Frame extraction finished.')
    } catch (error) {
      console.error(error)
      setFrameStatus('Error connecting to backend.')
    }
  }

  const openVscoLoginBrowser = async () => {
    setVscoSessionStatus('Opening VSCO login browser...')
    try {
      const response = await axios.post('http://localhost:8000/api/vsco/session/open-login')
      const ok = String(response.data?.status || '').toLowerCase() === 'success'
      setVscoSessionStatus(`${ok ? 'Success' : 'Error'}: ${response.data?.message || 'Unknown response'}`)
    } catch (error) {
      console.error(error)
      setVscoSessionStatus('Error: Could not open VSCO login browser.')
    }
  }

  const checkVscoSessionStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/vsco/session/status')
      const ok = String(response.data?.status || '').toLowerCase() === 'success'
      const details = response.data?.message || 'Unknown response'
      setVscoSessionStatus(`${ok ? 'Success' : 'Error'}: ${details}`)
    } catch (error) {
      console.error(error)
      setVscoSessionStatus('Error: Could not check VSCO session status.')
    }
  }

  const handleDisclaimerContinue = () => {
    setShowSafetyModal(false)
  }

  const handleDisclaimerDontShowAgain = () => {
    localStorage.setItem('lora_pack_disclaimer_v1', '1')
    setShowSafetyModal(false)
  }

  return (
    <div className="app-container animate-fade-in">
      {showSafetyModal && (
        <div className="safety-modal-backdrop" role="dialog" aria-modal="true" aria-label="Safety notice">
          <div className="safety-modal glass-panel">
            <h2>Welcome to LoRA Pack Studio</h2>
            <p className="subtitle" style={{ marginBottom: '12px' }}>
              Please read this before using downloads and scraping features.
            </p>

            <div className="safety-points">
              <p><strong>VSCO note:</strong> Public profiles can work, but VSCO often blocks anonymous requests. For better reliability, sign in to VSCO in Chrome or Edge first.</p>
              <p><strong>Cookie safety:</strong> This app only runs locally on your machine. Cookies are read temporarily to authenticate requests and are not uploaded by this app.</p>
              <p><strong>Privacy:</strong> Downloads, extracted frames, and metadata are saved only to your local project folders unless you manually move or share them.</p>
              <p><strong>Compliance:</strong> You are responsible for using this tool in line with each platform's terms and applicable laws.</p>
            </div>

            <div className="safety-actions">
              <button className="btn" onClick={handleDisclaimerDontShowAgain}>Do Not Show Again</button>
              <button className="btn btn-primary" onClick={handleDisclaimerContinue}>I Understand</button>
            </div>
          </div>
        </div>
      )}

      {showSettingsModal && (
        <div className="safety-modal-backdrop" role="dialog" aria-modal="true" aria-label="Cookie settings">
          <div className="safety-modal glass-panel">
            <h2>Cookie Settings</h2>
            <p className="subtitle" style={{ marginBottom: '12px' }}>
              Set default Netscape cookie files once. The app will reuse these paths for downloads.
            </p>

            <div className="form-group">
              <label>VSCO Cookie File</label>
              <input className="input" value={cookieConfig.vsco} onChange={(e) => setCookieConfig((prev) => ({ ...prev, vsco: e.target.value }))} placeholder="H:\\cookies\\vsco_cookies.txt" />
            </div>

            <div className="form-group">
              <label>TikTok Cookie File</label>
              <input className="input" value={cookieConfig.tiktok} onChange={(e) => setCookieConfig((prev) => ({ ...prev, tiktok: e.target.value }))} placeholder="H:\\cookies\\tiktok_cookies.txt" />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Instagram Cookie File</label>
              <input className="input" value={cookieConfig.instagram} onChange={(e) => setCookieConfig((prev) => ({ ...prev, instagram: e.target.value }))} placeholder="H:\\cookies\\instagram_cookies.txt" />
            </div>

            {cookieStatus && <p className="subtitle" style={{ marginTop: '10px' }}>{cookieStatus}</p>}

            <div className="safety-actions">
              <button className="btn" onClick={() => setShowSettingsModal(false)}>Close</button>
              <button className="btn btn-primary" onClick={saveCookieConfig}>Save Defaults</button>
            </div>
          </div>
        </div>
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
            Settings
          </button>
        </div>
      </header>

      <div className="grid-layout">
        <nav className="sidebar glass-panel" style={{ padding: '16px' }}>
          <button className={`nav-item ${activeTab === 'characters' ? 'active' : ''}`} onClick={() => setActiveTab('characters')}>
            <Users size={20} />
            Characters
          </button>

          <div style={{ margin: '16px 0', borderBottom: '1px solid var(--glass-border)' }}></div>

          <div style={{ padding: '0 16px', marginBottom: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {selectedCharacter ? `Active: ${selectedCharacter}` : 'Workflow'}
          </div>

          <button className={`nav-item ${activeTab === 'download' ? 'active' : ''}`} onClick={() => setActiveTab('download')}>
            <Download size={20} />
            Data Collection
          </button>
          <button className={`nav-item ${activeTab === 'video-frames' ? 'active' : ''}`} onClick={() => setActiveTab('video-frames')}>
            <Frame size={20} />
            Video Processing
          </button>
          <button className={`nav-item ${activeTab === 'process' ? 'active' : ''}`} onClick={() => setActiveTab('process')}>
            <Crop size={20} />
            Auto-Cropping (1:1)
          </button>
          <button className={`nav-item ${activeTab === 'outpaint' ? 'active' : ''}`} onClick={() => setActiveTab('outpaint')}>
            <Wand2 size={20} />
            AI Outpainting
          </button>
          <button className={`nav-item ${activeTab === 'gallery' ? 'active' : ''}`} onClick={() => setActiveTab('gallery')}>
            <ImageIcon size={20} />
            Curation & Gallery
          </button>
        </nav>

        <main className="glass-panel" style={{ minHeight: '70vh' }}>
          {activeTab === 'characters' && (
            <div className="animate-fade-in">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <div>
                  <h2>Characters</h2>
                  <p className="subtitle">Select a character to work on or create a new one.</p>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => {
                    const name = prompt('Enter new character name:')
                    if (name && name.trim() && !characters.includes(name.trim())) {
                      setCharacters(prev => [...prev, name.trim()])
                      setSelectedCharacter(name.trim())
                    }
                  }}
                >
                  <Plus size={20} />
                  New Character
                </button>
              </div>

              <div className="stats-grid">
                {characters.length === 0 ? (
                  <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', gridColumn: '1 / -1', color: 'var(--text-secondary)' }}>
                    <Users size={48} style={{ opacity: 0.2, margin: '0 auto 16px', display: 'block' }} />
                    <h3>No characters found</h3>
                    <p style={{ marginTop: '8px' }}>Click "New Character" to start building your first dataset.</p>
                  </div>
                ) : (
                  characters.map(char => (
                    <div
                      key={char}
                      className="glass-panel stat-card"
                      style={{ padding: '24px', cursor: 'pointer', borderColor: selectedCharacter === char ? 'var(--accent-color)' : 'var(--glass-border)', transition: 'all 0.2s' }}
                      onClick={() => setSelectedCharacter(char)}
                    >
                      <Users className="header-icon" size={32} style={{ marginBottom: '12px' }} />
                      <span style={{ fontSize: '1.2rem', fontWeight: 600 }}>{char}</span>
                      <span className="stat-label">Click to select</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'download' && (
            <div className="animate-fade-in">
              <h2>Data Collection</h2>
              <p className="subtitle" style={{ marginBottom: '32px' }}>
                Download images and videos from TikTok, Instagram, VSCO, etc.
              </p>

              {!selectedCharacter ? (
                <div className="glass-panel" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  <Users size={32} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
                  <p>Please select a character from the "Characters" tab first to start downloading into their folder.</p>
                </div>
              ) : (
                <>
                  <div className="form-group">
                    <label>Profile URL or Post URL</label>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <input
                        type="text"
                        className="input"
                        placeholder="https://vsco.co/username/gallery or https://tiktok.com/@username/video/..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                      />
                      <button className="btn btn-primary" onClick={handleDownload}>
                        <Download size={20} />
                        Start Run
                      </button>
                    </div>
                  </div>

                  {isVscoUrl && (
                    <div className="form-group" style={{ marginTop: '-6px' }}>
                      <label>VSCO Cookie File Override (optional)</label>
                      <input
                        type="text"
                        className="input"
                        placeholder="Leave empty to use Settings default"
                        value={vscoCookiesFile}
                        onChange={(e) => setVscoCookiesFile(e.target.value)}
                      />

                      <div style={{ display: 'flex', gap: '10px', marginTop: '10px', flexWrap: 'wrap' }}>
                        <button type="button" className="btn" onClick={openVscoLoginBrowser}>
                          Open VSCO Login Browser
                        </button>
                        <button type="button" className="btn" onClick={checkVscoSessionStatus}>
                          Check VSCO Session
                        </button>
                      </div>

                      {vscoSessionStatus && <p className="subtitle" style={{ marginTop: '8px' }}>{vscoSessionStatus}</p>}

                      <p className="subtitle" style={{ marginTop: '8px' }}>
                        Recommended flow: open VSCO login browser, sign in once, close it, then Start Run.
                      </p>
                    </div>
                  )}

                  {(status || isDownloading || downloadLogs.length > 0) && (
                    <div className="glass-panel" style={{ marginTop: '24px', background: 'rgba(99, 102, 241, 0.1)', borderColor: 'rgba(99, 102, 241, 0.2)' }}>
                      <p style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#818cf8', fontWeight: 500 }}>
                        <Search size={18} />
                        {status || 'Preparing...'}
                      </p>

                      <div className="download-progress-wrap">
                        <div className="download-progress-bar" style={{ width: `${Math.max(3, Math.min(100, downloadProgress))}%` }}></div>
                      </div>

                      {downloadLogs.length > 0 && (
                        <div className="download-log-box">
                          {downloadLogs.slice(-8).map((line: string, idx: number) => (
                            <div key={`${idx}-${line}`} className="download-log-line">{line}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {activeTab === 'video-frames' && (
            <div className="animate-fade-in" style={{ padding: '20px' }}>
              <h2>Video Frame Extraction</h2>
              <p className="subtitle" style={{ marginBottom: '32px' }}>
                Extract high-quality frames from downloaded videos using interval control.
              </p>

              {!selectedCharacter ? (
                <div className="glass-panel" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                  <Users size={32} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
                  <p>Please select a character from the "Characters" tab first.</p>
                </div>
              ) : (
                <div className="glass-panel" style={{ display: 'grid', gap: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                    <div>
                      <h3 style={{ marginBottom: '6px' }}>Source Video</h3>
                      <p className="subtitle" style={{ marginTop: 0 }}>Pick a downloaded video or paste a full local path.</p>
                    </div>
                    <button className="btn" onClick={loadCharacterVideos}>
                      <Search size={18} />
                      Refresh Videos
                    </button>
                  </div>

                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Available Videos</label>
                    <select className="premium-select" style={{ width: '100%', minHeight: '46px' }} value={videoPath} onChange={(e) => setVideoPath(e.target.value)}>
                      <option value="">Select a video...</option>
                      {availableVideos.map((video) => (
                        <option key={video.path} value={video.path}>
                          {video.name} ({video.folder})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Video Path (manual override)</label>
                    <input type="text" className="input" value={videoPath} placeholder="H:\\path\\to\\video.mp4" onChange={(e) => setVideoPath(e.target.value)} />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label>Interval (seconds)</label>
                      <input type="number" className="input" min="0.1" step="0.1" value={videoInterval} onChange={(e) => setVideoInterval(e.target.value)} />
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label>Max Frames (optional)</label>
                      <input type="number" className="input" min="1" step="1" value={maxFrames} onChange={(e) => setMaxFrames(e.target.value)} placeholder="Leave empty for all" />
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    <button className="btn btn-primary" onClick={handleExtractFrames}>
                      <Frame size={18} />
                      Extract Frames
                    </button>
                  </div>

                  {frameStatus && (
                    <div className="glass-panel" style={{ background: 'rgba(99, 102, 241, 0.1)', borderColor: 'rgba(99, 102, 241, 0.2)' }}>
                      <p style={{ color: '#818cf8', fontWeight: 500 }}>{frameStatus}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'process' && (
            <div className="animate-fade-in" style={{ padding: '20px' }}>
              <h2>Auto-Cropping (1:1)</h2>
              <p className="subtitle" style={{ marginBottom: '32px' }}>
                Smart crop your images. The bounding box can be minimized, enlarged, and freely adjusted, not just locked to a static square.
              </p>

              <div className="glass-panel" style={{ borderStyle: 'dashed', textAlign: 'center', padding: '60px 20px', color: 'var(--text-secondary)' }}>
                <Crop size={48} style={{ opacity: 0.5, marginBottom: '16px', margin: '0 auto', display: 'block' }} />
                <h3>Adjustable Crop Workspace</h3>
                <p className="subtitle">
                  Here we will implement the dynamic 1:1 cropping UI. You will be able to scale the box and position it optimally for each subject.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'outpaint' && (
            <div className="animate-fade-in" style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-secondary)' }}>
              <Wand2 size={48} style={{ opacity: 0.5, marginBottom: '16px', margin: '0 auto', display: 'block' }} />
              <h3>Module Under Development</h3>
              <p className="subtitle">This section is currently being constructed by the team.</p>
            </div>
          )}

          {activeTab === 'gallery' && (
            <div className="animate-fade-in">
              <h2>Curation Gallery</h2>
              <p className="subtitle" style={{ marginBottom: '32px' }}>
                Review downloaded media for <strong>{selectedCharacter || 'Unsorted'}</strong>, use auto-crop, or send directly to ComfyUI.
              </p>
              <Gallery character={selectedCharacter || 'Unsorted'} />
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
