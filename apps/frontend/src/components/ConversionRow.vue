<script setup lang="ts">
import Card from '@/components/ui/Card.vue';
import Badge from '@/components/ui/Badge.vue';
import Button from '@/components/ui/Button.vue';
import Icon from '@/components/Icon.vue';
import { fmtBytes, fmtTime, extIcon, deviceLabel } from '@/lib/formatters';
import type { QueueItem } from '@/store';

defineProps<{ item: QueueItem }>();
defineEmits<{
  (e: 'cancel', item: QueueItem): void;
  (e: 'dismiss', item: QueueItem): void;
  (e: 'download', item: QueueItem): void;
  (e: 'retry', item: QueueItem): void;
}>();

type StatusMeta = { label: string; badge: 'info' | 'purple' | 'success' | 'danger'; barColor: string; dot: string };
const STATUS: Record<string, StatusMeta> = {
  UPLOADING: { label: 'Uploading', badge: 'info', barColor: 'bg-sky-500', dot: 'bg-sky-500' },
  QUEUED: { label: 'Queued', badge: 'purple', barColor: 'bg-theme-light', dot: 'bg-theme-light' },
  PROCESSING: { label: 'Converting', badge: 'purple', barColor: 'bg-theme-medium', dot: 'bg-theme-medium' },
  COMPLETE: { label: 'Complete', badge: 'success', barColor: 'bg-success', dot: 'bg-success' },
  ERRORED: { label: 'Failed', badge: 'danger', barColor: 'bg-destructive', dot: 'bg-destructive' },
};

defineOptions({ name: 'ConversionRow' });
</script>

