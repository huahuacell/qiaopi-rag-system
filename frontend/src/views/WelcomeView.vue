<template>
  <div class="qp-home">
    <header class="qp-home-nav">
      <div class="qp-home-nav-inner">
        <router-link class="qp-home-brand" to="/">
          <span class="qp-home-seal has-image" aria-hidden="true">
            <img :src="brandLogo" alt="" />
          </span>
          <span class="qp-home-brand-copy">
            <strong>侨批 RAG 智能档案工作台</strong>
            <small>跨海家书的智能释读与证据追踪</small>
          </span>
        </router-link>

        <nav class="qp-home-links" aria-label="首页导航">
          <a href="#top">首页</a>
          <router-link to="/search">档案检索</router-link>
          <a href="#collection">馆藏脉络</a>
          <router-link to="/plain-interpretation">白话释读</router-link>
          <router-link to="/nlp">在线 NLP</router-link>
          <router-link to="/knowledge-graph">知识图谱</router-link>
          <router-link to="/style-transfer">侨批生成</router-link>
        </nav>

        <span class="qp-home-status">
          <i></i>
          {{ demoMode ? '显式演示模式' : '正式接口模式' }}
        </span>
      </div>
    </header>

    <main id="top">
      <section class="qp-hero">
        <div class="qp-paper-grain" aria-hidden="true"></div>
        <div class="qp-hero-wash" aria-hidden="true">
          <span class="wash wash-green"></span>
          <span class="wash wash-warm"></span>
          <span class="red-thread"></span>
          <svg class="paper-grid" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="qp-grid" width="60" height="60" patternUnits="userSpaceOnUse">
                <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#1F2A28" stroke-width="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#qp-grid)" />
          </svg>
        </div>

        <div class="qp-hero-inner">
          <div class="qp-hero-copy">
            <div class="qp-eyebrow">
              <span></span>
              <strong>人文数字档案馆</strong>
              <em>· 智能释读系统</em>
            </div>

            <h1>
              让侨批文献
              <br />
              <span>被看见</span><i>·</i><span>被读懂</span><i>·</i><span>被追溯</span>
            </h1>

            <div class="qp-rule" aria-hidden="true">
              <span></span>
              <i></i>
            </div>

            <p>
              面向侨批书信与侨乡记忆的智能档案系统，支持混合检索、白话释读、侨批体生成与证据追踪，帮助用户理解跨海书信中的人物关系、汇款信息与文化记忆。
            </p>

            <div class="qp-hero-actions">
              <router-link class="qp-action primary" to="/search">
                <el-icon><Search /></el-icon>
                查一封侨批
              </router-link>
              <router-link class="qp-action secondary" to="/dashboard">
                <el-icon><DataAnalysis /></el-icon>
                浏览馆藏数据
              </router-link>
            </div>

            <div class="qp-hero-metrics" aria-label="首页摘要数据">
              <div v-for="metric in heroMetrics" :key="metric.label">
                <strong>{{ metric.value }}</strong>
                <span>{{ metric.label }}</span>
              </div>
            </div>
          </div>

          <div class="qp-archive-stack" aria-label="侨批档案卡片预览">
            <article class="archive-envelope">
              <svg viewBox="0 0 480 80" aria-hidden="true">
                <path d="M0,0 L240,65 L480,0" fill="none" stroke="#C8BFA8" stroke-width="1" />
              </svg>
              <span>寄自南洋·新加坡</span>
            </article>

            <article class="archive-paper-card">
              <p>兹寄上国币八元整，</p>
              <p>烦转交家慈收讫。</p>
              <p>此致</p>
              <span class="stamp-mark">档案留存</span>
            </article>

            <article class="archive-reading-card">
              <div class="archive-band">
                <span>档案编号</span>
                <strong>QP-1930-021</strong>
              </div>
              <div class="archive-body">
                <div class="archive-tags">
                  <span>侨批摘录</span>
                  <span>证据片段</span>
                  <span>白话释读</span>
                </div>

                <div class="archive-keywords">
                  <strong>八元</strong>
                  <i>/</i>
                  <strong>母亲</strong>
                  <i>/</i>
                  <strong>新加坡</strong>
                </div>

                <div class="archive-divider"></div>

                <section class="archive-interpretation">
                  <h2><span></span>白话释读</h2>
                  <p>这封侨批的意思是：寄信人在新加坡平安，托人带回八元钱，并问候家中母亲安好。</p>
                </section>

                <section class="archive-evidence">
                  <h2>释读依据</h2>
                  <div>
                    <span>原文片段</span>
                    <span>关键词</span>
                    <span>亲属称谓</span>
                    <span>地点信息</span>
                  </div>
                </section>

                <svg class="postmark" width="56" height="56" viewBox="0 0 56 56" aria-hidden="true">
                  <circle cx="28" cy="28" r="26" fill="none" stroke="#A74432" stroke-width="1.5" stroke-dasharray="3 2" />
                  <circle cx="28" cy="28" r="18" fill="none" stroke="#A74432" stroke-width="1" />
                  <text x="28" y="25" text-anchor="middle" font-size="6" fill="#A74432" font-family="monospace">新加坡</text>
                  <text x="28" y="34" text-anchor="middle" font-size="5" fill="#A74432" font-family="monospace">1930</text>
                </svg>
              </div>
            </article>

            <aside class="archive-note">
              <p>批注：汇款已收讫，请查照。</p>
              <span>— 1930年春</span>
            </aside>
          </div>
        </div>

        <div class="scroll-cue" aria-hidden="true">
          <span>继续探索</span>
          <i></i>
        </div>
      </section>

      <section class="qp-capabilities" id="capabilities">
        <div class="qp-section-inner">
          <header class="qp-section-head">
            <div>
              <span></span>
              <strong>核心能力</strong>
            </div>
            <h2>四种批阅方式，一座文献档案</h2>
          </header>

          <div class="capability-grid">
            <router-link
              v-for="cap in capabilities"
              :key="cap.num"
              class="capability-card"
              :class="cap.tone"
              :to="cap.to"
            >
              <i class="card-stripe"></i>
              <div class="capability-top">
                <strong>{{ cap.num }}</strong>
                <span class="mini-postmark">{{ cap.stamp }}</span>
              </div>
              <div class="capability-title">
                <span class="capability-icon">
                  <el-icon>
                    <component :is="cap.icon" />
                  </el-icon>
                </span>
                <div>
                  <h3>{{ cap.title }}</h3>
                  <small>{{ cap.subtitle }}</small>
                </div>
              </div>
              <div class="capability-line"></div>
              <p>{{ cap.desc }}</p>
              <em>{{ cap.detail }}</em>
              <b>进入功能</b>
            </router-link>
          </div>
        </div>
      </section>

      <section class="qp-collection" id="collection">
        <div class="qp-section-inner">
          <header class="qp-section-head collection-head">
            <div>
              <span></span>
              <strong>馆藏脉络</strong>
            </div>
            <h2>馆藏脉络</h2>
            <p>从来源地、年代与亲属称谓中，看见跨海家书的流动轨迹。</p>
          </header>

          <div class="collection-stats">
            <article v-for="stat in stats" :key="stat.label">
              <strong>{{ stat.value }}<small v-if="stat.unit">{{ stat.unit }}</small></strong>
              <span>{{ stat.label }}</span>
            </article>
          </div>

          <div class="collection-panels">
            <article class="collection-panel timeline-panel">
              <h3><span></span>侨批流动的年代</h3>
              <div class="timeline-bars">
                <div v-for="decade in decades" :key="decade.label">
                  <strong>{{ decade.count }}</strong>
                  <i :style="{ height: `${decade.height}px` }"></i>
                  <span>{{ decade.label }}</span>
                  <small>{{ decade.sub }}</small>
                </div>
              </div>
              <b></b>
            </article>

            <article class="collection-panel origin-panel">
              <h3><span></span>侨批从何处来</h3>
              <div class="origin-content">
                <svg viewBox="0 0 100 100" aria-label="来源地示意图">
                  <circle cx="20" cy="50" r="6" fill="#0F4A43" opacity="0.9" />
                  <text x="20" y="62" text-anchor="middle" font-size="5" fill="#0F4A43">侨乡</text>
                  <g v-for="origin in origins" :key="origin.place">
                    <circle :cx="origin.x" :cy="origin.y" :r="3 + origin.pct / 20" fill="#A74432" opacity="0.6" />
                    <path
                      :d="`M ${origin.x} ${origin.y} Q ${(origin.x + 20) / 2} ${(origin.y + 50) / 2 - 10} 20 50`"
                      fill="none"
                      stroke="#A74432"
                      stroke-width="0.8"
                      stroke-dasharray="2 1"
                      opacity="0.25"
                    />
                  </g>
                  <text x="50" y="42" text-anchor="middle" font-size="4" fill="#6F7C78" opacity="0.5">南 海</text>
                </svg>
                <div class="origin-list">
                  <p v-for="origin in origins" :key="origin.place">
                    <i :style="{ width: `${origin.pct}%` }"></i>
                    <span>{{ origin.place }}</span>
                    <strong>{{ origin.pct }}%</strong>
                  </p>
                </div>
              </div>
            </article>

            <article class="collection-panel kinship-panel">
              <h3><span></span>信中被频繁呼唤的人</h3>
              <svg viewBox="0 0 100 100" aria-label="亲属称谓关系图">
                <line
                  v-for="edge in kinEdges"
                  :key="edge.join('-')"
                  :x1="nodeById(edge[0]).cx"
                  :y1="nodeById(edge[0]).cy"
                  :x2="nodeById(edge[1]).cx"
                  :y2="nodeById(edge[1]).cy"
                  stroke="#DDD6C8"
                  stroke-width="0.6"
                />
                <g v-for="node in kinshipNodes" :key="node.id">
                  <circle
                    :cx="node.cx"
                    :cy="node.cy"
                    :r="node.r"
                    :fill="node.primary ? '#0F4A43' : 'rgba(15,74,67,0.13)'"
                    :stroke="node.primary ? '#0F4A43' : '#DDD6C8'"
                    stroke-width="0.5"
                  />
                  <text
                    :x="node.cx"
                    :y="node.cy + 1"
                    text-anchor="middle"
                    dominant-baseline="middle"
                    :font-size="node.primary ? 6 : 5"
                    :fill="node.primary ? '#F7F3EA' : '#0F4A43'"
                  >
                    {{ node.label }}
                  </text>
                </g>
              </svg>
            </article>
          </div>

          <aside class="collection-note">
            <span></span>
            <p>这些分布并不只是统计结果，它们显示了侨批作为跨国家书、汇款凭证与家庭记忆的多重身份。</p>
          </aside>
        </div>
      </section>
    </main>

    <footer class="qp-footer">
      <div class="qp-footer-inner">
        <section class="footer-brand">
          <div>
            <span class="footer-seal">批</span>
            <div>
              <strong>侨批 RAG 智能档案工作台</strong>
              <small>跨海家书的智能释读</small>
            </div>
          </div>
          <p>面向侨批文献与侨乡记忆的人文数字档案馆，致力于让跨海书信被看见、被读懂、被追溯。</p>
          <em><i></i>演示系统运行中</em>
        </section>

        <section v-for="group in footerLinks" :key="group.title" class="footer-links">
          <h2><span></span>{{ group.title }}</h2>
          <router-link v-for="link in group.links" :key="link.text" :to="link.to">{{ link.text }}</router-link>
        </section>
      </div>

      <div class="footer-bottom">
        <span>© 2024 侨批 RAG · 人文数字档案演示系统</span>
        <em>跨海书信，不应湮没于时光</em>
      </div>
    </footer>
  </div>
