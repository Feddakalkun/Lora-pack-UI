import { motion } from 'framer-motion'

interface SafetyModalProps {
    onContinue: () => void
    onDontShowAgain: () => void
}

export function SafetyModal({ onContinue, onDontShowAgain }: SafetyModalProps) {
    return (
        <div className="safety-modal-backdrop" role="dialog" aria-modal="true" aria-label="Safety notice">
            <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                className="safety-modal glass-panel"
            >
                <h2>Welcome to LoRA Pack Studio</h2>
                <p className="subtitle" style={{ marginBottom: '12px' }}>
                    Please read this before using downloads and scraping features.
                </p>

                <div className="safety-points">
                    <p><strong>VSCO Note:</strong> VSCO often blocks anonymous requests. For higher reliability, use the "VSCO Login Browser" in Settings once.</p>
                    <p><strong>Cookie Safety:</strong> This app runs entirely locally. Cookies are read locally to authenticate requests and are never shared or uploaded.</p>
                    <p><strong>Privacy:</strong> All media is saved to your local project folders.</p>
                    <p><strong>Compliance:</strong> You are responsible for using this tool in accordance with each platform's terms of service.</p>
                </div>

                <div className="safety-actions">
                    <button className="btn" onClick={onDontShowAgain}>Do Not Show Again</button>
                    <button className="btn btn-primary" onClick={onContinue}>I Understand</button>
                </div>
            </motion.div>
        </div>
    )
}
