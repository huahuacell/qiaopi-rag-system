<template>
  <nav
    class="sea-route-navigation"
    aria-label="侨批海上邮路导航"
    @wheel="handleWheel"
  >
    <div class="route-stage">
      <div class="route-grid" aria-hidden="true"></div>

      <div class="route-illustration-layer" aria-hidden="true">
        <img
          v-for="(item, index) in navItems"
          :key="`${item.key}-illustration`"
          class="nav-illustration"
          :class="{ 'is-visible': index === visibleImageIndex }"
          :style="illustrationStyle(item)"
          :src="item.image"
          alt=""
          draggable="false"
        />
      </div>

      <svg
        class="route-svg"
        viewBox="0 0 320 980"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <clipPath id="route-progress-clip" clipPathUnits="userSpaceOnUse">
            <rect ref="progressClipRef" x="-12" y="-12" width="344" height="0" />
          </clipPath>
        </defs>
        <path class="route-path-shadow" :d="ROUTE_PATH" />
        <path ref="basePathRef" class="route-path-base" :d="ROUTE_PATH" />
        <path
          ref="progressPathRef"
          class="route-path-progress"
          :d="ROUTE_PATH"
          clip-path="url(#route-progress-clip)"
        />
      </svg>

      <span
        ref="indicatorRef"
        class="route-indicator"
        aria-hidden="true"
      ></span>

      <button
        v-for="(item, index) in navItems"
        :key="item.key"
        type="button"
        class="route-node"
        :class="{
          'is-active': index === activeIndex,
          'is-scroll-focus': index === focusIndex && index !== activeIndex
        }"
        :style="nodeStyle(item)"
        :aria-current="index === activeIndex ? 'page' : undefined"
        :aria-label="`前往${item.label}`"
        @click="navigateTo(index)"
        @focus="previewNode(index)"
        @blur="restoreFocus"
        @mouseenter="previewNode(index)"
        @mouseleave="restoreFocus"
      >
        <span class="route-node-label">
          <small>{{ String(index + 1).padStart(2, '0') }}</small>
          <strong>{{ item.label }}</strong>
        </span>
        <span class="route-node-ring" aria-hidden="true"></span>
        <span class="route-node-dot" aria-hidden="true"></span>
      </button>

    </div>
  </nav>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import nav1 from '../assets/nav/1.png'
import nav2 from '../assets/nav/2.png'
import nav3 from '../assets/nav/3.png'
import nav4 from '../assets/nav/4.png'
import nav5 from '../assets/nav/5.png'
import nav6 from '../assets/nav/6.png'
import nav7 from '../assets/nav/7.png'
import nav8 from '../assets/nav/8.png'
import nav9 from '../assets/nav/9.png'

const VIEWBOX_WIDTH = 320
const VIEWBOX_HEIGHT = 980
const WHEEL_THROTTLE = 580

const ROUTE_PATH = [
  'M 178 70',
  'C 154 104, 254 126, 232 178',
  'C 212 226, 62 229, 112 292',
  'C 155 340, 284 350, 246 408',
  'C 210 454, 76 465, 126 526',
  'C 170 576, 254 590, 202 636',
  'C 162 675, 93 690, 138 744',
  'C 181 790, 282 800, 238 850',
  'C 207 885, 126 904, 170 940'
].join(' ')

