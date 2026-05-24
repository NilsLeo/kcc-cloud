<script setup lang="ts">
const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>();
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="props.modelValue"
    @click="emit('update:modelValue', !props.modelValue)"
    :class="['inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors', props.modelValue ? 'bg-theme-medium' : 'bg-input']"
  >
    <span :class="['inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform', props.modelValue ? 'translate-x-[18px]' : 'translate-x-[2px]']" />
  </button>
</template>
