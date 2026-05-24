<script setup lang="ts">
import Icon from '@/components/Icon.vue';
defineProps<{ mode: 'comic' | 'manga' }>();
</script>

<template>
  <section class="relative overflow-hidden rounded-xl border bg-gradient-to-br from-theme-medium/[0.04] via-background to-background">
    <div
      class="absolute inset-0 dotted-bg opacity-50 pointer-events-none"
      style="mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%); -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);"
    />

    <div class="relative grid md:grid-cols-[1fr_auto] gap-6 items-center p-6 md:p-10">
      <div class="max-w-xl">
        <h2 class="text-3xl md:text-5xl font-semibold font-poppins tracking-tight leading-[1.1]">
          <span class="text-foreground">{{ mode === 'manga' ? 'Manga' : 'Comics' }} to </span><span class="text-theme-medium">e-reader.</span>
        </h2>
        <p class="text-muted-foreground mt-3 md:text-base max-w-lg leading-relaxed">
          Drop a CBZ, CBR, PDF or EPUB — get back a perfectly-sized file for your Kindle, Kobo, or reMarkable. Right-to-left for manga, auto-cropping, panel splitting.
        </p>
        <div class="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
          <span class="inline-flex items-center gap-1.5"><Icon name="check" class="h-3.5 w-3.5 text-success" />30+ device profiles</span>
        </div>
      </div>

      <div class="hidden md:block relative w-[300px] h-[230px] -my-2" aria-hidden="true">
        <img
          v-if="mode === 'manga'"
          src="/manga-hero.png"
          alt="Open manga tankobon with action panels"
          class="w-full h-full object-contain drop-shadow-xl select-none"
          draggable="false"
        />
        <img
          v-else
          src="/comic-hero.png"
          alt="Stack of open comic books with KRAK! burst"
          class="w-full h-full object-contain drop-shadow-xl select-none"
          draggable="false"
        />
      </div>
    </div>
  </section>
</template>