</template>

<script setup>
import brandLogo from '../assets/nav/1.png'
import { demoMode } from '../config/runtime'

const heroMetrics = [
  { value: '50,064', label: '馆藏记录' },
  { value: '213', label: '可释读文本' },
  { value: '1920—1960', label: '年代跨度' }
]

const capabilities = [
  {
    num: '01',
    title: '查批',
    subtitle: '混合检索',
    desc: '关键词、语义与证据片段结合，寻找相关侨批',
    detail: '支持古文关键词搜索与语义向量匹配，自动标记检索依据片段。',
    icon: 'Search',
    stamp: '检索',
    tone: 'tone-qp',
    to: '/search'
  },
  {
    num: '02',
    title: '读批',
    subtitle: '白话释读',
    desc: '将侨批原文转化为现代白话解释',
    detail: '逐段解读繁体古文，还原书信语境与时代背景，保留原文韵味。',
    icon: 'Reading',
    stamp: '释读',
    tone: 'tone-teal',
    to: '/plain-interpretation'
  },
  {
    num: '03',
    title: '溯源',
    subtitle: '证据追踪',
    desc: '展示释读所依据的原文片段与匹配原因',
    detail: '每条解读均附来源片段与置信说明，支持追溯验证。',
    icon: 'Connection',
    stamp: '溯源',
    tone: 'tone-seal',
    to: '/search'
  },
  {
    num: '04',
    title: '生批',
    subtitle: '侨批体生成',
    desc: '根据白话内容生成侨批风格文本',
    detail: '将现代表达转化为符合年代语感的侨批体书信，供研究与教学参考。',
    icon: 'EditPen',
    stamp: '生成',
    tone: 'tone-brown',
    to: '/style-transfer'
  }
]

