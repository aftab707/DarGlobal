import { createElement } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { safeSourceUrl } from './chatStream.js'

const components = {
  a({ href, children }) {
    return safeSourceUrl(href)
      ? createElement('a', { href, target: '_blank', rel: 'noopener noreferrer' }, children)
      : createElement('span', null, children)
  },
  img({ alt }) {
    return alt || ''
  },
}

export default function AssistantMarkdown({ text }) {
  return createElement(Markdown, { remarkPlugins: [remarkGfm], components }, text)
}