const navItems = [
  {
    key: 'home',
    label: '系统首页',
    route: '/',
    image: nav1,
    x: 178,
    y: 70,
    labelSide: 'right',
    imageSide: 'left',
    labelOffsetX: 20,
    labelOffsetY: -4,
    imageOffsetX: -142,
    imageOffsetY: -46,
    imageSize: 96,
    activeImageSize: 1.08,
    opacity: 0.96
  },
  {
    key: 'dashboard',
    label: '数据看板',
    route: '/dashboard',
    image: nav2,
    x: 232,
    y: 178,
    labelSide: 'left',
    imageSide: 'left',
    labelOffsetX: -112,
    labelOffsetY: -4,
    imageOffsetX: -154,
    imageOffsetY: -48,
    imageSize: 92,
    activeImageSize: 1.08,
    opacity: 0.95
  },
  {
    key: 'search',
    label: '检索',
    route: '/search',
    image: nav4,
    x: 112,
    y: 292,
    labelSide: 'right',
    imageSide: 'right',
    labelOffsetX: 20,
    labelOffsetY: -5,
    imageOffsetX: 65,
    imageOffsetY: -90,
    imageSize: 154,
    activeImageSize: 1.06,
    opacity: 0.98
  },
  {
    key: 'record-detail',
    label: '记录详情',
    route: '/records/CSQP-SFHC-TEXT-001',
    image: nav3,
    x: 246,
    y: 408,
    labelSide: 'left',
    imageSide: 'left',
    labelOffsetX: -82,
    labelOffsetY: -12,
    imageOffsetX: -172,
    imageOffsetY: -78,
    imageSize: 100,
    activeImageSize: 1.07,
    opacity: 0.96
  },
  {
    key: 'plain-interpretation',
    label: '白话解读',
    route: '/plain-interpretation',
    image: nav5,
    x: 126,
    y: 526,
    labelSide: 'right',
    imageSide: 'right',
    labelOffsetX: 20,
    labelOffsetY: -4,
    imageOffsetX: 82,
    imageOffsetY: -54,
    imageSize: 102,
    activeImageSize: 1.08,
    opacity: 0.96
  },
  {
    key: 'style-transfer',
    label: '风格转换',
    route: '/style-transfer',
    image: nav6,
    x: 202,
    y: 636,
    labelSide: 'right',
    imageSide: 'left',
    labelOffsetX: 20,
    labelOffsetY: 18,
    imageOffsetX: -160,
    imageOffsetY: -72,
    imageSize: 142,
    activeImageSize: 1.06,
    opacity: 0.96
  },
  {
    key: 'online-nlp',
    label: '在线 NLP',
    route: '/nlp',
    image: nav7,
    x: 138,
    y: 744,
    labelSide: 'right',
    imageSide: 'right',
    labelOffsetX: 20,
    labelOffsetY: -4,
    imageOffsetX: 84,
    imageOffsetY: -54,
    imageSize: 106,
    activeImageSize: 1.07,
    opacity: 0.96
  },
  {
    key: 'knowledge-graph',
    label: '知识图谱',
    route: '/knowledge-graph',
    image: nav8,
    x: 238,
    y: 850,
    labelSide: 'left',
    imageSide: 'left',
    labelOffsetX: -112,
    labelOffsetY: -4,
    imageOffsetX: -164,
    imageOffsetY: -58,
    imageSize: 112,
    activeImageSize: 1.07,
    opacity: 0.96
  },
  {
    key: 'analysis',
    label: '分类',
    route: '/analysis',
    image: nav9,
    x: 170,
    y: 940,
    labelSide: 'right',
    imageSide: 'right',
    labelOffsetX: 20,
    labelOffsetY: -4,
    imageOffsetX: 54,
    imageOffsetY: -74,
    imageSize: 110,
    activeImageSize: 1.07,
    opacity: 0.96
  }
]

const route = useRoute()
const router = useRouter()
const basePathRef = ref(null)
const progressPathRef = ref(null)
const progressClipRef = ref(null)
const indicatorRef = ref(null)
const activeIndex = ref(findActiveIndex(route.path))
const focusIndex = ref(activeIndex.value)
const visibleImageIndex = ref(activeIndex.value)

let totalLength = 0
let currentProgress = 0
let targetProgress = 0
let animationFrame = 0
let lastWheelAt = 0
let settledFocusIndex = activeIndex.value
let arrivalTargetIndex = activeIndex.value
let nodeProgresses = navItems.map((_, index) => index / (navItems.length - 1))

function findActiveIndex(path) {
  const recordIndex = navItems.findIndex((item) => item.key === 'record-detail')
  if (path.startsWith('/records/')) return recordIndex
  const exactIndex = navItems.findIndex((item) => item.route === path)
  return exactIndex >= 0 ? exactIndex : 0
}

function nodeStyle(item) {
  return {
    '--node-x': `${(item.x / VIEWBOX_WIDTH) * 100}%`,
    '--node-y': `${(item.y / VIEWBOX_HEIGHT) * 100}%`,
    '--label-x': `${item.labelOffsetX}px`,
    '--label-y': `${item.labelOffsetY}px`,
    '--label-align': item.labelSide === 'left' ? 'right' : 'left'
  }
}

