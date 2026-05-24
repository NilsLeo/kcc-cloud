<script setup lang="ts">
import { ref, computed } from 'vue';
import Card from '@/components/ui/Card.vue';
import Button from '@/components/ui/Button.vue';
import Icon from '@/components/Icon.vue';
import { useStore } from '@/store';
import { fmtBytes, extIcon, deviceLabel } from '@/lib/formatters';
import * as api from '@/api';

const store = useStore();
const downloadsPage = ref(1);
const DOWNLOADS_PER_PAGE = 6;

const totalPages = computed(() => Math.max(1, Math.ceil(store.downloads.length / DOWNLOADS_PER_PAGE)));
const pagedDownloads = computed(() => {
  const start = (downloadsPage.value - 1) * DOWNLOADS_PER_PAGE;
  return store.downloads.slice(start, start + DOWNLOADS_PER_PAGE);
});

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} minute${m === 1 ? '' : 's'} ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return h === 1 ? 'an hour ago' : `${h} hours ago`;
  const d = Math.floor(h / 24);
  if (d === 1) return 'yesterday';
  if (d < 7) return `${d} days ago`;
  return new Date(iso).toLocaleDateString();
}

function download(jobId: string) {
  window.location.href = api.downloadUrl(jobId);
}

function clearAll() {
  store.downloads.splice(0, store.downloads.length);
  localStorage.setItem('mgc_downloads', '[]');
}
</script>

<template>
  <div class="space-y-6 animate-slide-up">
    <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
      <div>
        <h2 class="text-2xl md:text-3xl font-bold font-poppins tracking-tight">My Downloads</h2>
        <p class="text-muted-foreground mt-1">Every file you've converted, ready to grab again.</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-muted/50 text-sm">
          <span class="text-muted-foreground">Total</span>
          <span class="font-mono font-medium">{{ store.downloads.length }}</span>
        </div>
        <Button v-if="store.downloads.length" variant="outline" size="sm" class="text-destructive hover:text-destructive" @click="clearAll">
          <Icon name="trash" class="h-3.5 w-3.5" /> Clear all
        </Button>
      </div>
    </div>

    <Card v-if="!store.downloads.length" class="border-dashed">
      <div class="py-16 flex flex-col items-center justify-center text-center">
        <div class="rounded-full bg-muted p-5 mb-4 text-muted-foreground">
          <Icon name="download" class="h-8 w-8" />
        </div>
        <h3 class="font-semibold font-poppins text-lg">No downloads yet</h3>
        <p class="text-sm text-muted-foreground mt-1 max-w-md">Convert something on the home page and it'll show up here. Files stick around for 24 hours.</p>
      </div>
    </Card>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-3">
      <Card v-for="d in pagedDownloads" :key="d.jobId" class="hover:border-theme-medium/40 transition-colors group">
        <div class="p-4 flex items-center gap-3">
          <div class="shrink-0 h-11 w-11 rounded-lg flex items-center justify-center bg-success/10 text-success">
            <Icon :name="extIcon(d.outputName)" class="h-5 w-5" />
          </div>
          <div class="flex-1 min-w-0">
            <h4 class="font-poppins font-medium text-sm truncate">{{ d.outputName }}</h4>
            <div class="flex items-center gap-2 text-xs text-muted-foreground mt-0.5 flex-wrap">
              <span class="inline-flex items-center gap-1"><Icon name="smartphone" class="h-3 w-3" />{{ deviceLabel(d.deviceLabel) }}</span>
              <span v-if="d.outputSize">·</span>
              <span v-if="d.outputSize" class="font-mono">{{ fmtBytes(d.outputSize) }}</span>
              <span>·</span>
              <span>{{ timeAgo(d.completedAt) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <Button variant="brand" size="sm" @click="download(d.jobId)">
              <Icon name="download" class="h-3.5 w-3.5" />Get
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              class="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
              @click="store.removeDownload(d.jobId)"
            >
              <Icon name="trash" class="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>

    <div v-if="store.downloads.length > DOWNLOADS_PER_PAGE" class="flex items-center justify-between gap-3 pt-2">
      <p class="text-xs text-muted-foreground">
        Showing <span class="font-medium text-foreground">{{ (downloadsPage - 1) * DOWNLOADS_PER_PAGE + 1 }}–{{ Math.min(downloadsPage * DOWNLOADS_PER_PAGE, store.downloads.length) }}</span>
        of <span class="font-medium text-foreground">{{ store.downloads.length }}</span>
      </p>
      <div class="flex items-center gap-1">
        <Button variant="outline" size="icon-sm" :disabled="downloadsPage === 1" aria-label="Previous page" @click="downloadsPage--">
          <Icon name="chevronLeft" class="h-4 w-4" />
        </Button>
        <button
          v-for="n in totalPages"
          :key="n"
          :class="['h-8 w-8 rounded-md text-xs font-medium transition-colors',
            n === downloadsPage ? 'bg-theme-medium text-white' : 'border border-input hover:bg-accent']"
          @click="downloadsPage = n"
        >{{ n }}</button>
        <Button variant="outline" size="icon-sm" :disabled="downloadsPage === totalPages" aria-label="Next page" @click="downloadsPage++">
          <Icon name="chevronRight" class="h-4 w-4" />
        </Button>
      </div>
    </div>
  </div>
</template>
