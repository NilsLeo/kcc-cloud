<script setup lang="ts">
defineProps<{ class?: string }>();
</script>

<template>
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" :class="$props.class || 'h-8 w-8'">
    <defs>
      <linearGradient id="lg-bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="hsl(266 85% 66%)" />
        <stop offset="100%" stop-color="hsl(263 70% 38%)" />
      </linearGradient>
      <linearGradient id="lg-page" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#ffffff" />
        <stop offset="100%" stop-color="#f4f1ff" />
      </linearGradient>
    </defs>
    <rect width="40" height="40" rx="10" fill="url(#lg-bg)" />
    <path d="M11 11 h13 a2 2 0 0 1 2 2 v16 a2 2 0 0 1 -2 2 H11 a2 2 0 0 1 -2 -2 V13 a2 2 0 0 1 2 -2 z" fill="#ffffff" opacity="0.35" />
    <path d="M14 9 h11 l5 5 v15 a2 2 0 0 1 -2 2 H14 a2 2 0 0 1 -2 -2 V11 a2 2 0 0 1 2 -2 z" fill="url(#lg-page)" />
    <path d="M25 9 v3 a2 2 0 0 0 2 2 h3 z" fill="hsl(266 60% 88%)" />
    <path d="M15.5 19 h6 m0 0 -2 -2 m2 2 -2 2" stroke="hsl(263 70% 45%)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" fill="none" />
    <circle cx="24.5" cy="24" r="1.2" fill="hsl(263 70% 45%)" />
    <path d="M15.5 24 h5" stroke="hsl(263 70% 45%)" stroke-width="1.6" stroke-linecap="round" opacity="0.6" />
  </svg>
</template>
