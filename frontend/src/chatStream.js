export function safeSourceUrl(value) {
  if (typeof value !== 'string' || /\s/.test(value)) return false
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password &&
      ['darglobal.co.uk', 'wasalt.sa'].some((domain) => url.hostname === domain || url.hostname.endsWith(`.${domain}`))
  } catch {
    return false
  }
}

export function createEventParser(onEvent) {
  let buffer = ''
  function parseBlock(block) {
    let name = 'message'
    const data = []
    for (const line of block.split(/\r\n|\r|\n/)) {
      if (line.startsWith(':')) continue
      const separator = line.indexOf(':')
      const field = separator < 0 ? line : line.slice(0, separator)
      let value = separator < 0 ? '' : line.slice(separator + 1)
      if (value.startsWith(' ')) value = value.slice(1)
      if (field === 'event') name = value
      if (field === 'data') data.push(value)
    }
    if (data.length) {
      let payload
      try {
        payload = JSON.parse(data.join('\n'))
      } catch {
        throw new Error('The assistant returned an invalid response.')
      }
      onEvent(name, payload)
    }
  }
  return {
    push(text) {
      buffer += text
      let match
      while ((match = /\r\n\r\n|\n\n|\r\r/.exec(buffer))) {
        parseBlock(buffer.slice(0, match.index))
        buffer = buffer.slice(match.index + match[0].length)
      }
    },
    finish() {
      if (buffer.trim()) throw new Error('The response was interrupted. Please try again.')
    },
  }
}

export async function readChatStream(response, onEvent) {
  if (!response.body || !response.headers.get('content-type')?.toLowerCase().startsWith('text/event-stream')) {
    throw new Error('The assistant returned an unexpected response.')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let complete = false
  let receivedText = false
  const parser = createEventParser((name, data) => {
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('The assistant returned an invalid response.')
    if (name === 'error') throw new Error(typeof data.message === 'string' ? data.message : 'The assistant is unavailable. Please try again.')
    if (name === 'sources' && (!Array.isArray(data.sources) || data.sources.some((source) => !source || typeof source !== 'object'))) {
      throw new Error('The assistant returned invalid sources.')
    }
    if (name === 'delta') {
      if (typeof data.text !== 'string') throw new Error('The assistant returned invalid text.')
      if (data.text) receivedText = true
    }
    if (name === 'done') {
      if (data.status !== 'complete') throw new Error('The response was interrupted. Please try again.')
      complete = true
    }
    onEvent(name, data)
  })
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      parser.push(decoder.decode(value, { stream: true }))
    }
    parser.push(decoder.decode())
    parser.finish()
    if (!complete || !receivedText) throw new Error('The response was interrupted. Please try again.')
  } finally {
    reader.releaseLock()
  }
}
