<template>
  <div class="landing">
    <!-- 顶部导航 -->
    <nav class="landing-nav">
      <div class="nav-inner">
        <div class="brand" @click="$router.push('/')">
          <span class="brand-icon">&#128187;</span>
          <span class="brand-name">gitcam</span>
        </div>
        <div class="nav-menu">
          <span class="nav-item" @click="$router.push('/')">首页</span>
          <span class="nav-item" @click="$router.push('/community')">社区论坛</span>
          <span class="nav-item" @click="$router.push('/projects')">项目</span>
        </div>
        <div class="nav-actions">
          <el-button text @click="$router.push('/login')">登录</el-button>
          <el-button type="primary" @click="$router.push('/register')">注册</el-button>
        </div>
      </div>
    </nav>

    <!-- Hero -->
    <div class="hero">
      <div class="hero-inner">
        <div class="hero-logo">&#128187;</div>
        <h1 class="hero-title">gitcam</h1>
        <p class="hero-subtitle">校园代码托管分享交流平台</p>
        <p class="hero-slogan">代码即讨论上下文，讨论即代码注解</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="$router.push('/register')">免费注册</el-button>
          <el-button size="large" @click="$router.push('/login')">登 录</el-button>
        </div>
      </div>
    </div>

    <!-- 特性 -->
    <div class="section">
      <div class="section-title">平台特性</div>
      <div class="features">
        <el-card class="feature-card" shadow="hover" v-for="f in features" :key="f.title">
          <el-icon :size="28" color="#409eff"><component :is="f.icon" /></el-icon>
          <div class="feature-title">{{ f.title }}</div>
          <div class="feature-desc">{{ f.desc }}</div>
        </el-card>
      </div>
    </div>

    <!-- 最新社区帖子 -->
    <div class="section" v-if="posts.length">
      <div class="section-title">社区最新讨论</div>
      <el-card shadow="never">
        <div v-for="p in posts" :key="p.id" class="post-item" @click="$router.push(`/community/${p.id}`)">
          <div class="post-left">
            <span class="post-title">{{ p.title }}</span>
            <el-tag size="small" type="primary" effect="plain">{{ p.category_label }}</el-tag>
            <el-tag v-if="p.status === 'solved'" size="small" type="success">已解决</el-tag>
          </div>
          <div class="post-right">
            <span>{{ p.vote_count }} 赞同 · {{ p.reply_count }} 回答</span>
            <span class="post-meta">{{ p.author?.full_name }} · {{ formatTime(p.created_at) }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- CTA -->
    <div class="cta">
      <h2>加入 gitcam，开始你的代码分享之旅</h2>
      <el-button type="primary" size="large" @click="$router.push('/register')">立即注册</el-button>
    </div>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="footer-inner">
        <span>gitcam 校园代码托管分享交流平台</span>
        <span>代码即讨论上下文，讨论即代码注解</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { communityApi, type CommunityPost } from '@/api'

const router = useRouter()

const features = [
  { title: '代码托管', desc: '真实 Git 仓库托管，clone / push / 分支 / Diff，与 GitHub 一致体验', icon: 'FolderOpened' },
  { title: '项目论坛', desc: '每个项目独立讨论区，代码片段一键插入，讨论与代码双向可达', icon: 'ChatDotRound' },
  { title: '代码即讨论', desc: '帖子可绑定 Commit / 文件 / 具体行，浏览代码时直接看到关联讨论', icon: 'Connection' },
  { title: '教学协作', desc: 'Issue / Wiki / 采纳问答，教师可评议，学生可沉淀知识', icon: 'School' },
]

const posts = ref<CommunityPost[]>([])

async function loadPosts() {
  try {
    const data = await communityApi.list({ per_page: 5 }) as { items: CommunityPost[] }
    posts.value = data.items
  } catch {
    posts.value = []
  }
}

function formatTime(t: string) {
  if (!t) return '-'
  const d = new Date(t)
  const diff = Date.now() - d.getTime()
  if (diff < 24 * 60 * 60 * 1000) return `${Math.max(1, Math.floor(diff / 3600000))} 小时前`
  if (diff < 7 * 24 * 60 * 60 * 1000) return `${Math.floor(diff / 86400000)} 天前`
  return d.toLocaleDateString('zh-CN')
}

onMounted(loadPosts)
</script>

<style scoped>
.landing {
  min-height: 100vh;
  background: #f7f8fa;
}
.landing-nav {
  background: #fff;
  border-bottom: 1px solid #e8eaed;
  position: sticky;
  top: 0;
  z-index: 10;
}
.nav-inner {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 20px;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 32px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.brand-icon {
  font-size: 22px;
}
.brand-name {
  font-size: 19px;
  font-weight: 700;
  color: #1f2d3d;
}
.nav-menu {
  display: flex;
  gap: 24px;
  flex: 1;
}
.nav-item {
  color: #606266;
  cursor: pointer;
  font-size: 14px;
}
.nav-item:hover {
  color: #409eff;
}
.nav-actions {
  display: flex;
  gap: 4px;
}
.hero {
  background: linear-gradient(135deg, #1f2d3d 0%, #2c3e50 100%);
  text-align: center;
  color: #fff;
  padding: 90px 20px;
}
.hero-logo {
  font-size: 52px;
}
.hero-title {
  margin: 12px 0 6px;
  font-size: 46px;
  letter-spacing: 3px;
}
.hero-subtitle {
  margin: 0;
  font-size: 20px;
  opacity: 0.85;
}
.hero-slogan {
  margin: 18px 0 30px;
  font-size: 15px;
  opacity: 0.7;
  letter-spacing: 2px;
}
.hero-actions {
  display: flex;
  justify-content: center;
  gap: 14px;
}
.section {
  max-width: 1080px;
  margin: 48px auto;
  padding: 0 20px;
}
.section-title {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 20px;
  text-align: center;
}
.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
}
.feature-card {
  text-align: center;
  padding: 8px 4px;
}
.feature-title {
  font-weight: 600;
  margin-top: 12px;
  font-size: 15px;
}
.feature-desc {
  color: #909399;
  font-size: 12.5px;
  margin-top: 8px;
  line-height: 1.7;
}
.post-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
}
.post-item:hover {
  background: #fafbfc;
}
.post-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.post-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.post-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  color: #909399;
  font-size: 12px;
  white-space: nowrap;
}
.cta {
  background: #fff;
  border-top: 1px solid #e8eaed;
  text-align: center;
  padding: 56px 20px;
}
.cta h2 {
  margin: 0 0 20px;
  color: #1f2d3d;
}
.footer {
  background: #1f2d3d;
  color: #a3aab4;
  padding: 26px 20px;
  text-align: center;
  font-size: 13px;
}
.footer-inner {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
@media (max-width: 767px) {
  .nav-inner {
    gap: 12px;
    padding: 0 12px;
  }
  .nav-menu {
    gap: 14px;
    font-size: 13px;
  }
  .hero {
    padding: 56px 16px;
  }
  .hero-title {
    font-size: 32px;
  }
  .hero-subtitle {
    font-size: 16px;
  }
  .hero-actions {
    flex-direction: column;
    align-items: center;
  }
  .hero-actions .el-button {
    width: 70%;
  }
  .section {
    margin: 32px auto;
    padding: 0 12px;
  }
  .post-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .post-right {
    align-items: flex-start;
  }
}
</style>
