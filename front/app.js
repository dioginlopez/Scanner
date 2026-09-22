const video = document.querySelector('#video');
const captureCanvas = document.querySelector('#captureCanvas');
const cameraSelect = document.querySelector('#cameraSelect');
const sampleInput = document.querySelector('#sampleInput');
const outputInput = document.querySelector('#outputInput');
const startButton = document.querySelector('#startButton');
const stopButton = document.querySelector('#stopButton');
const copyButton = document.querySelector('#copyButton');
const placeholder = document.querySelector('#placeholder');
const progressFill = document.querySelector('#progressFill');
const statusText = document.querySelector('#statusText');
const sampleReadout = document.querySelector('#sampleReadout');
const cameraState = document.querySelector('#cameraState');
const liveDot = document.querySelector('#liveDot');
const sessionBadge = document.querySelector('#sessionBadge');
const confidence = document.querySelector('#confidence');
const serviceDot = document.querySelector('#serviceDot');
const serviceLabel = document.querySelector('#serviceLabel');
const toast = document.querySelector('#toast');
const facePreview = document.querySelector('#facePreview');
const faceShape = document.querySelector('#faceShape');
const hairType = document.querySelector('#hairType');
const profileNote = document.querySelector('#profileNote');

const sliderLabels = {
  largura_mandibula: 'Largura do maxilar',
  altura_rosto: 'Altura da testa / rosto',
  largura_nariz: 'Largura do nariz',
  comprimento_nariz: 'Comprimento do nariz',
  espessura_labios: 'Espessura dos lábios',
  tamanho_olhos: 'Tamanho dos olhos',
  altura_sobrancelha: 'Altura da sobrancelha',
};
const metricLabels = {
  jaw_width: 'Maxilar', face_height: 'Testa / rosto', nose_width: 'Nariz',
  nose_length: 'Nariz (compr.)', lip_fullness: 'Lábios', eye_size: 'Olhos', brow_height: 'Sobrancelha',
};

let stream = null;
let captureTimer = null;
let scanning = false;
let lastSliders = null;
let toastTimer = null;
let captureInFlight = false;

function setServiceReady() {
  serviceDot.classList.add('ready');
  serviceLabel.textContent = 'SISTEMA PRONTO';
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3200);
}

async function readApiResponse(response) {
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`O servidor respondeu com uma página HTML (${response.status}). Verifique o backend e tente novamente.`);
  }
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `Falha na API (${response.status}).`);
  }
  return data;
}

async function loadCameras() {
  try {
    const permission = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    permission.getTracks().forEach(track => track.stop());
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter(device => device.kind === 'videoinput');
    cameraSelect.innerHTML = cameras.length ? '' : '<option value="">Nenhuma câmera encontrada</option>';
    cameras.forEach((camera, index) => {
      const option = document.createElement('option');
      option.value = camera.deviceId;
      option.textContent = camera.label || `Câmera ${index + 1}`;
      cameraSelect.appendChild(option);
    });
    setServiceReady();
  } catch (error) {
    serviceLabel.textContent = 'PERMISSÃO NECESSÁRIA';
    showToast('Permita o acesso à câmera para iniciar o scanner.');
  }
}

function buildEmptyResults() {
  const sliderList = document.querySelector('#sliderList');
  sliderList.innerHTML = Object.entries(sliderLabels).map(([key, label]) => `
    <div class="slider-row" data-key="${key}">
      <div><div class="slider-name">${label}</div><div class="bar"><span></span></div></div>
      <div class="slider-number">--</div>
    </div>`).join('');
  document.querySelector('#metricGrid').innerHTML = Object.entries(metricLabels).map(([key, label]) => `
    <div class="metric-item"><span>${label}</span><strong data-metric="${key}">--</strong></div>`).join('');
}

function setRunning(value) {
  scanning = value;
  startButton.disabled = value;
  stopButton.disabled = !value;
  sessionBadge.textContent = value ? 'SCANNING' : 'IDLE';
  sessionBadge.classList.toggle('live', value);
  liveDot.classList.toggle('active', value);
  cameraState.textContent = value ? 'CÂMERA ATIVA' : 'CÂMERA DESATIVADA';
}

async function startScanner() {
  if (scanning) return;
  const samples = Number(sampleInput.value);
  if (!Number.isInteger(samples) || samples < 10 || samples > 300) {
    showToast('Escolha entre 10 e 300 amostras.');
    sampleInput.focus();
    return;
  }
  if (!cameraSelect.value) {
    showToast('Selecione uma câmera antes de iniciar.');
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: cameraSelect.value }, width: { ideal: 640, max: 640 }, height: { ideal: 480, max: 480 }, frameRate: { ideal: 24, max: 30 } }, audio: false });
    video.srcObject = stream;
    await video.play();
    placeholder.classList.add('hidden');
    video.classList.add('visible');
    captureCanvas.width = 480;
    captureCanvas.height = 360;
    const response = await fetch('/api/session/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ samples, output_dir: outputInput.value.trim() }) });
    const data = await readApiResponse(response);
    setRunning(true);
    statusText.textContent = 'Procurando rosto e coletando proporções...';
    confidence.textContent = 'ANALISANDO';
    confidence.classList.remove('ready');
    captureNextFrame();
  } catch (error) {
    stopCamera();
    showToast(error.message || 'Não foi possível acessar a câmera.');
  }
}

