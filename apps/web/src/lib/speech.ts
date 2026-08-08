export type SpeechSupport = {
  recognition: boolean
  synthesis: boolean
  neural: boolean
}

export type TtsGender = 'female' | 'male'

export type SpeakOptions = {
  gender?: TtsGender
  lang?: 'en' | 'zh' | 'auto'
  /** 覆盖 localStorage / 环境默认音色 */
  voice?: string
  /** word=只读英文单词；sentence=整段 */
  mode?: 'word' | 'sentence'
}

type SpeechRecognitionLike = {
  lang: string
  continuous: boolean
  interimResults: boolean
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null
  onerror: ((ev: { error: string }) => void) | null
  onend: (() => void) | null
}

type SpeechRecognitionEventLike = {
  resultIndex: number
  results: ArrayLike<{
    isFinal: boolean
    0: { transcript: string }
  }>
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
}

const TTS_GENDER_KEY = 'eduai_tts_gender'

let voicesReady: Promise<SpeechSynthesisVoice[]> | null = null
let currentAudio: HTMLAudioElement | null = null
let audioUrl: string | null = null
let speakingToken = 0
let proxyUnavailableUntil = 0
let statusCache: { at: number; available: boolean } | null = null

export function getTtsGender(): TtsGender {
  if (typeof localStorage === 'undefined') return 'female'
  const v = localStorage.getItem(TTS_GENDER_KEY)
  return v === 'male' ? 'male' : 'female'
}

export function setTtsGender(gender: TtsGender) {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(TTS_GENDER_KEY, gender)
  // 换音色后立刻允许再试代理
  proxyUnavailableUntil = 0
  statusCache = null
}

export function getSpeechSupport(): SpeechSupport {
  const recognition = !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  const synthesis = typeof window !== 'undefined' && 'speechSynthesis' in window
  return { recognition, synthesis, neural: true }
}

export function createRecognizer(options: {
  lang?: string
  onInterim?: (text: string) => void
  onFinal?: (text: string) => void
  onError?: (message: string) => void
  onEnd?: () => void
}) {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Ctor) {
    throw new Error('当前浏览器不支持语音识别，请使用 Chrome / Edge')
  }

  const recognition = new Ctor()
  recognition.lang = options.lang || 'en-US'
  recognition.continuous = false
  recognition.interimResults = true

  recognition.onresult = (event) => {
    let interim = ''
    let finalText = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const piece = event.results[i]![0]!.transcript
      if (event.results[i]!.isFinal) finalText += piece
      else interim += piece
    }
    if (interim) options.onInterim?.(interim)
    if (finalText) options.onFinal?.(finalText.trim())
  }

  recognition.onerror = (ev) => {
    const map: Record<string, string> = {
      'not-allowed': '麦克风权限被拒绝，请在浏览器设置中允许',
      'no-speech': '没有检测到语音，请再试一次',
      aborted: '语音识别已取消',
      network: '语音识别网络错误',
    }
    options.onError?.(map[ev.error] || `语音识别失败：${ev.error}`)
  }

  recognition.onend = () => options.onEnd?.()

  return recognition
}