const stats = [
  { value: '50,064', label: '元数据记录', unit: '件' },
  { value: '213', label: '文本记录', unit: '封' },
  { value: '新加坡', label: '主要来源地', unit: '' },
  { value: '母亲', label: '高频亲属关系', unit: '' }
]

const decades = [
  { label: '1910s', count: 12, sub: '初期来往', height: 13 },
  { label: '1920s', count: 58, sub: '南洋热潮', height: 60 },
  { label: '1930s', count: 96, sub: '鼎盛年代', height: 100 },
  { label: '1940s', count: 70, sub: '战时离散', height: 73 },
  { label: '1950s', count: 44, sub: '重建归家', height: 46 },
  { label: '1960s', count: 18, sub: '尾声年代', height: 19 }
]

const origins = [
  { place: '新加坡', pct: 48, x: 68, y: 55 },
  { place: '马来亚', pct: 23, x: 62, y: 62 },
  { place: '印度尼西亚', pct: 15, x: 72, y: 72 },
  { place: '泰国', pct: 8, x: 56, y: 45 },
  { place: '越南', pct: 6, x: 60, y: 38 }
]

const kinshipNodes = [
  { id: 'mother', label: '母亲', cx: 50, cy: 50, r: 28, primary: true },
  { id: 'wife', label: '妻子', cx: 80, cy: 32, r: 20 },
  { id: 'father', label: '父亲', cx: 22, cy: 30, r: 18 },
  { id: 'son', label: '儿子', cx: 78, cy: 70, r: 15 },
  { id: 'daughter', label: '女儿', cx: 24, cy: 72, r: 13 },
  { id: 'brother', label: '兄弟', cx: 50, cy: 18, r: 11 }
]

