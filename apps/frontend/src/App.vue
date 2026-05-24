<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useStore } from '@/store';
import { DEVICES, deviceLabel } from '@/lib/formatters';
import LogoGlyph from '@/components/LogoGlyph.vue';
import Icon from '@/components/Icon.vue';
import Card from '@/components/ui/Card.vue';
import Button from '@/components/ui/Button.vue';
import Badge from '@/components/ui/Badge.vue';
import HeroSection from '@/components/HeroSection.vue';
import ConversionRow from '@/components/ConversionRow.vue';
import AdvancedOptionsPanel from '@/components/AdvancedOptionsPanel.vue';
import SupportCard from '@/components/SupportCard.vue';
import DownloadsPage from '@/components/DownloadsPage.vue';
import * as api from '@/api';
import type { QueueItem } from '@/store';

const store = useStore();

const route = ref<'converter' | 'downloads'>('converter');
const mode = ref<'comic' | 'manga'>('comic');
const dark = ref(true);

// Community: live GitHub star count
const starCount = ref<number | null>(null);
const starLabel = computed(() => {
  const n = starCount.value;
  if (n == null) return '';
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
  return String(n);
});

// UI state
const dragInUploader = ref(false);
const hoverInUploader = ref(false);
const deviceOpen = ref(false);
const advancedOpen = ref(false);
const pulseConfig = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const fileInputCompact = ref<HTMLInputElement | null>(null);

onMounted(() => {
  const saved = localStorage.getItem('mgc_theme');
  dark.value = saved !== 'light';
  const savedMode = localStorage.getItem('mgc_mode') as 'comic' | 'manga' | null;
  if (savedMode) mode.value = savedMode;

  fetch('https://api.github.com/repos/NilsLeo/kcc-cloud')
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => { if (d && typeof d.stargazers_count === 'number') starCount.value = d.stargazers_count; })
    .catch(() => {});
});
watch(dark, (v) => {
  document.documentElement.classList.toggle('dark', v);
  localStorage.setItem('mgc_theme', v ? 'dark' : 'light');
}, { immediate: true });
watch(mode, (v) => {
  store.advancedOptions.mangaStyle = v === 'manga';
  localStorage.setItem('mgc_mode', v);
}, { immediate: true });

// derived
const STATUS_ORDER: Record<string, number> = { UPLOADING: 0, PROCESSING: 1, QUEUED: 2, COMPLETE: 3, ERRORED: 4 };
const sortedItems = computed(() => [...store.items].sort((a, b) => (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99)));
const hasFiles = computed(() => store.items.length > 0);
const allDone = computed(() => hasFiles.value && store.items.every((f) => f.status === 'COMPLETE'));
const activeJobs = computed(() => store.items.filter((f) => ['UPLOADING', 'QUEUED', 'PROCESSING'].includes(f.status)).length);
const completedJobs = computed(() => store.items.filter((f) => f.status === 'COMPLETE').length);
const pendingCount = computed(() => store.items.filter((f) => f.status !== 'COMPLETE').length);
const currentStep = computed(() => {
  if (!hasFiles.value) return 1;
  if (!store.selectedProfile) return 2;
  return 3;
});

// handlers
function onDrop(e: DragEvent) {
  e.preventDefault();
  dragInUploader.value = false;
  const list = Array.from(e.dataTransfer?.files || []);
  if (list.length) store.addFiles(list);
}
function onFileInput(e: Event) {
  const target = e.target as HTMLInputElement;
  const list = Array.from(target.files || []);
  if (list.length) store.addFiles(list);
  target.value = '';
}
function openBigPicker() { fileInputRef.value?.click(); }
function startConvert() {
  if (!store.selectedProfile) {
    pulseConfig.value = true;
    setTimeout(() => (pulseConfig.value = false), 3000);
  }
}
function downloadItem(item: QueueItem) {
  if (item.jobId) window.location.href = api.downloadUrl(item.jobId);
}
function downloadAll() {
  for (const item of store.items.filter((i) => i.status === 'COMPLETE' && i.jobId)) {
    window.open(api.downloadUrl(item.jobId!), '_blank');
  }
}
</script>

