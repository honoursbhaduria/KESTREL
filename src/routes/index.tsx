import { createFileRoute } from '@tanstack/react-router'
import { Hero } from '~/components/sections/Hero'
import { Intro } from '~/components/sections/Intro'
import { Problem } from '~/components/sections/Problem'
import { Statement } from '~/components/sections/Statement'
import { Review } from '~/components/sections/Review'
import { Platform } from '~/components/sections/Platform'
import { Assemble } from '~/components/sections/Assemble'
import { Why } from '~/components/sections/Why'
import { UseCases } from '~/components/sections/UseCases'
import { Cta } from '~/components/sections/Cta'

export const Route = createFileRoute('/')({
  component: Home,
})

function Home() {
  return (
    <>
      <Hero />
      <Intro />
      <Problem />
      <Statement />
      <Review />
      <Platform />
      <Assemble />
      <Why />
      <UseCases />
      <Cta />
    </>
  )
}