function illustrationStyle(item) {
  return {
    '--illustration-x': `${(item.x / VIEWBOX_WIDTH) * 100}%`,
    '--illustration-y': `${(item.y / VIEWBOX_HEIGHT) * 100}%`,
    '--image-x': `${item.imageOffsetX}px`,
    '--image-y': `${item.imageOffsetY}px`,
    '--image-size': `${item.imageSize}px`,
    '--active-image-scale': item.activeImageSize,
    '--image-opacity': item.opacity,
    '--image-origin': item.imageSide === 'left' ? 'right center' : 'left center'
  }
}

function calculateNodeProgresses() {
  if (!basePathRef.value || !totalLength) return
  const samples = 1200
  nodeProgresses = navItems.map((item) => {
    let nearestProgress = 0
    let nearestDistance = Number.POSITIVE_INFINITY

    for (let sample = 0; sample <= samples; sample += 1) {
      const progress = sample / samples
      const point = basePathRef.value.getPointAtLength(totalLength * progress)
      const distance = Math.hypot(point.x - item.x, point.y - item.y)
      if (distance < nearestDistance) {
        nearestDistance = distance
        nearestProgress = progress
      }
    }

    let low = Math.max(0, nearestProgress - 1 / samples)
    let high = Math.min(1, nearestProgress + 1 / samples)

    for (let iteration = 0; iteration < 18; iteration += 1) {
      const left = low + (high - low) / 3
      const right = high - (high - low) / 3
      const leftPoint = basePathRef.value.getPointAtLength(totalLength * left)
      const rightPoint = basePathRef.value.getPointAtLength(totalLength * right)
      const leftDistance = Math.hypot(leftPoint.x - item.x, leftPoint.y - item.y)
      const rightDistance = Math.hypot(rightPoint.x - item.x, rightPoint.y - item.y)

      if (leftDistance < rightDistance) {
        high = right
      } else {
        low = left
      }
    }

    return (low + high) / 2
  })
}

function updateRouteVisual(progress) {
  if (
    !basePathRef.value ||
    !progressPathRef.value ||
    !progressClipRef.value ||
    !indicatorRef.value ||
    !totalLength
  ) return
  const clampedProgress = Math.min(1, Math.max(0, progress))
  const pointLength = totalLength * clampedProgress
  const point = basePathRef.value.getPointAtLength(pointLength)

  progressClipRef.value.setAttribute('height', `${point.y + 13.5}`)
  indicatorRef.value.style.left = `${(point.x / VIEWBOX_WIDTH) * 100}%`
  indicatorRef.value.style.top = `${(point.y / VIEWBOX_HEIGHT) * 100}%`
}

function animateProgress() {
  currentProgress += (targetProgress - currentProgress) * 0.085

  if (Math.abs(targetProgress - currentProgress) < 0.0001) {
    currentProgress = targetProgress
  }

  updateRouteVisual(currentProgress)

  if (
    Math.abs(targetProgress - currentProgress) < 0.0025 &&
    activeIndex.value === arrivalTargetIndex
  ) {
    visibleImageIndex.value = arrivalTargetIndex
  }

  animationFrame = requestAnimationFrame(animateProgress)
}

function progressForIndex(index) {
  return nodeProgresses[index] ?? index / (navItems.length - 1)
}

function setTargetIndex(index) {
  const safeIndex = Math.min(navItems.length - 1, Math.max(0, index))
  settledFocusIndex = safeIndex
  arrivalTargetIndex = safeIndex
  visibleImageIndex.value = -1
  focusIndex.value = safeIndex
  targetProgress = progressForIndex(safeIndex)
}

function navigateTo(index) {
  setTargetIndex(index)
  if (route.path !== navItems[index].route) {
    router.push(navItems[index].route)
  }
}

function previewNode(index) {
  focusIndex.value = index
}

function restoreFocus() {
  focusIndex.value = settledFocusIndex
}

function handleWheel(event) {
  event.preventDefault()
  const now = performance.now()
  if (now - lastWheelAt < WHEEL_THROTTLE || Math.abs(event.deltaY) < 8) return

  lastWheelAt = now
  const direction = event.deltaY > 0 ? 1 : -1
  const nextIndex = Math.min(navItems.length - 1, Math.max(0, activeIndex.value + direction))
  if (nextIndex !== activeIndex.value) {
    navigateTo(nextIndex)
  }
}