<template>
  <div :class="['min-h-screen flex flex-col bg-background', mode === 'manga' ? 'manga-theme' : 'comic-theme']">
    <!-- header -->
    <header class="border-b sticky top-0 z-30 bg-background/95 backdrop-blur">
      <div class="container mx-auto max-w-6xl px-4 h-16 flex items-center gap-6">
        <a href="#" class="flex items-center gap-2.5 shrink-0" @click.prevent="route = 'converter'">
          <LogoGlyph class="h-8 w-8" />
          <h1 class="font-poppins font-semibold tracking-tight text-lg leading-none">
            <span class="text-foreground">KCC</span><span class="text-theme-medium"> Cloud</span>
          </h1>
        </a>

        <!-- segmented mode toggle (desktop) -->
        <div class="hidden sm:flex items-center bg-muted rounded-md p-0.5 h-9">
          <button
            :class="['inline-flex items-center gap-1.5 px-3 h-8 text-sm font-medium rounded transition-all',
              mode === 'comic' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground']"
            @click="mode = 'comic'"
          >
            <Icon name="book" class="h-4 w-4" /> Comic
          </button>
          <button
            :class="['inline-flex items-center gap-1.5 px-3 h-8 text-sm font-medium rounded transition-all',
              mode === 'manga' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground']"
            @click="mode = 'manga'"
          >
            <Icon name="bookOpen" class="h-4 w-4" /> Manga
          </button>
        </div>

        <nav class="flex items-center gap-1 md:gap-4 ml-auto">
          <div class="hidden md:flex items-center gap-4 text-sm">
            <a
              href="#"
              :class="['transition-colors hover:text-foreground', route === 'converter' ? 'text-foreground font-medium' : 'text-muted-foreground']"
              @click.prevent="route = 'converter'"
            >Converter</a>
            <a
              href="#"
              :class="['transition-colors hover:text-foreground', route === 'downloads' ? 'text-foreground font-medium' : 'text-muted-foreground']"
              @click.prevent="route = 'downloads'"
            >Downloads</a>
          </div>

          <!-- GitHub Star button -->
          <a
            href="https://github.com/NilsLeo/kcc-cloud"
            target="_blank"
            rel="noopener noreferrer"
            class="hidden md:inline-flex items-center gap-1.5 h-8 px-2.5 text-xs font-medium rounded-md border bg-background hover:bg-accent transition-colors"
          >
            <Icon name="github" class="h-3.5 w-3.5" />
            <span>Star</span>
            <span v-if="starLabel" class="font-mono text-muted-foreground border-l pl-2 ml-0.5">{{ starLabel }}</span>
          </a>

          <Button variant="ghost" size="icon" aria-label="Toggle theme" @click="dark = !dark">
            <Icon :name="dark ? 'sun' : 'moon'" class="h-[1.1rem] w-[1.1rem]" />
          </Button>
        </nav>
      </div>

      <!-- mobile mode toggle -->
      <div class="sm:hidden border-t flex">
        <button
          :class="['flex-1 inline-flex items-center justify-center gap-2 py-2 text-sm font-medium border-b-2 transition-colors',
            mode === 'comic' ? 'border-theme-medium text-foreground' : 'border-transparent text-muted-foreground']"
          @click="mode = 'comic'"
        >
          <Icon name="book" class="h-4 w-4" /> Comic
        </button>
        <button
          :class="['flex-1 inline-flex items-center justify-center gap-2 py-2 text-sm font-medium border-b-2 transition-colors',
            mode === 'manga' ? 'border-theme-medium text-foreground' : 'border-transparent text-muted-foreground']"
          @click="mode = 'manga'"
        >
          <Icon name="bookOpen" class="h-4 w-4" /> Manga
        </button>
      </div>
    </header>

    <main class="flex-1 container mx-auto max-w-6xl px-4 py-6 md:py-10">

      <!-- CONVERTER -->
      <div v-if="route === 'converter'" class="flex flex-col gap-6 md:gap-8 animate-slide-up">
        <HeroSection :mode="mode" />

        <!-- steps -->
        <div class="flex items-center justify-between">
          <template v-for="(s, i) in [
            { title: 'Upload', desc: 'Drop your files' },
            { title: 'Configure', desc: 'Pick a device' },
            { title: 'Convert', desc: 'Download results' },
          ]" :key="i">
            <div class="flex flex-col items-center">
              <div
                :class="['flex items-center justify-center w-9 h-9 md:w-10 md:h-10 rounded-full border-2 text-sm font-semibold transition-colors',
                  currentStep >= i + 1 ? 'border-theme-medium bg-theme-medium text-white' : 'border-muted-foreground/40 text-muted-foreground']"
              >
                <Icon v-if="currentStep > i + 1" name="check" class="h-5 w-5" />
                <span v-else>{{ i + 1 }}</span>
              </div>
              <div class="mt-2 text-center">
                <div :class="['text-xs md:text-sm font-medium', currentStep >= i + 1 ? 'text-foreground' : 'text-muted-foreground']">{{ s.title }}</div>
                <div class="text-[10px] md:text-xs mt-0.5 text-muted-foreground hidden md:block">{{ s.desc }}</div>
              </div>
            </div>
            <div v-if="i < 2" :class="['flex-1 h-0.5 mx-2 -translate-y-3 md:-translate-y-4', currentStep > i + 1 ? 'bg-theme-medium' : 'bg-border']" />
          </template>
        </div>

        <!-- uploader (empty state) -->
        <Card
          v-if="!hasFiles"
          :class="['border-2 transition-all overflow-hidden', dragInUploader ? 'border-theme-medium border-dashed scale-[1.005] shadow-md' : 'border-input']"
        >
          <div
            class="dotted-bg flex flex-col items-center justify-center gap-4 py-12 px-6"
            @dragover.prevent="dragInUploader = true"
            @dragleave="dragInUploader = false"
            @drop="onDrop"
            @mouseenter="hoverInUploader = true"
            @mouseleave="hoverInUploader = false"
          >
            <label :class="['rounded-full p-6 cursor-pointer transition-all', (hoverInUploader || dragInUploader) ? 'bg-theme-medium/10 text-theme-medium scale-105' : 'bg-muted text-muted-foreground']">
              <input ref="fileInputRef" type="file" multiple accept=".pdf,.cbz,.cbr,.cb7,.zip,.rar,.epub" class="hidden" @change="onFileInput" />
              <!-- Batman SVG for comic mode on hover -->
              <svg v-if="(hoverInUploader || dragInUploader) && mode === 'comic'" xmlns="http://www.w3.org/2000/svg" viewBox="1.95 2 230.12 256" fill="currentColor" class="h-12 w-12">
                <path d="M232.043,157.557L216.22,2l-32.915,51.122c0,0-28.733-21.024-66.301-21.024c-37.577,0-60.744,17.332-60.744,17.332L9.57,2 L1.957,157.557h4.675C11.901,213.818,59.385,258,117,258s105.099-44.182,110.368-100.443H232.043z M47.147,109.233 c2.105-7.719,11.19-11.065,17.794-6.556l35.635,24.35H42.293L47.147,109.233z M169.194,102.677 c6.604-4.508,15.698-1.163,17.803,6.556l4.845,17.794h-58.283L169.194,102.677z M117,238.185c-46.68,0-85.26-35.314-90.447-80.628 h180.893C202.26,202.871,163.68,238.185,117,238.185z M146.646,200.214H90.891v-16.932h55.755V200.214z" />
              </svg>
              <!-- Konoha SVG for manga mode on hover -->
              <svg v-else-if="(hoverInUploader || dragInUploader) && mode === 'manga'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" fill="currentColor" class="h-12 w-12">
                <path d="M38.892 14.296C26.973 19.323 15.061 32.693 15.01 41.102c-.009 1.359-2.437 8.367-13.59 39.218L.039 84.141l27.731-.321c31.091-.359 32.628-.667 41.006-8.237 18.829-17.01 3.415-50.678-20.822-45.48-20.01 4.292-21.144 34.431-1.379 36.658 12.603 1.421 18.192-11.422 8.707-20.006-1.841-1.666-2.037-1.62-4.623 1.079-2.699 2.817-2.699 2.82-.68 4.647 4.522 4.092 1.159 8.906-4.439 6.355-6.306-2.873-7.474-12.102-2.199-17.377 13.386-13.386 34.151 8.644 23.31 24.731-16.699 24.779-55.114-1.28-42.293-28.69 8.743-18.692 31.564-23.429 50.15-10.41l5.702 3.995 7.395-5.566c8.152-6.136 8.232-6.278 5.458-9.658-2.098-2.557-1.74-2.656-8.938 2.474l-3.978 2.835-8.663-4.293c-11.285-5.592-23.213-6.537-32.592-2.581M16 62.281c0 .371-1.105 3.609-2.455 7.196L11.09 76h15.259l-2.071-2.25c-1.138-1.237-3.467-4.476-5.174-7.196C17.397 63.834 16 61.911 16 62.281" fill-rule="evenodd" />
              </svg>
              <Icon v-else name="upload" class="h-12 w-12" />
            </label>
            <div class="text-center">
              <p class="text-lg font-medium font-poppins">{{ dragInUploader ? 'Drop files here' : 'Drag and drop your files here' }}</p>
              <p class="text-sm text-muted-foreground mt-1">Supported: .cbz, .cbr, .cb7, .zip, .rar, .pdf, .epub</p>
              <p class="text-sm text-muted-foreground mt-1">Maximum 10 files · Maximum file size: <span class="font-medium text-theme-medium">1 GB</span></p>
            </div>
            <Button variant="brand" size="lg" class="mt-2" @click="openBigPicker">
              <Icon name="fileUp" class="h-4 w-4" /> Choose files
            </Button>
          </div>
        </Card>

        <!-- compact "Add more files" -->
        <Card
          v-else
          :class="['border-2 border-dashed transition-all', dragInUploader ? 'border-theme-medium bg-theme-medium/5' : 'border-muted-foreground/25 hover:border-theme-medium/50']"
        >
          <div
            class="p-4 flex items-center gap-4"
            @dragover.prevent="dragInUploader = true"
            @dragleave="dragInUploader = false"
            @drop="onDrop"
          >
            <label class="rounded-full bg-muted p-2 hover:bg-muted/80 transition-colors cursor-pointer text-muted-foreground">
              <input ref="fileInputCompact" type="file" multiple accept=".pdf,.cbz,.cbr,.cb7,.zip,.rar,.epub" class="hidden" @change="onFileInput" />
              <Icon name="upload" class="h-4 w-4" />
            </label>
            <div>
              <p class="text-sm font-medium font-poppins">Add more files</p>
              <p class="text-xs text-muted-foreground">Drag &amp; drop or click to browse</p>
            </div>
          </div>
        </Card>

        <!-- configure card -->
        <Card v-if="hasFiles && !allDone">
          <div class="p-5 md:p-6 space-y-5">
            <div :class="['space-y-3 rounded-lg transition-shadow', pulseConfig && 'animate-pulse-glow']">
              <div class="flex items-center gap-2">
                <Icon name="smartphone" class="h-5 w-5 text-muted-foreground" />
                <label class="text-base font-medium font-poppins">Select Your E-Reader</label>
                <Icon name="help" class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="relative">
                <button
                  :class="['flex w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm h-10',
                    'focus:outline-none focus:ring-2 focus:ring-theme-medium/40 focus:border-theme-medium',
                    !store.selectedProfile && 'text-muted-foreground']"
                  @click="deviceOpen = !deviceOpen"
                >
                  <span class="truncate">{{ store.selectedProfile ? deviceLabel(store.selectedProfile) : 'Select your E-Reader' }}</span>
                  <Icon name="chevronDown" :class="['h-4 w-4 opacity-50 transition-transform', deviceOpen && 'rotate-180']" />
                </button>
                <template v-if="deviceOpen">
                  <div class="fixed inset-0 z-30" @click="deviceOpen = false" />
                  <div class="absolute z-40 mt-1 w-full rounded-md border bg-background shadow-lg max-h-80 overflow-auto scrollbar-thin">
                    <template v-for="(devices, brand) in DEVICES" :key="brand">
                      <div class="px-3 py-1.5 text-xs font-semibold text-muted-foreground border-b">{{ brand }} Devices</div>
                      <button
                        v-for="(label, k) in devices"
                        :key="k"
                        :class="['flex w-full items-center justify-between px-3 py-2 text-sm hover:bg-accent text-left',
                          store.selectedProfile === k && 'bg-theme-medium/10 text-theme-medium font-medium']"
                        @click="store.selectedProfile = k as string; deviceOpen = false"
                      >
                        <span>{{ label }}</span>
                        <Icon v-if="store.selectedProfile === k" name="check" class="h-4 w-4" />
                      </button>
                    </template>
                  </div>
                </template>
              </div>
            </div>

            <!-- advanced options toggle -->
            <button
              class="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              @click="advancedOpen = !advancedOpen"
            >
              <Icon name="settings" class="h-4 w-4" /> Advanced Options
              <Icon name="chevronDown" :class="['h-4 w-4 transition-transform', advancedOpen && 'rotate-180']" />
              <Badge variant="purple" class="ml-1">32 params</Badge>
            </button>
            <div v-if="advancedOpen" class="animate-slide-up border-t pt-4">
              <AdvancedOptionsPanel
                :options="store.advancedOptions"
                :device-profile="store.selectedProfile"
                @change="(patch) => Object.assign(store.advancedOptions, patch)"
              />
            </div>
          </div>
        </Card>

        <!-- queue -->
        <div v-if="hasFiles" class="space-y-3">
          <div class="flex items-center gap-2">
            <h3 class="font-semibold font-poppins text-lg">Conversion queue</h3>
            <Badge v-if="activeJobs > 0" variant="purple">
              <span class="h-1.5 w-1.5 rounded-full bg-theme-medium animate-pulse" />{{ activeJobs }} active
            </Badge>
            <Badge v-if="completedJobs > 0" variant="success">
              <Icon name="check" class="h-3 w-3" />{{ completedJobs }} done
            </Badge>
          </div>
          <div class="space-y-2.5">
            <ConversionRow
              v-for="item in sortedItems"
              :key="item.id"
              :item="item"
              @cancel="(it) => store.cancelItem(it.id)"
              @dismiss="(it) => store.cancelItem(it.id)"
              @download="downloadItem"
              @retry="(it) => store.retryItem(it.id)"
            />
          </div>
        </div>

        <!-- sticky convert bar -->
        <div v-if="hasFiles && !allDone" class="sticky bottom-4 z-20">
          <Card class="border-theme-medium/20 shadow-lg">
            <div class="p-3 md:p-4 flex items-center justify-between gap-3">
              <div class="text-sm">
                <span class="font-medium font-poppins">{{ pendingCount }} file{{ pendingCount === 1 ? '' : 's' }} to convert</span>
                <span class="text-muted-foreground ml-2 hidden md:inline">
                  {{ store.selectedProfile ? '→ ' + deviceLabel(store.selectedProfile) : '→ Pick a device above' }}
                </span>
              </div>
              <Button variant="brand" size="lg" @click="startConvert">
                <Icon name="chevronsRight" class="h-4 w-4" /> Start conversion
              </Button>
            </div>
          </Card>
        </div>

        <!-- all done -->
        <Card v-if="allDone" class="border-success/30 bg-success/5">
          <div class="p-6 flex flex-col md:flex-row md:items-center gap-4">
            <div class="rounded-full bg-success/15 p-3 shrink-0 text-success">
              <Icon name="checkCircle" class="h-6 w-6" />
            </div>
            <div class="flex-1">
              <h3 class="font-semibold font-poppins text-lg">All files ready</h3>
              <p class="text-sm text-muted-foreground mt-0.5">{{ store.items.length }} file{{ store.items.length === 1 ? '' : 's' }} converted. Files stay available for 24 hours.</p>
            </div>
            <Button variant="brand" size="lg" @click="downloadAll">
              <Icon name="download" class="h-4 w-4" /> Download all
            </Button>
          </div>
        </Card>

        <SupportCard />
      </div>

      <!-- DOWNLOADS -->
      <DownloadsPage v-else-if="route === 'downloads'" />

      <!-- footer -->
      <footer class="mt-12 pt-8 border-t text-sm text-muted-foreground">
        <Card class="mb-6">
          <div class="p-5 flex items-start gap-4 flex-col md:flex-row md:items-center">
            <div class="rounded-md p-2 bg-muted text-muted-foreground">
              <Icon name="github" class="h-5 w-5" />
            </div>
            <div class="flex-1">
              <h3 class="font-semibold text-foreground font-poppins">Community Edition</h3>
              <p class="text-sm mt-1">Free forever. Self-hostable, MIT-licensed. A star on GitHub is the best support.</p>
            </div>
            <a
              href="https://github.com/NilsLeo/kcc-cloud"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 h-8 px-3 text-xs font-medium rounded-md border bg-background hover:bg-accent transition-colors"
            >
              <Icon name="star" class="h-3.5 w-3.5" /> Star on GitHub
              <span v-if="starLabel" class="font-mono text-muted-foreground border-l pl-2">{{ starLabel }}</span>
            </a>
          </div>
        </Card>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 class="font-semibold mb-2 text-foreground font-poppins">About</h3>
            <p class="text-sm leading-relaxed">Convert manga, comics and PDFs into e-reader-optimized formats. Supports Kindle, Kobo, reMarkable and 30+ other devices.</p>
          </div>
          <div>
            <h3 class="font-semibold mb-2 text-foreground font-poppins">Credits</h3>
            <p>Built on <a href="https://github.com/ciromattia/kcc" target="_blank" rel="noopener noreferrer" class="text-theme-medium hover:underline font-medium">Kindle Comic Converter</a>. Licensed under ISC.</p>
            <p class="text-xs mt-2 leading-relaxed">© 2012-2025 Ciro Mattia Gonano · © 2013-2019 Paweł Jastrzębski · © 2021-2023 Darodi · © 2023-2025 Alex Xu</p>
          </div>
        </div>

        <div class="pt-4 mt-6 border-t flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
          <span>Self-hosted Community Edition · ISC License</span>
          <div class="flex items-center gap-4">
            <a href="https://github.com/NilsLeo/kcc-cloud" target="_blank" rel="noopener noreferrer" class="hover:text-foreground transition-colors inline-flex items-center gap-1">
              <Icon name="github" class="h-3.5 w-3.5" />GitHub<span v-if="starLabel" class="opacity-60 ml-0.5">{{ starLabel }}</span>
            </a>
            <a href="https://github.com/NilsLeo/kcc-cloud/issues/new" target="_blank" rel="noopener noreferrer" class="hover:text-foreground transition-colors">Report bug</a>
            <a href="https://github.com/NilsLeo/kcc-cloud#readme" target="_blank" rel="noopener noreferrer" class="hover:text-foreground transition-colors">Documentation</a>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>
