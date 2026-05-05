const els = {
  recordButton: document.querySelector("#recordButton"),
  recordHalo: document.querySelector("#recordHalo"),
  resetButton: document.querySelector("#resetButton"),
  mainStatus: document.querySelector("#mainStatus"),
  recordTimer: document.querySelector("#recordTimer"),
  fileInput: document.querySelector("#fileInput"),
  fileDrop: document.querySelector(".file-drop"),
  playButton: document.querySelector("#playButton"),
  playIcon: document.querySelector("#playIcon"),
  playText: document.querySelector("#playText"),
  exportButton: document.querySelector("#exportButton"),
  autoEnhanceButton: document.querySelector("#autoEnhanceButton"),
  waveform: document.querySelector("#waveform"),
  emptyWave: document.querySelector("#emptyWave"),
  trackName: document.querySelector("#trackName"),
  trackCount: document.querySelector("#trackCount"),
  trackList: document.querySelector("#trackList"),
  trimStart: document.querySelector("#trimStart"),
  trimEnd: document.querySelector("#trimEnd"),
  trimStartLabel: document.querySelector("#trimStartLabel"),
  trimEndLabel: document.querySelector("#trimEndLabel"),
  smartTip: document.querySelector("#smartTip"),
  presetButtons: [...document.querySelectorAll(".preset")],
  controls: {
    clean: document.querySelector("#cleanControl"),
    clarity: document.querySelector("#clarityControl"),
    warmth: document.querySelector("#warmthControl"),
    polish: document.querySelector("#polishControl"),
    space: document.querySelector("#spaceControl"),
  },
  values: {
    clean: document.querySelector("#cleanValue"),
    clarity: document.querySelector("#clarityValue"),
    warmth: document.querySelector("#warmthValue"),
    polish: document.querySelector("#polishValue"),
    space: document.querySelector("#spaceValue"),
  },
};

const presets = {
  balanced: { clean: 35, clarity: 45, warmth: 35, polish: 55, space: 18 },
  vocal: { clean: 52, clarity: 72, warmth: 28, polish: 66, space: 24 },
  beat: { clean: 22, clarity: 44, warmth: 62, polish: 72, space: 12 },
};

const tips = {
  balanced: "Balanced keeps the sound clean, clear, and natural.",
  vocal: "Vocal brings words and melodies closer to the front.",
  beat: "Beat adds body and punch while keeping drums direct.",
};

const state = {
  audioContext: null,
  tracks: [],
  selectedTrackId: null,
  nextTrackId: 1,
  recorder: null,
  stream: null,
  chunks: [],
  recordingStartedAt: 0,
  timerInterval: null,
  activeSources: [],
  activeNodes: [],
  isPlaying: false,
};

function ensureAudioContext() {
  if (!state.audioContext) {
    state.audioContext = new AudioContext();
  }
  if (state.audioContext.state === "suspended") {
    return state.audioContext.resume().then(() => state.audioContext);
  }
  return Promise.resolve(state.audioContext);
}

function formatTime(seconds) {
  const safe = Math.max(0, Number.isFinite(seconds) ? seconds : 0);
  const mins = Math.floor(safe / 60).toString().padStart(2, "0");
  const secs = Math.floor(safe % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

function getSettings() {
  return Object.fromEntries(
    Object.entries(els.controls).map(([key, input]) => [key, Number(input.value)])
  );
}

function getSelectedTrack() {
  return state.tracks.find((track) => track.id === state.selectedTrackId) || state.tracks[0] || null;
}

function getSongDuration() {
  return state.tracks.reduce((longest, track) => Math.max(longest, track.buffer.duration), 0);
}

function getTrimTimes() {
  const duration = getSongDuration();
  if (!duration) {
    return { start: 0, end: 0, duration: 0 };
  }

  const startPercent = Number(els.trimStart.value);
  const endPercent = Number(els.trimEnd.value);
  let start = (startPercent / 100) * duration;
  let end = (endPercent / 100) * duration;

  if (end - start < 0.15) {
    if (document.activeElement === els.trimStart) {
      start = Math.max(0, end - 0.15);
      els.trimStart.value = String((start / duration) * 100);
    } else {
      end = Math.min(duration, start + 0.15);
      els.trimEnd.value = String((end / duration) * 100);
    }
  }

  return { start, end, duration: end - start };
}

function updateTrimLabels() {
  const trim = getTrimTimes();
  els.trimStartLabel.textContent = `Start ${formatTime(trim.start)}`;
  els.trimEndLabel.textContent = `End ${formatTime(trim.end)}`;
}

function setStatus(text) {
  els.mainStatus.textContent = text;
}

function hasTracks() {
  return state.tracks.length > 0;
}

function setControlsEnabled(enabled) {
  els.playButton.disabled = !enabled;
  els.exportButton.disabled = !enabled;
  els.autoEnhanceButton.disabled = !enabled;
  els.trimStart.disabled = !enabled;
  els.trimEnd.disabled = !enabled;
}

function syncControlOutputs() {
  for (const [key, input] of Object.entries(els.controls)) {
    els.values[key].textContent = input.value;
  }
}

function applyPreset(name) {
  const preset = presets[name];
  if (!preset) return;

  for (const [key, value] of Object.entries(preset)) {
    els.controls[key].value = value;
  }

  els.presetButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.preset === name);
  });

  els.smartTip.textContent = tips[name];
  syncControlOutputs();
  updateActiveNodes();
}

