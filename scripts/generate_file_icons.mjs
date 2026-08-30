#!/usr/bin/env node
/**
 * 从 @iconify-json/vscode-icons 提取文件类型图标，生成 src/assets/fileIcons.ts
 * 运行：node scripts/generate_file_icons.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const iconsJson = path.join(root, 'frontend', 'node_modules', '@iconify-json', 'vscode-icons', 'icons.json')
const outFile = path.join(root, 'frontend', 'src', 'assets', 'fileIcons.ts')

const data = JSON.parse(readFileSync(iconsJson, 'utf-8'))
const icons = data.icons

// 图标名 -> svg body（部分图标有 color 定义，直接内联）
function body(name) {
  const icon = icons[name]
  if (!icon) return null
  return icon.body
}

// 特殊文件名 -> 图标名
const BY_FILENAME = {
  'dockerfile': 'file-type-docker',
  'makefile': 'file-type-text',
  'cmakelists.txt': 'file-type-cmake',
  '.gitignore': 'file-type-git',
  '.gitattributes': 'file-type-git',
  '.env': 'file-type-dotenv',
  '.editorconfig': 'file-type-editorconfig',
  'license': 'file-type-license',
  'license.md': 'file-type-license',
  'license.txt': 'file-type-license',
  'package.json': 'file-type-json',
  'package-lock.json': 'file-type-json',
  'tsconfig.json': 'file-type-tsconfig',
  'tsconfig': 'file-type-tsconfig',
  'jsconfig.json': 'file-type-jsconfig',
  'vite.config.ts': 'file-type-vite',
  'vite.config.js': 'file-type-vite',
  'vue.config.js': 'file-type-vue',
  'readme.md': 'file-type-text',
  'readme': 'file-type-text',
  '.npmrc': 'file-type-npm',
  'npmignore': 'file-type-npm',
}

// 扩展名 -> 图标名
const BY_EXT = {
  py: 'file-type-python', pyw: 'file-type-python', pyi: 'file-type-python',
  js: 'file-type-js', mjs: 'file-type-js', cjs: 'file-type-js',
  ts: 'file-type-typescript', mts: 'file-type-typescript',
  tsx: 'file-type-typescript', jsx: 'file-type-js',
  java: 'file-type-java',
  c: 'file-type-c', h: 'file-type-c',
  cpp: 'file-type-cpp', cc: 'file-type-cpp', hpp: 'file-type-cpp', hxx: 'file-type-cpp',
  cs: 'file-type-csharp', csx: 'file-type-csharp',
  go: 'file-type-go',
  rs: 'file-type-rust',
  rb: 'file-type-ruby', rake: 'file-type-ruby',
  php: 'file-type-php',
  html: 'file-type-html', htm: 'file-type-html',
  css: 'file-type-css',
  scss: 'file-type-scss', sass: 'file-type-sass', less: 'file-type-less',
  json: 'file-type-json', jsonc: 'file-type-json',
  yaml: 'file-type-yaml', yml: 'file-type-yaml',
  xml: 'file-type-xml',
  sql: 'file-type-sql',
  md: 'file-type-markdown', markdown: 'file-type-markdown',
  txt: 'file-type-text', text: 'file-type-text',
  log: 'file-type-text',
  ini: 'file-type-ini', cfg: 'file-type-ini', conf: 'file-type-ini',
  toml: 'file-type-toml',
  env: 'file-type-dotenv',
  sh: 'file-type-text', bash: 'file-type-text', zsh: 'file-type-text',
  bat: 'file-type-text', cmd: 'file-type-text', ps1: 'file-type-powershell',
  svg: 'file-type-svg',
  png: 'file-type-image', jpg: 'file-type-image', jpeg: 'file-type-image',
  gif: 'file-type-image', webp: 'file-type-image', bmp: 'file-type-image',
  ico: 'file-type-image', tiff: 'file-type-image', tif: 'file-type-image', avif: 'file-type-image',
  pdf: 'file-type-pdf2',
  zip: 'file-type-zip', tar: 'file-type-zip', gz: 'file-type-zip', tgz: 'file-type-zip',
  '7z': 'file-type-zip', rar: 'file-type-zip', bz2: 'file-type-zip', xz: 'file-type-zip',
  mp3: 'file-type-audio', wav: 'file-type-audio', flac: 'file-type-audio', aac: 'file-type-audio', ogg: 'file-type-audio', m4a: 'file-type-audio', opus: 'file-type-audio',
  mp4: 'file-type-video', mov: 'file-type-video', avi: 'file-type-video', mkv: 'file-type-video',
  webm: 'file-type-video', flv: 'file-type-video', wmv: 'file-type-video', m4v: 'file-type-video',
  exe: 'file-type-binary', so: 'file-type-binary', dll: 'file-type-binary', bin: 'file-type-binary', wasm: 'file-type-binary', elf: 'file-type-binary', class: 'file-type-binary', jar: 'file-type-binary',
  doc: 'file-type-word', docx: 'file-type-word', dot: 'file-type-word', rtf: 'file-type-text', odt: 'file-type-text',
  xls: 'file-type-excel', xlsx: 'file-type-excel', csv: 'file-type-text', tsv: 'file-type-text',
  ppt: 'file-type-powerpoint', pptx: 'file-type-powerpoint', key: 'file-type-powerpoint',
  vue: 'file-type-vue', svelte: 'file-type-svelte', astro: 'file-type-astro',
  kt: 'file-type-kotlin', kts: 'file-type-kotlin', swift: 'file-type-swift', dart: 'file-type-dartlang',
  lua: 'file-type-lua', pl: 'file-type-perl', pm: 'file-type-perl', scala: 'file-type-scala',
  hs: 'file-type-haskell', r: 'file-type-r', m: 'file-type-matlab',
  ipynb: 'file-type-jupyter', sol: 'file-type-solidity', v: 'file-type-verilog',
  groovy: 'file-type-groovy', clj: 'file-type-clojure', ex: 'file-type-elixir', fs: 'file-type-fsharp',
  gradle: 'file-type-gradle', proto: 'file-type-protobuf', graphql: 'file-type-graphql', gql: 'file-type-graphql',
  prisma: 'file-type-prisma', tf: 'file-type-terraform', hcl: 'file-type-terraform',
  lock: 'file-type-text', gitkeep: 'file-type-text',
  yml2: 'file-type-yaml', gitattributes: 'file-type-git', gitmodules: 'file-type-git',
  json5: 'file-type-json', webmanifest: 'file-type-json',
  shx: 'file-type-text', pug: 'file-type-pug', jade: 'file-type-pug', ejs: 'file-type-ejs',
  hbs: 'file-type-handlebars', handlebars: 'file-type-handlebars', mustache: 'file-type-handlebars',
  styl: 'file-type-stylus', stylus: 'file-type-stylus',
  makefile: 'file-type-text', cmake: 'file-type-cmake',
  vuepress: 'file-type-vue', yarn: 'file-type-yarn', pnpm: 'file-type-pnpm',
}

const folderOpen = body('default-folder-opened') || body('default-folder')
const folderClosed = body('default-folder')
const defaultFile = body('default-file') || body('file-type-text')

// 收集用到的图标
const used = new Set(['default-file', 'default-folder', 'default-folder-opened'])
for (const name of Object.values(BY_FILENAME)) used.add(name)
for (const name of Object.values(BY_EXT)) used.add(name)

const entries = []
for (const name of used) {
  const b = body(name)
  if (!b) {
    console.warn(`缺少图标: ${name}，将回退到 default-file`)
    continue
  }
  entries.push(`  '${name}': '${b.replace(/'/g, "\\'")}',`)
}

// 生成映射表输出（含解析函数所需数据：文件名表、扩展名表、svg bodies）
const out = `// 由 scripts/generate_file_icons.mjs 自动生成，请勿手改
export interface FileIconEntry { body: string; title: string }

export const FILE_ICON_BY_FILENAME: Record<string, string> = ${JSON.stringify(BY_FILENAME, null, 2)}

export const FILE_ICON_BY_EXT: Record<string, string> = ${JSON.stringify(BY_EXT, null, 2)}

export const FILE_ICONS: Record<string, string> = {
${entries.join('\n')}
}

export const FOLDER_ICON = ${JSON.stringify(folderClosed)}
export const FOLDER_OPEN_ICON = ${JSON.stringify(folderOpen)}
export const DEFAULT_FILE_ICON = ${JSON.stringify(defaultFile)}
`

writeFileSync(outFile, out, 'utf-8')
const missing = [...used].filter((n) => !icons[n])
console.log(`已生成 ${outFile}`)
console.log(`图标数量: ${entries.length}，缺失（将回退）: ${missing.length ? missing.join(', ') : '无'}`)
