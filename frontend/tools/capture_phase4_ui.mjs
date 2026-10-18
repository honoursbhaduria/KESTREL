import { chromium } from 'playwright'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  console.log('Navigating to register...')
  await page.goto('http://localhost:3003/register')
  await page.waitForLoadState('networkidle')

  const testEmail = `architect_phase4_${Date.now()}@example.com`
  await page.fill('input[placeholder="Ar. Vikram Sethi"]', 'Ar. Vikram Sethi')
  await page.fill('input[placeholder="Sethi & Associates"]', 'Sethi Design Studio')
  await page.fill('input[type="email"]', testEmail)
  await page.fill('input[type="password"]', 'CorrectHorseBatteryStaple123!')

  console.log('Submitting registration...')
  await page.click('button[type="submit"]')

  console.log('Waiting for projects page...')
  await page.waitForURL('**/projects', { timeout: 15000 })
  await page.waitForTimeout(1000)

  console.log('Creating New Project...')
  await page.click('button:has-text("New Project")')
  await page.waitForTimeout(600)

  await page.fill('input[placeholder="e.g. Vasant Vihar Villa, Sector 42"]', 'Vasant Kunj Generative Villa')
  await page.click('button:has-text("Create Project")')
  await page.waitForTimeout(1500)

  console.log('Opening project...')
  await page.click('text="Vasant Kunj Generative Villa"')
  await page.waitForURL('**/projects/**', { timeout: 15000 })
  await page.waitForTimeout(1500)

  const artifactDir = '/home/honours/.gemini/antigravity-cli/brain/74207a42-7f4f-4838-9c61-9d51bad2ce60'

  // 1. First ensure plot & envelope are configured
  console.log('Configuring site plot for envelope...')
  await page.click('button:has-text("[02] Site Plot & Buildable Envelope")')
  await page.waitForTimeout(1000)
  await page.click('button:has-text("Recalculate Envelope")')
  await page.waitForTimeout(2000)

  // 2. Switch to [00] AI Brief & Generator
  console.log('Switching to AI Brief & Generator tab...')
  await page.click('button:has-text("[00] AI Brief & Generator")')
  await page.waitForTimeout(1000)

  // 3. Structure Brief
  console.log('Structuring brief...')
  await page.click('button:has-text("Structure Brief → Program")')
  await page.waitForTimeout(3000)

  console.log('Capturing structured program & statutory feasibility...')
  await page.screenshot({ path: `${artifactDir}/screenshot_phase4_brief_program.png`, fullPage: false })

  // 4. Start Layout Generation
  console.log('Triggering generative layout solver...')
  const genBtn = await page.$('button:has-text("Generate 3 Code-Checked Schemes")')
  if (genBtn) {
    await genBtn.click()
    // Wait for generation to complete
    await page.waitForTimeout(6000)
  }

  console.log('Capturing generated schemes gallery...')
  await page.screenshot({ path: `${artifactDir}/screenshot_phase4_generated_options.png`, fullPage: false })

  // 5. Compare Schemes
  console.log('Opening scheme comparison modal...')
  const compareBtn = await page.$('button:has-text("Compare Schemes A & B Side-by-Side")')
  if (compareBtn) {
    await compareBtn.click()
    await page.waitForTimeout(1500)
    await page.screenshot({ path: `${artifactDir}/screenshot_phase4_compare_modal.png`, fullPage: false })

    // Click select this scheme
    const selectBtns = await page.$$('button:has-text("Select this Scheme")')
    if (selectBtns.length > 0) {
      await selectBtns[0].click()
      await page.waitForTimeout(2500)
    }
  } else {
    // Open in workspace directly
    const openBtn = await page.$('button:has-text("Open in 2D Workspace")')
    if (openBtn) {
      await openBtn.click()
      await page.waitForTimeout(2500)
    }
  }

  // 6. Trigger review and capture loaded scheme in 2D workspace
  console.log('Triggering statutory review on loaded scheme in workspace...')
  const runReviewBtn = await page.$('button:has-text("Run Statutory Review")')
  if (runReviewBtn) {
    await runReviewBtn.click()
    await page.waitForTimeout(2000)
  }

  console.log('Capturing synthesized scheme loaded in 2D Workspace...')
  await page.screenshot({ path: `${artifactDir}/screenshot_phase4_workspace_scheme.png`, fullPage: false })

  await browser.close()
  console.log('All screenshots captured successfully!')
}

run().catch((err) => {
  console.error('Playwright capture error:', err)
  process.exit(1)
})