function addTrack(buffer, name, type = "audio") {
  const track = {
    id: state.nextTrackId,
    name,
    type,
    buffer,
    volume: 85,
    muted: false,
    solo: false,
  };

  state.nextTrackId += 1;
  state.tracks.push(track);
  state.selectedTrackId = track.id;
  els.trimStart.value = 0;
  els.trimEnd.value = 100;
  renderTracks();
  drawWaveform();
  updateTrimLabels();
  setControlsEnabled(true);
  setStatus(`${name} added`);
}

async function loadBlob(blob, name = "New track", type = "audio") {
  await ensureAudioContext();
  stopPlayback();
  const arrayBuffer = await blob.arrayBuffer();
  const decoded = await state.audioContext.decodeAudioData(arrayBuffer.slice(0));
  addTrack(decoded, name, type);
}

async function toggleRecording() {
  if (state.recorder && state.recorder.state === "recording") {
    state.recorder.stop();
    return;
  }

  try {
    await ensureAudioContext();
    state.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.chunks = [];
    state.recorder = new MediaRecorder(state.stream);

    state.recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) state.chunks.push(event.data);
    });

    state.recorder.addEventListener("stop", async () => {
      clearInterval(state.timerInterval);
      state.timerInterval = null;
      state.stream.getTracks().forEach((track) => track.stop());
      els.recordHalo.classList.remove("recording");
      els.recordButton.setAttribute("aria-label", "Start recording");
      setStatus("Processing your recording");

      const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const blob = new Blob(state.chunks, { type: state.recorder.mimeType || "audio/webm" });
      await loadBlob(blob, `Recording ${time}`, "recording");
    });

    state.recorder.start();
    state.recordingStartedAt = Date.now();
    els.recordTimer.textContent = "00:00";
    els.recordHalo.classList.add("recording");
    els.recordButton.setAttribute("aria-label", "Stop recording");
    setStatus(hasTracks() ? "Recording a new track" : "Recording");
    state.timerInterval = setInterval(() => {
      els.recordTimer.textContent = formatTime((Date.now() - state.recordingStartedAt) / 1000);
    }, 200);
  } catch (error) {
    console.error(error);
    setStatus("Microphone permission is needed to record");
  }
}

function makeImpulseResponse(ctx, seconds, decay, mix) {
  const length = Math.max(1, Math.floor(ctx.sampleRate * seconds));
  const impulse = ctx.createBuffer(2, length, ctx.sampleRate);

  for (let channel = 0; channel < impulse.numberOfChannels; channel += 1) {
    const data = impulse.getChannelData(channel);
    for (let i = 0; i < length; i += 1) {
      const fade = Math.pow(1 - i / length, decay);
      data[i] = (Math.random() * 2 - 1) * fade * mix;
    }
  }

  return impulse;
}

function makeSaturationCurve(amount) {
  const samples = 1024;
  const curve = new Float32Array(samples);
  const drive = 1 + amount * 0.18;

  for (let i = 0; i < samples; i += 1) {
    const x = (i * 2) / samples - 1;
    curve[i] = Math.tanh(x * drive);
  }

  return curve;
}