/** 只保留可朗读的口语正文，去掉场景说明与 Tip */
export function speakableText(content: string) {
  const lines = content.split('\n').map((l) => l.trim()).filter(Boolean)
  const kept: string[] = []
  for (const line of lines) {
    if (/^\(?\s*Tip:/i.test(line)) continue
    if (/^(Scene|Goals)\s*:/i.test(line)) continue
    if (/^You can start with/i.test(line)) continue
    if (/^[“"].+[”"]$/.test(line) && kept.length === 0) {
      kept.push(line.replace(/[“”']/g, ''))
      continue
    }
    kept.push(line)
  }
  return kept
    .join(' ')
    .replace(/[“”]/g, '"')
    .replace(/\s*\((?:Tip:)?[^)]*\)\s*/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/** 背单词：只提取英文词头，去掉音标/中文/词性 */
export function extractHeadword(raw: string): string {
  let s = (raw || '').trim()
  if (!s) return ''
  s = s.replace(/\/[^/\n]{1,40}\//g, ' ')
  s = s.replace(/\[[^\]]{1,40}\]/g, ' ')
  s = s.replace(/[\u4e00-\u9fff]+/g, ' ')
  s = s.replace(/\([^)]{0,16}\)/g, ' ')
  s = s.replace(/\s+/g, ' ').trim()
  const m = s.match(/^([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,5})/)
  if (m?.[1]) return m[1].trim()
  const letters = s.match(/[A-Za-z][A-Za-z'\-]*/g)
  return letters ? letters.slice(0, 6).join(' ') : ''
}

function splitSentences(text: string): string[] {
  const parts = text
    .replace(/([.!?。！？…])\s+/g, '$1\n')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  return parts.length ? parts : [text]
}

function scoreVoice(v: SpeechSynthesisVoice, preferMale: boolean): number {
  const name = `${v.name} ${v.voiceURI}`
  let score = 0
  if (/^en(-|_)US/i.test(v.lang)) score += 40
  else if (/^en(-|_)GB/i.test(v.lang)) score += 32
  else if (/^en/i.test(v.lang)) score += 20
  else return -1

  if (/neural|natural|online|enhanced|premium|superstar/i.test(name)) score += 50
  if (/Google US English/i.test(name)) score += 45
  if (/Microsoft (Ava|Jenny|Aria|Emma|Michelle|Guy|Andrew|Brian)/i.test(name)) score += 48
  if (/Samantha|Karen|Moira|Daniel|Serena|Susan|Victoria/i.test(name)) score += 36
  if (/Siri|Allison|Nicky|Tom/i.test(name)) score += 28
  if (v.localService === false) score += 18
  if (/compact|eloquence|robot|whisper/i.test(name)) score -= 25

  const maleHint = /male|guy|david|daniel|tom|brian|andrew|james|mark/i.test(name)
  const femaleHint = /female|jenny|aria|emma|samantha|karen|susan|victoria|zira|samantha/i.test(name)
  if (preferMale && maleHint) score += 25
  if (!preferMale && femaleHint) score += 25
  if (preferMale && femaleHint) score -= 15
  if (!preferMale && maleHint) score -= 15
  return score
}

export function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  if (!('speechSynthesis' in window)) return Promise.resolve([])
  if (voicesReady) return voicesReady

  voicesReady = new Promise((resolve) => {
    const read = () => window.speechSynthesis.getVoices()
    const immediate = read()
    if (immediate.length) {
      resolve(immediate)
      return
    }
    const onChange = () => {
      const list = read()
      if (!list.length) return
      window.speechSynthesis.removeEventListener('voiceschanged', onChange)
      resolve(list)
    }
    window.speechSynthesis.addEventListener('voiceschanged', onChange)
    window.setTimeout(() => {
      window.speechSynthesis.removeEventListener('voiceschanged', onChange)
      resolve(read())
    }, 600)
  })
  return voicesReady
}

export async function pickBestEnglishVoice(
  gender: TtsGender = 'female',
): Promise<SpeechSynthesisVoice | null> {
  const voices = await loadVoices()
  const ranked = voices
    .map((v) => ({ v, score: scoreVoice(v, gender === 'male') }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
  return ranked[0]?.v ?? null
}

function stopBrowserSpeech() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

function stopAudioSpeech() {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.src = ''
    currentAudio = null
  }
  if (audioUrl) {
    URL.revokeObjectURL(audioUrl)
    audioUrl = null
  }
}

export function stopSpeaking() {
  speakingToken += 1
  stopBrowserSpeech()
  stopAudioSpeech()
}

async function fetchTtsAvailable(): Promise<boolean> {
  if (statusCache && Date.now() - statusCache.at < 30_000) return statusCache.available
  try {
    const res = await fetch('/api/v1/tts/status')
    if (!res.ok) {
      statusCache = { at: Date.now(), available: false }
      return false
    }
    const data = (await res.json()) as { available?: boolean }
    statusCache = { at: Date.now(), available: !!data.available }
    return !!data.available
  } catch {
    statusCache = { at: Date.now(), available: false }
    return false
  }
}

function resolveGender(opts?: SpeakOptions): TtsGender {
  if (opts?.gender === 'male' || opts?.gender === 'female') return opts.gender
  const env = (import.meta.env.VITE_TTS_VOICE as string | undefined) || ''
  if (/^(male|onyx|echo|fable|ash)$/i.test(env)) return 'male'
  if (/^(female|nova|shimmer|alloy)$/i.test(env)) return 'female'
  return getTtsGender()
}

async function speakViaProxy(
  text: string,
  token: number,
  opts?: SpeakOptions,
): Promise<boolean> {
  if (Date.now() < proxyUnavailableUntil) return false
  const available = await fetchTtsAvailable()
  if (!available) {
    proxyUnavailableUntil = Date.now() + 20_000
    return false
  }

  const gender = resolveGender(opts)
  try {
    const res = await fetch('/api/v1/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        gender,
        voice: opts?.voice || gender,
        lang: opts?.lang === 'auto' ? undefined : opts?.lang || 'en',
        rate: opts?.mode === 'word' ? '-5%' : '-8%',
        mode: opts?.mode || 'sentence',
      }),
    })
    if (!res.ok) {
      if (res.status === 503 || res.status === 502) {
        proxyUnavailableUntil = Date.now() + 15_000
        statusCache = { at: Date.now(), available: false }
      }
      return false
    }
    const ctype = res.headers.get('content-type') || ''
    if (!ctype.includes('audio') && !ctype.includes('octet-stream')) {
      return false
    }
    const blob = await res.blob()
    if (!blob.size) return false
    if (token !== speakingToken) return true
    proxyUnavailableUntil = 0
    return playBlob(blob, token)
  } catch {
    return false
  }
}

async function speakViaOpenAICompat(
  text: string,
  token: number,
  opts?: SpeakOptions,
): Promise<boolean> {
  const base = (
    (import.meta.env.VITE_TTS_BASE_URL as string | undefined) ||
    ''
  ).replace(/\/$/, '')
  const key = (import.meta.env.VITE_TTS_API_KEY as string | undefined) || ''
  // 不再回退到 VITE_LLM_*（DeepSeek 等无语音接口，只会空耗）
  if (!base || !key) return false

  const model =
    (import.meta.env.VITE_TTS_MODEL as string | undefined) || 'gpt-4o-mini-tts'
  const gender = resolveGender(opts)
  const voice =
    opts?.voice ||
    (import.meta.env.VITE_TTS_VOICE as string | undefined) ||
    (gender === 'male' ? 'onyx' : 'nova')

  try {
    const res = await fetch(`${base}/audio/speech`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        voice,
        input: text,
        response_format: 'mp3',
        speed: 0.95,
      }),
    })
    if (!res.ok) {
      if (model !== 'tts-1-hd') {
        const retry = await fetch(`${base}/audio/speech`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${key}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: 'tts-1-hd',
            voice,
            input: text,
            response_format: 'mp3',
            speed: 0.95,
          }),
        })
        if (!retry.ok) return false
        const blob = await retry.blob()
        if (token !== speakingToken) return true
        return playBlob(blob, token)
      }
      return false
    }
    const blob = await res.blob()
    if (token !== speakingToken) return true
    return playBlob(blob, token)
  } catch {
    return false
  }
}

