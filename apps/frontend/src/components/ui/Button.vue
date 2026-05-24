<script setup lang="ts">
import { cn } from '@/lib/utils'
import { buttonVariants } from './button'
import type { VariantProps } from 'class-variance-authority'

const props = withDefaults(defineProps<{
  variant?: VariantProps<typeof buttonVariants>['variant']
  size?: VariantProps<typeof buttonVariants>['size']
  class?: string
  as?: string
}>(), { as: 'button' })
</script>
<template>
  <component :is="as" :class="cn(buttonVariants({ variant: props.variant, size: props.size }), props.class)">
    <slot />
  </component>
</template>