function connectEffectChain(ctx, source, destination, settings) {
  const clean = settings.clean / 100;
  const clarity = settings.clarity / 100;
  const warmth = settings.warmth / 100;
  const polish = settings.polish / 100;
  const space = settings.space / 100;

  const highPass = ctx.createBiquadFilter();
  highPass.type = "highpass";
  highPass.frequency.value = 25 + clean * 120;
  highPass.Q.value = 0.7;

  const lowShelf = ctx.createBiquadFilter();
  lowShelf.type = "lowshelf";
  lowShelf.frequency.value = 160;
  lowShelf.gain.value = warmth * 5;

  const presence = ctx.createBiquadFilter();
  presence.type = "peaking";
  presence.frequency.value = 2800 + clarity * 1500;
  presence.Q.value = 0.95;
  presence.gain.value = clarity * 7 - 1;

  const air = ctx.createBiquadFilter();
  air.type = "highshelf";
  air.frequency.value = 8200;
  air.gain.value = clarity * 3;

  const saturator = ctx.createWaveShaper();
  saturator.curve = makeSaturationCurve(warmth);
  saturator.oversample = "4x";

  const compressor = ctx.createDynamicsCompressor();
  compressor.threshold.value = -30 + polish * 12;
  compressor.knee.value = 18 + polish * 14;
  compressor.ratio.value = 2 + polish * 7;
  compressor.attack.value = 0.004;
  compressor.release.value = 0.12 + (1 - polish) * 0.2;

  const makeup = ctx.createGain();
  makeup.gain.value = 0.9 + polish * 0.42;

  const dry = ctx.createGain();
  dry.gain.value = 1;

  const wet = ctx.createGain();
  wet.gain.value = space * 0.24;

  const convolver = ctx.createConvolver();
  convolver.buffer = makeImpulseResponse(ctx, 0.35 + space * 1.25, 2.4, 0.7);

  const limiter = ctx.createDynamicsCompressor();
  limiter.threshold.value = -3;
  limiter.knee.value = 0;
  limiter.ratio.value = 18;
  limiter.attack.value = 0.001;
  limiter.release.value = 0.045;

  source
    .connect(highPass)
    .connect(lowShelf)
    .connect(presence)
    .connect(air)
    .connect(saturator)
    .connect(compressor)
    .connect(makeup);

  makeup.connect(dry).connect(limiter);
  makeup.connect(convolver).connect(wet).connect(limiter);
  limiter.connect(destination);

  return { highPass, lowShelf, presence, air, compressor, makeup, wet };
}

function updateActiveNodes() {
  if (!state.activeNodes.length || !state.audioContext) return;
  const settings = getSettings();
  const now = state.audioContext.currentTime;
  const clean = settings.clean / 100;
  const clarity = settings.clarity / 100;
  const warmth = settings.warmth / 100;
  const polish = settings.polish / 100;
  const space = settings.space / 100;

  state.activeNodes.forEach((nodes) => {
    nodes.highPass.frequency.setTargetAtTime(25 + clean * 120, now, 0.03);
    nodes.lowShelf.gain.setTargetAtTime(warmth * 5, now, 0.03);
    nodes.presence.frequency.setTargetAtTime(2800 + clarity * 1500, now, 0.03);
    nodes.presence.gain.setTargetAtTime(clarity * 7 - 1, now, 0.03);
    nodes.air.gain.setTargetAtTime(clarity * 3, now, 0.03);
    nodes.compressor.threshold.setTargetAtTime(-30 + polish * 12, now, 0.03);
    nodes.compressor.ratio.setTargetAtTime(2 + polish * 7, now, 0.03);
    nodes.makeup.gain.setTargetAtTime(0.9 + polish * 0.42, now, 0.03);
    nodes.wet.gain.setTargetAtTime(space * 0.24, now, 0.03);
  });
}

function getPlayableTracks() {
  const soloed = state.tracks.filter((track) => track.solo && !track.muted);
  return (soloed.length ? soloed : state.tracks).filter((track) => !track.muted);
}

async function play() {
  if (!hasTracks()) return;
  await ensureAudioContext();

  const trim = getTrimTimes();
  const playable = getPlayableTracks();
  if (!playable.length) {
    setStatus("All tracks are muted");
    return;
  }

  stopPlayback(false);
  state.activeSources = [];
  state.activeNodes = [];

  const master = state.audioContext.createGain();
  master.gain.value = Math.min(1, 1 / Math.sqrt(playable.length));
  master.connect(state.audioContext.destination);

  playable.forEach((track) => {
    if (trim.start >= track.buffer.duration) return;

    const source = state.audioContext.createBufferSource();
    const gain = state.audioContext.createGain();
    source.buffer = track.buffer;
    gain.gain.value = track.volume / 100;
    source.connect(gain);
    const nodes = connectEffectChain(state.audioContext, gain, master, getSettings());
    source.start(0, trim.start, Math.min(trim.duration, track.buffer.duration - trim.start));
    state.activeSources.push(source);
    state.activeNodes.push(nodes);
  });

  if (!state.activeSources.length) {
    setStatus("Nothing to play in this trim range");
    return;
  }

  let endedCount = 0;
  state.activeSources.forEach((source) => {
    source.addEventListener("ended", () => {
      endedCount += 1;
      if (endedCount >= state.activeSources.length) stopPlayback(false);
    });
  });

  state.isPlaying = true;
  els.playIcon.textContent = "Pause";
  els.playText.textContent = "Pause";
  setStatus(`Playing ${playable.length} track${playable.length === 1 ? "" : "s"}`);
}

