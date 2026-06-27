import http from 'node:http'

const PORT = 8098

function extractOrigin(url) {
  try {
    const u = new URL(url)
    return `${u.protocol}//${u.host}`
  } catch {
    return ''
  }
}

function rewriteHtml(html, targetOrigin) {
  const browse = '/browse/'
  let out = html

  // Rewrite absolute https/http URLs in HTML attributes (do first, before relative rewrites)
  out = out.replace(/((?:src|href|action)\s*=\s*["'])https:\/\//gi, `$1${browse}https://`)
  out = out.replace(/((?:src|href|action)\s*=\s*["'])http:\/\//gi, `$1${browse}http://`)

  // Rewrite protocol-relative URLs: src="//cdn.example.com/..."
  out = out.replace(/((?:src|href|action)\s*=\s*["'])\/\//gi, `$1${browse}https://`)

  // Rewrite root-relative URLs: src="/path" (but not already-rewritten /browse/ paths)
  out = out.replace(/((?:src|href|action)\s*=\s*["'])\/(?!browse\/)/gi, `$1${browse}${targetOrigin}/`)

  // Rewrite url() in inline styles
  out = out.replace(/url\(\s*['"]?\/(?!browse\/)/gi, `url('${browse}${targetOrigin}/`)

  // Inject <base> tag for any relative URLs the regex missed
  if (!out.match(/<base\s/i)) {
    out = out.replace(/<head([^>]*)>/i, `<head$1><base href="${browse}${targetOrigin}/">`)
  }

  return out
}

function rewriteCss(css, targetOrigin) {
  const browse = '/browse/'
  let out = css
  // Rewrite url(https://...) and url(http://...) first
  out = out.replace(/url\(\s*['"]?https:\/\//gi, `url('${browse}https://`)
  out = out.replace(/url\(\s*['"]?http:\/\//gi, `url('${browse}http://`)
  // Rewrite url(/path) — skip already-rewritten /browse/ paths
  out = out.replace(/url\(\s*['"]?\/(?!browse\/)/gi, `url('${browse}${targetOrigin}/`)
  return out
}

const server = http.createServer(async (req, res) => {
  // Extract target URL from X-Target-URL header (set by nginx)
  // Format: /browse/https://example.com/path
  const targetHeader = req.headers['x-target-url'] || req.url
  const match = targetHeader.match(/^\/browse\/(.+)$/)
  if (!match) {
    res.writeHead(400, { 'Content-Type': 'text/plain' })
    res.end('Missing target URL. Use /browse/<url>')
    return
  }

  const targetUrl = decodeURIComponent(match[1])
  const targetOrigin = extractOrigin(targetUrl)

  if (!targetOrigin) {
    res.writeHead(400, { 'Content-Type': 'text/plain' })
    res.end('Invalid target URL')
    return
  }

  try {
    const upstream = await fetch(targetUrl, {
      headers: {
        'User-Agent': req.headers['user-agent'] || 'Mozilla/5.0',
        'Accept': req.headers['accept'] || '*/*',
        'Accept-Language': req.headers['accept-language'] || 'en-US,en;q=0.9',
      },
      redirect: 'manual',
    })

    // Handle redirects: rewrite Location header to go through proxy
    if (upstream.status >= 300 && upstream.status < 400) {
      const location = upstream.headers.get('location')
      if (location) {
        let rewritten = location
        if (location.startsWith('/')) {
          rewritten = `/browse/${targetOrigin}${location}`
        } else if (location.startsWith('http')) {
          rewritten = `/browse/${location}`
        }
        res.writeHead(upstream.status, { 'Location': rewritten })
        res.end()
        return
      }
    }

    const contentType = upstream.headers.get('content-type') || ''
    const headers = {}

    // Copy safe headers, skip anti-framing ones
    const skipHeaders = new Set([
      'x-frame-options',
      'content-security-policy',
      'content-security-policy-report-only',
      'content-encoding',
      'transfer-encoding',
      'content-length',
      'strict-transport-security',
    ])

    for (const [key, value] of upstream.headers.entries()) {
      if (!skipHeaders.has(key.toLowerCase())) {
        headers[key] = value
      }
    }

    const body = await upstream.arrayBuffer()
    let output

    if (contentType.includes('text/html')) {
      const text = new TextDecoder().decode(body)
      output = Buffer.from(rewriteHtml(text, targetOrigin))
      headers['content-type'] = contentType
    } else if (contentType.includes('text/css')) {
      const text = new TextDecoder().decode(body)
      output = Buffer.from(rewriteCss(text, targetOrigin))
      headers['content-type'] = contentType
    } else {
      output = Buffer.from(body)
    }

    headers['content-length'] = output.length
    headers['x-proxied-by'] = 'umh-cockpit-browse'

    res.writeHead(upstream.status, headers)
    res.end(output)
  } catch (err) {
    res.writeHead(502, { 'Content-Type': 'text/plain' })
    res.end(`Proxy error: ${err.message}`)
  }
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[browse-proxy] listening on 127.0.0.1:${PORT}`)
})
