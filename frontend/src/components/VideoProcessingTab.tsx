import { Search, Play, Scissors } from 'lucide-react'
import axios from 'axios'

interface VideoItem {
    name: string
    path: string
    folder: string
    size: number
    url: string
}

interface VideoProcessingTabProps {
    selectedCharacter: string | null
    availableVideos: VideoItem[]
    videoPath: string
    setVideoPath: (path: string) => void
    videoInterval: string
    setVideoInterval: (val: string) => void
    maxFrames: string
    setMaxFrames: (val: string) => void
    status: string
    setStatus: (msg: string) => void
    onRefresh: () => void
    apiBase: string
}

export function VideoProcessingTab({
    selectedCharacter,
    availableVideos,
    videoPath,
    setVideoPath,
    videoInterval,
    setVideoInterval,
    maxFrames,
    setMaxFrames,
    status,
    setStatus,
    onRefresh,
    apiBase
}: VideoProcessingTabProps) {

    const handleExtract = async () => {
        if (!selectedCharacter || !videoPath) return

        setStatus('Dispatching frame extraction request...')
        try {
            const response = await axios.post(`${apiBase}/api/video/extract-frames`, {
                video_path: videoPath.trim(),
                character: selectedCharacter,
                interval: Number(videoInterval) || 1,
                max_frames: maxFrames.trim() ? Number(maxFrames) : null,
            })
            setStatus(response.data.message || 'Extraction sequence completed.')
        } catch (error) {
            console.error(error)
            setStatus('Extraction failed: Backend communication error.')
        }
    }

    return (
        <div className="animate-fade-in">
            <h2>Neural Frame Extraction</h2>
            <p className="subtitle" style={{ marginBottom: '32px' }}>
                Deconstruct videos into high-quality training assets with precision interval control.
            </p>

            {!selectedCharacter ? (
                <div className="glass-panel" style={{ padding: '32px', textAlign: 'center' }}>
                    <p>Please select a character to view their video assets.</p>
                </div>
            ) : (
                <div className="video-workflow grid" style={{ gridTemplateColumns: '1.2fr 1fr', gap: '24px' }}>

                    {/* Left Side: Selection */}
                    <div className="video-selection-engine glass-panel">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <h3 style={{ margin: 0 }}>Available Source Media</h3>
                            <button className="icon-btn" onClick={onRefresh} title="Scan for new videos">
                                <Search size={18} />
                            </button>
                        </div>

                        <div className="video-list" style={{ maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {availableVideos.length === 0 ? (
                                <p className="subtitle" style={{ textAlign: 'center', padding: '40px' }}>No videos found. Use Data Collection first.</p>
                            ) : (
                                availableVideos.map((video) => (
                                    <div
                                        key={video.path}
                                        className={`video-item-card ${videoPath === video.path ? 'active' : ''}`}
                                        onClick={() => setVideoPath(video.path)}
                                    >
                                        <div className="video-preview-stub">
                                            <Play size={20} />
                                        </div>
                                        <div className="video-meta">
                                            <span className="name">{video.name}</span>
                                            <span className="folder">{video.folder}</span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Right Side: Parameters */}
                    <div className="video-parameters glass-panel">
                        <h3>Extraction Parameters</h3>

                        <div className="form-group">
                            <label>Manual Path Override</label>
                            <input
                                className="input"
                                value={videoPath}
                                onChange={(e) => setVideoPath(e.target.value)}
                                placeholder="Full system path if not listed..."
                            />
                        </div>

                        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <div className="form-group">
                                <label>Step Interval (S)</label>
                                <input
                                    type="number"
                                    className="input"
                                    value={videoInterval}
                                    onChange={(e) => setVideoInterval(e.target.value)}
                                    step="0.1"
                                />
                            </div>
                            <div className="form-group">
                                <label>Max Asset Limit</label>
                                <input
                                    type="number"
                                    className="input"
                                    value={maxFrames}
                                    onChange={(e) => setMaxFrames(e.target.value)}
                                    placeholder="Unlimited"
                                />
                            </div>
                        </div>

                        <button
                            className="btn btn-primary"
                            style={{ width: '100%', marginTop: '20px', height: '50px' }}
                            onClick={handleExtract}
                            disabled={!videoPath}
                        >
                            <Scissors size={20} />
                            Execute Frame Extraction
                        </button>

                        {status && (
                            <div className="status-box glass-panel" style={{ marginTop: '24px', background: 'rgba(255,255,255,0.03)' }}>
                                <p className="subtitle" style={{ margin: 0, color: 'var(--text-primary)' }}>{status}</p>
                            </div>
                        )}
                    </div>

                </div>
            )}
        </div>
    )
}
