import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../lib/api'
import AdminLayout from '../layouts/AdminLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/',
      component: AdminLayout,
      meta: { auth: true },
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
        {
          path: 'hub',
          name: 'teacher-hub',
          component: () => import('../views/TeacherHubView.vue'),
        },
        {
          path: 'students',
          name: 'students',
          meta: { adminOnly: true },
          component: () => import('../views/StudentsView.vue'),
        },
        { path: 'users', name: 'users', meta: { adminOnly: true }, component: () => import('../views/UsersView.vue') },
        { path: 'teachers', name: 'teachers', meta: { adminOnly: true }, component: () => import('../views/TeachersView.vue') },
        { path: 'courses', name: 'courses', component: () => import('../views/CoursesView.vue') },
        { path: 'classes', name: 'classes', component: () => import('../views/ClassesView.vue') },
        { path: 'questions', name: 'questions', component: () => import('../views/QuestionsView.vue') },
        { path: 'papers', name: 'papers', component: () => import('../views/PapersView.vue') },
        { path: 'grading', name: 'grading', component: () => import('../views/GradeQueueView.vue') },
        { path: 'reports', name: 'reports', component: () => import('../views/ReportsView.vue') },
        {
          path: 'announcements',
          name: 'announcements',
          component: () => import('../views/AnnouncementsView.vue'),
        },
        { path: 'orders', name: 'orders', meta: { adminOnly: true }, component: () => import('../views/OrdersView.vue') },
        { path: 'settings', name: 'settings', meta: { adminOnly: true }, component: () => import('../views/SettingsView.vue') },
        { path: 'assistants', name: 'assistants', component: () => import('../views/AssistantsView.vue') },
        { path: 'ai-config', name: 'ai-config', meta: { adminOnly: true }, component: () => import('../views/AiConfigView.vue') },
        { path: 'knowledge', name: 'knowledge', component: () => import('../views/KnowledgeView.vue') },
        { path: 'ppt', name: 'ppt', component: () => import('../views/PptView.vue') },
        { path: 'ebooks', name: 'ebooks', component: () => import('../views/EbooksView.vue') },
        { path: 'articles', name: 'articles', component: () => import('../views/ArticlesAdminView.vue') },
        { path: 'templates', name: 'templates', component: () => import('../views/TemplatesView.vue') },
        { path: 'feedback', name: 'feedback', component: () => import('../views/FeedbackView.vue') },
        { path: 'geometry', name: 'geometry', component: () => import('../views/GeometryView.vue') },
        { path: 'datasets', name: 'datasets', meta: { adminOnly: true }, component: () => import('../views/DatasetsView.vue') },
        { path: 'api-tokens', name: 'api-tokens', meta: { adminOnly: true }, component: () => import('../views/ApiTokensView.vue') },
        { path: 'workflows', name: 'workflows', component: () => import('../views/WorkflowsView.vue') },
        { path: 'billing', name: 'billing', meta: { adminOnly: true }, component: () => import('../views/BillingView.vue') },
        { path: 'audits', name: 'audits', meta: { adminOnly: true }, component: () => import('../views/AuditsView.vue') },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.auth && !getToken()) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.name === 'login' && getToken()) return { name: 'dashboard' }
  return true
})

export default router
