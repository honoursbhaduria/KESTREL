import { chromium } from 'playwright'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  console.log('Navigating to register...')
  await page.goto('http://localhost:3003/register')
  await page.waitForLoadState('networkidle')

  const testEmail = `architect_phase3_${Date.now()}@example.com`
  await page.fill('input[placeholder="Ar. Vikram Sethi"]', 'Ar. Vikram Sethi')
  await page.fill('input[placeholder="Sethi & Associates"]', 'Sethi Design Studio')
  await page.fill('input[type="email"]', testEmail)
  await page.fill('input[type="password"]', 'CorrectHorseBatteryStaple123!')
  
  console.log('Submitting registration...')
  await page.click('button[type="submit"]')

  console.log('Waiting for projects page...')
  await page.waitForURL('**/projects', { timeout: 15000 })
  await page.waitForTimeout(1000)

  console.log('Opening New Project modal...')
  await page.click('button:has-text("New Project")')
  await page.waitForTimeout(600)

  console.log('Filling Project Title...')
  await page.fill('input[placeholder="e.g. Vasant Vihar Villa, Sector 42"]', 'Skyline Modern Residence')
  await page.click('button:has-text("Create Project")')
  await page.waitForTimeout(1500)

  console.log('Opening project details...')
  // Click on the project card with title
  await page.click('text="Skyline Modern Residence"')

  await page.waitForURL('**/projects/**', { timeout: 15000 })
  await page.waitForTimeout(2000)

  const artifactDir = '/home/honours/.gemini/antigravity-cli/brain/74207a42-7f4f-4838-9c61-9d51bad2ce60'

  // 1. Capture primary Plan Workspace view (Clean 2BHK Plan)
  console.log('Capturing primary workspace view...')
  await page.screenshot({ path: `${artifactDir}/screenshot_workspace_plan.png`, fullPage: false })

  // 2. Run Statutory Review on 2BHK
  console.log('Running statutory review on 2BHK...')
  const reviewBtn = await page.$('button:has-text("Run Review")')
  if (reviewBtn) {
    await reviewBtn.click()
    await page.waitForTimeout(2000)
  }

  // 3. Switch to Code Violations Fixture
  console.log('Switching to Code Violations Fixture...')
  const fixtureSelect = await page.$('select[aria-label="Load Prebuilt Architectural Scheme"]')
  if (fixtureSelect) {
    await fixtureSelect.selectOption('violations')
    await page.waitForTimeout(2000)

    // Run review on violations
    const reviewBtn2 = await page.$('button:has-text("Run Review")')
    if (reviewBtn2) {
      await reviewBtn2.click()
      await page.waitForTimeout(2000)
    }

    // Click on a fail issue to highlight
    const failCard = await page.$('div:has-text("Fail"):has-text("is below required minimum")')
    if (failCard) {
      await failCard.click()
      await page.waitForTimeout(1000)
    }

    console.log('Capturing review highlight screenshot...')
    await page.screenshot({ path: `${artifactDir}/screenshot_review_highlight.png`, fullPage: false })
  }

  // 4. Open Version History drawer
  console.log('Opening Version History drawer...')
  const historyBtn = await page.$('button:has-text("Versions")')
  if (historyBtn) {
    await historyBtn.click()
    await page.waitForTimeout(1000)
    console.log('Capturing version history screenshot...')
    await page.screenshot({ path: `${artifactDir}/screenshot_version_history.png`, fullPage: false })
  }

  console.log('All Phase 3 screenshots captured successfully!')
  await browser.close()
}

run().catch((err) => {
  console.error('Error during capture:', err)
  process.exit(1)
})