watch(
  () => route.fullPath,
  async () => {
    activeIndex.value = findActiveIndex(route.path)
    settledFocusIndex = activeIndex.value
    focusIndex.value = activeIndex.value
    await nextTick()
    setTargetIndex(activeIndex.value)
  }
)

onMounted(async () => {
  await nextTick()
  totalLength = basePathRef.value?.getTotalLength() || 0
  calculateNodeProgresses()
  currentProgress = progressForIndex(activeIndex.value)
  targetProgress = currentProgress
  updateRouteVisual(currentProgress)
  animationFrame = requestAnimationFrame(animateProgress)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animationFrame)
})
</script>

<style scoped>
.sea-route-navigation {
  --paper-bg: #f8f4ea;
  --paper-line: rgba(47, 93, 80, 0.08);
  --ink-green: #2f5d50;
  --deep-green: #203f36;
  --muted-green: #8aa69d;
  --route-soft: rgba(125, 153, 143, 0.4);
  --seal-red: #b85c4a;
  --soft-gold: #d8c3a5;
  --ease-out-expo: cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
  min-height: calc(100vh - 82px);
  color: var(--deep-green);
  user-select: none;
}

.route-stage {
  --route-content-shift: -42px;
  --route-content-shift-y: -18px;
  position: relative;
  width: 100%;
  height: calc(100vh - 82px);
  min-height: 0;
  overflow: hidden;
  isolation: isolate;
}

.route-stage::before,
.route-stage::after {
  content: "";
  position: absolute;
  z-index: 0;
  border: 1px solid rgba(47, 93, 80, 0.055);
  border-radius: 50%;
  pointer-events: none;
}

.route-stage::before {
  top: 23%;
  left: -28%;
  width: 86%;
  height: 22%;
  transform: rotate(-16deg);
}

.route-stage::after {
  right: -34%;
  bottom: 12%;
  width: 90%;
  height: 24%;
  transform: rotate(13deg);
}

.route-grid {
  position: absolute;
  z-index: 0;
  inset: 0;
  opacity: 0.42;
  background:
    linear-gradient(var(--paper-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--paper-line) 1px, transparent 1px);
  background-size: 26px 26px;
  mask-image: linear-gradient(to bottom, transparent, #000 8%, #000 92%, transparent);
  pointer-events: none;
}

.route-illustration-layer {
  position: absolute;
  z-index: 1;
  inset: 0;
  pointer-events: none;
  transform: translate3d(var(--route-content-shift), var(--route-content-shift-y), 0);
}

.route-svg {
  position: absolute;
  z-index: 3;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
  transform: translate3d(var(--route-content-shift), var(--route-content-shift-y), 0);
}

.route-path-shadow,
.route-path-base,
.route-path-progress {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.route-path-shadow {
  stroke: rgba(255, 252, 244, 0.76);
  stroke-width: 8;
}

.route-path-base {
  stroke: var(--route-soft);
  stroke-width: 2;
  stroke-dasharray: 2 7;
}

.route-path-progress {
  stroke: var(--ink-green);
  stroke-width: 2.6;
  filter: drop-shadow(0 2px 5px rgba(47, 93, 80, 0.2));
}

.route-indicator {
  position: absolute;
  z-index: 18;
  margin-left: var(--route-content-shift);
  margin-top: var(--route-content-shift-y);
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 252, 244, 0.96);
  border-radius: 999px;
  background: var(--seal-red);
  box-shadow:
    0 0 0 5px rgba(184, 92, 74, 0.11),
    0 8px 18px rgba(184, 92, 74, 0.22);
  transform: translate3d(-50%, -50%, 0);
  pointer-events: none;
  will-change: left, top;
}

.route-node {
  position: absolute;
  z-index: 8;
  top: calc(var(--node-y) + var(--route-content-shift-y));
  left: calc(var(--node-x) + var(--route-content-shift));
  width: 28px;
  height: 28px;
  margin: 0;
  border: 0;
  padding: 0;
  color: inherit;
  background: transparent;
  cursor: pointer;
  overflow: visible;
  transform: translate3d(-50%, -50%, 0);
  -webkit-tap-highlight-color: transparent;
}

.route-node:focus-visible {
  outline: 1px dashed var(--seal-red);
  outline-offset: 6px;
}

.route-node-ring,
.route-node-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 999px;
  transform: translate3d(-50%, -50%, 0);
  transition:
    width 680ms var(--ease-out-expo),
    height 680ms var(--ease-out-expo),
    opacity 320ms ease,
    background 320ms ease,
    box-shadow 680ms var(--ease-out-expo);
}