const kinEdges = [
  ['mother', 'wife'],
  ['mother', 'father'],
  ['mother', 'son'],
  ['mother', 'daughter'],
  ['mother', 'brother']
]

const nodeById = (id) => kinshipNodes.find((node) => node.id === id)

const footerLinks = [
  {
    title: '功能入口',
    links: [
      { text: '档案检索', to: '/search' },
      { text: '白话释读', to: '/plain-interpretation' },
      { text: '证据溯源', to: '/search' },
      { text: '在线 NLP', to: '/nlp' },
      { text: '知识图谱', to: '/knowledge-graph' },
      { text: '侨批生成', to: '/style-transfer' }
    ]
  },
  {
    title: '馆藏资源',
    links: [
      { text: '馆藏脉络', to: '/dashboard' },
      { text: '年代索引', to: '/dashboard' },
      { text: '来源地图', to: '/dashboard' },
      { text: '称谓图谱', to: '/knowledge-graph' }
    ]
  },
  {
    title: '关于系统',
    links: [
      { text: '数据看板', to: '/dashboard' },
      { text: '记录详情', to: '/records/CSQP-SFHC-TEXT-001' },
      { text: '分析工作台', to: '/analysis' },
      { text: '系统首页', to: '/' }
    ]
  }
]
</script>
