const TIME_ZONE = "Asia/Jerusalem";
const DEFAULT_TO_EMAIL = "ori.fellous21@gmail.com";
const DEFAULT_CHANNEL_HANDLE = "@Micha.Stocks";
const FALLBACK_CHANNEL_ID = "UCQpDtNipLcAr13nU9MtXAIg";
const LIVE_MODES = {
  opening: {
    label: "opening live",
    subjectPrefix: "Micha Stocks opening live",
    targetHour: 17,
    targetMinute: 30,
    beforeMinutes: 90,
    afterMinutes: 240,
    keywords: ["opening", "market open", "open live", "\u05e4\u05ea\u05d9\u05d7\u05d4", "\u05e4\u05ea\u05d9\u05d7\u05ea"],
  },
  closing: {
    label: "closing live",
    subjectPrefix: "Micha Stocks closing live",
    targetHour: 0,
    targetMinute: 0,
    beforeMinutes: 75,
    afterMinutes: 240,
    keywords: ["closing", "market close", "close live", "\u05e1\u05d2\u05d9\u05e8\u05d4", "\u05e1\u05d2\u05d9\u05e8\u05ea"],
  },
};
const STOCK_ALIASES = [
  { symbol: "NVDA", name: "Nvidia", aliases: ["nvidia", "n vidia", "\u05d0\u05e0\u05d1\u05d9\u05d3\u05d9\u05d4", "\u05e0\u05d1\u05d9\u05d3\u05d9\u05d4"] },
  { symbol: "TSLA", name: "Tesla", aliases: ["tesla", "\u05d8\u05e1\u05dc\u05d4"] },
  { symbol: "AAPL", name: "Apple", aliases: ["apple", "\u05d0\u05e4\u05dc"] },
  { symbol: "MSFT", name: "Microsoft", aliases: ["microsoft", "\u05de\u05d9\u05e7\u05e8\u05d5\u05e1\u05d5\u05e4\u05d8"] },
  { symbol: "AMZN", name: "Amazon", aliases: ["amazon", "aws", "\u05d0\u05de\u05d6\u05d5\u05df"] },
  { symbol: "GOOGL", name: "Alphabet/Google", aliases: ["google", "alphabet", "\u05d2\u05d5\u05d2\u05dc", "\u05d0\u05dc\u05e4\u05d1\u05d9\u05ea"] },
  { symbol: "META", name: "Meta", aliases: ["meta", "facebook", "\u05de\u05d8\u05d0", "\u05de\u05d8\u05d4", "\u05e4\u05d9\u05d9\u05e1\u05d1\u05d5\u05e7"] },
  { symbol: "PLTR", name: "Palantir", aliases: ["palantir", "\u05e4\u05dc\u05e0\u05d8\u05d9\u05e8"] },
  { symbol: "AMD", name: "Advanced Micro Devices", aliases: ["advanced micro devices", "\u05d0\u05d9\u05d9 \u05d0\u05dd \u05d3\u05d9"] },
  { symbol: "AVGO", name: "Broadcom", aliases: ["broadcom", "\u05d1\u05e8\u05d5\u05d3\u05e7\u05d5\u05dd"] },
  { symbol: "SMCI", name: "Super Micro", aliases: ["super micro", "supermicro", "\u05e1\u05d5\u05e4\u05e8 \u05de\u05d9\u05e7\u05e8\u05d5"] },
  { symbol: "MSTR", name: "MicroStrategy/Strategy", aliases: ["microstrategy", "micro strategy", "strategy stock", "\u05de\u05d9\u05d9\u05e7\u05e8\u05d5\u05e1\u05d8\u05e8\u05d8\u05d2\u05d9"] },
  { symbol: "COIN", name: "Coinbase", aliases: ["coinbase", "\u05e7\u05d5\u05d9\u05e0\u05d1\u05d9\u05d9\u05e1"] },
  { symbol: "HOOD", name: "Robinhood", aliases: ["robinhood", "robin hood", "\u05e8\u05d5\u05d1\u05d9\u05df \u05d4\u05d5\u05d3"] },
  { symbol: "NFLX", name: "Netflix", aliases: ["netflix", "\u05e0\u05d8\u05e4\u05dc\u05d9\u05e7\u05e1"] },
  { symbol: "CRM", name: "Salesforce", aliases: ["salesforce", "sales force"] },
  { symbol: "ORCL", name: "Oracle", aliases: ["oracle", "\u05d0\u05d5\u05e8\u05e7\u05dc"] },
  { symbol: "INTC", name: "Intel", aliases: ["intel", "\u05d0\u05d9\u05e0\u05d8\u05dc"] },
  { symbol: "TSM", name: "Taiwan Semiconductor", aliases: ["taiwan semiconductor", "tsmc"] },
  { symbol: "MU", name: "Micron", aliases: ["micron", "\u05de\u05d9\u05d9\u05e7\u05e8\u05d5\u05df"] },
  { symbol: "NBIS", name: "Nebius", aliases: ["nebius", "\u05e0\u05d1\u05d9\u05d5\u05e1"] },
  { symbol: "QCOM", name: "Qualcomm", aliases: ["qualcomm", "\u05e7\u05d5\u05d5\u05d0\u05dc\u05e7\u05d5\u05dd"] },
  { symbol: "ARM", name: "Arm", aliases: ["arm holdings", "arm stock"] },
  { symbol: "SHOP", name: "Shopify", aliases: ["shopify"] },
  { symbol: "UBER", name: "Uber", aliases: ["uber"] },
  { symbol: "ABNB", name: "Airbnb", aliases: ["airbnb", "air bnb"] },
  { symbol: "RDDT", name: "Reddit", aliases: ["reddit"] },
  { symbol: "RBLX", name: "Roblox", aliases: ["roblox"] },
  { symbol: "SOFI", name: "SoFi", aliases: ["sofi", "so fi"] },
  { symbol: "UPST", name: "Upstart", aliases: ["upstart"] },
  { symbol: "AFRM", name: "Affirm", aliases: ["affirm"] },
  { symbol: "MARA", name: "MARA Holdings", aliases: ["mara"] },
  { symbol: "RIOT", name: "Riot Platforms", aliases: ["riot platforms", "riot stock"] },
  { symbol: "CLSK", name: "CleanSpark", aliases: ["cleanspark", "clean spark"] },
  { symbol: "IONQ", name: "IonQ", aliases: ["ionq", "ion q"] },
  { symbol: "RGTI", name: "Rigetti", aliases: ["rigetti"] },
  { symbol: "QBTS", name: "D-Wave Quantum", aliases: ["d-wave", "d wave", "dwave"] },
  { symbol: "RKLB", name: "Rocket Lab", aliases: ["rocket lab"] },
  { symbol: "LUNR", name: "Intuitive Machines", aliases: ["intuitive machines", "lunar"] },
  { symbol: "ASTS", name: "AST SpaceMobile", aliases: ["ast spacemobile", "ast space mobile"] },
  { symbol: "CRWD", name: "CrowdStrike", aliases: ["crowdstrike", "crowd strike"] },
  { symbol: "PANW", name: "Palo Alto Networks", aliases: ["palo alto networks"] },
  { symbol: "SNOW", name: "Snowflake", aliases: ["snowflake", "\u05e1\u05e0\u05d5\u05e4\u05dc\u05d9\u05d9\u05e7"] },
  { symbol: "ZS", name: "Zscaler", aliases: ["zscaler", "z scaler", "\u05d6\u05d9-\u05e1\u05e7\u05d9\u05d9\u05dc\u05e8", "\u05d6\u05d9 \u05e1\u05e7\u05d9\u05d9\u05dc\u05e8", "\u05d6\u05d9\u05e1\u05e7\u05d9\u05d9\u05dc\u05e8"] },
  { symbol: "DDOG", name: "Datadog", aliases: ["datadog", "data dog"] },
  { symbol: "NET", name: "Cloudflare", aliases: ["cloudflare", "cloud flare"] },
  { symbol: "MDB", name: "MongoDB", aliases: ["mongodb", "mongo db"] },
  { symbol: "NOW", name: "ServiceNow", aliases: ["servicenow", "service now"] },
  { symbol: "VRT", name: "Vertiv", aliases: ["vertiv"] },
  { symbol: "DELL", name: "Dell", aliases: ["dell", "\u05d3\u05dc"] },
  { symbol: "HIMS", name: "Hims & Hers", aliases: ["hims", "hims and hers", "hims & hers"] },
  { symbol: "APP", name: "AppLovin", aliases: ["applovin", "app lovin"] },
  { symbol: "NVO", name: "Novo Nordisk", aliases: ["novo nordisk"] },
  { symbol: "LLY", name: "Eli Lilly", aliases: ["eli lilly", "lilly"] },
];

