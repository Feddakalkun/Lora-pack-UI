import { Download, Search, Users, ExternalLink, ShieldCheck } from 'lucide-react'
import axios from 'axios'

interface DownloadTabProps {
    selectedCharacter: string | null
    vscoCookiesFile: string
    tiktokCookiesFile: string
    isVscoUrl: boolean
    isTiktokUrl: boolean
    url: string
    setUrl: (url: string) => void
    onDownloadStarted: (jobId: string) => void
    status: string
    setStatus: (status: string) => void
    isDownloading: boolean
    downloadProgress: number
    downloadLogs: string[]
    apiBase: string
    onOpenVscoLogin: () => void
    onCheckVscoSession: () => void
    vscoSessionStatus: string
    setDownloadLogs: (fn: (prev: string[]) => string[]) => void
}

export function DownloadTab({
    selectedCharacter,
    vscoCookiesFile,
    tiktokCookiesFile,
    isVscoUrl,
    isTiktokUrl,
    url,
    setUrl,
    onDownloadStarted,
    status,
    setStatus,
    isDownloading,
    downloadProgress,
    downloadLogs,
    apiBase,
    onOpenVscoLogin,
    onCheckVscoSession,
    vscoSessionStatus,
    setDownloadLogs
}: DownloadTabProps) {

    const handleDownload = async () => {
        if (!url) return
        setStatus('Initializing download engine...')
        setDownloadLogs((prev: string[]) => [...prev, `[INFO] Contacting backend at: ${apiBase}`])

        try {
            const response = await axios.post(`${apiBase}/api/download/start`, {
                url: url,
                platform: 'auto',
                character: selectedCharacter || 'Unsorted',
                vsco_cookies_file: isVscoUrl && vscoCookiesFile.trim() ? vscoCookiesFile.trim() : null,
                tiktok_cookies_file: isTiktokUrl && tiktokCookiesFile.trim() ? tiktokCookiesFile.trim() : null,
            })

            if (response.data?.status === 'success' && response.data?.job_id) {
                onDownloadStarted(response.data.job_id)
            } else {
                setStatus(`Error: ${response.data?.message || 'Could not start job.'}`)
            }
        } catch (error: any) {
            console.error('Download initiation failed:', error)
            let details = 'Connection failed. Ensure the backend is running.'
            if (error.response) {
                details = `Server Error (${error.response.status}): ${JSON.stringify(error.response.data)}`
            } else if (error.request) {
                details = 'No response from server. Check if port 8000 is open.'
            } else {
                details = error.message
            }
            setStatus(`Critical Error: ${details}`)
            setDownloadLogs((prev: string[]) => [...prev, `[CRITICAL] ${details}`])
        }
    }

    return (
        <div className="animate-fade-in">
            <h2>Media Intelligence & Data Collection</h2>
            <p className="subtitle" style={{ marginBottom: '32px' }}>
                Paste a URL from VSCO or TikTok to ingest media directly into your training pipeline.
            </p>

            {!selectedCharacter ? (
                <div className="glass-panel" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <Users size={32} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
                    <p>Please select a <strong>Character</strong> first to enable localized downloads.</p>
                </div>
            ) : (
                <div className="download-workflow">
                    <div className="form-group glass-panel" style={{ padding: '24px' }}>
                        <label>Source URL</label>
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <input
                                type="text"
                                className="input"
                                placeholder="https://vsco.co/username or https://tiktok.com/@username..."
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                            />
                            <button
                                className="btn btn-primary"
                                onClick={handleDownload}
                                disabled={isDownloading}
                            >
                                <Download size={20} />
                                {isDownloading ? 'In Progress' : 'Start Ingestion'}
                            </button>
                        </div>
                    </div>

                    {isVscoUrl && (
                        <div className="form-group glass-panel" style={{ padding: '24px', marginTop: '16px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <label style={{ margin: 0 }}>VSCO Session Management</label>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    <button className="btn small" onClick={onOpenVscoLogin} title="Open helper window">
                                        <ExternalLink size={16} /> Open Login
                                    </button>
                                    <button className="btn small" onClick={onCheckVscoSession}>
                                        <ShieldCheck size={16} /> Verify Session
                                    </button>
                                </div>
                            </div>
                            {vscoSessionStatus && <p className="subtitle" style={{ color: 'var(--accent-color)', fontWeight: 500 }}>{vscoSessionStatus}</p>}
                        </div>
                    )}

                    {(status || isDownloading || downloadLogs.length > 0) && (
                        <div className="glass-panel" style={{ marginTop: '24px', background: 'rgba(99, 102, 241, 0.05)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                                <p style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-color)', fontWeight: 600 }}>
                                    <Search size={18} />
                                    {status || 'Ingestion Engine Active'}
                                </p>
                                <span style={{ fontSize: '0.9rem', opacity: 0.8 }}>{downloadProgress}%</span>
                            </div>

                            <div className="download-progress-wrap">
                                <div
                                    className="download-progress-bar"
                                    style={{ width: `${Math.max(2, downloadProgress)}%`, transition: 'width 0.5s cubic-bezier(0.4, 0, 0.2, 1)' }}
                                ></div>
                            </div>

                            {downloadLogs.length > 0 && (
                                <div className="download-log-box" style={{ marginTop: '16px', maxHeight: '150px' }}>
                                    {downloadLogs.slice(-6).map((line: string, idx: number) => (
                                        <div key={`${idx}-${line}`} className="download-log-line">{line}</div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
