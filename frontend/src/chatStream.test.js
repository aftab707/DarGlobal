import test from 'node:test'
import assert from 'node:assert/strict'
import { createEventParser, readChatStream, safeSourceUrl } from './chatStream.js'

function responseWithChunks(chunks) {
  const encoder = new TextEncoder()
  return new Response(new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(typeof chunk === 'string' ? encoder.encode(chunk) : chunk)
      controller.close()
    },
  }), { headers: { 'Content-Type': 'text/event-stream; charset=utf-8' } })
}

test('parses split boundaries, CRLF and multiple data lines', () => {
  const events = []
  const parser = createEventParser((name, data) => events.push([name, data]))
  parser.push('event: delta\r\ndata: {"text":\r')
  parser.push('\ndata: "hello"}\r\n\r')
  parser.push('\nevent: done\ndata: {"status":"complete"}\n\n')
  parser.finish()
  assert.deepEqual(events, [['delta', { text: 'hello' }], ['done', { status: 'complete' }]])
})

test('streams Arabic across byte boundaries and handles multiple events', async () => {
  const bytes = new TextEncoder().encode('event: sources\ndata: {"sources":[]}\n\nevent: delta\ndata: {"text":"مرحبا"}\n\nevent: done\ndata: {"status":"complete"}\n\n')
  const events = []
  await readChatStream(responseWithChunks([...bytes].map((byte) => new Uint8Array([byte]))), (name, data) => events.push([name, data]))
  assert.equal(events[1][1].text, 'مرحبا')
  assert.deepEqual(events.map(([name]) => name), ['sources', 'delta', 'done'])
})

test('reports provider errors and interrupted streams', async () => {
  await assert.rejects(readChatStream(responseWithChunks(['event: error\ndata: {"message":"Try again"}\n\n']), () => {}), /Try again/)
  await assert.rejects(readChatStream(responseWithChunks(['event: delta\ndata: {"text":"partial"}\n\n']), () => {}), /interrupted/)
  await assert.rejects(readChatStream(responseWithChunks(['event: done\ndata: {"status":"complete"}\n\n']), () => {}), /interrupted/)
  await assert.rejects(readChatStream(responseWithChunks(['event: delta\ndata: nope\n\n']), () => {}), /invalid response/)
})

test('allows only safe source domains and protocols', () => {
  assert.equal(safeSourceUrl('https://wasalt.sa/property/1'), true)
  assert.equal(safeSourceUrl('https://darglobal.co.uk/aida-360'), true)
  assert.equal(safeSourceUrl('https://wasalt.sa.evil.example/'), false)
  assert.equal(safeSourceUrl('javascript:alert(1)'), false)
  assert.equal(safeSourceUrl('https://user@wasalt.sa/'), false)
})