const config = {
  resendApiKey: process.env.RESEND_API_KEY,
  fromEmail: process.env.RESEND_FROM_EMAIL || "Micha Stocks Digest <onboarding@resend.dev>",
  toEmail: process.env.DIGEST_TO_EMAIL || DEFAULT_TO_EMAIL,
  channelHandle: process.env.YOUTUBE_CHANNEL_HANDLE || DEFAULT_CHANNEL_HANDLE,
  channelId: process.env.YOUTUBE_CHANNEL_ID || "",
  digestMode: process.env.DIGEST_MODE || "morning",
  forceSendOutsideNine: process.env.FORCE_SEND === "1",
};

if (process.env.SKIP_MICHA_MAIN !== "1") {
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
}

async function main() {
  if (!config.resendApiKey) {
    throw new Error("Missing RESEND_API_KEY. Add it as a GitHub Actions secret.");
  }

  const now = new Date();
  const channelId = config.channelId || await resolveChannelId(config.channelHandle) || FALLBACK_CHANNEL_ID;
  const feed = await fetchText(`https://www.youtube.com/feeds/videos.xml?channel_id=${channelId}`);
  const videos = parseFeed(feed);

  if (config.digestMode === "morning") {
    await sendMorningDigest({ now, channelId, videos });
    return;
  }

  const liveMode = LIVE_MODES[config.digestMode];
  if (!liveMode) {
    throw new Error(`Unknown DIGEST_MODE: ${config.digestMode}`);
  }

  await sendLiveDigest({ now, videos, liveMode, modeName: config.digestMode });
}