function playBlob(blob: Blob, token: number): Promise<boolean> {
  return new Promise((resolve) => {
    stopAudioSpeech()
    audioUrl = URL.createObjectURL(blob)
    const audio = new Audio(audioUrl)
    currentAudio = audio
    audio.onended = () => {
      if (token === speakingToken) stopAudioSpeech()
      resolve(true)
    }
    audio.onerror = () => resolve(false)
    void audio.play().catch(() => resolve(false))
  })
}

function speakViaBrowser(
  text: string,
  token: number,
  gender: TtsGender,
): Promise<void> {
  return new Promise(async (resolve, reject) => {
    if (!('speechSynthesis' in window)) {
      reject(new Error('当前浏览器不支持语音播报'))
      return
    }
    stopBrowserSpeech()
    try {
      window.speechSynthesis.resume()
    } catch {
      /* ignore */
    }
    const voice = await pickBestEnglishVoice(gender)
    const sentences = splitSentences(text)
    let i = 0

    const speakNext = () => {
      if (token !== speakingToken) {
        resolve()
        return
      }
      if (i >= sentences.length) {
        resolve()
        return
      }
      try {
        window.speechSynthesis.resume()
      } catch {
        /* ignore */
      }
      const utter = new SpeechSynthesisUtterance(sentences[i]!)
      i += 1
      utter.lang = voice?.lang?.startsWith('en-GB') ? 'en-GB' : 'en-US'
      utter.rate = 0.9
      utter.pitch = gender === 'male' ? 0.95 : 1.02
      utter.volume = 1
      if (voice) utter.voice = voice
      utter.onend = () => {
        // 句间停顿，贴近自然口语
        window.setTimeout(speakNext, 280)
      }
      utter.onerror = (ev) => {
        if (ev.error === 'interrupted' || ev.error === 'canceled') {
          resolve()
          return
        }
        reject(new Error(`系统朗读失败：${ev.error || 'unknown'}`))
      }
      window.speechSynthesis.speak(utter)
    }

    window.setTimeout(speakNext, 120)
  })
}

export type SpeakResult = {
  engine: 'neural' | 'browser'
  gender: TtsGender
  fallback?: boolean
}

/**
 * 优先后端 Edge 神经 TTS（男女声 + 自然断句），再可选 OpenAI TTS，最后浏览器回退。
 */
export async function speakEnglish(
  text: string,
  opts?: SpeakOptions,
): Promise<SpeakResult> {
  const gender = resolveGender(opts)
  const mode = opts?.mode || 'sentence'
  const clean =
    mode === 'word' ? extractHeadword(text) : speakableText(text)
  if (!clean) return { engine: 'browser', gender }

  const token = ++speakingToken
  stopBrowserSpeech()
  stopAudioSpeech()

  if (await speakViaProxy(clean, token, { ...opts, gender, mode })) {
    return { engine: 'neural', gender }
  }
  if (await speakViaOpenAICompat(clean, token, { ...opts, gender })) {
    return { engine: 'neural', gender }
  }

  await speakViaBrowser(clean, token, gender)
  return { engine: 'browser', gender, fallback: true }
}

/** 背单词专用：只朗读英文单词本身 */
export function speakWord(word: string, opts?: Omit<SpeakOptions, 'mode'>) {
  return speakEnglish(word, { ...opts, mode: 'word', lang: opts?.lang || 'en' })
}
