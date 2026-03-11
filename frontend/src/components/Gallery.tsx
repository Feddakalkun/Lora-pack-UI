import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Maximize2, Check, X, Scissors, Trash2 } from 'lucide-react'
import axios from 'axios'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://localhost:8000'

interface ImageItem {
    name: string
    url: string
    size: number
    folder: string
}

interface GalleryProps {
    character: string
}

export function Gallery({ character }: GalleryProps) {
    const [images, setImages] = useState<ImageItem[]>([])
    const [loading, setLoading] = useState(true)
    const [selectedImage, setSelectedImage] = useState<ImageItem | null>(null)
    const [viewFolder, setViewFolder] = useState('root')

    const fetchImages = async () => {
        setLoading(true)
        try {
            const response = await axios.get(`${API_BASE}/api/images/${character}`)
            setImages(response.data.images)
        } catch (error) {
            console.error('Error fetching images:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchImages()
    }, [character])

    const filteredImages = images.filter(img =>
        viewFolder === 'root' ? true : img.folder === viewFolder
    )

    const formatSize = (bytes: number) => {
        return (bytes / 1024 / 1024).toFixed(2) + ' MB'
    }

    return (
        <div className="gallery-container">
            <div className="gallery-header glass-panel">
                <div className="gallery-filters">
                    <div className="filter-group">
                        <span className="filter-label">Viewing:</span>
                        <select
                            className="premium-select"
                            value={viewFolder}
                            onChange={(e) => setViewFolder(e.target.value)}
                        >
                            <option value="root">All Folders</option>
                            <option value="source">Source Folder</option>
                            <option value="tiktok">TikTok</option>
                            <option value="frames">Frames</option>
                            <option value="keep">Keep</option>
                            <option value="inpaint">Inpaint</option>
                            <option value="final_keep">Final Keep</option>
                        </select>
                    </div>
                    <div className="filter-group">
                        <span className="filter-label">Showing:</span>
                        <span className="stat-value small">{filteredImages.length}</span>
                    </div>
                </div>
                <div className="gallery-actions">
                    <button className="icon-btn action-keep" title="Move all to Keep">
                        <Check size={18} />
                    </button>
                    <button className="icon-btn action-remove" title="Move all to Trash">
                        <Trash2 size={18} />
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="gallery-loading">
                    <div className="spinner"></div>
                    <p>Loading curated images...</p>
                </div>
            ) : (
                <div className="gallery-grid">
                    {filteredImages.map((img, idx) => (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            key={idx}
                            className="gallery-card"
                        >
                            <div className="img-wrapper" onClick={() => setSelectedImage(img)}>
                                <img src={img.url} alt={img.name} loading="lazy" />
                                <div className="img-overlay">
                                    <Maximize2 size={24} />
                                </div>
                            </div>
                            <div className="gallery-card-info">
                                <span className="img-name" title={img.name}>{img.name}</span>
                                <span className="img-size">{formatSize(img.size)}</span>
                            </div>

                            {/* Quick Triage Actions */}
                            <div className="quick-actions">
                                <button className="action-btn keep" title="Keep">
                                    <Check size={16} />
                                    <span>Keep</span>
                                </button>
                                <button className="action-btn crop" title="Send to Auto-Crop">
                                    <Scissors size={16} />
                                </button>
                                <button className="action-btn trash" title="Remove">
                                    <X size={16} />
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}

            {/* Lightbox / Fullscreen Image Viewer Modal */}
            <AnimatePresence>
                {selectedImage && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="lightbox-overlay"
                        onClick={() => setSelectedImage(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.9 }}
                            animate={{ scale: 1 }}
                            exit={{ scale: 0.9 }}
                            className="lightbox-content"
                            onClick={e => e.stopPropagation()}
                        >
                            <img src={selectedImage.url} alt={selectedImage.name} />
                            <div className="lightbox-toolbar glass-panel">
                                <span className="lightbox-title">{selectedImage.name}</span>
                                <div className="lightbox-actions">
                                    <button className="action-btn keep"><Check size={20} /> Keep</button>
                                    <button className="action-btn crop"><Scissors size={20} /> Auto-Crop</button>
                                    <button className="action-btn trash"><Trash2 size={20} /> Remove</button>
                                </div>
                                <button className="icon-btn close-btn" onClick={() => setSelectedImage(null)}>
                                    <X size={24} />
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
