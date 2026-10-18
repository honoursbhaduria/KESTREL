#!/usr/bin/env node
/**
 * Reference scraper: builds a local mood board + animation inventory for a site.
 *
 *   node tools/scrape-reference.mjs [url] [--pages 8] [--videos] [--out reference/<host>]
 *
 * Output (reference/<host>/):
 *   images/            every image/SVG the pages load (deduplicated by URL)
 *   videos/            only with --videos
 *   manifest.json      one entry per asset: source URL, page, size, alt text, element
 *   animations.json    runtime log of GSAP tweens/timelines, ScrollTrigger and Lenis config
 *   css-motion.json    @keyframes and every rule that sets animation/transition
 *   libraries.json     external scripts the site loads
 *   index.html         gallery with reverse-image-search links (Lens / TinEye / Bing)
 *   REPORT.md          human summary
 *
 * This is for research and finding similar or licensable imagery. The downloaded files
 * belong to the site's owners: keep them out of the app bundle (reference/ is gitignored).
 */
import { chromium } from 'playwright'
import { createHash } from 'node:crypto'
import { existsSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

// ---------------------------------------------------------------- args
const args = process.argv.slice(2)
const flag = (name, fallback) => {
  const i = args.indexOf(`--${name}`)
  if (i === -1) return fallback
  const next = args[i + 1]
  return next && !next.startsWith('--') ? next : true
}
const START = args.find((a) => /^https?:\/\//.test(a)) ?? 'https://heronaiapp.com/'
const ORIGIN = new URL(START).origin
const HOST = new URL(START).hostname
const MAX_PAGES = Number(flag('pages', 8))
const WANT_VIDEOS = !!flag('videos', false)
const OUT = path.resolve(flag('out', `reference/${HOST}`))
const DELAY_MS = 1200 // pause between pages: be gentle with their server

// ---------------------------------------------------------------- robots.txt
async function loadRobots() {
  try {
    const res = await fetch(`${ORIGIN}/robots.txt`)
    if (!res.ok) return () => true
    const lines = (await res.text()).split('\n').map((l) => l.trim())
    const disallow = []
    let applies = false
    for (const line of lines) {
      const [k, ...rest] = line.split(':')
      const v = rest.join(':').trim()
      if (/^user-agent$/i.test(k)) applies = v === '*'
      else if (applies && /^disallow$/i.test(k) && v) disallow.push(v)
    }
    return (url) => !disallow.some((d) => new URL(url).pathname.startsWith(d))
  } catch {
    return () => true
  }
}

// ---------------------------------------------------------------- page instrumentation
/**
 * Runs in the page before any site script. Intercepts the `gsap` and `Lenis` globals as
 * the CDN bundles assign them, and wraps the tween/timeline/ScrollTrigger APIs so every
 * call is logged to window.__motionLog with its target and options.
 */
const INSTRUMENT = () => {
  const log = (window.__motionLog = [])
  const MAX = 4000
  const describe = (t) => {
    if (t == null) return null
    if (typeof t === 'string') return t
    if (Array.isArray(t) || (typeof NodeList !== 'undefined' && t instanceof NodeList)) {
      const list = Array.from(t)
      return list.length ? `${describe(list[0])}${list.length > 1 ? ` (+${list.length - 1})` : ''}` : '[]'
    }
    if (t instanceof Element) {
      const cls = typeof t.className === 'string' ? t.className.trim().split(/\s+/).slice(0, 3).join('.') : ''
      return `${t.tagName.toLowerCase()}${t.id ? `#${t.id}` : ''}${cls ? `.${cls}` : ''}`
    }
    if (typeof t === 'object') return '{object}'
    return String(t)
  }
  // Plain-data copy of tween options: no functions, elements, GSAP internals or cycles
  const clean = (vars, depth = 0) => {
    if (!vars || typeof vars !== 'object') return vars
    if (depth > 3) return '{…}'
    if (vars instanceof Element) return describe(vars)
    if (Array.isArray(vars)) return vars.slice(0, 12).map((v) => clean(v, depth + 1))
    const proto = Object.getPrototypeOf(vars)
    if (proto !== Object.prototype && proto !== null) return `{${proto?.constructor?.name ?? 'object'}}`
    const out = {}
    for (const [k, v] of Object.entries(vars)) {
      if (k.startsWith('_')) continue
      if (typeof v === 'function') out[k] = 'ƒ'
      else if (k === 'scrollTrigger' && v && typeof v === 'object') out[k] = clean({ ...v, trigger: describe(v.trigger) }, depth + 1)
      else out[k] = clean(v, depth + 1)
    }
    return out
  }
  const push = (entry) => { if (log.length < MAX) log.push({ t: Math.round(performance.now()), page: location.pathname, ...entry }) }

  const wrapTimeline = (tl, id) => {
    for (const m of ['to', 'from', 'fromTo', 'set']) {
      const orig = tl[m]
      if (typeof orig !== 'function') continue
      tl[m] = function (target, ...rest) {
        const vars = m === 'fromTo' ? { from: clean(rest[0]), to: clean(rest[1]), position: rest[2] } : { ...clean(rest[0]), position: rest[1] }
        push({ api: `timeline#${id}.${m}`, target: describe(target), vars })
        return orig.call(this, target, ...rest)
      }
    }
    return tl
  }

  let tlCount = 0
  const wrapGsap = (g) => {
    if (!g || g.__wrapped) return g
    g.__wrapped = true
    for (const m of ['to', 'from', 'fromTo', 'set']) {
      const orig = g[m].bind(g)
      g[m] = (target, ...rest) => {
        const vars = m === 'fromTo' ? { from: clean(rest[0]), to: clean(rest[1]) } : clean(rest[0])
        push({ api: `gsap.${m}`, target: describe(target), vars })
        return orig(target, ...rest)
      }
    }
    const origTl = g.timeline.bind(g)
    g.timeline = (vars) => {
      const id = ++tlCount
      push({ api: 'gsap.timeline', id, vars: clean(vars) })
      return wrapTimeline(origTl(vars), id)
    }
    const origReg = g.registerPlugin.bind(g)
    g.registerPlugin = (...plugins) => {
      for (const p of plugins) {
        const name = p?.name || p?.prototype?.constructor?.name || 'plugin'
        push({ api: 'gsap.registerPlugin', target: name })
        if (p && typeof p.create === 'function' && /ScrollTrigger/.test(name)) {
          const origCreate = p.create.bind(p)
          p.create = (vars) => { push({ api: 'ScrollTrigger.create', target: describe(vars?.trigger), vars: clean(vars) }); return origCreate(vars) }
        }
      }
      return origReg(...plugins)
    }
    return g
  }

  const trap = (name, onSet) => {
    let value
    try {
      Object.defineProperty(window, name, {
        configurable: true,
        get: () => value,
        set: (v) => { value = onSet(v) },
      })
    } catch { /* already defined */ }
  }
  trap('gsap', wrapGsap)
  trap('Lenis', (L) => {
    if (typeof L !== 'function') return L
    return new Proxy(L, {
      construct(target, argsList) {
        push({ api: 'new Lenis', vars: clean(argsList[0] ?? {}) })
        return Reflect.construct(target, argsList)
      },
    })
  })
}

// ---------------------------------------------------------------- helpers
/** JSON.stringify that replaces repeated/circular references instead of throwing. */
const safeJson = (value) => {
  const seen = new WeakSet()
  return JSON.stringify(value, (_k, v) => {
    if (v && typeof v === 'object') {
      if (seen.has(v)) return '[circular]'
      seen.add(v)
    }
    return v
  }, 2)
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const hash = (s) => createHash('sha1').update(s).digest('hex').slice(0, 10)
const extFor = (url, type = '') => {
  const fromUrl = path.extname(new URL(url).pathname).toLowerCase()
  if (fromUrl && fromUrl.length <= 5) return fromUrl
  if (type.includes('svg')) return '.svg'
  if (type.includes('png')) return '.png'
  if (type.includes('webp')) return '.webp'
  if (type.includes('avif')) return '.avif'
  if (type.includes('gif')) return '.gif'
  if (type.includes('mp4')) return '.mp4'
  if (type.includes('webm')) return '.webm'
  return '.jpg'
}
const slug = (url) => {
  const base = path.basename(new URL(url).pathname).replace(/\.[a-z0-9]+$/i, '').replace(/[^a-z0-9_-]+/gi, '-').slice(-48)
  return `${base || 'asset'}-${hash(url)}`
}

/** Scroll the page in steps so lazy images load and scroll-driven animations fire. */
async function autoScroll(page) {
  await page.mouse.move(400, 400)
  let lastY = -1
  for (let i = 0; i < 80; i++) {
    await page.mouse.wheel(0, 600)
    await sleep(350)
    // Sites using Lenis/inner scrollers report scroll differently: stop when nothing moves
    const y = await page.evaluate(() => {
      const el = document.scrollingElement
      const inner = [...document.querySelectorAll('*')].find((e) => e.scrollHeight > e.clientHeight + 50 && /(auto|scroll)/.test(getComputedStyle(e).overflowY))
      return Math.round((el?.scrollTop ?? 0) + (inner?.scrollTop ?? 0))
    })
    if (y === lastY && i > 3) break
    lastY = y
  }
}

// ---------------------------------------------------------------- main
async function main() {
  const allowed = await loadRobots()
  if (!allowed(START)) throw new Error(`robots.txt disallows ${START}`)

  await mkdir(path.join(OUT, 'images'), { recursive: true })
  if (WANT_VIDEOS) await mkdir(path.join(OUT, 'videos'), { recursive: true })

  const executablePath = process.env.CHROME_PATH || (existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : undefined)
  const browser = await chromium.launch({ executablePath })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  await context.addInitScript(INSTRUMENT)

  /** url -> asset record */
  const assets = new Map()
  const cssTexts = new Map()
  const scripts = new Set()

  context.on('response', async (res) => {
    const url = res.url()
    const type = res.headers()['content-type'] ?? ''
    const kind = res.request().resourceType()
    try {
      if (kind === 'stylesheet' || type.includes('text/css')) {
        if (!cssTexts.has(url)) cssTexts.set(url, await res.text())
        return
      }
      if (kind === 'script') { scripts.add(url); return }
      const isImage = kind === 'image' || type.startsWith('image/')
      const isVideo = kind === 'media' || type.startsWith('video/')
      if (!isImage && !(isVideo && WANT_VIDEOS)) {
        if (isVideo && !assets.has(url)) assets.set(url, { url, kind: 'video', type, file: null, pages: new Set() })
        return
      }
      if (assets.has(url) || !res.ok() || url.startsWith('data:')) return
      const body = await res.body()
      const dir = isImage ? 'images' : 'videos'
      const file = `${dir}/${slug(url)}${extFor(url, type)}`
      await writeFile(path.join(OUT, file), body)
      assets.set(url, { url, kind: isImage ? 'image' : 'video', type, bytes: body.length, file, pages: new Set() })
    } catch { /* response body unavailable (redirects, aborted) */ }
  })

  const page = await context.newPage()
  const queue = [START]
  const visited = new Set()
  const domRefs = []
  const motion = []

  while (queue.length && visited.size < MAX_PAGES) {
    const url = queue.shift()
    if (visited.has(url) || !allowed(url)) continue
    visited.add(url)
    console.log(`→ ${url}`)
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 })
    } catch (e) {
      console.warn(`  could not load: ${e.message}`)
      continue
    }
    await sleep(6000) // let any preloader finish
    await page.locator('button:has-text("Accept"), .cookie-banner-accept').first().click({ timeout: 1500 }).catch(() => {})
    await autoScroll(page)
    await sleep(800)

    const info = await page.evaluate(() => {
      const abs = (u) => { try { return new URL(u, location.href).href } catch { return null } }
      const imgs = [...document.querySelectorAll('img')].map((img) => ({
        url: abs(img.currentSrc || img.src), alt: img.alt || '', w: img.naturalWidth, h: img.naturalHeight,
        el: `img.${[...img.classList].slice(0, 2).join('.')}`,
      }))
      const bgs = []
      for (const el of document.querySelectorAll('*')) {
        const bg = getComputedStyle(el).backgroundImage
        for (const m of bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)) bgs.push({ url: abs(m[1]), alt: '', el: `${el.tagName.toLowerCase()}.${[...el.classList].slice(0, 2).join('.')} (background)` })
      }
      const videos = [...document.querySelectorAll('video, video source')].map((v) => ({ url: abs(v.currentSrc || v.src), alt: '', el: 'video' }))
      const svgs = [...document.querySelectorAll('svg')].filter((s) => s.getBoundingClientRect().width > 60).map((s) => s.outerHTML)
      const links = [...document.querySelectorAll('a[href]')].map((a) => abs(a.getAttribute('href'))).filter(Boolean)
      return { imgs, bgs, videos, svgs, links, motion: window.__motionLog ?? [] }
    })

    for (const r of [...info.imgs, ...info.bgs, ...info.videos]) if (r.url) domRefs.push({ ...r, page: url })
    motion.push(...info.motion)
    for (const [i, svg] of info.svgs.entries()) {
      const file = `images/inline-svg-${hash(url)}-${i}.svg`
      await writeFile(path.join(OUT, file), svg.includes('xmlns') ? svg : svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"'))
      assets.set(`${url}#svg${i}`, { url: `${url}#svg${i}`, kind: 'inline-svg', type: 'image/svg+xml', file, pages: new Set([url]) })
    }
    for (const link of info.links) {
      const u = new URL(link)
      u.hash = ''
      if (u.origin === ORIGIN && !visited.has(u.href) && !queue.includes(u.href) && !/\.(pdf|zip|jpg|png)$/i.test(u.pathname)) queue.push(u.href)
    }
    await sleep(DELAY_MS)
  }

  // Merge DOM context (alt text, element, natural size) into downloaded assets
  for (const r of domRefs) {
    const a = assets.get(r.url)
    if (!a) continue
    a.pages.add(r.page)
    a.alt ||= r.alt
    a.el ||= r.el
    if (r.w) { a.width = r.w; a.height = r.h }
  }

  // ---------------------------------------------------------------- CSS motion
  const keyframes = {}
  const motionRules = []
  for (const [url, css] of cssTexts) {
    for (const m of css.matchAll(/@(?:-webkit-)?keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*)\s*\}/g)) {
      keyframes[m[1]] = { source: url, body: m[2].replace(/\s+/g, ' ').trim().slice(0, 600) }
    }
    for (const m of css.matchAll(/([^{}@]+)\{([^{}]*\b(?:animation|transition)[^{}]*)\}/g)) {
      const decls = m[2].split(';').map((d) => d.trim()).filter((d) => /^(animation|transition)/.test(d))
      if (decls.length) motionRules.push({ selector: m[1].trim().slice(0, 160), decls, source: url })
    }
  }

  // ---------------------------------------------------------------- summarise runtime motion
  const byApi = {}
  const eases = {}
  const durations = {}
  for (const e of motion) {
    byApi[e.api.replace(/#\d+/, '')] = (byApi[e.api.replace(/#\d+/, '')] ?? 0) + 1
    const vars = e.vars?.to ?? e.vars ?? {}
    if (vars.ease) eases[vars.ease] = (eases[vars.ease] ?? 0) + 1
    if (typeof vars.duration === 'number') durations[vars.duration] = (durations[vars.duration] ?? 0) + 1
  }

  // ---------------------------------------------------------------- write outputs
  const list = [...assets.values()].map((a) => ({ ...a, pages: [...a.pages] }))
  await writeFile(path.join(OUT, 'manifest.json'), JSON.stringify({ source: START, scraped: new Date().toISOString(), pages: [...visited], assets: list }, null, 2))
  await writeFile(path.join(OUT, 'animations.json'), safeJson({ summary: { byApi, eases, durations }, log: motion }))
  await writeFile(path.join(OUT, 'css-motion.json'), JSON.stringify({ keyframes, rules: motionRules }, null, 2))
  await writeFile(path.join(OUT, 'libraries.json'), JSON.stringify([...scripts].sort(), null, 2))

  const lens = (u) => `https://lens.google.com/uploadbyurl?url=${encodeURIComponent(u)}`
  const tineye = (u) => `https://tineye.com/search?url=${encodeURIComponent(u)}`
  const bing = (u) => `https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:${encodeURIComponent(u)}`
  const cards = list.filter((a) => a.file && a.kind !== 'video').map((a) => `
    <figure>
      <a href="${a.file}" target="_blank"><img src="${a.file}" loading="lazy" alt=""></a>
      <figcaption>
        <b>${a.alt || path.basename(a.file)}</b>
        <small>${a.width ? `${a.width}×${a.height} · ` : ''}${a.bytes ? `${Math.round(a.bytes / 1024)} KB` : a.kind}</small>
        ${a.kind === 'inline-svg' ? '' : `<span><a href="${lens(a.url)}" target="_blank">Lens</a> · <a href="${tineye(a.url)}" target="_blank">TinEye</a> · <a href="${bing(a.url)}" target="_blank">Bing</a> · <a href="${a.url}" target="_blank">source</a></span>`}
      </figcaption>
    </figure>`).join('')
  await writeFile(path.join(OUT, 'index.html'), `<!doctype html><meta charset="utf-8"><title>Reference — ${HOST}</title>
<style>body{font:13px system-ui;margin:24px;background:#f3f2ee;color:#282828}h1{font-size:18px}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
figure{margin:0;background:#fff;border:1px solid #ddd}img{width:100%;height:180px;object-fit:contain;background:repeating-conic-gradient(#eee 0 25%,#fff 0 50%) 0/16px 16px;display:block}
figcaption{padding:8px;display:grid;gap:4px}small{color:#777}a{color:#fa3600}</style>
<h1>${list.length} assets from ${HOST} — reference only</h1><p>Use the Lens / TinEye / Bing links to find similar or licensable images.</p><main>${cards}</main>`)

  const top = (o, n = 8) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `- \`${k}\` × ${v}`).join('\n') || '- (none captured)'
  await writeFile(path.join(OUT, 'REPORT.md'), `# Reference report — ${HOST}

Scraped ${new Date().toISOString()} · ${visited.size} page(s)

## Assets
- Images downloaded: ${list.filter((a) => a.kind === 'image').length}
- Inline SVGs saved: ${list.filter((a) => a.kind === 'inline-svg').length}
- Videos: ${list.filter((a) => a.kind === 'video').length}${WANT_VIDEOS ? '' : ' (URLs only; pass --videos to download)'}

Open \`index.html\` for the gallery with reverse-image-search links.

## Libraries
${[...scripts].map((s) => `- ${s}`).join('\n')}

## Runtime animation (GSAP / ScrollTrigger / Lenis)
Calls captured: ${motion.length}

By API:
${top(byApi, 12)}

Most-used eases:
${top(eases)}

Most-used durations (s):
${top(durations)}

Full call log with targets and options: \`animations.json\`.

## CSS motion
- @keyframes: ${Object.keys(keyframes).length} (${Object.keys(keyframes).slice(0, 12).join(', ')})
- Rules with animation/transition: ${motionRules.length}

Details: \`css-motion.json\`.

---
These files belong to the site's owners. Use them to study the design and find similar or
licensable imagery; don't ship them in your own project without permission.
`)

  await browser.close()
  console.log(`\nDone → ${path.relative(process.cwd(), OUT)}/  (${list.length} assets, ${motion.length} animation calls, ${Object.keys(keyframes).length} keyframes)`)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