.route-node-ring {
  z-index: 5;
  width: 18px;
  height: 18px;
  border: 1px solid rgba(47, 93, 80, 0.28);
  background: rgba(248, 244, 234, 0.84);
}

.route-node-dot {
  z-index: 6;
  width: 6px;
  height: 6px;
  background: var(--muted-green);
  box-shadow: 0 0 0 3px rgba(248, 244, 234, 0.86);
}

.route-node-label {
  position: absolute;
  z-index: 7;
  top: calc(50% + var(--label-y));
  left: calc(50% + var(--label-x));
  display: flex;
  align-items: baseline;
  gap: 6px;
  width: max-content;
  max-width: 106px;
  color: rgba(67, 88, 82, 0.68);
  text-align: var(--label-align);
  text-shadow: 0 1px rgba(255, 252, 244, 0.88);
  transform: translate3d(0, -50%, 0);
  transition:
    color 320ms ease,
    transform 680ms var(--ease-out-expo),
    opacity 320ms ease;
}

.route-node-label small {
  color: rgba(184, 92, 74, 0.5);
  font-family: "JetBrains Mono", "Consolas", monospace;
  font-size: 8px;
  font-weight: 500;
  letter-spacing: 0.08em;
}

.route-node-label strong {
  font-family: "Noto Serif SC", "SimSun", serif;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.nav-illustration {
  position: absolute;
  top: calc(var(--illustration-y) + var(--image-y));
  left: calc(var(--illustration-x) + var(--image-x));
  width: var(--image-size);
  max-width: none;
  height: auto;
  opacity: 0;
  pointer-events: none;
  transform: translate3d(0, 16px, 0) scale(0.88);
  transform-origin: var(--image-origin);
  filter: sepia(0.08) saturate(0.82) drop-shadow(0 14px 22px rgba(32, 63, 54, 0.13));
  transition:
    opacity 420ms ease,
    transform 760ms var(--ease-out-expo),
    filter 760ms var(--ease-out-expo);
  will-change: opacity, transform;
}

.route-node:hover,
.route-node.is-active,
.route-node.is-scroll-focus {
  z-index: 14;
}

.nav-illustration.is-visible {
  opacity: var(--image-opacity);
  transform: translate3d(0, 0, 0) scale(var(--active-image-scale));
  filter: sepia(0.04) saturate(0.94) drop-shadow(0 17px 26px rgba(32, 63, 54, 0.16));
}

.route-node:hover .route-node-label,
.route-node.is-active .route-node-label,
.route-node.is-scroll-focus .route-node-label {
  color: var(--deep-green);
  transform: translate3d(0, calc(-50% - 2px), 0);
}

.route-node:hover .route-node-ring,
.route-node.is-scroll-focus .route-node-ring {
  width: 24px;
  height: 24px;
  border-color: rgba(47, 93, 80, 0.48);
  background: rgba(248, 244, 234, 0.92);
}

.route-node:hover .route-node-dot,
.route-node.is-scroll-focus .route-node-dot {
  width: 8px;
  height: 8px;
  background: var(--ink-green);
}

.route-node.is-active .route-node-ring {
  width: 27px;
  height: 27px;
  border-color: rgba(184, 92, 74, 0.48);
  background: rgba(255, 252, 244, 0.94);
  animation: nodePulse 3.2s ease-in-out infinite;
}

.route-node.is-active .route-node-dot {
  width: 9px;
  height: 9px;
  background: var(--seal-red);
  box-shadow: 0 0 0 4px rgba(184, 92, 74, 0.1);
}

.route-node.is-active .route-node-label strong {
  font-weight: 600;
}

@keyframes nodePulse {
  0%,
  100% {
    box-shadow: 0 0 0 5px rgba(184, 92, 74, 0.1);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(184, 92, 74, 0.035);
  }
}

@media (prefers-reduced-motion: reduce) {
  .route-node-ring,
  .route-node-dot,
  .route-node-label,
  .nav-illustration {
    transition-duration: 1ms;
  }

  .route-node.is-active .route-node-ring {
    animation: none;
  }
}
</style>
