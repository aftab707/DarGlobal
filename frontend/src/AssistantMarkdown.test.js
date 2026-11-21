import test from 'node:test'
import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import AssistantMarkdown from './AssistantMarkdown.js'

function render(text) {
  return renderToStaticMarkup(createElement(AssistantMarkdown, { text }))
}

test('formats headings, bold, lists and tables in assistant responses', () => {
  const html = render('## Property\n\n- **Size**: 450 m²\n- **Location**: Riyadh\n\n| Type | City |\n| --- | --- |\n| Villa | Riyadh |')
  assert.match(html, /<h2>Property<\/h2>/)
  assert.match(html, /<ul>[\s\S]*<strong>Size<\/strong>: 450 m²/)
  assert.match(html, /<table>[\s\S]*<td>Villa<\/td>/)
})

test('renders only trusted links and does not render active HTML or remote images', () => {
  const html = render('[Source](https://wasalt.sa/property/1) [Unsafe](https://evil.example) [Bad](javascript:alert(1)) ![photo](https://evil.example/tracker.png) <script>alert(1)</script>')
  assert.match(html, /href="https:\/\/wasalt\.sa\/property\/1"/)
  assert.match(html, /rel="noopener noreferrer"/)
  assert.doesNotMatch(html, /href="https:\/\/evil\.example/)
  assert.doesNotMatch(html, /<img|<script/)
})
