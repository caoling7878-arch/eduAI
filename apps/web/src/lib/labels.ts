/** 学员端状态可读文案。 */

const GRADE_STATUS: Record<string, string> = {
  pending: '排队中',
  ai_scored: 'AI 初评完成',
  teacher_reviewed: '教师已复核',
  reviewed: '教师已复核',
}

const FEEDBACK_STATUS: Record<string, string> = {
  open: '待处理',
  processing: '处理中',
  resolved: '已回复',
  closed: '已关闭',
}

export function gradeStatusLabel(status: string | undefined | null): string {
  if (!status) return '未知状态'
  return GRADE_STATUS[status] || status
}

export function feedbackStatusLabel(status: string | undefined | null): string {
  if (!status) return '未知'
  return FEEDBACK_STATUS[status] || status
}
