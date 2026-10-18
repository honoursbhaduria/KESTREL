import { chromium } from 'playwright'
import { spawn } from 'child_process'

async function waitForServer(url, timeoutMs = 15000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url)
      if (res.ok || res.status < 500) return true
    } catch {
      // wait and retry
    }
    await new Promise((r) => setTimeout(r, 200))
  }
  throw new Error(`Server at ${url} did not become ready within ${timeoutMs}ms`)
}

async function run() {
  console.log('Starting preview server on port 3002...')
  const previewProcess = spawn('npx', ['vite', 'preview', '--port', '3002', '--host', '0.0.0.0'], {
    cwd: '/home/honours/haron/frontend',
    stdio: 'ignore',
  })

  try {
    await waitForServer('http://localhost:3002')
    console.log('Preview server is ready!')

    const browser = await chromium.launch({ headless: true })
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 2,
    })
    const page = await context.newPage()

    console.log('Navigating to /login...')
    await page.goto('http://localhost:3002/login', { waitUntil: 'networkidle' })
    await page.screenshot({ path: '/home/honours/haron/screenshot_login.png' })
    console.log('Saved screenshot_login.png')

  console.log('Navigating to /register...')
  await page.goto('http://localhost:3002/register', { waitUntil: 'networkidle' })
  await page.screenshot({ path: '/home/honours/haron/screenshot_register.png' })
  console.log('Saved screenshot_register.png')

  // Create real user & live project with plot + envelope in backend
  const email = `ananya.${Date.now()}@kestrel-studio.com`
  console.log(`Registering live architect user: ${email}...`)
  const regRes = await fetch('http://localhost:8001/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password: 'ArchitecturalDesign2026!',
      full_name: 'Ar. Ananya Sharma',
      org_name: 'Studio Kestrel Architects',
    }),
  })

  if (!regRes.ok) {
    throw new Error(`Failed to register: ${await regRes.text()}`)
  }

  const authData = await regRes.json()
  const token = authData.access_token
  const authHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  // Create 3 realistic projects for the studio list
  console.log('Creating live studio projects in backend...')
  const p1Res = await fetch('http://localhost:8001/api/v1/projects', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify({
      name: 'Courtyard Villa · Sector 42',
      description: '3-storey sustainable residence with central lightwell and passive solar ventilation.',
    }),
  })
  const project1 = await p1Res.json()

  await fetch('http://localhost:8001/api/v1/projects', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify({
      name: 'Dehradun Hillside Residence',
      description: 'Step-terrace villa adhering to Uttarakhand hill bylaws and setbacks.',
    }),
  })

  await fetch('http://localhost:8001/api/v1/projects', {
    method: 'POST',
    headers: authHeaders,
    body: JSON.stringify({
      name: 'Noida Urban Duplex',
      description: 'G+2 high-density family home with ground floor stilt parking and terrace garden.',
    }),
  })

  // Define Plot & Ruleset for project 1
  console.log('Setting plot geometry and ruleset for Project 1...')
  await fetch(`http://localhost:8001/api/v1/projects/${project1.id}/plot`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify({
      width_mm: 15000,
      depth_mm: 20000,
      road_sides: [{ edge_index: 0, road_width_mm: 12000 }],
      north_angle_deg: 0,
    }),
  })

  await fetch(`http://localhost:8001/api/v1/projects/${project1.id}/ruleset`, {
    method: 'PUT',
    headers: authHeaders,
    body: JSON.stringify({
      ruleset_id: 'up-bylaws',
    }),
  })

  // Inject authentication into browser localStorage
  await page.evaluate((auth) => {
    localStorage.setItem('haron_access_token', auth.access_token)
    localStorage.setItem('haron_refresh_token', auth.refresh_token)
    localStorage.setItem('haron_user', JSON.stringify(auth.user))
    localStorage.setItem('haron_org', JSON.stringify(auth.org))
  }, authData)

  console.log('Navigating to /projects with real live backend data...')
  await page.goto('http://localhost:3002/projects', { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: '/home/honours/haron/screenshot_projects.png' })
  console.log('Saved screenshot_projects.png')

  console.log(`Navigating to /projects/${project1.id} with real computed envelope...`)
  await page.goto(`http://localhost:3002/projects/${project1.id}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1000)
  await page.screenshot({ path: '/home/honours/haron/screenshot_plot_envelope.png' })
  console.log('Saved screenshot_plot_envelope.png')

  console.log('Switching to Applied Rule Constraints tab...')
  await page.click('button:has-text("Applied Rule Constraints")')
  await page.waitForTimeout(500)
  await page.screenshot({ path: '/home/honours/haron/screenshot_applied_rules.png' })
  console.log('Saved screenshot_applied_rules.png')

  await browser.close()
  console.log('All screenshots captured successfully!')
  } finally {
    previewProcess.kill()
  }
}

run().catch((err) => {
  console.error(err)
  process.exit(1)
})