async function sendMorningDigest({ now, channelId, videos }) {
  const localParts = getLocalParts(now);
  if (!config.forceSendOutsideNine && localParts.hour < 9) {
    console.log(`Skipping: local hour is ${localParts.hour}, before the 9 AM digest window in ${TIME_ZONE}.`);
    return;
  }

  const cutoff = localDateAtHour(now, 9);
  const morningVideos = videos
    .filter((video) => isSameLocalDate(video.publishedAt, now))
    .filter((video) => video.publishedAt <= cutoff)
    .sort((a, b) => b.publishedAt - a.publishedAt);

  if (morningVideos.length === 0) {
    await sendEmail({
      subject: "Micha Stocks daily summary - no same-day video found",
      text: `No same-day Micha Stocks video was found before 9:00 AM ${TIME_ZONE}.\n\nChecked channel: ${channelId}\nDate: ${formatLocalDate(now)}`,
      html: `<p>No same-day Micha Stocks video was found before 9:00 AM ${TIME_ZONE}.</p><p>Checked channel: ${channelId}<br>Date: ${formatLocalDate(now)}</p>`,
      idempotencyKey: `micha-stocks:${formatLocalDate(now)}:morning:no-video`,
    });
    return;
  }

  const video = morningVideos[0];
  await sendVideoDigest({
    video,
    subjectPrefix: "Micha Stocks daily summary",
    idempotencyKey: `micha-stocks:${formatLocalDate(now)}:morning:${video.videoId}`,
  });
}

async function sendLiveDigest({ now, videos, liveMode, modeName }) {
  const targetTime = localDateAtTime(now, liveMode.targetHour, liveMode.targetMinute);
  if (!config.forceSendOutsideNine && now < targetTime) {
    console.log(`Skipping ${liveMode.label}: before ${formatLocalDateTime(targetTime)} in ${TIME_ZONE}.`);
    return;
  }

  const windowStart = new Date(targetTime.getTime() - liveMode.beforeMinutes * 60 * 1000);
  const windowEnd = new Date(targetTime.getTime() + liveMode.afterMinutes * 60 * 1000);
  const candidates = videos
    .filter((video) => video.publishedAt >= windowStart && video.publishedAt <= windowEnd)
    .sort((a, b) => b.publishedAt - a.publishedAt);
  const keywordMatch = candidates.find((video) => hasLiveKeyword(video, liveMode.keywords));
  const video = keywordMatch || candidates[0];

  if (!video) {
    console.log(`No ${liveMode.label} video found between ${formatLocalDateTime(windowStart)} and ${formatLocalDateTime(windowEnd)}.`);
    return;
  }

  await sendVideoDigest({
    video,
    subjectPrefix: liveMode.subjectPrefix,
    idempotencyKey: `micha-stocks:${formatLocalDate(targetTime)}:${modeName}:${video.videoId}`,
  });
}

