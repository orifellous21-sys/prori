const TIME_ZONE = "Asia/Jerusalem";
const DEFAULT_TO_EMAIL = "ori.fellous21@gmail.com";
const DEFAULT_CHANNEL_HANDLE = "@Micha.Stocks";
const FALLBACK_CHANNEL_ID = "UCQpDtNipLcAr13nU9MtXAIg";

const config = {
  resendApiKey: process.env.RESEND_API_KEY,
  fromEmail: process.env.RESEND_FROM_EMAIL || "Micha Stocks Digest <onboarding@resend.dev>",
  toEmail: process.env.DIGEST_TO_EMAIL || DEFAULT_TO_EMAIL,
  channelHandle: process.env.YOUTUBE_CHANNEL_HANDLE || DEFAULT_CHANNEL_HANDLE,
  channelId: process.env.YOUTUBE_CHANNEL_ID || "",
  forceSendOutsideNine: process.env.FORCE_SEND === "1",
};

main().catch(async (error) => {
  console.error(error);
  if (config.resendApiKey) {
    await sendEmail({
      subject: "Micha Stocks daily summary - failed",
      text: `The Micha Stocks digest failed.\n\n${error.stack || error.message}`,
      html: `<p>The Micha Stocks digest failed.</p><pre>${escapeHtml(error.stack || error.message)}</pre>`,
    });
  }
  process.exit(1);
});

async function main() {
  if (!config.resendApiKey) {
    throw new Error("Missing RESEND_API_KEY. Add it as a GitHub Actions secret.");
  }

  const now = new Date();
  const localParts = getLocalParts(now);
  if (!config.forceSendOutsideNine && localParts.hour !== 9) {
    console.log(`Skipping: local hour is ${localParts.hour}, not 9 in ${TIME_ZONE}.`);
    return;
  }

  const channelId = config.channelId || await resolveChannelId(config.channelHandle) || FALLBACK_CHANNEL_ID;
  const feed = await fetchText(`https://www.youtube.com/feeds/videos.xml?channel_id=${channelId}`);
  const videos = parseFeed(feed)
    .filter((video) => isSameLocalDate(video.publishedAt, now))
    .filter((video) => video.publishedAt <= now)
    .sort((a, b) => b.publishedAt - a.publishedAt);

  if (videos.length === 0) {
    await sendEmail({
      subject: "Micha Stocks daily summary - no same-day video found",
      text: `No same-day Micha Stocks video was found before 9:00 AM ${TIME_ZONE}.\n\nChecked channel: ${channelId}\nDate: ${formatLocalDate(now)}`,
      html: `<p>No same-day Micha Stocks video was found before 9:00 AM ${TIME_ZONE}.</p><p>Checked channel: ${channelId}<br>Date: ${formatLocalDate(now)}</p>`,
    });
    return;
  }

  const video = videos[0];
  const videoPage = await fetchText(video.url);
  const pageDescription = extractMetaDescription(videoPage) || video.description;
  const transcript = await getTranscript(videoPage).catch((error) => {
    console.warn(`Transcript unavailable: ${error.message}`);
    return "";
  });

  const sourceText = [video.title, pageDescription, transcript].filter(Boolean).join("\n\n");
  const digest = buildDigest(video, sourceText);
  await sendEmail({
    subject: `Micha Stocks daily summary - ${video.title}`.slice(0, 180),
    text: digest.text,
    html: digest.html,
  });
}

async function resolveChannelId(handle) {
  const cleanHandle = handle.startsWith("@") ? handle : `@${handle}`;
  const html = await fetchText(`https://www.youtube.com/${encodeURIComponent(cleanHandle)}/videos`);
  const match = html.match(/"channelId":"(UC[0-9A-Za-z_-]{22})"/) ||
    html.match(/youtube\.com\/channel\/(UC[0-9A-Za-z_-]{22})/);
  return match?.[1] || "";
}

function parseFeed(xml) {
  const entries = [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(([, entry]) => {
    const videoId = textBetween(entry, "<yt:videoId>", "</yt:videoId>");
    return {
      videoId,
      title: decodeXml(textBetween(entry, "<title>", "</title>")),
      url: `https://www.youtube.com/watch?v=${videoId}`,
      publishedAt: new Date(textBetween(entry, "<published>", "</published>")),
      updatedAt: new Date(textBetween(entry, "<updated>", "</updated>")),
      description: decodeXml(textBetween(entry, "<media:description>", "</media:description>")),
    };
  });
  return entries.filter((entry) => entry.videoId && !Number.isNaN(entry.publishedAt.getTime()));
}

async function getTranscript(videoPageHtml) {
  const tracksJson = extractJsonArrayAfter(videoPageHtml, '"captionTracks":');
  if (!tracksJson) return "";

  const tracks = JSON.parse(tracksJson);
  const track = tracks.find((item) => /^(he|iw)/i.test(item.languageCode || "")) ||
    tracks.find((item) => /^en/i.test(item.languageCode || "")) ||
    tracks[0];
  if (!track?.baseUrl) return "";

  const transcriptXml = await fetchText(track.baseUrl);
  return [...transcriptXml.matchAll(/<text[^>]*>([\s\S]*?)<\/text>/g)]
    .map(([, text]) => decodeXml(text.replace(/\n/g, " ")).trim())
    .filter(Boolean)
    .join(" ");
}

function extractJsonArrayAfter(text, marker) {
  const markerIndex = text.indexOf(marker);
  if (markerIndex === -1) return "";
  const start = text.indexOf("[", markerIndex);
  if (start === -1) return "";

  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let index = start; index < text.length; index += 1) {
    const char = text[index];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (char === "\\") {
      escaped = true;
      continue;
    }
    if (char === '"') inString = !inString;
    if (inString) continue;
    if (char === "[") depth += 1;
    if (char === "]") depth -= 1;
    if (depth === 0) return text.slice(start, index + 1);
  }
  return "";
}

