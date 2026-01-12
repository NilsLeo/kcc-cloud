export const runtime = "nodejs"

export async function POST(req: Request) {
  try {
    const body = req.body
    if (!body) {
      return new Response(JSON.stringify({ received: 0 }), { status: 200 })
    }

    const reader = body.getReader()
    let received = 0
    // Drain the stream to let the client push data as fast as possible
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      if (value) received += value.byteLength
    }

    return new Response(JSON.stringify({ received }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })
  } catch (e) {
    return new Response(JSON.stringify({ received: 0 }), { status: 200 })
  }
}

