import { Fragment, type ElementType } from 'react'

type Props = { as?: ElementType; text: string; className?: string; id?: string }

/** Splits a heading into masked words. Screen readers get the plain string. */
export function SplitText({ as: Tag = 'h2', text, className = '', id }: Props) {
  return (
    <Tag className={`split ${className}`} aria-label={text} id={id}>
      {text.split(' ').map((word, i) => (
        <Fragment key={i}>
          <span className="split-word" aria-hidden="true"><span>{word}</span></span>{' '}
        </Fragment>
      ))}
    </Tag>
  )
}
