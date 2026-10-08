import { useState, type SyntheticEvent } from 'react'

/**
 * Catalogue photos come with mixed backgrounds (white, light gray, black). Sample the image's corner
 * pixel once it loads and paint the frame the same color so the photo blends into its card.
 */
export default function ProductImage({ src, alt, className, lazy = true }: {
  src: string
  alt: string
  className: string
  lazy?: boolean
}) {
  const [background, setBackground] = useState<string | undefined>()
  const [failed, setFailed] = useState(false)

  function handleLoad(e: SyntheticEvent<HTMLImageElement>) {
    try {
      const canvas = document.createElement('canvas')
      canvas.width = canvas.height = 1
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      if (!ctx) return
      ctx.drawImage(e.currentTarget, 0, 0, 1, 1, 0, 0, 1, 1)
      const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data
      setBackground(`rgb(${r}, ${g}, ${b})`)
    } catch {
      // Cross-origin or decode issue: keep the default frame color.
    }
  }

  return (
    <div className={className} style={background ? { background } : undefined}>
      {failed ? (
        <span className="image-fallback" role="img" aria-label={alt || undefined}>Photo coming soon</span>
      ) : (
        <img src={src} alt={alt} loading={lazy ? 'lazy' : 'eager'} onLoad={handleLoad} onError={() => setFailed(true)} />
      )}
    </div>
  )
}
