import { createRouter, createWebHistory } from 'vue-router'

import AnalysisView from '../views/AnalysisView.vue'
import DashboardView from '../views/DashboardView.vue'
import KnowledgeGraphView from '../views/KnowledgeGraphView.vue'
import PlainInterpretationView from '../views/PlainInterpretationView.vue'
import RecordDetailView from '../views/RecordDetailView.vue'
import SearchView from '../views/SearchView.vue'
import StyleTransferView from '../views/StyleTransferView.vue'
import WelcomeView from '../views/WelcomeView.vue'

const routes = [
  { path: '/', name: 'welcome', component: WelcomeView },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/search', name: 'search', component: SearchView },
  { path: '/records/:recordId', name: 'record-detail', component: RecordDetailView },
  { path: '/plain-interpretation', name: 'plain-interpretation', component: PlainInterpretationView },
  { path: '/style-transfer', name: 'style-transfer', component: StyleTransferView },
  { path: '/knowledge-graph', name: 'knowledge-graph', component: KnowledgeGraphView },
  { path: '/analysis', name: 'analysis', component: AnalysisView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