async function sendVideoDigest({ video, subjectPrefix, idempotencyKey }) {
  const videoPage = await fetchText(video.url);
  const pageDescription = extractVideoDescription(videoPage) || video.description;
  const transcript = await getTranscript(videoPage).catch((error) => {
    console.warn(`Transcript unavailable: ${error.message}`);
    return "";
  });

  const sourceText = [video.title, pageDescription, transcript].filter(Boolean).join("\n\n");
  const digest = buildDigest(video, sourceText);
  console.log(`Digest source lengths: description=${pageDescription.length}, transcript=${transcript.length}, stocks=${digest.stockCount}`);
  await sendEmail({
    subject: `${subjectPrefix} - ${video.title}`.slice(0, 180),
    text: digest.text,
    html: digest.html,
    idempotencyKey,
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

  return fetchTranscriptText(track.baseUrl);
}

async function fetchTranscriptText(baseUrl) {
  const urls = [baseUrl, addQueryParam(baseUrl, "fmt", "json3")];
  for (const url of urls) {
    const transcriptBody = await fetchText(url).catch(() => "");
    if (!transcriptBody) continue;

    const parsedJson = parseJsonTranscript(transcriptBody);
    if (parsedJson) return parsedJson;

    const parsedXml = parseXmlTranscript(transcriptBody);
    if (parsedXml) return parsedXml;
  }
  return "";
}

function parseJsonTranscript(value) {
  if (!value.trim().startsWith("{")) return "";
  const data = JSON.parse(value);
  return (data.events || [])
    .flatMap((event) => event.segs || [])
    .map((segment) => segment.utf8 || "")
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function parseXmlTranscript(value) {
  return [...value.matchAll(/<text[^>]*>([\s\S]*?)<\/text>/g)]
    .map(([, text]) => decodeXml(text.replace(/\n/g, " ")).trim())
    .filter(Boolean)
    .join(" ");
}

function addQueryParam(url, key, value) {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
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

  return { text, html, stockCount: stocks.length };
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
    "AI", "API", "URL", "RSS", "TV", "CNBC", "NYSE", "NASDAQ", "AWS", "PLUS", "CTA",
  ]);
  const detected = new Map();

  for (const match of text.matchAll(/(?:\$|NASDAQ:|NYSE:)?\b([A-Z]{2,5})\b/g)) {
    const symbol = match[1];
    if (!stopWords.has(symbol)) {
      addDetectedStock(detected, { symbol, matchedTerm: symbol, index: match.index ?? 0 });
    }
  }

  for (const stock of STOCK_ALIASES) {
    const match = findAliasMatch(text, stock.aliases);
    if (match) {
      addDetectedStock(detected, {
        symbol: stock.symbol,
        name: stock.name,
        matchedTerm: match.term,
        index: match.index,
      });
    }
  }

  return [...detected.values()]
    .sort((a, b) => a.index - b.index)
    .slice(0, 25)
    .map((stock) => ({
      symbol: stock.name ? `${stock.symbol} (${stock.name})` : stock.symbol,
      note: describeMention(text, stock.symbol, stock.matchedTerm),
    }));
}

function hasLiveKeyword(video, keywords) {
  const searchable = `${video.title} ${video.description}`.toLowerCase();
  return keywords.some((keyword) => searchable.includes(keyword.toLowerCase()));
}

function addDetectedStock(detected, stock) {
  const existing = detected.get(stock.symbol);
  if (!existing || stock.index < existing.index || (stock.name && !existing.name)) {
    detected.set(stock.symbol, stock);
  }
}

function findAliasMatch(text, aliases) {
  let best = null;
  for (const alias of aliases) {
    const match = findTerm(text, alias);
    if (match && (!best || match.index < best.index)) best = match;
  }
  return best;
}

function findTerm(text, term) {
  const escaped = escapeRegExp(term);
  const isAsciiTerm = /^[a-z0-9 .&-]+$/i.test(term);
  const boundary = isAsciiTerm ? "(?<![A-Za-z0-9])" : "(?<![\\p{L}\\p{N}])";
  const endBoundary = isAsciiTerm ? "(?![A-Za-z0-9])" : "(?![\\p{L}\\p{N}])";
  const regex = new RegExp(`${boundary}${escaped}${endBoundary}`, isAsciiTerm ? "i" : "iu");
  const match = text.match(regex);
  return match ? { term: match[0], index: match.index ?? 0 } : null;
}

function describeMention(text, symbol, matchedTerm = symbol) {
  const index = findTerm(text, matchedTerm)?.index ?? findTerm(text, symbol)?.index ?? 0;
  const context = text.slice(Math.max(0, index - 180), Math.min(text.length, index + 260)).trim();
  return `Mention context: ${context || "mentioned, but not enough context was available."}`;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function sendEmail({ subject, text, html, idempotencyKey }) {
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.resendApiKey}`,
      "Content-Type": "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
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

function localDateAtHour(date, hour) {
  return localDateAtTime(date, hour, 0);
}

function localDateAtTime(date, hour, minute) {
  const localDate = formatLocalDate(date);
  const [year, month, day] = localDate.split("-").map(Number);
  const approxUtc = new Date(Date.UTC(year, month - 1, day, hour - 2, minute, 0));
  for (let offsetMinutes = -180; offsetMinutes <= 180; offsetMinutes += 15) {
    const candidate = new Date(approxUtc.getTime() + offsetMinutes * 60 * 1000);
    const parts = getLocalParts(candidate);
    if (parts.year === year && parts.month === month && parts.day === day && parts.hour === hour && parts.minute === minute) {
      return candidate;
    }
  }
  return approxUtc;
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

function extractVideoDescription(html) {
  return extractPlayerShortDescription(html) || extractMetaDescription(html);
}

function extractPlayerShortDescription(html) {
  const playerResponse = extractJsonObjectAfter(html, "var ytInitialPlayerResponse = ") ||
    extractJsonObjectAfter(html, "ytInitialPlayerResponse = ");
  const description = playerResponse?.videoDetails?.shortDescription ||
    extractJsonStringAfter(html, '"shortDescription":"') ||
    "";
  return extractVideoSpecificDescription(description) || description;
}

function extractJsonStringAfter(text, marker) {
  const markerIndex = text.indexOf(marker);
  if (markerIndex === -1) return "";
  let raw = "";
  let escaped = false;
  for (let index = markerIndex + marker.length; index < text.length; index += 1) {
    const char = text[index];
    if (escaped) {
      raw += `\\${char}`;
      escaped = false;
      continue;
    }
    if (char === "\\") {
      escaped = true;
      continue;
    }
    if (char === '"') break;
    raw += char;
  }
  try {
    return JSON.parse(`"${raw}"`);
  } catch {
    return "";
  }
}

function extractVideoSpecificDescription(description) {
  const markers = ["📌 על הסרטון הזה:", "על הסרטון הזה:"];
  const marker = markers.find((item) => description.includes(item));
  if (!marker) return "";

  const start = description.indexOf(marker) + marker.length;
  const rest = description.slice(start).trim();
  const endMarkers = ["\n⸻", "\n🛡", "\n🌐", "\n⚠️"];
  const end = endMarkers
    .map((item) => rest.indexOf(item))
    .filter((index) => index >= 0)
    .sort((a, b) => a - b)[0];
  return (end >= 0 ? rest.slice(0, end) : rest).trim();
}

function extractJsonObjectAfter(text, marker) {
  const markerIndex = text.indexOf(marker);
  if (markerIndex === -1) return null;
  const start = text.indexOf("{", markerIndex);
  if (start === -1) return null;

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
    if (char === "{") depth += 1;
    if (char === "}") depth -= 1;
    if (depth === 0) {
      try {
        return JSON.parse(text.slice(start, index + 1));
      } catch {
        return null;
      }
    }
  }
  return null;
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

export { buildDigest, extractStockMentions, extractVideoDescription, parseJsonTranscript, parseXmlTranscript };