function stopPlayback(showStatus = true) {
  state.activeSources.forEach((source) => {
    try {
      source.stop();
    } catch (error) {
      console.debug(error);
    }
  });

  state.activeSources = [];
  state.activeNodes = [];
  state.isPlaying = false;
  els.playIcon.textContent = "Play";
  els.playText.textContent = "Play";
  if (showStatus && hasTracks()) setStatus("Ready to preview");
}

function cleanBufferForExport(ctx, buffer, settings, trim) {
  const sampleRate = buffer.sampleRate;
  const startFrame = Math.max(0, Math.floor(trim.start * sampleRate));
  const endFrame = Math.min(buffer.length, Math.ceil(trim.end * sampleRate));
  const length = Math.max(1, endFrame - startFrame);
  const copy = ctx.createBuffer(buffer.numberOfChannels, length, sampleRate);
  const threshold = (settings.clean / 100) * 0.018;
  const quietReduction = 1 - (settings.clean / 100) * 0.78;

  for (let channel = 0; channel < buffer.numberOfChannels; channel += 1) {
    const source = buffer.getChannelData(channel);
    const target = copy.getChannelData(channel);

    for (let i = 0; i < length; i += 1) {
      const sample = source[startFrame + i] || 0;
      target[i] = Math.abs(sample) < threshold ? sample * quietReduction : sample;
    }
  }

  return copy;
}