function captureNextFrame() {
  if (!scanning || captureInFlight) return;
  captureInFlight = true;
  const context = captureCanvas.getContext('2d');
  context.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
  captureCanvas.toBlob(async blob => {
    if (!scanning || !blob) return;
    captureInFlight = false;
    try {
      const body = new FormData();
      body.append('frame', blob, 'frame.jpg');
      const response = await fetch('/api/session/frame', { method: 'POST', body });
      const data = await readApiResponse(response);
      updateLive(data);
      if (data.count >= data.target) {
        await finishScanner();
        return;
      }
    } catch (error) {
      stopScanner(false);
      showToast(error.message);
      return;
    } finally {
      captureInFlight = false;
    }
    captureTimer = setTimeout(captureNextFrame, 220);
  }, 'image/jpeg', .82);
}

function updateLive(data) {
  progressFill.style.width = `${data.percent}%`;
  sampleReadout.textContent = `${data.count} / ${data.target} SAMPLES`;
  cameraState.textContent = data.detected ? 'ROSTO DETECTADO' : 'PROCURANDO ROSTO';
  liveDot.classList.toggle('active', data.detected);
  statusText.textContent = data.detected ? 'Leitura válida. Mantenha o rosto estável.' : 'Centralize o rosto dentro da moldura.';
  if (data.metrics) updateMetrics(data.metrics);
}

async function finishScanner() {
  try {
    const response = await fetch('/api/session/finish', { method: 'POST' });
    const data = await readApiResponse(response);
    stopCamera();
    setRunning(false);
    renderResult(data);
    statusText.textContent = 'Análise concluída. Use os valores no editor do FC26.';
    confidence.textContent = 'LEITURA OK';
    confidence.classList.add('ready');
  } catch (error) {
    stopScanner(false);
    showToast(error.message);
  }
}

function renderResult(data) {
  lastSliders = data.sliders;
  Object.entries(data.sliders).forEach(([key, value]) => {
    const row = document.querySelector(`.slider-row[data-key="${key}"]`);
    if (!row) return;
    row.querySelector('.slider-number').textContent = value;
    row.querySelector('.bar span').style.width = `${value}%`;
  });
  updateMetrics(data.metrics);
  renderProfile(data.profile, data.sliders);
  document.querySelector('#jsonReport').textContent = `JSON  /  ${data.json_path}`;
  document.querySelector('#mdReport').textContent = `MD    /  ${data.markdown_path}`;
  copyButton.disabled = false;
}

function renderProfile(profile, sliders) {
  if (!profile) return;
  faceShape.textContent = profile.formato_rosto || '--';
  hairType.textContent = profile.cabelo_estimado || '--';
  profileNote.textContent = `${profile.observacao_cabelo || ''} ${profile.nota || ''}`.trim();
  const width = 76 + (Number(sliders.largura_mandibula) - 50) * .16;
  const height = 118 + (Number(sliders.altura_rosto) - 50) * .3;
  facePreview.style.setProperty('--face-width', `${Math.max(58, Math.min(94, width))}px`);
  facePreview.style.setProperty('--face-height', `${Math.max(100, Math.min(140, height))}px`);
  facePreview.classList.add('has-result');
}

function updateMetrics(metrics) {
  Object.entries(metrics).forEach(([key, value]) => {
    const element = document.querySelector(`[data-metric="${key}"]`);
    if (element) element.textContent = Number(value).toFixed(4);
  });
}

function stopCamera() {
  if (captureTimer) clearTimeout(captureTimer);
  captureTimer = null;
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null;
  video.srcObject = null;
  video.classList.remove('visible');
  placeholder.classList.remove('hidden');
}

async function stopScanner(notify = true) {
  if (!scanning) return;
  setRunning(false);
  stopCamera();
  await fetch('/api/session/stop', { method: 'POST' });
  statusText.textContent = 'Captura interrompida.';
  cameraState.textContent = 'CÂMERA DESATIVADA';
  if (notify) showToast('Escaneamento interrompido.');
}

copyButton.addEventListener('click', async () => {
  if (!lastSliders) return;
  const content = Object.entries(lastSliders).map(([key, value]) => `${sliderLabels[key]}: ${value}`).join('\n');
  await navigator.clipboard.writeText(content);
  showToast('Sliders copiados para a área de transferência.');
});
startButton.addEventListener('click', startScanner);
stopButton.addEventListener('click', () => stopScanner());
window.addEventListener('beforeunload', () => { if (scanning) navigator.sendBeacon('/api/session/stop'); });

buildEmptyResults();
loadCameras();