function buildDigest(video, sourceText) {
  const normalized = sourceText.replace(/\s+/g, " ").trim();
  const summary = summarize(normalized);
  const stocks = extractStockMentions(normalized);

  const stockText = stocks.length
    ? stocks.map((stock) => `- ${stock.symbol}: ${stock.note}`).join("\n")
    : "- No clear stock tickers were detected in the available title, description, or transcript.";

  const text = [
    `Video: ${video.title}`,
    `URL: ${video.url}`,
    `Published: ${formatLocalDateTime(video.publishedAt)}`,
    "",
    "Main subject:",
    summary,
    "",
    "Stocks discussed:",
    stockText,
    "",
    "Note: This is a summary of the video content, not financial advice.",
  ].join("\n");

  const html = `
    <h2>${escapeHtml(video.title)}</h2>
    <p><a href="${escapeHtml(video.url)}">Watch video</a><br>
    Published: ${escapeHtml(formatLocalDateTime(video.publishedAt))}</p>
    <h3>Main subject</h3>
    <p>${escapeHtml(summary)}</p>
    <h3>Stocks discussed</h3>
    ${stocks.length ? `<ul>${stocks.map((stock) => `<li><strong>${escapeHtml(stock.symbol)}</strong>: ${escapeHtml(stock.note)}</li>`).join("")}</ul>` : "<p>No clear stock tickers were detected in the available title, description, or transcript.</p>"}
    <p><em>This is a summary of the video content, not financial advice.</em></p>
  `;

  return { text, html };
}

function summarize(text) {
  const sentences = text
    .split(/(?<=[.!?])\s+|(?<=׃)\s+/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length > 40 && sentence.length < 350);

  const titleLike = sentences[0] || text.slice(0, 280);
  const followUps = sentences.slice(1, 4).join(" ");
  return [titleLike, followUps].filter(Boolean).join(" ").slice(0, 1200);
}

function extractStockMentions(text) {
  const stopWords = new Set([
    "AM", "PM", "CEO", "CFO", "ETF", "IPO", "EPS", "GDP", "USA", "USD", "SEC", "ATH",
    "AI", "API", "URL", "RSS", "TV", "CNBC", "NYSE", "NASDAQ",
  ]);
  const matches = [...text.matchAll(/(?:\$|NASDAQ:|NYSE:)?\b([A-Z]{2,5})\b/g)]
    .map((match) => match[1])
    .filter((symbol) => !stopWords.has(symbol));

  const unique = [...new Set(matches)].slice(0, 25);
  return unique.map((symbol) => ({
    symbol,
    note: describeMention(text, symbol),
  }));
}

function describeMention(text, symbol) {
  const index = text.indexOf(symbol);
  const context = text.slice(Math.max(0, index - 180), Math.min(text.length, index + 260)).trim();
  const lower = context.toLowerCase();
  let tone = "neutral/unclear";
  if (/(breakout|strong|uptrend|beat|growth|bull|positive|buy|support|פריצה|חזקה|עלייה|חיובי)/i.test(lower)) {
    tone = "positive/watchlist";
  } else if (/(risk|down|drop|weak|bear|sell|below|warning|miss|סיכון|ירידה|חלשה|אזהרה|שבירה)/i.test(lower)) {
    tone = "cautious/negative";
  }
  return `${tone}. Context: ${context || "mentioned, but not enough context was available."}`;
}

async function sendEmail({ subject, text, html }) {
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.resendApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: config.fromEmail,
      to: [config.toEmail],
      subject,
      text,
      html,
    }),
  });

  const body = await response.text();
  if (!response.ok) {
    throw new Error(`Resend failed with ${response.status}: ${body}`);
  }
  console.log(`Sent email: ${body}`);
}

async function fetchText(url) {
  const response = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 MichaStocksDigest/1.0",
      "Accept-Language": "he,en;q=0.8",
    },
  });
  if (!response.ok) throw new Error(`Fetch failed ${response.status} for ${url}`);
  return response.text();
}

function getLocalParts(date) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);
  return Object.fromEntries(parts.map((part) => [part.type, Number(part.value) || part.value]));
}

function isSameLocalDate(a, b) {
  return formatLocalDate(a) === formatLocalDate(b);
}

function formatLocalDate(date) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function formatLocalDateTime(date) {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function textBetween(text, start, end) {
  const startIndex = text.indexOf(start);
  if (startIndex === -1) return "";
  const contentStart = startIndex + start.length;
  const endIndex = text.indexOf(end, contentStart);
  if (endIndex === -1) return "";
  return text.slice(contentStart, endIndex);
}

function extractMetaDescription(html) {
  const match = html.match(/<meta\s+name="description"\s+content="([^"]*)"/i) ||
    html.match(/<meta\s+property="og:description"\s+content="([^"]*)"/i);
  return match ? decodeXml(match[1]) : "";
}

function decodeXml(value) {
  return value
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, number) => String.fromCodePoint(Number.parseInt(number, 10)));
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