async function exportAudio() {
  if (!hasTracks()) return;

  stopPlayback();
  setStatus("Exporting polished mix");
  els.exportButton.disabled = true;

  const settings = getSettings();
  const trim = getTrimTimes();
  const playable = getPlayableTracks();
  const sampleRate = state.audioContext?.sampleRate || 44100;
  const length = Math.max(1, Math.ceil(trim.duration * sampleRate));
  const offline = new OfflineAudioContext(2, length, sampleRate);
  const master = offline.createGain();
  master.gain.value = Math.min(1, 1 / Math.sqrt(Math.max(1, playable.length)));
  master.connect(offline.destination);

  playable.forEach((track) => {
    if (trim.start >= track.buffer.duration) return;

    const cleaned = cleanBufferForExport(offline, track.buffer, settings, trim);
    const source = offline.createBufferSource();
    const gain = offline.createGain();
    source.buffer = cleaned;
    gain.gain.value = track.volume / 100;
    source.connect(gain);
    connectEffectChain(offline, gain, master, settings);
    source.start(0);
  });

  const rendered = await offline.startRendering();
  const wav = audioBufferToWav(rendered);
  const blob = new Blob([wav], { type: "audio/wav" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = "studio-simple-polished-mix.wav";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);

  els.exportButton.disabled = false;
  setStatus("Export complete");
}

function audioBufferToWav(buffer) {
  const channels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const samples = buffer.length;
  const bytesPerSample = 2;
  const blockAlign = channels * bytesPerSample;
  const dataSize = samples * blockAlign;
  const arrayBuffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(arrayBuffer);
  let offset = 0;

  function writeString(value) {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
    offset += value.length;
  }

  writeString("RIFF");
  view.setUint32(offset, 36 + dataSize, true);
  offset += 4;
  writeString("WAVE");
  writeString("fmt ");
  view.setUint32(offset, 16, true);
  offset += 4;
  view.setUint16(offset, 1, true);
  offset += 2;
  view.setUint16(offset, channels, true);
  offset += 2;
  view.setUint32(offset, sampleRate, true);
  offset += 4;
  view.setUint32(offset, sampleRate * blockAlign, true);
  offset += 4;
  view.setUint16(offset, blockAlign, true);
  offset += 2;
  view.setUint16(offset, bytesPerSample * 8, true);
  offset += 2;
  writeString("data");
  view.setUint32(offset, dataSize, true);
  offset += 4;

  const channelData = [];
  for (let channel = 0; channel < channels; channel += 1) {
    channelData.push(buffer.getChannelData(channel));
  }

  for (let i = 0; i < samples; i += 1) {
    for (let channel = 0; channel < channels; channel += 1) {
      const sample = Math.max(-1, Math.min(1, channelData[channel][i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
  }

  return arrayBuffer;
}

function getTrackStats(track) {
  const data = track.buffer.getChannelData(0);
  const step = Math.max(1, Math.floor(data.length / 12000));
  let sum = 0;
  let quietSum = 0;
  let quietCount = 0;
  let peak = 0;

  for (let i = 0; i < data.length; i += step) {
    const sample = Math.abs(data[i]);
    sum += sample * sample;
    peak = Math.max(peak, sample);
    if (sample < 0.035) {
      quietSum += sample;
      quietCount += 1;
    }
  }

  return {
    rms: Math.sqrt(sum / Math.ceil(data.length / step)),
    peak,
    noise: quietCount ? quietSum / quietCount : 0,
  };
}

function autoEnhance() {
  if (!hasTracks()) return;

  const stats = state.tracks.map(getTrackStats);
  const avgRms = stats.reduce((sum, item) => sum + item.rms, 0) / stats.length;
  const avgNoise = stats.reduce((sum, item) => sum + item.noise, 0) / stats.length;
  const maxPeak = Math.max(...stats.map((item) => item.peak));
  const recordingCount = state.tracks.filter((track) => track.type === "recording").length;

  const values = {
    clean: clamp(Math.round(28 + avgNoise * 1200 + recordingCount * 7), 28, 72),
    clarity: clamp(Math.round(48 + recordingCount * 9 - avgRms * 50), 42, 78),
    warmth: clamp(Math.round(42 + (maxPeak < 0.45 ? 12 : 0) - recordingCount * 3), 28, 64),
    polish: clamp(Math.round(62 + (avgRms < 0.08 ? 12 : 0) + state.tracks.length * 3), 58, 84),
    space: clamp(Math.round(recordingCount ? 22 : 14), 10, 30),
  };

  for (const [key, value] of Object.entries(values)) {
    els.controls[key].value = value;
  }

  state.tracks.forEach((track) => {
    const stat = getTrackStats(track);
    const target = stat.rms > 0 ? 0.14 / stat.rms : 1;
    track.volume = clamp(Math.round(track.volume * target), 45, 100);
  });

  els.presetButtons.forEach((button) => button.classList.remove("active"));
  els.smartTip.textContent = "Auto-enhance balanced the tracks and set the polish controls for this song.";
  syncControlOutputs();
  updateActiveNodes();
  renderTracks();
  setStatus("Auto-enhance applied");
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function drawWaveform() {
  const canvas = els.waveform;
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(320, Math.floor(rect.width * dpr));
  const height = Math.max(180, Math.floor(rect.height * dpr));
  const selected = getSelectedTrack();

  canvas.width = width;
  canvas.height = height;
  ctx.clearRect(0, 0, width, height);

  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#141724");
  gradient.addColorStop(1, "#101820");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const mid = height / 2;
  ctx.strokeStyle = "rgba(255,255,255,0.09)";
  ctx.lineWidth = 1 * dpr;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(width, mid);
  ctx.stroke();

  if (!selected) return;

  const data = selected.buffer.getChannelData(0);
  const step = Math.max(1, Math.floor(data.length / width));
  const amp = height * 0.42;

  ctx.strokeStyle = selected.type === "recording" ? "#ff3d74" : "#00d4aa";
  ctx.lineWidth = Math.max(1, dpr);
  ctx.beginPath();

  for (let x = 0; x < width; x += 1) {
    let min = 1;
    let max = -1;
    const start = x * step;
    for (let i = 0; i < step && start + i < data.length; i += 1) {
      const sample = data[start + i];
      if (sample < min) min = sample;
      if (sample > max) max = sample;
    }
    ctx.moveTo(x, mid + min * amp);
    ctx.lineTo(x, mid + max * amp);
  }
  ctx.stroke();

  const trim = getTrimTimes();
  const songDuration = getSongDuration();
  const startX = songDuration ? (trim.start / songDuration) * width : 0;
  const endX = songDuration ? (trim.end / songDuration) * width : width;

  ctx.fillStyle = "rgba(0, 0, 0, 0.38)";
  ctx.fillRect(0, 0, startX, height);
  ctx.fillRect(endX, 0, width - endX, height);

  ctx.fillStyle = "#ffd166";
  ctx.fillRect(startX - 2 * dpr, 0, 4 * dpr, height);
  ctx.fillRect(endX - 2 * dpr, 0, 4 * dpr, height);
}

function renderTracks() {
  const count = state.tracks.length;
  const selected = getSelectedTrack();

  els.emptyWave.classList.toggle("hidden", count > 0);
  els.trackCount.textContent = count ? `${count} track${count === 1 ? "" : "s"} in this song` : "No tracks yet";
  els.trackName.textContent = selected ? selected.name : "No audio loaded yet";
  els.trackList.innerHTML = "";

  state.tracks.forEach((track) => {
    const card = document.createElement("article");
    card.className = `track-card${track.id === state.selectedTrackId ? " active" : ""}`;
    card.dataset.trackId = String(track.id);

    card.innerHTML = `
      <button class="track-main" data-action="select">
        <span class="track-title">${escapeHtml(track.name)}</span>
        <span class="track-meta">${track.type === "recording" ? "Recording" : "Audio"} - ${formatTime(track.buffer.duration)}</span>
      </button>
      <label class="track-volume">
        <span>Volume ${track.volume}</span>
        <input type="range" min="0" max="100" value="${track.volume}" data-action="volume" />
      </label>
      <div class="track-actions">
        <button class="track-action${track.muted ? " active" : ""}" data-action="mute">Mute</button>
        <button class="track-action${track.solo ? " active" : ""}" data-action="solo">Solo</button>
      </div>
    `;

    els.trackList.append(card);
  });
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return map[char];
  });
}

function resetSession() {
  stopPlayback(false);
  state.tracks = [];
  state.selectedTrackId = null;
  state.nextTrackId = 1;
  els.trackName.textContent = "No audio loaded yet";
  els.recordTimer.textContent = "00:00";
  els.trimStart.value = 0;
  els.trimEnd.value = 100;
  setControlsEnabled(false);
  renderTracks();
  updateTrimLabels();
  drawWaveform();
  setStatus("Ready when you are");
}

els.recordButton.addEventListener("click", toggleRecording);
els.playButton.addEventListener("click", () => {
  if (state.isPlaying) stopPlayback();
  else play();
});
els.exportButton.addEventListener("click", exportAudio);
els.autoEnhanceButton.addEventListener("click", autoEnhance);
els.resetButton.addEventListener("click", resetSession);

els.fileInput.addEventListener("change", async (event) => {
  const files = [...event.target.files];
  for (const file of files) {
    await loadBlob(file, file.name, "audio");
  }
  event.target.value = "";
});

if (els.fileDrop) {
  els.fileDrop.addEventListener("dragover", (event) => {
    event.preventDefault();
  });

  els.fileDrop.addEventListener("drop", async (event) => {
    event.preventDefault();
    const files = [...event.dataTransfer.files].filter((file) => file.type.startsWith("audio/"));
    for (const file of files) {
      await loadBlob(file, file.name, "audio");
    }
  });
}

els.trackList.addEventListener("input", (event) => {
  const card = event.target.closest(".track-card");
  const track = state.tracks.find((item) => item.id === Number(card?.dataset.trackId));
  if (!track || event.target.dataset.action !== "volume") return;

  track.volume = Number(event.target.value);
  renderTracks();
  if (state.isPlaying) {
    stopPlayback(false);
    play();
  }
});

els.trackList.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  const card = event.target.closest(".track-card");
  const track = state.tracks.find((item) => item.id === Number(card?.dataset.trackId));
  if (!track || !button) return;

  const action = button.dataset.action;
  if (action === "select") state.selectedTrackId = track.id;
  if (action === "mute") track.muted = !track.muted;
  if (action === "solo") track.solo = !track.solo;

  renderTracks();
  drawWaveform();
  if (state.isPlaying && (action === "mute" || action === "solo")) {
    stopPlayback(false);
    play();
  }
});

for (const input of [els.trimStart, els.trimEnd]) {
  input.addEventListener("input", () => {
    updateTrimLabels();
    drawWaveform();
    if (state.isPlaying) {
      stopPlayback(false);
      play();
    }
  });
}

for (const input of Object.values(els.controls)) {
  input.addEventListener("input", () => {
    syncControlOutputs();
    updateActiveNodes();
  });
}

els.presetButtons.forEach((button) => {
  button.addEventListener("click", () => applyPreset(button.dataset.preset));
});

window.addEventListener("resize", drawWaveform);

syncControlOutputs();
resetSession();
