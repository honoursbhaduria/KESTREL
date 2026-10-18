export type LegalSection = { id: string; title: string; body: string[] }

/** Sticky contents list beside numbered legal sections. */
export function Legal({ sections }: { sections: LegalSection[] }) {
  return (
    <div className="legal">
      <nav className="legal__toc" aria-label="On this page">
        <p className="mono">Contents</p>
        {sections.map((s, i) => <a href={`#${s.id}`} key={s.id}><span className="mono">0{i + 1}</span>{s.title}</a>)}
      </nav>
      <div className="legal__body">
        {sections.map((s, i) => (
          <section id={s.id} key={s.id} className="legal__sec">
            <h2 className="h5"><span className="mono accent">0{i + 1}</span>{s.title}</h2>
            {s.body.map((p) => <p className="body" key={p}>{p}</p>)}
          </section>
        ))}
      </div>
    </div>
  )
}
