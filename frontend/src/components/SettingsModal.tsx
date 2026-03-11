import { motion } from 'framer-motion'
import { X, Save } from 'lucide-react'

interface CookieConfig {
    vsco: string
    tiktok: string
    instagram: string
}

interface SettingsModalProps {
    onClose: () => void
    onSave: () => void
    config: CookieConfig
    setConfig: (config: CookieConfig) => void
    status: string
}

export function SettingsModal({ onClose, onSave, config, setConfig, status }: SettingsModalProps) {
    return (
        <div className="safety-modal-backdrop" role="dialog" aria-modal="true">
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="safety-modal glass-panel"
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h2>Global Settings</h2>
                    <button className="icon-btn" onClick={onClose}><X size={20} /></button>
                </div>

                <p className="subtitle" style={{ marginBottom: '24px' }}>
                    Set default Netscape cookie file paths. These will be used automatically for all downloads.
                </p>

                <div className="form-group">
                    <label>VSCO Cookie File (.txt)</label>
                    <input
                        className="input"
                        value={config.vsco}
                        onChange={(e) => setConfig({ ...config, vsco: e.target.value })}
                        placeholder="e.g. H:\cookies\vsco.txt"
                    />
                </div>

                <div className="form-group">
                    <label>TikTok Cookie File (.txt)</label>
                    <input
                        className="input"
                        value={config.tiktok}
                        onChange={(e) => setConfig({ ...config, tiktok: e.target.value })}
                        placeholder="e.g. H:\cookies\tiktok.txt"
                    />
                </div>

                <div className="form-group">
                    <label>Instagram Cookie File (.txt)</label>
                    <input
                        className="input"
                        value={config.instagram}
                        onChange={(e) => setConfig({ ...config, instagram: e.target.value })}
                        placeholder="e.g. H:\cookies\instagram.txt"
                    />
                </div>

                {status && <p className="status-msg" style={{ marginTop: '10px', color: status.includes('Success') ? 'var(--success-color)' : '#ff4444' }}>{status}</p>}

                <div className="safety-actions" style={{ marginTop: '32px' }}>
                    <button className="btn" style={{ flex: 1 }} onClick={onClose}>Close</button>
                    <button className="btn btn-primary" style={{ flex: 1 }} onClick={onSave}>
                        <Save size={18} />
                        Save Configuration
                    </button>
                </div>
            </motion.div>
        </div>
    )
}