<template>
  <Card
    :class="[
      'transition-all',
      item.status === 'COMPLETE' && 'border-success/40 bg-success/[0.03]',
      item.status === 'ERRORED' && 'border-destructive/40 bg-destructive/[0.03]',
    ]"
  >
    <div class="p-4 md:p-5 flex items-start gap-3 md:gap-4">
      <div
        :class="[
          'shrink-0 h-11 w-11 md:h-12 md:w-12 rounded-lg flex items-center justify-center',
          item.status === 'COMPLETE' ? 'bg-success/15 text-success'
            : item.status === 'ERRORED' ? 'bg-destructive/15 text-destructive'
              : item.status === 'UPLOADING' ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
                : 'bg-theme-medium/10 text-theme-medium',
        ]"
      >
        <Icon :name="item.status === 'UPLOADING' ? 'upload' : extIcon(item.name)" class="h-5 w-5 md:h-6 md:w-6" />
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h4 class="font-poppins font-medium text-sm md:text-base truncate">
                {{ item.status === 'COMPLETE' && item.convertedName ? item.convertedName : item.name }}
              </h4>
              <Badge :variant="STATUS[item.status].badge">
                <span :class="['h-1.5 w-1.5 rounded-full', STATUS[item.status].dot, (item.status === 'UPLOADING' || item.status === 'PROCESSING') && 'animate-pulse']" />
                {{ STATUS[item.status].label }}
              </Badge>
            </div>
            <div class="flex items-center gap-x-3 gap-y-1 mt-1 text-xs text-muted-foreground flex-wrap">
              <span>{{ fmtBytes(item.size) }}</span>
              <template v-if="item.deviceProfile">
                <span>·</span>
                <span class="inline-flex items-center gap-1"><Icon name="smartphone" class="h-3 w-3" />{{ deviceLabel(item.deviceProfile) }}</span>
              </template>
              <template v-if="item.outputFormat">
                <span>·</span>
                <span class="font-medium text-foreground">{{ item.outputFormat }}</span>
              </template>
              <template v-if="item.status === 'COMPLETE' && item.duration">
                <span>·</span>
                <span class="inline-flex items-center gap-1"><Icon name="clock" class="h-3 w-3" />{{ fmtTime(item.duration) }}</span>
              </template>
            </div>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <Button v-if="item.status === 'COMPLETE'" variant="brand" size="sm" @click="$emit('download', item)">
              <Icon name="download" class="h-3.5 w-3.5" />Download
            </Button>
            <Button v-if="item.status === 'ERRORED'" variant="outline" size="sm" @click="$emit('retry', item)">Retry</Button>
            <Button
              variant="ghost"
              size="icon-sm"
              class="text-muted-foreground hover:text-foreground"
              @click="(item.status === 'COMPLETE' || item.status === 'ERRORED') ? $emit('dismiss', item) : $emit('cancel', item)"
            >
              <Icon name="x" class="h-4 w-4" />
            </Button>
          </div>
        </div>

        <!-- UPLOADING -->
        <div v-if="item.status === 'UPLOADING'" class="mt-3 px-3 py-2 rounded-md border border-sky-500/30 bg-sky-500/[0.04]">
          <div class="flex items-center justify-between text-[11px] mb-1.5">
            <span class="inline-flex items-center gap-1.5 font-medium text-sky-700 dark:text-sky-300">
              <Icon name="upload" class="h-3 w-3" /> Uploading to server
            </span>
            <span class="font-mono tabular-nums text-foreground font-medium">{{ Math.round(item.progress) }}%</span>
          </div>
          <div class="relative h-1.5 rounded-full overflow-hidden bg-sky-500/10">
            <div v-if="item.confirmedProgress != null" class="absolute inset-y-0 left-0 bg-sky-600 transition-all" :style="{ width: Math.min(100, item.confirmedProgress) + '%' }" />
            <div class="absolute inset-y-0 left-0 bg-sky-400/70 transition-all" :style="{ width: Math.min(100, item.progress) + '%' }">
              <div class="h-full w-full progress-shimmer animate-shimmer" />
            </div>
          </div>
          <div class="flex items-center justify-between mt-1 text-[11px] text-muted-foreground">
            <span>{{ fmtBytes(item.size * item.progress / 100) }} of {{ fmtBytes(item.size) }}</span>
            <span v-if="item.confirmedProgress != null && item.confirmedProgress < item.progress" class="font-mono text-[10px]">{{ Math.round(item.confirmedProgress) }}% confirmed</span>
          </div>
        </div>

        <!-- QUEUED / PROCESSING -->
        <div v-else-if="item.status === 'QUEUED' || item.status === 'PROCESSING'" class="mt-3">
          <div class="relative h-1.5 rounded-full overflow-hidden bg-muted">
            <div
              v-if="item.status !== 'QUEUED'"
              :class="['absolute inset-y-0 left-0 transition-all', STATUS[item.status].barColor]"
              :style="{ width: Math.min(100, item.progress) + '%' }"
            >
              <div class="h-full w-full progress-shimmer animate-shimmer" />
            </div>
            <div v-else class="absolute inset-0 bg-theme-light/30">
              <div class="h-full w-1/3 bg-theme-medium/80 progress-shimmer animate-shimmer rounded-full" />
            </div>
          </div>
          <div class="flex items-center justify-between mt-1.5 text-xs">
            <span class="text-muted-foreground">
              <template v-if="item.status === 'QUEUED'">Waiting for a worker…</template>
              <template v-else>{{ item.statusDetail || 'Processing pages…' }}</template>
            </span>
            <span class="font-mono tabular-nums text-foreground font-medium">
              <template v-if="item.status === 'QUEUED'">—</template>
              <template v-else>{{ Math.round(item.progress) }}%</template>
              <span v-if="item.eta && item.status === 'PROCESSING'" class="text-muted-foreground font-normal ml-2">ETA {{ fmtTime(item.eta) }}</span>
            </span>
          </div>
        </div>

        <!-- COMPLETE summary -->
        <div v-if="item.status === 'COMPLETE'" class="mt-3 flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
          <span>Input: <span class="font-mono text-foreground">{{ fmtBytes(item.size) }}</span></span>
          <span>→</span>
          <span>Output: <span class="font-mono text-foreground">{{ fmtBytes(item.outputSize) }}</span></span>
        </div>

        <!-- ERRORED message -->
        <div v-if="item.status === 'ERRORED'" class="mt-3 text-xs text-destructive bg-destructive/5 rounded-md p-2 border border-destructive/20">
          {{ item.error || 'Conversion failed. Try a different file or adjust your settings.' }}
        </div>
      </div>
    </div>
  </Card>
</template>
