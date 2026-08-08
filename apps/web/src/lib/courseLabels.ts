/** 学习进度 course_id → 可读标题 / 续学路由 */
import { hotCourses } from '../data/courses'

const EXTRA: Record<string, { title: string; route: string }> = {
  classroom: { title: 'AI 互动课堂', route: '/classroom' },
}

export function courseLabel(courseId: string): string {
  const hit = hotCourses.find((c) => c.id === courseId)
  if (hit) return hit.title
  if (EXTRA[courseId]) return EXTRA[courseId].title
  if (courseId.startsWith('course-')) return `课程 #${courseId.replace('course-', '')}`
  return courseId
}

export function courseRoute(courseId: string): string {
  const hit = hotCourses.find((c) => c.id === courseId)
  if (hit) return hit.route
  if (EXTRA[courseId]) return EXTRA[courseId].route
  if (courseId.startsWith('course-')) return `/catalog/${courseId.replace('course-', '')}`
  return '/catalog'
}
