<script setup lang="ts">
import { cn } from '@/lib/utils';

type Variant = 'default' | 'outline' | 'success' | 'purple' | 'info' | 'warn' | 'danger';

const props = defineProps<{ variant?: Variant; class?: string }>();

const VARIANTS: Record<Variant, string> = {
  default: 'bg-primary text-primary-foreground border-transparent',
  outline: 'border-border text-foreground',
  success: 'bg-success text-success-foreground border-transparent',
  purple: 'bg-theme-medium/15 text-theme-dark dark:text-theme-light border-transparent',
  info: 'bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30',
  warn: 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30',
  danger: 'bg-destructive/10 text-destructive border-destructive/30',
};
</script>

<template>
  <span :class="cn('inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold gap-1', VARIANTS[props.variant ?? 'default'], props.class)">
    <slot />
  </span>
</template>
