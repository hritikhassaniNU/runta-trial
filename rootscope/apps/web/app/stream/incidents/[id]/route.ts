export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: { id: string } }
) {
  const upstream = process.env.API_UPSTREAM || "http://127.0.0.1:8000";
  const response = await fetch(
    `${upstream}/api/incidents/${params.id}/events`,
    {
      cache: "no-store",
      headers: { Accept: "text/event-stream" },
    }
  );
  if (!response.ok || !response.body) {
    return new Response("stream unavailable", { status: 502 });
  }
  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
