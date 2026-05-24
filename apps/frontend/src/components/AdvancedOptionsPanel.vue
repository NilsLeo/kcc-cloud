<script setup lang="ts">
import { ref, computed } from 'vue';
import Icon from '@/components/Icon.vue';
import Badge from '@/components/ui/Badge.vue';
import Switch from '@/components/ui/Switch.vue';
import { ADVANCED_SECTIONS } from '@/lib/advancedDefaults';

const props = defineProps<{
  options: Record<string, any>;
  deviceProfile: string;
}>();

const emit = defineEmits<{ (e: 'change', patch: Record<string, any>): void }>();

const openIdx = ref(0);
const isOther = computed(() => props.deviceProfile === 'Other' || props.deviceProfile === 'OTHER');

function set(k: string, v: any) {
  emit('change', { [k]: v });
}
</script>

<template>
  <div class="space-y-2">
    <div v-for="(section, i) in ADVANCED_SECTIONS" :key="section.title" class="rounded-lg border bg-card overflow-hidden">
      <button
        class="w-full flex items-center justify-between p-3.5 hover:bg-muted/40 transition-colors text-left"
        @click="openIdx = openIdx === i ? -1 : i"
      >
        <div class="flex items-center gap-2.5">
          <Icon :name="section.icon" class="h-4 w-4 text-theme-medium" />
          <span class="font-poppins font-medium text-sm">{{ section.title }}</span>
          <Badge variant="outline" class="text-[10px] py-0">{{ section.items.length }}</Badge>
          <Badge v-if="section.title === 'Custom profile' && isOther" variant="warn">Required</Badge>
        </div>
        <Icon name="chevronDown" :class="['h-4 w-4 transition-transform text-muted-foreground', openIdx === i && 'rotate-180']" />
      </button>
      <div v-if="openIdx === i" class="border-t p-4 space-y-3 animate-slide-up">
        <p v-if="section.note" class="text-xs text-muted-foreground italic">{{ section.note }}</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <template v-for="item in section.items" :key="item.k">
            <!-- toggle -->
            <label
              v-if="item.type === 'toggle'"
              class="flex items-start justify-between gap-3 p-2.5 rounded-md border bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
            >
              <div class="min-w-0">
                <div class="text-sm font-medium">{{ item.t }}</div>
                <div v-if="(item as any).s" class="text-xs text-muted-foreground">{{ (item as any).s }}</div>
              </div>
              <Switch :model-value="!!options[item.k]" @update:model-value="(v: boolean) => set(item.k, v)" />
            </label>

            <!-- select -->
            <div v-else-if="item.type === 'select'" class="p-2.5 rounded-md border bg-muted/30 space-y-1.5">
              <label class="text-sm font-medium block">{{ item.t }}</label>
              <select
                :value="options[item.k]"
                class="w-full h-8 rounded-md border border-input bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
                @change="(e) => {
                  const v = (e.target as HTMLSelectElement).value;
                  set(item.k, isNaN(+v) ? v : +v);
                }"
              >
                <option v-for="opt in (item as any).options" :key="opt[0]" :value="opt[0]">{{ opt[1] }}</option>
              </select>
            </div>

            <!-- number -->
            <div v-else-if="item.type === 'number'" class="p-2.5 rounded-md border bg-muted/30 space-y-1.5">
              <label class="text-sm font-medium block">
                {{ item.t }}
                <span v-if="(item as any).requiredForOther && isOther" class="text-destructive ml-0.5">*</span>
              </label>
              <div class="relative">
                <input
                  type="number"
                  :value="options[item.k]"
                  :class="['w-full h-8 rounded-md border bg-background px-2 pr-10 text-xs focus:outline-none focus:ring-2 focus:ring-theme-medium/40',
                    (item as any).requiredForOther && isOther && !options[item.k] ? 'border-amber-500/50' : 'border-input']"
                  @input="(e) => set(item.k, +(e.target as HTMLInputElement).value)"
                />
                <span v-if="(item as any).suffix" class="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-muted-foreground">{{ (item as any).suffix }}</span>
              </div>
            </div>

            <!-- slider -->
            <div v-else-if="item.type === 'slider'" class="p-2.5 rounded-md border bg-muted/30 space-y-1.5">
              <div class="flex items-baseline justify-between">
                <label class="text-sm font-medium">{{ item.t }}</label>
                <span class="text-xs font-mono text-muted-foreground">{{ Number(options[item.k]).toFixed((item as any).step < 1 ? 1 : 0) }}</span>
              </div>
              <input
                type="range"
                :min="(item as any).min"
                :max="(item as any).max"
                :step="(item as any).step"
                :value="options[item.k]"
                class="w-full accent-theme-medium"
                @input="(e) => set(item.k, +(e.target as HTMLInputElement).value)"
              />
            </div>

            <!-- text -->
            <div v-else-if="item.type === 'text'" class="p-2.5 rounded-md border bg-muted/30 space-y-1.5">
              <label class="text-sm font-medium block">{{ item.t }}</label>
              <input
                type="text"
                :value="options[item.k]"
                class="w-full h-8 rounded-md border border-input bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
                @input="(e) => set(item.k, (e.target as HTMLInputElement).value)"
              />
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
