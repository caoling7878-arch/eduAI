import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/auth',
      name: 'auth',
      component: () => import('../views/AuthView.vue'),
    },
    {
      path: '/courses/geometry-lab',
      name: 'geometry-lab',
      component: () => import('../views/GeometryLabView.vue'),
    },
    {
      path: '/courses/geometry-lab/vision',
      name: 'geometry-vision',
      component: () => import('../views/LabVisionView.vue'),
    },
    {
      path: '/courses/geometry-lab/tutor',
      name: 'geometry-tutor',
      component: () => import('../views/GeometryTutorView.vue'),
    },
    {
      path: '/courses/geometry-lab/:lessonId',
      name: 'geometry-lesson',
      component: () => import('../views/GeometryLessonView.vue'),
      props: true,
    },
    {
      path: '/courses/english-coach',
      name: 'english-coach',
      component: () => import('../views/EnglishCoachView.vue'),
    },
    {
      path: '/courses/love-words',
      name: 'love-words',
      component: () => import('../views/LoveWordsView.vue'),
    },
    {
      path: '/courses/math-calc',
      name: 'math-calc',
      component: () => import('../views/MathCalcView.vue'),
    },
    {
      path: '/courses/ai-coding',
      name: 'ai-coding',
      component: () => import('../views/CodingCourseView.vue'),
    },
    {
      path: '/courses/ai-coding/:lessonId',
      name: 'ai-coding-lesson',
      component: () => import('../views/CodingLessonView.vue'),
      props: true,
    },
    {
      path: '/classroom',
      name: 'classroom-hub',
      component: () => import('../views/ClassroomHubView.vue'),
    },
    {
      path: '/classroom/:classroomId',
      name: 'classroom-player',
      component: () => import('../views/ClassroomPlayerView.vue'),
      props: true,
    },
    {
      path: '/ai',
      name: 'companions',
      component: () => import('../views/CompanionsView.vue'),
    },
    {
      path: '/ai/:assistantId',
      name: 'ai-chat',
      component: () => import('../views/AiChatView.vue'),
      props: true,
    },
    {
      path: '/me',
      name: 'me',
      component: () => import('../views/MeView.vue'),
    },
    {
      path: '/practice',
      name: 'practice',
      component: () => import('../views/PracticeView.vue'),
    },
    {
      path: '/recommend',
      name: 'recommend',
      component: () => import('../views/RecommendView.vue'),
    },
    {
      path: '/wrongbook',
      name: 'wrongbook',
      component: () => import('../views/WrongbookView.vue'),
    },
    {
      path: '/messages',
      name: 'messages',
      component: () => import('../views/MessagesView.vue'),
    },
    {
      path: '/learning',
      name: 'learning',
      component: () => import('../views/LearningView.vue'),
    },
    {
      path: '/path',
      name: 'learning-path',
      component: () => import('../views/LearningPathView.vue'),
    },
    {
      path: '/words',
      name: 'words',
      redirect: '/courses/love-words',
    },
    {
      path: '/reading',
      name: 'reading',
      component: () => import('../views/DailyArticlesView.vue'),
    },
    {
      path: '/reading/:id',
      name: 'reading-detail',
      component: () => import('../views/ArticleDetailView.vue'),
      props: true,
    },
    {
      path: '/feedback',
      name: 'feedback',
      component: () => import('../views/FeedbackView.vue'),
    },
    {
      path: '/ebooks',
      name: 'ebooks',
      component: () => import('../views/EbooksView.vue'),
    },
    {
      path: '/ebooks/:id',
      name: 'ebook-reader',
      component: () => import('../views/EbookReaderView.vue'),
      props: true,
    },
    {
      path: '/announcements',
      name: 'announcements',
      component: () => import('../views/AnnouncementsView.vue'),
    },
    {
      path: '/announcements/:id',
      name: 'announcement-detail',
      component: () => import('../views/AnnouncementDetailView.vue'),
      props: true,
    },
    {
      path: '/catalog',
      name: 'catalog',
      component: () => import('../views/CourseCatalogView.vue'),
    },
    {
      path: '/catalog/:id',
      name: 'catalog-detail',
      component: () => import('../views/CourseDetailView.vue'),
      props: true,
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
