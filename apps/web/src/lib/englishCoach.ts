import type { EnglishScenario } from '../data/courses'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
}

const tips = [
  'Tip: Try a full sentence with a subject and verb.',
  'Tip: “Could you…?” sounds more polite than “Can you…?”.',
  'Tip: Add one detail (size / time / reason) to sound more natural.',
  'Tip: Great! Next time, try linking two ideas with “and” or “because”.',
]

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]!
}

/** 本地规则陪练：无 API Key 时也能完整体验 */
export function localCoachReply(scenario: EnglishScenario, history: ChatMessage[]): string {
  const lastUser = [...history].reverse().find((m) => m.role === 'user')?.content ?? ''
  const lower = lastUser.toLowerCase()
  const turn = history.filter((m) => m.role === 'user').length

  let reply = ''

  if (scenario.id === 'cafe') {
    if (turn <= 1) {
      reply =
        'Welcome! Today we have a caramel latte and a matcha croissant. Would you like a hot drink or something cold?'
    } else if (lower.includes('latte') || lower.includes('coffee') || lower.includes('tea')) {
      reply = 'Nice choice! What size would you like — small, medium, or large? Any oat milk or sugar?'
    } else if (lower.includes('small') || lower.includes('medium') || lower.includes('large')) {
      reply = 'Got it. That will be about six dollars. Would you like it for here or to go?'
    } else if (lower.includes('here') || lower.includes('go') || lower.includes('take')) {
      reply = 'Perfect. Please wait at the counter — it’ll be ready in two minutes. Anything else?'
    } else {
      reply = 'Sure. Could you tell me the drink name and the size you want?'
    }
  } else if (scenario.id === 'school') {
    if (turn <= 1) {
      reply = "Hi Alex! I'm Mia. I like drawing and basketball. What do you usually do after school?"
    } else if (lower.includes('music') || lower.includes('game') || lower.includes('read') || lower.includes('sport')) {
      reply = 'That sounds fun! Maybe we can join the club fair together this Friday. Are you free?'
    } else if (lower.includes('yes') || lower.includes('free') || lower.includes('sure')) {
      reply = 'Awesome! Let’s meet at the library gate at 4 pm. How should I find you?'
    } else {
      reply = 'Cool. Tell me one hobby you enjoy — I can share mine too.'
    }
  } else if (scenario.id === 'travel') {
    if (turn <= 1) {
      reply =
        'Of course. Gate B12 is in Terminal 2. Go straight, take the escalator up, then follow the blue signs. Do you have about 40 minutes?'
    } else if (lower.includes('yes') || lower.includes('minute') || lower.includes('time')) {
      reply =
        'Good. Security usually takes 10–15 minutes. Keep your boarding pass ready. Need help with the tram?'
    } else if (lower.includes('tram') || lower.includes('help') || lower.includes('lost')) {
      reply = 'The airport tram comes every 5 minutes. Stay on until “Terminal 2 – Gates B”. You’ve got this!'
    } else {
      reply = 'No problem. Are you connecting flights, or is this your final destination today?'
    }
  } else {
    if (turn <= 1) {
      reply =
        'Welcome. Let’s begin with a warm-up: Can you briefly introduce a project you are proud of?'
    } else if (lower.includes('project') || lower.includes('built') || lower.includes('team')) {
      reply =
        'Interesting. What was your specific role, and what result did you achieve? Please keep it under one minute.'
    } else if (lower.includes('learn') || lower.includes('internship') || lower.includes('because')) {
      reply =
        'Clear motivation. Do you have any questions for me about the team or the tech stack?'
    } else {
      reply = 'Thanks. Could you give a concrete example that shows how you solve problems under pressure?'
    }
  }

  const tip = pick(tips)
  return `${reply}\n\n(${tip})`
}

export async function coachReply(
  scenario: EnglishScenario,
  history: ChatMessage[],
): Promise<{ content: string; source: 'api' | 'local' }> {
  const base = import.meta.env.VITE_LLM_BASE_URL as string | undefined
  const key = import.meta.env.VITE_LLM_API_KEY as string | undefined
  const model = (import.meta.env.VITE_LLM_MODEL as string | undefined) || 'gpt-4o-mini'

  if (!base || !key) {
    return { content: localCoachReply(scenario, history), source: 'local' }
  }

  const messages = [
    { role: 'system', content: scenario.coachSystem },
    ...history
      .filter((m) => m.role !== 'system')
      .map((m) => ({ role: m.role, content: m.content })),
  ]

  const endpoint = base.replace(/\/$/, '') + '/chat/completions'
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      model,
      temperature: 0.7,
      messages,
    }),
  })

  if (!res.ok) {
    return {
      content: localCoachReply(scenario, history) + '\n\n(API 暂不可用，已切换本地陪练)',
      source: 'local',
    }
  }

  const data = (await res.json()) as {
    choices?: Array<{ message?: { content?: string } }>
  }
  const content = data.choices?.[0]?.message?.content?.trim()
  if (!content) {
    return { content: localCoachReply(scenario, history), source: 'local' }
  }
  return { content, source: 'api' }
}
