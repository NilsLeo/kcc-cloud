<script setup lang="ts">
import { ref } from 'vue';
import Icon from '@/components/Icon.vue';
import Button from '@/components/ui/Button.vue';

const open = ref(false);
const title = ref('');
const body = ref('');
const submitting = ref(false);
const submitted = ref(false);

function submit() {
  submitting.value = true;
  setTimeout(() => {
    submitting.value = false;
    submitted.value = true;
  }, 700);
}
</script>

<template>
  <div class="rounded-lg border bg-card overflow-hidden">
    <div class="p-4 flex items-start gap-3 flex-col md:flex-row md:items-center">
      <div class="rounded-md bg-muted text-muted-foreground p-2 shrink-0">
        <Icon name="bug" class="h-4 w-4" />
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="font-poppins font-medium text-sm">Found a bug?</h3>
        <p class="text-xs text-muted-foreground">A short repro helps us fix it fast.</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <a
          href="https://github.com/NilsLeo/kcc-cloud/issues/new"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1.5 h-8 px-2.5 text-xs font-medium rounded-md border bg-background hover:bg-accent transition-colors"
        >
          <Icon name="github" class="h-3.5 w-3.5" /> Open on GitHub
        </a>
        <Button variant="outline" size="sm" @click="open = !open">
          <Icon name="bug" class="h-3.5 w-3.5" />
          {{ open ? 'Cancel' : 'Report here' }}
        </Button>
      </div>
    </div>
    <div v-if="open" class="border-t p-4 space-y-3 animate-slide-up">
      <div v-if="submitted" class="flex items-start gap-2 p-3 rounded-md bg-success/10 border border-success/30 text-sm">
        <Icon name="checkCircle" class="h-4 w-4 text-success mt-0.5 shrink-0" />
        <div>
          <div class="font-medium text-foreground">Bug report sent</div>
          <div class="text-muted-foreground text-xs">Thanks — we'll triage it shortly.</div>
        </div>
      </div>
      <form v-else class="space-y-3" @submit.prevent="submit">
        <div class="space-y-1.5">
          <label class="text-xs font-medium">Title</label>
          <input
            v-model="title"
            required
            placeholder="e.g. KFX output is missing the last page"
            class="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
          />
        </div>
        <div class="space-y-1.5">
          <label class="text-xs font-medium">Steps to reproduce</label>
          <textarea
            v-model="body"
            required
            rows="3"
            placeholder="1. Upload …  2. Pick device …  3. Convert …  4. See error: …"
            class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
          />
        </div>
        <div class="flex items-center justify-end">
          <Button variant="brand" size="sm" type="submit" :disabled="submitting">
            <Icon v-if="submitting" name="loader" class="h-3.5 w-3.5 animate-spin" />
            <Icon v-else name="send" class="h-3.5 w-3.5" />
            {{ submitting ? 'Sending…' : 'Submit report' }}
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>
